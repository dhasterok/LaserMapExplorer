"""Paged toolbar (pinned row + pages), the View menu, and the status bar's
Notes/Workflow recording IndicatorLights.

The per-page action lists below pin the *current* layout. They were stale
when this file was converted from a script -- the toolbar had since moved
'Add Plot to Tree' to the pinned row and reworked the Processing page --
which the script never reported, because it was never run by pytest.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import pytest
from PyQt6.QtCore import Qt

#: Page name -> its actions, in order.
PAGE_ACTIONS = {
    'Home': ['Open Project', 'Add Samples', 'Import Files', 'Help', 'Theme'],
    'Plot': ['Full Map', 'Crop', 'Swap Axes', 'Correlation', 'Histogram',
             'Scatter Plot', 'Ternary Plot', 'TEC Plot', 'Radar Plot'],
    # 'Clusers' is a typo in the UI itself, pinned here as-is so this test
    # tracks the toolbar rather than asserting what it ought to say.
    'Processing': ['Noise Reduction', 'Filters', 'ROI', 'Polygons', 'Clusers'],
    'Log': ['Notes', 'Record', 'Workflow', 'Capture', 'Snapshot'],
    'Analysis': ['Calculator', 'Regression', 'Dimensional Reduction', 'Cluster',
                 'Geochronology', 'Profiles', 'Diffusion', 'Stoichiometry'],
}


def action_texts(toolbar):
    """Visible action labels, newlines flattened, separators/spacers dropped."""
    return [a.text().replace('\n', ' ') for a in toolbar.actions()
            if not a.isSeparator() and a.text()]


@pytest.fixture
def shown_window(lame_window):
    """A shown window -- isVisible() reflects the whole ancestor chain, not a
    widget's own state, so the toolbar checks need this."""
    lame_window.show()
    return lame_window


@pytest.fixture
def paged(shown_window):
    return shown_window.toolbar.paged


def test_pinned_row_has_the_expected_actions(paged):
    texts = action_texts(paged.pinned_bar)
    assert 'Analytes' in texts
    assert 'Update Plot' in texts
    assert 'Save Project' in texts
    assert 'Add Plot to Tree' in texts


def test_capture_is_always_visible(shown_window):
    """Capture lives on the Log page and in the Workflow menu, not the pinned
    row, but must always be visible/clickable: clicking it while off is what
    creates and links a workflow file in the first place, so it can't be
    gated behind a workflow already being active. The Workflow
    IndicatorLight is the actual "is recording happening" signal."""
    assert shown_window.lame_action.CaptureToggle.isVisible()


def test_all_five_pages_are_registered(paged):
    assert paged.pages.count() == 5
    assert set(paged._page_names) == set(PAGE_ACTIONS)


@pytest.mark.parametrize("page_name, expected", sorted(PAGE_ACTIONS.items()))
def test_page_actions(paged, page_name, expected):
    widget = paged.pages.widget(paged._page_names.index(page_name))
    assert action_texts(widget) == expected


def test_set_current_page_switches_the_visible_page(paged):
    assert paged.current_page_name() == 'Home'

    paged.set_current_page('Plot')

    assert paged.current_page_name() == 'Plot'
    assert paged.pages.currentIndex() == paged._page_names.index('Plot')


def test_content_row_height_is_fixed_across_pages(paged):
    """A bounded toolbar footprint -- switching pages must not resize it."""
    paged.set_current_page('Home')
    height_home = paged.pages.height()

    paged.set_current_page('Processing')

    assert paged.pages.height() == height_home


@pytest.mark.parametrize("has_file, recording, expected", [
    # No file loaded reads as 'no_file' regardless of the capture toggle.
    (False, True, 'no_file'),
    (True, True, 'recording'),
    (True, False, 'idle'),
])
def test_workflow_indicator_light(shown_window, has_file, recording, expected):
    shown_window.statusbar.set_workflow_status(has_file=has_file, recording=recording)
    assert shown_window.statusbar.workflowLight.status == expected


@pytest.mark.parametrize("has_file, recording, expected", [
    (False, True, 'no_file'),
    (True, True, 'recording'),
    (True, False, 'idle'),
])
def test_notes_indicator_light(shown_window, has_file, recording, expected):
    shown_window.statusbar.set_notes_status(has_file=has_file, recording=recording)
    assert shown_window.statusbar.notesLight.status == expected


def test_sample_id_combobox_surface_is_preserved(shown_window):
    """tests/test_menu_wiring.py depends on this surface."""
    assert hasattr(shown_window.toolbar, 'comboBoxSampleId')
    assert hasattr(shown_window.toolbar, 'update_sample_id')


def test_view_menu_only_has_the_show_button_text_toggle(shown_window):
    """The old grouped-toolbar entries are gone."""
    assert [a.text() for a in shown_window.menu_bar.menuView.actions()] == ['Show Button Text']


def test_show_button_text_toggles_icon_only_across_pinned_row_and_pages(shown_window, paged):
    assert shown_window.lame_action.ShowToolbarText.isChecked()
    assert paged.pinned_bar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon

    shown_window.lame_action.ShowToolbarText.setChecked(False)

    assert paged.pinned_bar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    for i in range(paged.pages.count()):
        assert paged.pages.widget(i).toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly

    shown_window.lame_action.ShowToolbarText.setChecked(True)

    assert paged.pinned_bar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon


def test_creating_a_project_auto_advances_to_the_plot_page(shown_window, paged):
    paged.set_current_page('Home')
    assert paged.current_page_name() == 'Home'

    shown_window.project_manager.new_project()

    assert paged.current_page_name() == 'Plot'
