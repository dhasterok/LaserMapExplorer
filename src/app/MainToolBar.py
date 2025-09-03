from PyQt6.QtCore import QSize, Qt, QRect, QObject
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QMenuBar, QMenu, QWidget, QLabel, QVBoxLayout, QComboBox, QMessageBox
from src.app.UITheme import default_font, PreferencesDialog
from src.common.CustomWidgets import CustomAction, CustomActionMenu
from src.app.config import ICONPATH
from src.app.settings import prefs
from src.common.Logger import log, no_log

class MainActions(QObject):
    def __init__(self, ui):
        super().__init__(ui)

        self.ui = ui

        self.setupActions()
    
    def setupActions(self):

        # File Actions
        self.OpenDirectory = CustomAction(
            text="Open\nDirectory",
            light_icon_unchecked="icon-add-directory-64.svg",
            parent=self.ui,
        )
        self.OpenDirectory.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.OpenDirectory.setObjectName("actionOpenDirectory")
        self.OpenDirectory.setToolTip("Select a directory of samples")
        self.OpenDirectory.setShortcut("Ctrl+O")

        self.SaveFigure = CustomAction(
            text = "Save\nFigure",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=self.ui,
        )
        self.SaveFigure.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SaveFigure.setObjectName("actionSaveFile")
        self.SaveFigure.setToolTip("Save the current file")
        self.SaveFigure.setShortcut("Ctrl+P")

        self.Undo = QAction(parent=self.ui)
        self.Undo.setObjectName("actionUndo")

        self.Cut = QAction(parent=self.ui)
        self.Cut.setObjectName("actionCut")

        self.Copy = QAction(parent=self.ui)
        self.Copy.setObjectName("actionCopy")

        #self.Shortcuts = QAction(parent=self.ui)
        #self.Shortcuts.setObjectName("actionShortcuts")

        self.Calculator = CustomAction(
            text="Calculator",
            light_icon_unchecked="icon-calculator-64.svg",
            dark_icon_unchecked="icon-calculator-dark-64.svg",
            parent=self.ui,
        )
        self.Calculator.setObjectName("actionCalculator")
        self.Calculator.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.SelectAnalytes = CustomAction(
            text = "Analytes",
            light_icon_unchecked="icon-atom-64.svg",
            dark_icon_unchecked="icon-atom-dark-64.svg",
            parent=self.ui,
        )
        self.SelectAnalytes.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SelectAnalytes.setObjectName("actionSelectAnalytes")

        self.BiPlot = CustomAction(
            text="Scatter Plot",
            light_icon_unchecked="icon-scatter-64.svg",
            parent=self.ui,
        )
        self.BiPlot.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.BiPlot.setObjectName("actionBiPlot")

        self.Ternary = CustomAction(
            text="Ternary Plot",
            light_icon_unchecked="icon-ternary-64.svg",
            parent=self.ui,
        )
        self.Ternary.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Ternary.setObjectName("actionTernary")

        self.Cluster = CustomAction(
            text="Cluster",
            light_icon_unchecked="icon-cluster-64.svg",
            dark_icon_unchecked="icon-cluster-dark-64.svg",
            parent=self.ui,
        )
        self.Cluster.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Cluster.setObjectName("actionCluster")

        self.TEC = CustomAction(
            text="TEC plot",
            light_icon_unchecked="icon-TEC-64.svg",
            dark_icon_unchecked="icon-cluster-dark-64.svg",
            parent=self.ui,
        )
        self.TEC.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.TEC.setObjectName("actionTEC")

        self.Radar = QAction(parent=self.ui)
        self.Radar.setObjectName("actionRadar")

        self.Compare_Spot_Map = CustomAction(
            text="Compare Spot",
            light_icon_unchecked="icon-analysis-64.svg",
            parent=self.ui,
        )
        self.Compare_Spot_Map.setEnabled(False)
        self.Compare_Spot_Map.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Compare_Spot_Map.setObjectName("actionCompare_Spot_Map")

        # bself.uild menubar entry
        self.Preferences = QAction(parent=self.ui)
        self.Preferences.setObjectName("actionPreferences")
        self.Preferences.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.Preferences.setText("Preferences")
        self.Preferences.triggered.connect(self.open_preferences)

        self.About = QAction(parent=self.ui)
        self.About.setObjectName("actionAbout")
        self.About.setMenuRole(QAction.MenuRole.AboutRole)
        self.About.setText("About")

        self.Quit_LaME = CustomAction(
            text="Quit",
            light_icon_unchecked="",
            dark_icon_unchecked="",
            parent=self.ui,
        )
        self.Quit_LaME.setMenuRole(QAction.MenuRole.QuitRole)
        self.Quit_LaME.setObjectName("actionQuit_LaME")
        self.Quit_LaME.setToolTip("Exit LaME")
        self.Quit_LaME.setShortcut("Ctrl+Q")

        self.Batch_Process = CustomAction(
            text="Batch\nProcess",
            light_icon_unchecked="icon-batch-64.svg",
            parent=self.ui,
        )
        self.Batch_Process.setEnabled(False)
        self.Batch_Process.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Batch_Process.setObjectName("actionBatch_Process")

        self.SpotData = CustomAction(
            text="Spot Data",
            light_icon_unchecked="icon-spot-64.svg",
            parent=self.ui,
        )
        self.SpotData.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SpotData.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SpotData.setObjectName("actionSpotData")

        self.FilterToggle = CustomAction(
            text="Filter",
            light_icon_unchecked="icon-filter-64.svg",
            light_icon_checked="icon-filter2-64.png",
            parent=self.ui,
        )
        self.FilterToggle.setCheckable(True)
        self.FilterToggle.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.FilterToggle.setObjectName("actionFilterToggle")
        self.FilterToggle.setToolTip("Open the filter dock")

        self.Profiles = CustomAction(
            text="Profiles",
            light_icon_unchecked="icon-profile-64.svg",
            dark_icon_unchecked="icon-profile-dark-64.svg",
            parent=self.ui,
        )
        self.Profiles.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Profiles.setObjectName("actionProfiles")
        self.Profiles.setToolTip("Open the profile dock")

        self.PolygonMask = CustomAction(
            text="Polygons",
            light_icon_unchecked="icon-polygon-new-64.svg",
            dark_icon_unchecked="icon-polygon-new-dark-64.svg",
            parent=self.ui,
        )
        self.PolygonMask.setCheckable(True)
        self.PolygonMask.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.PolygonMask.setObjectName("actionPolygonMask")
        self.PolygonMask.setToolTip("Turn filtering by polygon on/off")

        self.ClusterMask = CustomAction(
            text="Clusers",
            light_icon_unchecked="icon-mask-light-64.svg",
            light_icon_checked="icon-mask-dark-64.svg",
            parent=self.ui,
        )
        self.ClusterMask.setCheckable(True)
        self.ClusterMask.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ClusterMask.setObjectName("actionClusterMask")
        self.ClusterMask.setToolTip("Turn filter by cluster on/off")

        self.Correlation = CustomAction(
            text="Correlation",
            light_icon_unchecked="icon-correlation-64.svg",
            parent=self.ui,
        )
        self.Correlation.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Correlation.setObjectName("actionCorrelation")

        self.Histograms = CustomAction(
            text="Histogram",
            light_icon_unchecked="icon-histogram-64.svg",
            dark_icon_unchecked="icon-histogram-dark-64.svg",
            parent=self.ui,
        )
        self.Histograms.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Histograms.setObjectName("actionHistograms")

        self.Reset = CustomAction(
            text="Reset",
            light_icon_unchecked="icon-nuke-64.svg",
            parent=self.ui,
        )
        self.Reset.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Reset.setObjectName("actionReset")
        self.Reset.setToolTip("Clear all changes and plots to start over")

        self.OpenSample = CustomAction(
            text="Open\nSample",
            light_icon_unchecked="icon-open-file-64.svg",
            dark_icon_unchecked="icon-open-file-dark-64.svg",
            parent=self.ui,
        )
        self.OpenSample.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.OpenSample.setObjectName("actionOpenSample")

        self.NoiseReduction = CustomAction(
            text="Noise\nReduction",
            light_icon_unchecked="icon-noise-reduction-off-64.svg",
            dark_icon_unchecked="icon-noise-reduction-on-64.svg",
            parent=self.ui,
        )
        self.NoiseReduction.setCheckable(True)
        self.NoiseReduction.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.NoiseReduction.setObjectName("actionNoiseReduction")
        self.NoiseReduction.setToolTip("Apply noise reduction to analytes")

        self.SavePlotToTree = CustomAction(
            text="Add Plot\nto Tree",
            light_icon_unchecked="icon-tree-64.svg",
            parent=self.ui,
        )
        self.SavePlotToTree.setEnabled(True)
        self.SavePlotToTree.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SavePlotToTree.setObjectName("actionSavePlotToTree")
        self.SavePlotToTree.setShortcut("Ctrl+Shift+=")
        self.SavePlotToTree.setToolTip("Save the current plot to the plot selector")

        self.ImportFiles = CustomAction(
            text="Import\nFiles",
            light_icon_unchecked="icon-import-directory-64.svg",
            parent=self.ui,
        )
        self.ImportFiles.setObjectName("actionImportFiles")
        self.ImportFiles.setToolTip("Import a directory with raw or processed data")

        self.SwapAxes = CustomAction(
            text="Swap Axes",
            light_icon_unchecked="icon-swap-64.svg",
            dark_icon_unchecked="icon-swap-dark-64.svg",
            parent=self.ui,
        )
        self.SwapAxes.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SwapAxes.setObjectName("actionSwapAxes")
        self.SwapAxes.setToolTip("Swap or rotate axes")

        self.Crop = CustomAction(
            text="Crop",
            light_icon_unchecked="icon-crop-64.svg",
            dark_icon_unchecked="icon-crop-dark-64.svg",
            parent=self.ui,
        )
        self.Crop.setCheckable(True)
        self.Crop.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Crop.setObjectName("actionCrop")
        self.Crop.setToolTip("Open the crop tool")

        self.FullMap = CustomAction(
            text="Full Map",
            light_icon_unchecked="icon-fit-to-width-64.svg",
            dark_icon_unchecked="icon-fit-to-width-dark-64.svg",
            parent=self.ui,
        )
        self.FullMap.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)
        self.FullMap.setObjectName("actionFullMap")
        self.FullMap.setToolTip("View the full map, resetting crop to original extent")

        self.ClearFilters = CustomAction(
            text="Filters",
            light_icon_unchecked="icon-map-64.svg",
            dark_icon_unchecked="icon-map-dark-64.svg",
            parent=self.ui,
        )
        self.ClearFilters.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ClearFilters.setObjectName("actionClearFilters")
        self.ClearFilters.setToolTip("Clear all filters")

        self.ReportBug = CustomAction(
            text="Report\nBug",
            light_icon_unchecked="icon-bugs-64.png",
            parent=self.ui,
        )
        self.ReportBug.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ReportBug.setObjectName("actionReportBug")
        self.ReportBug.setToolTip("Report bug or request new feature")

        self.SaveProject = CustomAction(
            text="Save\nProject",
            light_icon_unchecked="icon-save-session-64.svg",
            dark_icon_unchecked="icon-save-session-dark-64.svg",
            parent=self.ui,
        )
        self.SaveProject.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SaveProject.setObjectName("actionSaveProject")

        self.OpenProject = CustomAction(
            text="Open\nProject",
            light_icon_unchecked="icon-open-session-64.svg",
            dark_icon_unchecked="icon-open-session-dark-64.svg",
            parent=self.ui,
        )
        self.OpenProject.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.OpenProject.setObjectName("actionOpenProject")

        self.Help = CustomAction(
            text="Help",
            light_icon_unchecked="icon-question-64.svg",
            parent=self.ui,
        )
        self.Help.setCheckable(True)
        self.Help.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Help.setObjectName("actionHelp")
        self.Help.setToolTip("Click once to active and a second time on a tool to open a help page.")
        self.Help.toggled.connect(lambda _: self.toggle_help_mode())

        self.ViewMode = CustomAction(
            text="",
            light_icon_unchecked="icon-sun-and-moon-64.svg",
            dark_icon_unchecked="",
            parent=self.ui,
        )
        self.ViewMode.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)
        self.ViewMode.setObjectName("actionViewMode")
        self.ViewMode.setToolTip("Switch between light, dark, and auto modes")

        self.ImportSpots = CustomAction(
            text="Import Spots",
            light_icon_unchecked="icon-import-spots-64.svg",
            dark_icon_unchecked="",
            parent=self.ui,
        )
        self.ImportSpots.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ImportSpots.setObjectName("actionImportSpots")
        
        self.WorkflowTool = CustomAction(
            text="Workflow",
            light_icon_unchecked="icon-workflow-design-64.svg",
            parent=self.ui,
        )
        self.WorkflowTool.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.WorkflowTool.setObjectName("actionWorkflowTool")
        self.WorkflowTool.setToolTip("Open, create, and record workflows using the workflow design tool")

        self.Logger = CustomAction(
            text="Logger",
            light_icon_unchecked="icon-log-64.svg",
            parent=self.ui,
        )
        self.Logger.setObjectName("actionLogger")
        self.Logger.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.Notes = CustomAction(
            text="Notes",
            light_icon_unchecked="icon-notes-64.svg",
            parent=self.ui,
        )
        self.Notes.setObjectName("actionNotes")
        self.Notes.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.Filters = CustomAction(
            text="Filtering",
            light_icon_unchecked="icon-filter-64.svg",
            dark_icon_unchecked="icon-filter-dark-64.svg",
            parent=self.ui,
        )
        self.Filters.setObjectName("actionFilters")
        self.Filters.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.UserGuide = QAction( text="User Guide", parent=self.ui )
        self.UserGuide.setObjectName("actionUserGuide")
        self.UserGuide.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.Tutorials = QAction( text="Tutorials", parent=self.ui )
        self.Tutorials.setObjectName("actionTutorials")
        self.Tutorials.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.Polygons = CustomAction(
            text="Polygons",
            light_icon_unchecked="icon-polygon-new-64.svg",
            dark_icon_unchecked="icon-polygon-new-64.svg",
            parent=self.ui,
        )
        self.Polygons.setObjectName("actionPolygons")
        self.Polygons.setMenuRole(QAction.MenuRole.TextHeuristicRole)

        self.Clusters = CustomAction(
            text="Clusters",
            light_icon_unchecked="icon-cluster-64.svg",
            dark_icon_unchecked="icon-cluster-dark-64.svg",
            parent=self.ui,
        )
        self.Clusters.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Clusters.setObjectName("actionClusters")

        self.Info = CustomAction(
            text="Info",
            light_icon_unchecked="icon-info-64.svg",
            parent=self.ui,
        )
        self.Info.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Info.setObjectName("actionInfo")

        self.SpotTools = CustomAction(
            text="Spot Tools",
            light_icon_unchecked="icon-spot-64.svg",
            parent=self.ui,
        )
        self.SpotTools.setCheckable(True)
        self.SpotTools.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SpotTools.setObjectName("actionSpotTools")
        self.SpotTools.setToolTip("Open tools for spot analyses")

        self.SpecialTools = CustomAction(
            text="Special Tools",
            light_icon_unchecked="icon-zoning-64.svg",
            parent=self.ui,
        )
        self.SpecialTools.setCheckable(True)
        self.SpecialTools.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SpecialTools.setObjectName("actionSpecialTools")
        self.SpecialTools.setToolTip("Open tools for P-T-t calculations")

        self.UpdatePlot = CustomAction(
            text="Update\nPlot",
            light_icon_unchecked="icon-launch-64.svg",
            dark_icon_unchecked="",
            parent=self.ui,
        )
        self.UpdatePlot.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.UpdatePlot.setObjectName("actionUpdatePlot")
        self.UpdatePlot.setToolTip("Force a plot update")

        self.Regression = CustomAction(
            text="Regression",
            light_icon_unchecked="icon-regression-64.svg",
            dark_icon_unchecked="icon-regression-dark-64.svg",
            parent=self.ui,
        )
        self.Regression.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Regression.setObjectName("actionRegression")
        self.Regression.setToolTip("Fit lines/curves to data")

        self.connect_logger()

    def connect_actions(self):
        self.UpdatePlot.triggered.connect(lambda: setattr(self.ui,"plot_flag",True)) # hopefully solve issues when plot stops updating
        self.UpdatePlot.triggered.connect(lambda: self.ui.control_dock.update_plot_type(force=True))
        self.UpdatePlot.triggered.connect(lambda: self.ui.style_dock.update_plot_type(force=True))

        self.SpotTools.setChecked(False)
        self.SpotTools.triggered.connect(self.ui.control_dock.toggle_spot_tab)
        self.ImportSpots.setVisible(False)

        self.SpecialTools.setChecked(False)
        self.SpecialTools.triggered.connect(self.ui.control_dock.toggle_special_tab)

        self.Regression.setChecked(False)
        self.Regression.triggered.connect(self.ui.open_regression)

        if self.ui.data:
            self.toggle_actions(True)
        else:
            self.toggle_actions(False)

        self.SelectAnalytes.triggered.connect(lambda _: self.ui.open_select_analyte_dialog())

        self.Filters.triggered.connect(lambda _: self.ui.open_mask_dock('filter'))
        self.Polygons.triggered.connect(lambda _: self.ui.open_mask_dock('polygon'))
        self.Clusters.triggered.connect(lambda _: self.ui.open_mask_dock('cluster'))
        self.Profiles.triggered.connect(lambda _: self.ui.open_profile())

        self.Calculator.triggered.connect(lambda _: self.ui.open_calculator())
        self.Notes.triggered.connect(lambda _: self.ui.open_notes())
        self.Logger.triggered.connect(lambda _: self.ui.open_logger())
        self.WorkflowTool.triggered.connect(lambda _: self.ui.open_workflow())
        self.Info.triggered.connect(lambda _: self.ui.open_info_dock())

        self.Quit_LaME.triggered.connect(self.ui.quit)

        self.ReportBug.triggered.connect(lambda _: self.ui.open_browser('report_bug'))
        self.UserGuide.triggered.connect(lambda _: self.ui.open_browser('user_guide'))
        self.Tutorials.triggered.connect(lambda _: self.ui.open_browser('tutorials'))

        self.ViewMode.triggered.connect(self.ui.theme_manager.cycle_mode)


    @no_log
    def connect_logger(self):
        """Connects user interactions with widgets to the logger"""        
        ## MainWindow toolbar
        self.OpenSample.triggered.connect(lambda: log("lame_action.OpenSample", prefix="UI"))
        self.OpenDirectory.triggered.connect(lambda: log("lame_action.OpenDirectory", prefix="UI"))
        self.OpenProject.triggered.connect(lambda: log("lame_action.OpenProject", prefix="UI"))
        self.SaveProject.triggered.connect(lambda: log("lame_action.SaveProject", prefix="UI"))
        self.SelectAnalytes.triggered.connect(lambda: log("lame_action.SelectAnalytes", prefix="UI"))
        self.WorkflowTool.triggered.connect(lambda: log("lame_action.WorkflowTool", prefix="UI"))
        self.FullMap.triggered.connect(lambda: log("lame_action.FullMap", prefix="UI"))
        self.Crop.triggered.connect(lambda: log("lame_action.Crop", prefix="UI"))
        self.SwapAxes.triggered.connect(lambda: log("lame_action.SwapAxes", prefix="UI"))
        self.NoiseReduction.triggered.connect(lambda: log("lame_action.NoiseReduction", prefix="UI"))
        self.ClearFilters.triggered.connect(lambda: log("lame_action.ClearFilters", prefix="UI"))
        self.Filters.triggered.connect(lambda: log("lame_action.Filters", prefix="UI"))
        self.PolygonMask.triggered.connect(lambda: log("lame_action.PolygonMask", prefix="UI"))
        self.ClusterMask.triggered.connect(lambda: log("lame_action.ClusterMask", prefix="UI"))
        self.UpdatePlot.triggered.connect(lambda: log("lame_action.UpdatePlot", prefix="UI"))
        self.SavePlotToTree.triggered.connect(self._save_plot_to_tree)
        self.Notes.triggered.connect(lambda: log("lame_action.Notes", prefix="UI"))
        self.Calculator.triggered.connect(lambda: log("lame_action.Calculator", prefix="UI"))
        self.ReportBug.triggered.connect(lambda: log("lame_action.ReportBug", prefix="UI"))
        self.Help.triggered.connect(lambda: log("lame_action.Help", prefix="UI"))
        self.Reset.triggered.connect(lambda: log("lame_action.Reset", prefix="UI"))
        self.ViewMode.triggered.connect(lambda: log("lame_action.ViewMode", prefix="UI"))

    def open_preferences(self):
        dlg = PreferencesDialog(prefs, parent=self.ui)
        if dlg.exec():
            # dialog already updated prefs via accept, listeners will fire
            pass

    def toggle_actions(self, enable):
        """Disables/enables widgets based on existence of self.ui.data.
        
        Parameters
        ----------
        enable
            Enable actions if data exists
        """
        self.SelectAnalytes.setEnabled(enable)
        self.FullMap.setEnabled(enable)
        self.Crop.setEnabled(enable)
        self.SwapAxes.setEnabled(enable)
        self.NoiseReduction.setEnabled(enable)
        self.Filters.setEnabled(enable)
        self.Polygons.setEnabled(enable)
        self.Clusters.setEnabled(enable)
        self.Profiles.setEnabled(enable)
        self.Info.setEnabled(enable)
        self.Notes.setEnabled(enable)
        self.Reset.setEnabled(enable)
        self.UpdatePlot.setEnabled(enable)
        self.SavePlotToTree.setEnabled(enable)

    def toggle_help_mode(self):
        """Toggles help mode

        Toggles ``self.Help``, when checked, the cursor will change so indicates help tool is active.
        """        
        if self.Help.isChecked():
            self.ui.setCursor(Qt.CursorShape.WhatsThisCursor)
        else:
            self.ui.setCursor(Qt.CursorShape.ArrowCursor)

    def _save_plot_to_tree(self):
        """Save the current plot to the tree via CanvasWidget."""
        try:
            if hasattr(self.ui, 'canvas_widget') and self.ui.canvas_widget:
                result = self.ui.canvas_widget.save_current_plot_to_tree()
                if result:
                    log("Successfully saved plot to tree", "INFO")
                else:
                    log("Failed to save plot to tree", "WARNING")
            else:
                log("Canvas widget not available", "WARNING")
        except Exception as e:
            log(f"Error in save plot to tree action: {e}", "ERROR")

