"""MapImporter's post-import success handler chains into
ProjectManager.add_samples(), not the old dead LameIO.open_directory() path.

Rather than driving MapImporter's full raw-instrument-data pipeline (a lot
of unrelated setup -- data_type/method dispatch, standards config, real
LA-ICP-MS files), these drive the real ``import_data()`` with the two
data-reading calls it makes (``get_metadata()``,
``import_la_icp_ms_data()``) stubbed to set exactly what a real successful
import would (``ok``, ``sample_ids``, ``root_path``). The tail logic under
test -- evict stale cache -> add_samples() -> reload if selected -- then
runs completely unmodified, exactly as shipped.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import pandas as pd
import pytest

from src.importers.MapImporter import MapImporter


@pytest.fixture
def import_factory(lame_window, sample_factory):
    """``make()`` -> a MapImporter that reports a successful RM01 import.

    The sample file is created up front, so ``add_samples()`` finds a real
    file at the path the stubbed import claims to have written.
    """
    path = sample_factory('RM01')

    def make():
        dialog = MapImporter(parent=lame_window)
        dialog.comboBoxDataType.setCurrentText('LA-ICP-MS')
        dialog.checkBoxSaveToRoot.setChecked(True)
        dialog.root_path = path.parent
        dialog.paths = [str(path.parent)]
        # A one-row stand-in for what get_metadata() reads out of the metadata
        # table. It has to be a real DataFrame with the columns the tail logic
        # touches -- save_import_settings() indexes 'Import' per sample and
        # stores the whole row in the sidecar -- not an empty dict.
        dialog.get_metadata = lambda: pd.DataFrame({
            'Import': [True],
            'Sample ID': ['RM01'],
            'Select files': [1],
            'Standard': [''],
            'Scan axis': ['Xc'],
            'Swap XY': [False],
            'Reverse X': [False],
            'Reverse Y': [False],
        })
        dialog.import_la_icp_ms_data = lambda save_path: (
            setattr(dialog, 'ok', True),
            setattr(dialog, 'sample_ids', ['RM01']),
        )
        return dialog

    return make, path


def test_successful_import_adds_the_sample_via_project_manager(lame_window, import_factory):
    """With no project open, this also has to create the untitled one."""
    make, path = import_factory
    pm = lame_window.project_manager
    assert pm.current_project is None

    make().import_data()

    assert pm.current_project is not None
    assert 'RM01' in pm.current_project.samples
    assert pm.current_project.samples['RM01'].sample_path == path.resolve()


def test_reimporting_evicts_the_stale_cached_sample_object(lame_window, import_factory):
    """Re-importing the same sample_ids leaves the identifiers unchanged, so
    neither AppData.sample_list's nor .sample_id's setter fires a change
    notification -- the cached SampleObj has to be evicted explicitly or the
    reimported file is never re-read."""
    make, _path = import_factory
    make().import_data()
    lame_window.app_data.sample_id = 'RM01'
    lame_window.change_sample()
    assert 'RM01' in lame_window.data
    old_sample_obj = lame_window.data['RM01']

    make().import_data()

    assert 'RM01' in lame_window.data
    assert lame_window.data['RM01'] is not old_sample_obj
