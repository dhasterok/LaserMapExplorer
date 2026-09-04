from PyQt6.QtWidgets import QStatusBar, QLabel
from lame_core.CustomWidgets import CustomToolButton, IndicatorLight

# Shared by both the Notes and Workflow status-bar lights (see
# MainWindow._refresh_notes_indicator/_refresh_workflow_indicator, which
# resolve each dock's current file-loaded/recording state to one of these
# keys and push it via set_notes_status/set_workflow_status below).
RECORDING_STATUS_DICT = {
    'no_file':   {'tip_text': 'No file loaded', 'color': '#888888'},
    'idle':      {'tip_text': 'Not recording',  'color': '#DAA520'},  # goldenrod
    'recording': {'tip_text': 'Recording',      'color': '#e02020'},
}


class MainStatusBar(QStatusBar):
    def __init__(self, ui=None):
        super().__init__(ui)

        self.ui = ui

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
        self.setObjectName("statusbar")

        # Add the button to the status bar
        self.labelInvalidValues = QLabel("Negative/zeros: False, NaNs: False")
        self.addPermanentWidget(self.labelInvalidValues)

        # Create a button to hide/show the dock
        self.toolButtonLeftDock = CustomToolButton(
            text="Left Dock",
            light_icon_unchecked='icon-left-toolbar-hide-64.svg',
            light_icon_checked='icon-left-toolbar-show-64.svg',
            parent=self
        )
        self.toolButtonLeftDock.setChecked(True)
        self.toolButtonLeftDock.setToolTip("Show or hide the left dock")
        self.toolButtonRightDock = CustomToolButton(
            text="Right Dock",
            light_icon_unchecked='icon-right-toolbar-hide-64.svg',
            light_icon_checked='icon-right-toolbar-show-64.svg',
            parent=self
        )
        self.toolButtonRightDock.setChecked(True)
        self.toolButtonRightDock.setToolTip("Show or hide the right dock")
        self.toolButtonBottomDock = CustomToolButton(
            text="BottomDock",
            light_icon_unchecked='icon-bottom-toolbar-hide-64.svg',
            light_icon_checked='icon-bottom-toolbar-show-64.svg',
            parent=self
        )
        self.toolButtonBottomDock.setChecked(True)
        self.toolButtonBottomDock.setToolTip("Show or hide the bottom dock")

        self.addPermanentWidget(self.toolButtonLeftDock)
        self.addPermanentWidget(self.toolButtonBottomDock)
        self.addPermanentWidget(self.toolButtonRightDock)

        # Notes/Workflow recording indicators -- added last so they land at
        # the far right of the status bar (each addPermanentWidget call
        # inserts further right than the previous one). Gray = no file
        # loaded, golden = file loaded but not recording, red = recording;
        # see MainWindow._refresh_notes_indicator/_refresh_workflow_indicator
        # for what drives each state.
        self.notesLight = IndicatorLight(
            status_dict=RECORDING_STATUS_DICT, status='no_file',
            label='Notes', label_position='right', size=14, parent=self,
        )
        self.workflowLight = IndicatorLight(
            status_dict=RECORDING_STATUS_DICT, status='no_file',
            label='Workflow', label_position='right', size=14, parent=self,
        )
        self.addPermanentWidget(self.notesLight)
        self.addPermanentWidget(self.workflowLight)

    def connect_widgets(self):
        # dockWidgetLeftToolbox/dockWidgetStyling are just the Qt objectNames of
        # these docks (see ControlDock/StylingDock) - the actual Python
        # references live on MainWindow, deferred via lambda since neither dock
        # exists yet when MainStatusBar is constructed (see MainWindow.setupUI).
        self.toolButtonLeftDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.ui.control_dock, button=self.toolButtonLeftDock))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.ui.style_dock, button=self.toolButtonRightDock))

    def set_notes_status(self, has_file, recording):
        """Update the Notes indicator light.

        Parameters
        ----------
        has_file : bool
            Whether a notes file is currently loaded (see
            MainWindow._refresh_notes_indicator).
        recording : bool
            Whether the "Record to Notes" toggle is currently on. Ignored
            (treated as not-recording) when `has_file` is False -- gray
            always wins over red/golden.
        """
        self.notesLight.set_status(self._resolve_status(has_file, recording))

    def set_workflow_status(self, has_file, recording):
        """Update the Workflow indicator light.

        Parameters
        ----------
        has_file : bool
            Whether a workflow file is currently active (see
            MainWindow._refresh_workflow_indicator).
        recording : bool
            Whether workflow action-capture is currently on. Ignored
            (treated as not-recording) when `has_file` is False -- gray
            always wins over red/golden.
        """
        self.workflowLight.set_status(self._resolve_status(has_file, recording))

    @staticmethod
    def _resolve_status(has_file, recording):
        if not has_file:
            return 'no_file'
        return 'recording' if recording else 'idle'

    def toggle_dock_visibility(self, dock, button=None):
        """Toggles the visibility and checked state of a dock and its controlling button

        _extended_summary_

        Parameters
        ----------
        dock : QDockWidget
            Dock widget to show or hide.
        button : QToolButton, QPushButton, QAction, optional
            Changes the checked state of button, by default None
        """
        if dock.isVisible():
            dock.hide()
            if button is not None:
                button.setChecked(False)
        else:
            dock.show()
            if button is not None:
                button.setChecked(True)