class MainMenubar(QMenuBar):
    def __init__(self, ui, lame_action: MainActions):
        super().__init__(parent=ui)

        self.setGeometry(QRect(0, 0, 1158, 37))
        self.setNativeMenuBar(True)
        self.setObjectName("menubar")

        # LaME Menu
        self.menuLaME = QMenu(parent=self)
        self.menuLaME.setObjectName("menuLaME")
        self.menuLaME.setTitle("LaME")

        self.menuLaME.addAction(lame_action.Preferences)
        self.menuLaME.addAction(lame_action.About)
        self.menuLaME.addSeparator()
        self.menuLaME.addAction(lame_action.Preferences)
        self.menuLaME.addAction(lame_action.ViewMode)
        self.menuLaME.addSeparator()
        self.menuLaME.addAction(lame_action.Quit_LaME)

        # File Menu
        self.menuFile = QMenu(parent=self)
        self.menuFile.setObjectName("menuFile")
        self.menuFile.setTitle("File")

        self.menuFile.addAction(lame_action.OpenSample)
        self.menuFile.addAction(lame_action.OpenDirectory)
        self.menuFile.addAction(lame_action.OpenProject)
        self.menuFile.addAction(lame_action.SpotData)
        self.menuFile.addSeparator()
        self.menuFile.addAction(lame_action.SaveProject)
        self.menuFile.addAction(lame_action.SaveFigure)
        self.menuFile.addSeparator()
        self.menuFile.addAction(lame_action.Reset)
        self.menuFile.addAction(lame_action.ImportFiles)
        self.menuFile.addAction(lame_action.ImportSpots)

        # Plot Menu
        self.menuPlot = QMenu(parent=self)
        self.menuPlot.setObjectName("menuPlot")
        self.menuPlot.setTitle("Plot")

        self.menuPlot.addAction(lame_action.Correlation)
        self.menuPlot.addAction(lame_action.Histograms)
        self.menuPlot.addAction(lame_action.BiPlot)
        self.menuPlot.addAction(lame_action.Ternary)
        self.menuPlot.addAction(lame_action.TEC)
        self.menuPlot.addAction(lame_action.Radar)
        self.menuPlot.addAction(lame_action.Cluster)
        self.menuPlot.addSeparator()
        self.menuPlot.addAction(lame_action.SavePlotToTree)

        # Analyze Menu
        self.menuAnalyze = QMenu(parent=self)
        self.menuAnalyze.setObjectName("menuAnalyze")
        self.menuAnalyze.setTitle("Analyze")

        self.menuAnalyze.addAction(lame_action.FilterToggle)
        self.menuAnalyze.addAction(lame_action.PolygonMask)
        self.menuAnalyze.addAction(lame_action.ClusterMask)
        self.menuAnalyze.addAction(lame_action.NoiseReduction)
        self.menuAnalyze.addSeparator()
        self.menuAnalyze.addAction(lame_action.Compare_Spot_Map)
        self.menuAnalyze.addAction(lame_action.Profiles)

        # Tools Menu
        self.menuTools = QMenu(parent=self)
        self.menuTools.setObjectName("menuTools")
        self.menuTools.setTitle("Tools")

        self.menuTools.addAction(lame_action.Filters)
        self.menuTools.addAction(lame_action.Polygons)
        self.menuTools.addAction(lame_action.Clusters)
        self.menuTools.addSeparator()
        self.menuTools.addAction(lame_action.SpotTools)
        self.menuTools.addAction(lame_action.Profiles)
        self.menuTools.addAction(lame_action.SpecialTools)
        self.menuTools.addAction(lame_action.Regression)
        self.menuTools.addSeparator()
        self.menuTools.addAction(lame_action.Info)
        self.menuTools.addAction(lame_action.Logger)
        self.menuTools.addAction(lame_action.Calculator)
        self.menuTools.addAction(lame_action.Notes)
        self.menuTools.addSeparator()
        self.menuTools.addAction(lame_action.WorkflowTool)

        # Help Menu
        self.menuHelp = QMenu(parent=self)
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.setTitle("Help")

        self.menuHelp.addAction(lame_action.UserGuide)
        self.menuHelp.addAction(lame_action.Tutorials)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(lame_action.ReportBug)

        self.addMenu(self.menuLaME)
        self.addMenu(self.menuFile)
        self.addMenu(self.menuPlot)
        self.addMenu(self.menuAnalyze)
        self.addMenu(self.menuTools)
        self.addMenu(self.menuHelp)

