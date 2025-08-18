from PyQt6.QtWidgets import QStatusBar, QLabel
from src.common.CustomWidgets import CustomToolButton

class MainStatusBar(QStatusBar):
    def __init__(self, ui=None):
        super().__init__(ui)

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
        self.toolButtonLeftDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetLeftToolbox, button=self.toolButtonLeftDock))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetStyling, button=self.toolButtonRightDock))

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