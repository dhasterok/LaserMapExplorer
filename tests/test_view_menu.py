"""Headless check: paged toolbar (pinned row + pages) and the status bar's
workflow-capture lamp.

Run: .venv/bin/python <this file>
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

project_root = Path("/Users/dhasterok/Documents/GitHub/LaserMapExplorer")
sys.path.insert(0, str(project_root))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

app = QApplication(sys.argv)

import src.app.config  # noqa: F401

from src.app.MainWindow import MainWindow

win = MainWindow(app)
win.show()  # isVisible() reflects the whole ancestor chain, not just a widget's own state
tb = win.toolbar
paged = tb.paged

# ------------------------------------------------------------------
# Pinned row has the expected actions. Capture itself lives on the Log page
# and in the Workflow menu, not the pinned row -- but it must always be
# visible/clickable there (clicking it while off is what creates/links a
# workflow file in the first place, so it can't be gated behind a workflow
# already being active); the WorkflowLamp on the status bar is the actual
# "is recording happening" indicator.
# ------------------------------------------------------------------
def action_texts(toolbar):
    return [a.text().replace('\n', ' ') for a in toolbar.actions() if not a.isSeparator()]

pinned_texts = action_texts(paged.pinned_bar)
assert 'Analytes' in pinned_texts
assert 'Update Plot' in pinned_texts
assert 'Save Project' in pinned_texts
assert win.lame_action.CaptureToggle.isVisible(), "Capture should always be visible/clickable"
print("PASS: pinned row has the expected actions, Capture is always visible")

# ------------------------------------------------------------------
# Five pages exist with the expected actions
# ------------------------------------------------------------------
assert paged.pages.count() == 5
for name in ('Home', 'Plot', 'Processing', 'Log', 'Analysis'):
    assert name in paged._page_names, f"missing page {name!r}"
print("PASS: all 5 pages are registered (Home, Plot, Processing, Log, Analysis)")

def page_texts(name):
    return action_texts(paged.pages.widget(paged._page_names.index(name)))

assert page_texts('Plot') == [
    'Add Plot to Tree', 'Full Map', 'Crop', 'Swap Axes',
    'Correlation', 'Histogram', 'Scatter Plot', 'Ternary Plot', 'TEC Plot', 'Radar Plot',
], page_texts('Plot')
assert page_texts('Processing') == ['Noise Reduction', 'Filters', 'Filter', 'Polygons', 'Clusers', 'ROI'], page_texts('Processing')
assert page_texts('Log') == ['Notes', 'Workflow', 'Capture', 'Snapshot'], page_texts('Log')
assert page_texts('Analysis') == [
    'Calculator', 'Regression', 'Dimensional Reduction', 'Cluster', 'Geochronology', 'Profiles', 'Diffusion', 'Stoichiometry',
], page_texts('Analysis')
print("PASS: Plot/Processing/Log/Analysis pages have the expected actions in order")

# ------------------------------------------------------------------
# Page tabs actually switch the stacked widget's current page
# ------------------------------------------------------------------
assert paged.current_page_name() == 'Home'
paged.set_current_page('Plot')
assert paged.current_page_name() == 'Plot'
assert paged.pages.currentIndex() == paged._page_names.index('Plot')
print("PASS: set_current_page() switches the visible page")

# ------------------------------------------------------------------
# Persistent toolbar height doesn't change across pages (bounded footprint)
# ------------------------------------------------------------------
height_home = paged.pages.height()
paged.set_current_page('Processing')
height_processing = paged.pages.height()
assert height_home == height_processing, (height_home, height_processing)
print("PASS: content row height is fixed across pages")

# ------------------------------------------------------------------
# WorkflowLamp on the status bar reflects actual capture state, not
# whether a workflow file happens to be active
# ------------------------------------------------------------------
win.statusbar.set_capture_status(True)
assert 'e02020' in win.statusbar.workflowLamp.styleSheet(), win.statusbar.workflowLamp.styleSheet()

win.statusbar.set_capture_status(False)
assert 'a0a0a0' in win.statusbar.workflowLamp.styleSheet(), win.statusbar.workflowLamp.styleSheet()
print("PASS: WorkflowLamp reflects capture on/off")

# ------------------------------------------------------------------
# comboBoxSampleId / update_sample_id still work as external code expects
# (tests/test_menu_wiring.py depends on this surface)
# ------------------------------------------------------------------
assert hasattr(tb, 'comboBoxSampleId')
assert hasattr(tb, 'update_sample_id')
print("PASS: comboBoxSampleId / update_sample_id preserved")

# ------------------------------------------------------------------
# View menu no longer references the old grouped toolbars, just the text
# style toggle
# ------------------------------------------------------------------
view_actions = win.menu_bar.menuView.actions()
assert [a.text() for a in view_actions] == ['Show Button Text'], [a.text() for a in view_actions]
print("PASS: View menu only has the Show Button Text toggle")

# ------------------------------------------------------------------
# Show Button Text toggle switches pinned row + every page between
# icon+text and icon-only (page tabs stay text-only either way)
# ------------------------------------------------------------------
assert win.lame_action.ShowToolbarText.isChecked()
assert paged.pinned_bar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon

win.lame_action.ShowToolbarText.setChecked(False)
assert paged.pinned_bar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
for i in range(paged.pages.count()):
    assert paged.pages.widget(i).toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly

win.lame_action.ShowToolbarText.setChecked(True)
assert paged.pinned_bar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextUnderIcon
print("PASS: 'Show Button Text' toggles icon-only vs icon+text across pinned row and pages")

# ------------------------------------------------------------------
# Auto-advance to Plot page when a project is loaded
# ------------------------------------------------------------------
paged.set_current_page('Home')
assert paged.current_page_name() == 'Home'
win.project_manager.new_project()
assert paged.current_page_name() == 'Plot', "opening/creating a project should auto-advance to the Plot page"
print("PASS: creating a project auto-advances the toolbar to the Plot page")

print("\nALL paged-toolbar TESTS PASSED")
