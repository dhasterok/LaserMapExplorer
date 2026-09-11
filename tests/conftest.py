"""Shared pytest fixtures.

Two groups live here:

* the original ``app``/``main_window``/``import_sample`` helpers, used by
  ``test_menubar.py``;
* the ``lame_*`` integration fixtures below, used by the MainWindow-driven
  integration tests (project save/close/reopen, dock teardown, menu wiring).
  Those were standalone ``.venv/bin/python <file>`` scripts until they were
  converted to pytest; the boilerplate every one of them repeated --
  QApplication setup, modal-dialog stubbing, building a sample file, and
  constructing a MainWindow -- is factored out here.
"""
import os

# Must be set before anything constructs a QApplication.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
# NB: don't import pytestqt here. The `qtbot` fixture comes from the
# pytest-qt *plugin*, which pytest loads on its own -- importing the module
# at conftest scope only adds a hard dependency that turns a missing (or
# wrong-environment) pytest-qt into an ImportError during conftest loading,
# which collects nothing and hides the real problem. Run the suite with this
# project's interpreter (`.venv/bin/pytest`), not whichever pytest is first
# on PATH.
from PyQt6.QtWidgets import QApplication, QFileDialog, QComboBox, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Shared OpenGL contexts must be requested before the QApplication exists;
# every converted script set this at import time for the same reason.
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

from main import MainWindow, create_app  # Import the create_app function


@pytest.fixture(scope='module')
def app():
    global app
    """Fixture for creating the QApplication."""
    app = create_app()
    return app

@pytest.fixture
def main_window(qtbot, app):
    """Fixture for creating the MainWindow."""
    main_window = MainWindow(app)
    qtbot.addWidget(main_window)
    return main_window

def import_sample(qtbot, main_window, mocker):
    # Mock the file dialog to return the desired directory
    mocker.patch.object(QFileDialog, 'getExistingDirectory', return_value='maps/Alex_garnet_maps/processed data')


    # Mock the exec method of QFileDialog to simulate the dialog being accepted
    mocker.patch.object(QFileDialog, 'exec', return_value=QFileDialog.DialogCode.Accepted)
    mocker.patch.object(QFileDialog, 'selectedFiles', return_value=['maps/Alex_garnet_maps/processed data/RM02.lame.csv'])

    # Find the action and trigger it
    action_open_sample = main_window.findChild(QAction, 'actionAddSampleFiles')


    # Manually trigger the QAction
    action_open_sample.trigger()

    # Allow any processing to complete
    qtbot.wait(100)

    # Allow any processing to complete
    #qtbot.mouseClick(main_window.menuBar().actionOpenDirectory, Qt.LeftButton)

    # Check if the comboBoxSampleId has the expected value
    combo_box_sample_id = main_window.findChild(QComboBox, 'comboBoxSampleId')

    assert combo_box_sample_id.currentText() == 'RM02'


# ---------------------------------------------------------------------------
# Integration fixtures (MainWindow-driven)
# ---------------------------------------------------------------------------

#: Analyte columns written into the synthetic sample, with plausible CPS
#: magnitudes so log scaling and autoscaling behave as they do on real data.
_SYNTHETIC_ANALYTES = {
    'Al27': (1e4, 1e5),
    'Ca43': (1e3, 1e4),
    'Fe57': (5e3, 5e4),
    'Sr88': (1e2, 1e3),
    'Zr90': (1e1, 1e3),
    'Ce140': (1e0, 1e2),
}


@pytest.fixture(scope='session')
def lame_app():
    """One QApplication shared by every MainWindow-driven integration test.

    Qt allows only one per process, so this is session-scoped and reuses an
    instance another fixture may already have built.
    """
    return QApplication.instance() or create_app()


