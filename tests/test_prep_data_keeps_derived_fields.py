"""``prep_data`` must not destroy the columns only ``processed`` holds.

``prep_data('all')`` rebuilds ``processed`` from ``raw``. It carried Cluster
and Cluster-score columns across and regenerated computed ratios, but
**Calculated, PCA score and Stoichiometry columns were simply dropped** --
and with them their whole ``data_type``, which is what
``AppData.field_dict`` is built from. So every field-type dropdown lost the
entry as well: the fields became unplottable *and* unselectable, with no
error anywhere.

The trigger is ordinary. ``update_norm`` with no ``field`` -- changing the
scale for all analytes at once -- calls ``prep_data('all')``, as does a
change of outlier or negative-handling method. Calculate a field, then touch
any of those, and the field is gone.

Carried, not recomputed: the values may be stale against inputs the same
call has just re-preprocessed. Recomputing a Calculated field from its
``formula`` needs the calculator, which ``apply_processing_state`` reaches
through an injected ``field_calculator`` and this method cannot.
"""
import numpy as np
import pytest


@pytest.fixture
def sample_with_derived_fields(loaded_window, dialogs):
    """A loaded sample carrying one column of every derived type."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    sample = window.data['RM01']
    n = len(sample.processed)

    sample.add_columns('Calculated', 'Eu*', np.linspace(0.1, 0.9, n))
    sample.add_columns('PCA score', ['PC1', 'PC2'], np.ones((n, 2)))
    sample.add_columns('Stoichiometry', ['Grt_X', 'Grt_dominant'],
                       np.column_stack([np.full(n, 2.97), np.full(n, 2.0)]))
    sample.add_columns('Cluster', 'k-means', np.zeros(n))
    sample.add_columns('Cluster score', 'k-means score', np.zeros(n))
    return window, sample


def types_present(sample):
    return set(sample.processed.get_attribute_dict('data_type'))


DERIVED = ['Calculated', 'PCA score', 'Stoichiometry', 'Cluster', 'Cluster score']


def test_prep_data_keeps_every_derived_field_type(sample_with_derived_fields):
    _window, sample = sample_with_derived_fields
    assert DERIVED[0] in types_present(sample)

    sample.prep_data('all')

    missing = [t for t in DERIVED if t not in types_present(sample)]
    assert missing == [], f"prep_data dropped {missing}"


@pytest.mark.parametrize("column", ['Eu*', 'PC1', 'Grt_X', 'Grt_dominant', 'k-means'])
def test_the_columns_themselves_survive(sample_with_derived_fields, column):
    _window, sample = sample_with_derived_fields
    sample.prep_data('all')
    assert column in sample.processed.columns


def test_values_are_preserved(sample_with_derived_fields):
    _window, sample = sample_with_derived_fields
    before = sample.processed['Eu*'].values.copy()
    sample.prep_data('all')
    assert np.allclose(sample.processed['Eu*'].values, before, equal_nan=True)


def test_changing_the_scale_for_all_fields_does_not_lose_them(sample_with_derived_fields):
    """``update_norm`` with no ``field`` is the realistic way in."""
    _window, sample = sample_with_derived_fields
    sample.update_norm(norm='log')
    assert 'Calculated' in types_present(sample)
    assert 'Eu*' in sample.processed.columns


def test_the_field_type_stays_selectable(sample_with_derived_fields):
    """The user-visible symptom: 'Calculated' disappearing from every
    field-type dropdown, because field_dict is built from data_type."""
    window, sample = sample_with_derived_fields
    sample.prep_data('all')

    assert 'Calculated' in window.app_data.field_dict
    assert 'Eu*' in window.app_data.get_field_list('Calculated')
    assert 'Stoichiometry' in window.app_data.field_dict


def test_attributes_survive_too(sample_with_derived_fields):
    """A bare re-add would lose what makes these columns usable --
    the formula a Calculated field is rebuilt from on project load, and the
    discrete/category attributes that make Grt_dominant draw a swatch legend
    instead of a colour bar."""
    _window, sample = sample_with_derived_fields
    sample.processed.set_attribute('Eu*', 'formula', '{Analyte.Al27}*2')
    sample.processed.set_attribute('Grt_dominant', 'discrete', True)
    sample.processed.set_attribute('Grt_dominant', 'category_labels',
                                   ['pyrope', 'almandine'])
    sample.processed.set_attribute('Grt_X', 'units', 'apfu')

    sample.prep_data('all')

    assert sample.processed.get_attribute('Eu*', 'formula') == '{Analyte.Al27}*2'
    assert sample.processed.get_attribute('Grt_dominant', 'discrete') is True
    assert sample.processed.get_attribute('Grt_dominant', 'category_labels') == \
        ['pyrope', 'almandine']
    assert sample.processed.get_attribute('Grt_X', 'units') == 'apfu'


def test_a_second_calculated_field_does_not_disturb_the_first(loaded_window, dialogs,
                                                              monkeypatch):
    """How this was found: compute one field, compute another, and both the
    maps and the 'Calculated' dropdown entry were gone."""
    from PyQt6.QtWidgets import QInputDialog

    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.open_calculator()
    dock = window.calculator
    sample = window.data['RM01']

    names = iter(['Eu*', 'YHo'])
    monkeypatch.setattr(QInputDialog, 'getText',
                        staticmethod(lambda *a, **k: (next(names), True)))

    for formula in ['{Analyte.Al27}*2', '{Analyte.Fe57}/{Analyte.Ca43}']:
        dock.calc_text_edit.setPlainText(formula)
        dock.calculate_new_field()

    sample.prep_data('all')          # anything that re-preprocesses

    assert sorted(window.app_data.get_field_list('Calculated')) == ['Eu*', 'YHo']
