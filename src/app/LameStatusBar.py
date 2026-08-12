from PyQt6.QtWidgets import QStatusBar, QLabel
from lame_core.CustomWidgets import CustomToolButton

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

        # Indicates whether the ActionRecorder is auto-pushing actions into the
        # open Workflow dock's Blockly workspace (see MainWindow.toggle_action_capture).
        # A separate lamp rather than relying on the CaptureToggle button's own
        # visibility/checked state, since that button must always stay visible
        # and clickable (clicking it while off is what creates/links a workflow
        # file in the first place - see MainWindow.ensure_active_workflow_file).
        self.workflowLamp = QLabel("●")  # filled circle
        self.workflowLamp.setObjectName("workflowLamp")
        self._set_lamp_style(False)
        self.addPermanentWidget(self.workflowLamp)

        # Create a button to hide/show the dock
        self.toolButtonLeftDock = CustomToolButton(
            text="Left Dock",
            light_icon_unchecked='icon-left-toolbar-hide-64.svg',
            light_icon_checked='icon-left-toolbar-show-64.svg',
            parent=self
        )
        self.toolButtonLeftDock.setChecked(True)
        self.toolButtonRightDock = CustomToolButton(
            text="Right Dock",
            light_icon_unchecked='icon-right-toolbar-hide-64.svg',
            light_icon_checked='icon-right-toolbar-show-64.svg',
            parent=self
        )
        self.toolButtonRightDock.setChecked(True)
        self.toolButtonBottomDock = CustomToolButton(
            text="BottomDock",
            light_icon_unchecked='icon-bottom-toolbar-hide-64.svg',
            light_icon_checked='icon-bottom-toolbar-show-64.svg',
            parent=self
        )
        self.toolButtonBottomDock.setChecked(True)

        self.addPermanentWidget(self.toolButtonLeftDock)
        self.addPermanentWidget(self.toolButtonBottomDock)
        self.addPermanentWidget(self.toolButtonRightDock)

    def connect_widgets(self):
        # dockWidgetLeftToolbox/dockWidgetStyling are just the Qt objectNames of
        # these docks (see ControlDock/StylingDock) - the actual Python
        # references live on MainWindow, deferred via lambda since neither dock
        # exists yet when MainStatusBar is constructed (see MainWindow.setupUI).
        self.toolButtonLeftDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.ui.control_dock, button=self.toolButtonLeftDock))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.ui.style_dock, button=self.toolButtonRightDock))

    def set_capture_status(self, enabled):
        """Update the workflow lamp to reflect whether recording is happening.

        Parameters
        ----------
        enabled : bool
            Whether workflow auto-capture is currently on.
        """
        self._set_lamp_style(enabled)

    def _set_lamp_style(self, enabled):
        color = "#e02020" if enabled else "#a0a0a0"
        self.workflowLamp.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.workflowLamp.setToolTip(
            "Recording: workflow actions are being captured" if enabled
            else "Workflow capture is off"
        )

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