@pytest.fixture(scope='session')
def synthetic_sample_csv(tmp_path_factory) -> Path:
    """A small, valid ``.lame.csv`` -- the template every sample copy is made from.

    The converted scripts all pointed at one particular 43 MB file outside
    the repo (``~/maps/processed data/RM01.lame.csv``), which made them
    unrunnable anywhere else and cost ~10 s per load. None of them depended
    on its contents -- they need "a sample that loads, with analytes to
    filter on" -- so they now build this instead: same schema (Xc/Yc, analyte
    columns, one ``a / b`` ratio column), a 40x30 grid, a few hundred KB.
    """
    path = tmp_path_factory.mktemp('lame_sample_template') / 'template.lame.csv'
    rng = np.random.default_rng(0)
    nx, ny = 40, 30
    xs, ys = np.meshgrid(np.arange(nx) * 10.0, np.arange(ny) * 10.0)
    columns = {'Xc': xs.ravel(), 'Yc': ys.ravel()}
    for analyte, (lo, hi) in _SYNTHETIC_ANALYTES.items():
        columns[analyte] = rng.uniform(lo, hi, nx * ny)
    # A ratio column, so 'Ratio'-typed fields exist too (see
    # DataHandling.reset_data's ' / ' name check).
    columns['Sr88 / Ca43'] = columns['Sr88'] / columns['Ca43']
    pd.DataFrame(columns).to_csv(path, index=False)
    return path


@pytest.fixture
def sample_factory(tmp_path, synthetic_sample_csv):
    """``make(name, subdir=None)`` -> a fresh ``<name>.lame.csv``.

    Each call returns an independent file under this test's tmp_path, so a
    test can add several samples and freely write sidecars or touch mtimes
    next to them. ``subdir`` puts the sample in its own directory, for the
    tests that specifically cover samples gathered from *different*
    directories into one project.
    """
    def make(name: str, subdir: str | None = None) -> Path:
        directory = tmp_path if subdir is None else tmp_path / subdir
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'{name}.lame.csv'
        shutil.copy(synthetic_sample_csv, path)
        return path
    return make


class DialogStub:
    """Answers the modal dialogs a headless test can't click.

    ``question`` drives every dirty-changes prompt (Save / Discard / Cancel)
    and ``save_filename`` the save-as dialog; a test sets whichever it needs
    before triggering the action under test.
    """

    def __init__(self):
        self.question = QMessageBox.StandardButton.Discard
        self.warning = QMessageBox.StandardButton.Discard
        self.information = QMessageBox.StandardButton.Ok
        self.save_filename = ''
        #: Args of every QMessageBox.information call, for tests that assert
        #: an action was *blocked* with a guidance dialog rather than silently
        #: doing nothing.
        self.information_calls = []


@pytest.fixture
def dialogs(monkeypatch) -> DialogStub:
    """Stub out QMessageBox/QFileDialog, returning a :class:`DialogStub`.

    monkeypatch undoes the patches at teardown, so -- unlike the scripts,
    which reassigned the staticmethods globally and left them replaced --
    one test's choice can't leak into the next.
    """
    stub = DialogStub()

    def record_information(*args, **kwargs):
        stub.information_calls.append(args)
        return stub.information

    monkeypatch.setattr(QMessageBox, 'question', staticmethod(lambda *a, **k: stub.question))
    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(lambda *a, **k: stub.warning))
    monkeypatch.setattr(QMessageBox, 'information', staticmethod(record_information))
    monkeypatch.setattr(QMessageBox, 'critical', staticmethod(lambda *a, **k: stub.information))
    monkeypatch.setattr(
        QFileDialog, 'getSaveFileName', staticmethod(lambda *a, **k: (str(stub.save_filename), ''))
    )
    return stub


@pytest.fixture
def lame_window(lame_app, dialogs):
    """A real MainWindow with its modal dialogs stubbed.

    Function-scoped: these tests mutate and tear down project state, so each
    gets its own window rather than inheriting whatever the last one left
    behind (the scripts ran as one long sequence and did inherit it).
    """
    window = MainWindow(lame_app)
    yield window
    try:
        window.close()
    except Exception:
        pass


@pytest.fixture
def loaded_window(lame_window, sample_factory):
    """``(window, sample_path)`` with one sample already added.

    ``add_samples()`` drives ``initialize_sample_object()`` synchronously, so
    the sample is fully loaded into ``window.data`` on return.
    """
    path = sample_factory('RM01')
    lame_window.project_manager.add_samples([path])
    return lame_window, path


def first_analyte(window, sample_id='RM01') -> str:
    """The first Analyte-typed field of a loaded sample."""
    return window.data[sample_id].processed.match_attribute('data_type', 'Analyte')[0]
