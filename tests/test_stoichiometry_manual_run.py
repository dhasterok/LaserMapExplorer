"""The stoichiometry dock computes only when Run is clicked.

Every settings widget used to be wired straight to ``calculate``, so picking
an input basis, a redox method, a BDL treatment or a scope region ran the
whole pipeline and *wrote mineral-formula columns back into the sample*.
Those writes use ``merge=True``, so they are not undone by changing the
setting back: a user working their way towards the combination they wanted
left a trail of partial results in the data on the way.

A debounce timer used to stand between the region list and ``calculate`` to
blunt the worst of it. With the run under the user's control that timer has
nothing left to do, so it is gone.

Settings changes now only mark the displayed results stale.
"""
import pytest
from PyQt6.QtWidgets import QMainWindow

import src.stoichiometry.dock as dock_module
from src.stoichiometry.dock import StoichiometryDock


@pytest.fixture
def counting_dock(qapp, monkeypatch):
    """``(dock, calls)`` where ``calls`` records every ``calculate()`` call.

    Patched on the class *before* construction, so the signal connections
    made in ``connect_widgets`` bind to the counter.
    """
    calls = []
    monkeypatch.setattr(StoichiometryDock, 'calculate',
                        lambda self, *args: calls.append(args))

    parent = QMainWindow()
    parent.show()
    dock = StoichiometryDock(parent)
    yield dock, calls
    parent.close()


def test_opening_the_dock_computes_nothing(counting_dock):
    _dock, calls = counting_dock
    assert calls == []


def test_showing_the_dock_again_computes_nothing(counting_dock):
    """``showEvent`` refreshes the region lists; it must not run the pipeline."""
    dock, calls = counting_dock
    dock.hide()
    dock.show()
    assert calls == []


@pytest.mark.parametrize("widget_name,action", [
    ('analyte_units_combobox', lambda w: w.setCurrentIndex(1)),
    ('comboBoxLodTreatment', lambda w: w.setCurrentIndex(2)),
    ('checkBoxCompareRedox', lambda w: w.setChecked(True)),
    ('minerals_combobox', lambda w: w.setCurrentIndex(1)),
])
def test_changing_a_setting_does_not_compute(counting_dock, widget_name, action):
    dock, calls = counting_dock
    action(getattr(dock, widget_name))
    assert calls == []
    assert dock._results_stale is True


def test_changing_the_scope_column_does_not_compute(counting_dock):
    dock, calls = counting_dock
    dock.filter_combobox.setCurrentIndex(0)
    dock._on_scope_column_changed()
    assert calls == []
    assert dock._results_stale is True


def test_run_is_the_only_thing_that_computes(counting_dock):
    dock, calls = counting_dock
    dock.analyte_units_combobox.setCurrentIndex(1)
    dock.checkBoxCompareRedox.setChecked(True)
    assert calls == []

    dock.run_action.trigger()
    assert len(calls) == 1


def test_nothing_is_connected_to_calculate_but_the_run_action(qapp):
    """A guard against the next widget being wired up the old way."""
    import inspect
    source = inspect.getsource(StoichiometryDock.connect_widgets)
    connected = [line.strip() for line in source.splitlines()
                 if 'connect(self.calculate)' in line]
    assert connected == ['self.run_action.triggered.connect(self.calculate)']


def test_the_debounce_timer_is_gone(qapp):
    """It existed only to limit how often a settings change recomputed."""
    assert 'QTimer' not in inspect_source()
    assert '_scope_debounce' not in inspect_source()


def inspect_source():
    import inspect
    return inspect.getsource(dock_module)


# --- what the user is told ---------------------------------------------------

@pytest.fixture
def garnet_window(lame_window, tmp_path):
    """A real window holding a sample garnet's config can actually resolve.

    The shared synthetic sample has no Si, Mg or Mn, so ``_resolve_columns``
    finds nothing and ``calculate`` bails before writing anything -- which
    would make this test pass against the old behaviour too.
    """
    import numpy as np
    import pandas as pd

    nx, ny = 12, 10
    xs, ys = np.meshgrid(np.arange(nx) * 10.0, np.arange(ny) * 10.0)
    n = nx * ny
    rng = np.random.default_rng(0)
    # ppm, roughly almandine
    frame = {'Xc': xs.ravel(), 'Yc': ys.ravel()}
    for name, centre in [('Si29', 180000.), ('Al27', 110000.), ('Fe57', 250000.),
                         ('Mg24', 15000.), ('Mn55', 5000.), ('Ca43', 15000.)]:
        frame[name] = rng.normal(centre, centre * 0.02, n)
    path = tmp_path / 'GRT01.lame.csv'
    pd.DataFrame(frame).to_csv(path, index=False)

    lame_window.project_manager.add_samples([path])
    lame_window.app_data.sample_id = 'GRT01'
    lame_window.change_sample()
    return lame_window


def mineral_columns(sample):
    return [c for c in sample.processed.columns if c.startswith('Grt_')]


def test_settings_changes_write_nothing_into_the_sample(garnet_window):
    """The point of the change, against a real window and a sample the
    pipeline can actually run on: nothing reaches the data until Run."""
    window = garnet_window
    sample = window.data['GRT01']
    assert mineral_columns(sample) == []

    window.open_stoichiometry_dock()
    dock = window.stoichiometry_dock

    dock.analyte_units_combobox.setCurrentIndex(1)
    dock.analyte_units_combobox.setCurrentIndex(0)
    dock.comboBoxLodTreatment.setCurrentIndex(2)
    dock.checkBoxCompareRedox.setChecked(True)
    dock.hide()
    dock.show()

    assert mineral_columns(sample) == [], "a settings change wrote to the sample"
    assert dock._results_stale is True


def test_run_writes_the_mineral_columns(garnet_window):
    """...and Run still does the whole job."""
    window = garnet_window
    sample = window.data['GRT01']
    window.open_stoichiometry_dock()
    dock = window.stoichiometry_dock

    dock.run_action.trigger()

    written = mineral_columns(sample)
    assert 'Grt_dominant' in written, written
    assert dock._results_stale is False
    assert StoichiometryDock._STALE_NOTICE not in dock.textEditResults.toPlainText()


def test_the_dock_opens_telling_you_to_click_run(counting_dock):
    dock, _calls = counting_dock
    assert dock.textEditResults.toPlainText() == StoichiometryDock._RUN_PROMPT


def test_stale_results_are_labelled_rather_than_cleared(counting_dock):
    """The previous run's numbers stay on screen -- they are still the last
    thing that was actually computed -- with a line saying so."""
    dock, _calls = counting_dock
    dock._last_results = {
        'mineral': 'garnet', 'mineral_abbreviation': 'Grt', 'scope': 'All pixels',
        'input_mode': 'ppm', 'redox_method': 'none', 'lod_treatment': 'zero',
        'n_pixels': 1234, 'endmember_members': ['pyrope', 'almandine'],
    }

    dock._results_stale = False
    dock._update_results_text()
    fresh = dock.textEditResults.toPlainText()
    assert StoichiometryDock._STALE_NOTICE not in fresh
    assert 'Pixels calculated: 1234' in fresh

    dock._mark_stale()
    stale = dock.textEditResults.toPlainText()
    assert stale.startswith(StoichiometryDock._STALE_NOTICE)
    assert 'Pixels calculated: 1234' in stale