class MainToolbar(QToolBar):
    def __init__(self, ui, lame_action: MainActions):
        super().__init__(parent=ui)

        self.ui = ui

        font = default_font()
        font.setPointSize(10)
        self.setFont(font)
        self.setToolTip("")
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setObjectName("toolBar")

        ui.addToolBar(Qt.ToolBarArea.TopToolBarArea, self)

        sample_widget = QWidget(self)

        sample_widget.setGeometry(QRect(15, 85, 211, 40))
        sample_widget.setMaximumSize(QSize(16777215, 40))
        sample_widget.setObjectName("widgetSampleSelect")

        sample_widget_layout = QVBoxLayout(self)
        sample_widget_layout.setContentsMargins(0, 0, 0, 0)

        select_sample_label = QLabel(parent=self)
        select_sample_label.setText("Select sample")

        self.comboBoxSampleId = QComboBox(parent=self)
        self.comboBoxSampleId.setPlaceholderText("Load sample or directory...")
        self.comboBoxSampleId.setObjectName("comboBoxSampleId")

        sample_widget_layout.addWidget(select_sample_label)
        sample_widget_layout.addWidget(self.comboBoxSampleId)

        sample_widget.setLayout(sample_widget_layout)


        self.addAction(lame_action.OpenSample)
        self.addAction(lame_action.OpenDirectory)
        self.addAction(lame_action.ImportFiles)
        self.addAction(lame_action.ImportSpots)
        self.addAction(lame_action.OpenProject)
        self.addAction(lame_action.SaveProject)
        self.addSeparator()
        #self.addWidget(sample_widget)
        self.addAction(lame_action.SelectAnalytes)
        self.insertWidget(lame_action.SelectAnalytes, sample_widget)
        self.addAction(lame_action.WorkflowTool)
        self.addSeparator()
        self.addAction(lame_action.FullMap)
        self.addAction(lame_action.Crop)
        self.addAction(lame_action.SwapAxes)
        self.addSeparator()
        self.addAction(lame_action.NoiseReduction)
        self.addAction(lame_action.ClearFilters)
        self.addAction(lame_action.FilterToggle)
        self.addAction(lame_action.PolygonMask)
        self.addAction(lame_action.ClusterMask)
        self.addSeparator()
        self.addAction(lame_action.UpdatePlot)
        self.addAction(lame_action.SavePlotToTree)
        self.addSeparator()
        self.addAction(lame_action.Notes)
        self.addAction(lame_action.Calculator)
        self.addSeparator()
        self.addAction(lame_action.ReportBug)
        self.addAction(lame_action.Reset)
        self.addAction(lame_action.Help)
        self.addAction(lame_action.ViewMode)

        self.connect_observers()
        self.connect_actions()
        self.connect_logger()
    
    def connect_actions(self):
        self.comboBoxSampleId.activated.connect(lambda _: self.update_sample_id())

    def connect_logger(self):
        self.comboBoxSampleId.activated.connect(lambda: log(f"comboBoxSampleId, value=[{self.comboBoxSampleId.currentText()}]", prefix="UI"))

    def connect_observers(self):
        self.ui.app_data.normReferenceChanged.connect(lambda new_text: self.update_ref_index_combobox(new_text))
        self.ui.app_data.sampleListChanged.connect(lambda new_list: self.update_sample_list_combobox(new_list))
        self.ui.app_data.sampleChanged.connect(lambda new_sample: self.update_sample_id_combobox(new_sample))

    def update_ref_index_combobox(self, new_index):
        rev_val = self.ui.app_data.ref_list[new_index]
        self.ui.dock.update_ref_chem_combobox(rev_val)

    def update_sample_list_combobox(self, new_sample_list: list):
        """Updates ``MainWindow.comboBoxSampleID.items()``

        Called as an update to ``app_data.sample_list``.  Updates sample ID list.

        Parameters
        ----------
        new_sample_list : list
            New list of sample IDs.
        """
        # Populate the comboBoxSampleId with the sample names
        self.comboBoxSampleId.clear()
        self.comboBoxSampleId.addItems(new_sample_list)

        self.ui.change_directory()

    def update_sample_id_combobox(self, new_sample_id):
        """Updates ``MainWindow.comboBoxSampleID.currentText()``

        Called as an update to ``app_data.sample_id``.  Updates sample ID and calls ``change_sample``

        Parameters
        ----------
        value : str
            New sample ID.
        """
        if new_sample_id == self.comboBoxSampleId.currentText():
            return
        self.comboBoxSampleId.setCurrentText(new_sample_id)
        
        self.ui.change_sample()

        # self.profile_dock.profiling.add_samples()
        # self.polygon.add_samples()

    def update_sample_id(self):
        """Updates ``app_data.sample_id``"""
        if self.ui.app_data.sample_id == self.comboBoxSampleId.currentText():
            return

        # See if the user wants to really change samples and save or discard the current work
        if self.ui.data and self.ui.app_data.sample_id != '':
            # Create and configure the QMessageBox
            response = QMessageBox.warning(self,
                    "Save sample",
                    "Do you want to save the current analysis?",
                    QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save)
            #iconWarning = QIcon(":/resources/icons/icon-warning-64.svg")
            #msgBox.setWindowIcon(iconWarning)  # Set custom icon

            # If the user clicks discard, then no need to save, just change the sample
            if response == QMessageBox.StandardButton.Save:
                self.io.save_project()
            elif response == QMessageBox.StandardButton.Cancel:
                # change the sample ID back to the current sample
                self.comboBoxSampleId.setCurrentText(self.ui.app_data.sample_id)
                return

        # at this point, the user has decided to proceed with changing the sample
        # update the current sample ID
        self.ui.app_data.sample_id = self.comboBoxSampleId.currentText()
        # initiate the sample change
        self.change_sample()
