from PyQt6.QtCore import QSize, Qt, QRect, QObject
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QMenuBar, QMenu, QWidget, QLabel, QVBoxLayout, QComboBox, QMessageBox
from lame_core.UITheme import default_font, PreferencesDialog
from lame_core.CustomWidgets import CustomAction, CustomActionMenu
from lame_core.PagedToolBar import PagedToolBar
from lame_core.config import ICONPATH
from src.app.settings import prefs
from src.control.Logger import log, no_log

class MainActions(QObject):
    def __init__(self, ui):
        super().__init__(ui)

        self.ui = ui

        self.setupActions()
    
    def setupActions(self):

        # File Actions
        self.AddSampleDirectory = CustomAction(
            text="Add Sample\nDirectory",
            light_icon_unchecked="icon-add-directory-64.svg",
            parent=self.ui,
        )
        self.AddSampleDirectory.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.AddSampleDirectory.setObjectName("actionAddSampleDirectory")
        self.AddSampleDirectory.setToolTip("Add all samples in a directory to the current project")
        self.AddSampleDirectory.setShortcut("Ctrl+O")

        self.NewProject = CustomAction(
            text="New\nProject",
            light_icon_unchecked="icon-add-list-64.svg",
            dark_icon_unchecked="icon-add-list-dark-64.svg",
            parent=self.ui,
        )
        self.NewProject.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.NewProject.setObjectName("actionNewProject")
        self.NewProject.setToolTip("Start a new, empty project")

        self.SaveProjectAs = CustomAction(
            text="Save Project\nAs...",
            light_icon_unchecked="icon-save-session-64.svg",
            dark_icon_unchecked="icon-save-session-dark-64.svg",
            parent=self.ui,
        )
        self.SaveProjectAs.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SaveProjectAs.setObjectName("actionSaveProjectAs")
        self.SaveProjectAs.setToolTip("Save the current project to a new location")

        self.CloseProject = CustomAction(
            text="Close\nProject",
            light_icon_unchecked="icon-open-session-64.svg",
            dark_icon_unchecked="icon-open-session-dark-64.svg",
            parent=self.ui,
        )
        self.CloseProject.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.CloseProject.setObjectName("actionCloseProject")
        self.CloseProject.setToolTip("Close the current project")

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
        self.Undo.setToolTip("Undo the last action")

        self.Cut = QAction(parent=self.ui)
        self.Cut.setObjectName("actionCut")
        self.Cut.setToolTip("Cut the selection")

        self.Copy = QAction(parent=self.ui)
        self.Copy.setObjectName("actionCopy")
        self.Copy.setToolTip("Copy the selection")

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
        self.Calculator.setToolTip("Open the field calculator")

        self.SelectAnalytes = CustomAction(
            text = "Analytes",
            light_icon_unchecked="icon-atom-64.svg",
            dark_icon_unchecked="icon-atom-dark-64.svg",
            parent=self.ui,
        )
        self.SelectAnalytes.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SelectAnalytes.setObjectName("actionSelectAnalytes")
        self.SelectAnalytes.setToolTip("Select analytes and ratios to load and analyze")

        self.BiPlot = CustomAction(
            text="Scatter Plot",
            light_icon_unchecked="icon-scatter-64.svg",
            icon_text="Scatter",
            parent=self.ui,
        )
        self.BiPlot.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.BiPlot.setObjectName("actionBiPlot")
        self.BiPlot.setToolTip("Create a scatter or heatmap plot")

        self.Ternary = CustomAction(
            text="Ternary Plot",
            light_icon_unchecked="icon-ternary-64.svg",
            icon_text="Ternary",
            parent=self.ui,
        )
        self.Ternary.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Ternary.setObjectName("actionTernary")
        self.Ternary.setToolTip("Create a ternary plot or ternary map")

        self.DimRed = CustomAction(
            text="Dimensional Reduction",
            light_icon_unchecked="icon-dimensional-analysis-64.svg",
            dark_icon_unchecked="icon-dimensional-analysis-dark-64.svg",
            icon_text="Dimensional\nReduction",
            parent=self.ui,
        )
        self.DimRed.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.DimRed.setObjectName("actionDimRed")
        self.DimRed.setToolTip("Open the dimensional reduction (PCA) page")

        self.Cluster = CustomAction(
            text="Cluster",
            light_icon_unchecked="icon-cluster-64.svg",
            dark_icon_unchecked="icon-cluster-dark-64.svg",
            parent=self.ui,
        )
        self.Cluster.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Cluster.setObjectName("actionCluster")
        self.Cluster.setToolTip("Create a cluster map")

        self.TEC = CustomAction(
            text="TEC Plot",
            light_icon_unchecked="icon-TEC-64.svg",
            dark_icon_unchecked="icon-cluster-dark-64.svg",
            icon_text="TEC",
            parent=self.ui,
        )
        self.TEC.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.TEC.setObjectName("actionTEC")
        self.TEC.setToolTip("Create a trace-element compatibility (TEC) diagram")

        self.Radar = CustomAction(
            text="Radar Plot",
            light_icon_unchecked="icon-radar-64.svg",
            icon_text="Radar",
            parent=self.ui)
        self.Radar.setObjectName("actionRadar")
        self.Radar.setToolTip("Create a radar (spider) plot")

        self.Compare_Spot_Map = CustomAction(
            text="Compare Spot",
            light_icon_unchecked="icon-analysis-64.svg",
            parent=self.ui,
        )
        self.Compare_Spot_Map.setEnabled(False)
        self.Compare_Spot_Map.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Compare_Spot_Map.setObjectName("actionCompare_Spot_Map")
        self.Compare_Spot_Map.setToolTip("Compare spot analyses against map data")

        # self.build menubar entry
        self.Preferences = QAction(parent=self.ui)
        self.Preferences.setObjectName("actionPreferences")
        self.Preferences.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.Preferences.setText("Preferences")
        self.Preferences.setToolTip("Open the preferences dialog")
        self.Preferences.triggered.connect(self.open_preferences)

        self.About = QAction(parent=self.ui)
        self.About.setObjectName("actionAbout")
        self.About.setMenuRole(QAction.MenuRole.AboutRole)
        self.About.setText("About")
        self.About.setToolTip("About LaME")

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
        self.Batch_Process.setToolTip("Batch process multiple samples")

        self.SpotData = CustomAction(
            text="Spot Data",
            light_icon_unchecked="icon-spot-64.svg",
            parent=self.ui,
        )
        self.SpotData.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SpotData.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SpotData.setObjectName("actionSpotData")
        self.SpotData.setToolTip("Open the Spot Data page")

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
        self.PolygonMask.setChecked(True)
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
        self.ClusterMask.setChecked(True)
        self.ClusterMask.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ClusterMask.setObjectName("actionClusterMask")
        self.ClusterMask.setToolTip("Turn filter by cluster on/off")

        # Absorbs the old standalone FilterToggle action -- an ROI's
        # definition IS a filter definition (see SampleObj.add_roi), so
        # this toggle now gates both the live filter-table preview and
        # committed/selected ROIs together (see MainWindow.toggle_roi_mask).
        # Uses the filter icon (not the generic mask icon) since users think
        # of this as "the filter" toggle.
        self.ROIMask = CustomAction(
            text="ROI",
            light_icon_unchecked="icon-filter-64.svg",
            light_icon_checked="icon-filter-dark-64.png",
            parent=self.ui,
        )
        self.ROIMask.setCheckable(True)
        self.ROIMask.setChecked(True)
        self.ROIMask.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ROIMask.setObjectName("actionROIMask")
        self.ROIMask.setToolTip("Turn filtering by ROI/filter on/off")

        self.Correlation = CustomAction(
            text="Correlation",
            light_icon_unchecked="icon-correlation-64.svg",
            parent=self.ui,
        )
        self.Correlation.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Correlation.setObjectName("actionCorrelation")
        self.Correlation.setToolTip("Create a correlation matrix plot")

        self.Histograms = CustomAction(
            text="Histogram",
            light_icon_unchecked="icon-histogram-64.svg",
            dark_icon_unchecked="icon-histogram-dark-64.svg",
            parent=self.ui,
        )
        self.Histograms.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Histograms.setObjectName("actionHistograms")
        self.Histograms.setToolTip("Create a histogram")

        self.Reset = CustomAction(
            text="Reset",
            light_icon_unchecked="icon-nuke-64.svg",
            parent=self.ui,
        )
        self.Reset.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Reset.setObjectName("actionReset")
        self.Reset.setToolTip("Clear all changes and plots to start over")

        self.AddSampleFiles = CustomAction(
            text="Add Samples",
            light_icon_unchecked="icon-add-directory-64.svg",
            parent=self.ui,
        )
        self.AddSampleFiles.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.AddSampleFiles.setObjectName("actionAddSampleFiles")
        self.AddSampleFiles.setToolTip("Add one or more sample files to the current project")

        # Toolbar-only entry point: clicking the icon just pops this menu
        # (no separate dropdown arrow -- CustomActionMenu wires its own
        # `triggered` to `menu.exec()`). The two items call `.trigger()` on
        # the real AddSampleFiles/AddSampleDirectory actions above/below
        # rather than the dialog methods directly, so picking either one
        # here still goes through the same triggered-signal wiring
        # (dialog + logging) as the File menu's copies of those actions.
        add_sample_menu_items = [
            ("Add Sample Files", self.AddSampleFiles.trigger),
            ("Add Sample Directory", self.AddSampleDirectory.trigger),
            ]
        self.SampleMenu = CustomActionMenu(
            text="Add\nSamples",
            menu_items=add_sample_menu_items,
            light_icon_unchecked="icon-add-directory-64.svg",
            parent=self.ui)
        self.SampleMenu.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SampleMenu.setObjectName("actionSampleMenu")
        self.SampleMenu.setToolTip("Add one or more sample files or a directory of samples to the current project")

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
        self.SaveProject.setToolTip("Save the current project")

        self.OpenProject = CustomAction(
            text="Open\nProject",
            light_icon_unchecked="icon-open-session-64.svg",
            dark_icon_unchecked="icon-open-session-dark-64.svg",
            parent=self.ui,
        )
        self.OpenProject.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.OpenProject.setObjectName("actionOpenProject")
        self.OpenProject.setToolTip("Open an existing project")

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
            icon_text="Theme",
            parent=self.ui,
        )
        self.ViewMode.setMenuRole(QAction.MenuRole.ApplicationSpecificRole)
        self.ViewMode.setObjectName("actionViewMode")
        self.ViewMode.setToolTip("Switch between light, dark, and auto modes")

        self.ShowToolbarText = QAction(parent=self.ui)
        self.ShowToolbarText.setObjectName("actionShowToolbarText")
        self.ShowToolbarText.setText("Show Button Text")
        self.ShowToolbarText.setCheckable(True)
        self.ShowToolbarText.setChecked(True)
        self.ShowToolbarText.setToolTip("Show text labels beneath toolbar icons (uncheck to save space)")

        self.ImportSpots = CustomAction(
            text="Import Spots",
            light_icon_unchecked="icon-import-spots-64.svg",
            dark_icon_unchecked="",
            parent=self.ui,
        )
        self.ImportSpots.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ImportSpots.setObjectName("actionImportSpots")
        self.ImportSpots.setToolTip("Import spot analysis data")
        
        # --- Workflow Actions ---
        self.WorkflowTool = CustomAction(
            text="Workflow",
            light_icon_unchecked="icon-workflow-design-64.svg",
            parent=self.ui,
        )
        self.WorkflowTool.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.WorkflowTool.setObjectName("actionWorkflowTool")
        self.WorkflowTool.setToolTip("Open, create, and record workflows using the workflow design tool")

        self.CaptureToggle = CustomAction(
            text="Capture",
            light_icon_unchecked="icon-capture-off-64.svg",
            light_icon_checked="icon-capture-on-64.svg",
            dark_icon_unchecked="icon-capture-off-dark-64.svg",
            dark_icon_checked="icon-capture-on-dark-64.svg",
            parent=self.ui,
        )
        self.CaptureToggle.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.CaptureToggle.setObjectName("actionCaptureToggle")
        self.CaptureToggle.setToolTip("Auto-capture actions into the project's active workflow file")

        self.NewWorkflow = CustomAction(
            text="New Workflow",
            light_icon_unchecked="icon-workflow-design-64.svg",
            parent=self.ui,
        )
        self.NewWorkflow.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.NewWorkflow.setObjectName("actionNewWorkflow")
        self.NewWorkflow.setToolTip("Create a new workflow file and make it the project's active workflow")

        self.OpenWorkflow = CustomAction(
            text="Open Workflow",
            light_icon_unchecked="icon-workflow-design-64.svg",
            parent=self.ui,
        )
        self.OpenWorkflow.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.OpenWorkflow.setObjectName("actionOpenWorkflow")
        self.OpenWorkflow.setToolTip("Open an existing workflow file")

        self.SaveWorkflow = CustomAction(
            text="Save Workflow",
            light_icon_unchecked="icon-workflow-design-64.svg",
            parent=self.ui,
        )
        self.SaveWorkflow.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.SaveWorkflow.setObjectName("actionSaveWorkflow")
        self.SaveWorkflow.setToolTip("Save the current workflow file")

        self.CloseWorkflow = CustomAction(
            text="Close Workflow",
            light_icon_unchecked="icon-workflow-design-64.svg",
            parent=self.ui,
        )
        self.CloseWorkflow.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.CloseWorkflow.setObjectName("actionCloseWorkflow")
        self.CloseWorkflow.setToolTip("Close the current workflow file")

        self.Snapshot = CustomAction(
            text="Snapshot",
            light_icon_unchecked="icon-camera-64.svg",
            dark_icon_unchecked="icon-camera-dark-64.svg",
            parent=self.ui,
        )
        self.Snapshot.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Snapshot.setObjectName("actionSnapshot")
        self.Snapshot.setToolTip("Capture the most recent plot's settings and data state into the active workflow file")

        self.Logger = CustomAction(
            text="Logger",
            light_icon_unchecked="icon-log-64.svg",
            parent=self.ui,
        )
        self.Logger.setObjectName("actionLogger")
        self.Logger.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Logger.setToolTip("Open the logger")

        self.Notes = CustomAction(
            text="Notes",
            light_icon_unchecked="icon-notes-64.svg",
            parent=self.ui,
        )
        self.Notes.setObjectName("actionNotes")
        self.Notes.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Notes.setToolTip("Open the notes editor")

        # Mirrors CaptureToggle (Workflow's own auto-capture toggle), but for
        # Notes -- see MainWindow.toggle_notes_capture / ReportWriter's module
        # docstring for the (deliberately narrower, plot-events-only) scope.
        self.RecordNotesToggle = CustomAction(
            text="Record",
            light_icon_unchecked="icon-capture-off-64.svg",
            light_icon_checked="icon-capture-on-64.svg",
            dark_icon_unchecked="icon-capture-off-dark-64.svg",
            dark_icon_checked="icon-capture-on-dark-64.svg",
            parent=self.ui,
        )
        self.RecordNotesToggle.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.RecordNotesToggle.setObjectName("actionRecordNotesToggle")
        self.RecordNotesToggle.setToolTip("Auto-capture plots into the open Notes file")

        self.Filters = CustomAction(
            text="Filtering",
            light_icon_unchecked="icon-filter-64.svg",
            dark_icon_unchecked="icon-filter-dark-64.svg",
            parent=self.ui,
        )
        self.Filters.setObjectName("actionFilters")
        self.Filters.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Filters.setToolTip("Open the filter dock")

        self.UserGuide = QAction( text="User Guide", parent=self.ui )
        self.UserGuide.setObjectName("actionUserGuide")
        self.UserGuide.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.UserGuide.setToolTip("Open the user guide")

        self.Tutorials = QAction( text="Tutorials", parent=self.ui )
        self.Tutorials.setObjectName("actionTutorials")
        self.Tutorials.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Tutorials.setToolTip("Open the tutorials")

        self.Polygons = CustomAction(
            text="Polygons",
            light_icon_unchecked="icon-polygon-new-64.svg",
            dark_icon_unchecked="icon-polygon-new-64.svg",
            parent=self.ui,
        )
        self.Polygons.setObjectName("actionPolygons")
        self.Polygons.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Polygons.setToolTip("Open the polygon mask dock")

        self.Clusters = CustomAction(
            text="Clusters",
            light_icon_unchecked="icon-cluster-64.svg",
            dark_icon_unchecked="icon-cluster-dark-64.svg",
            parent=self.ui,
        )
        self.Clusters.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Clusters.setObjectName("actionClusters")
        self.Clusters.setToolTip("Open the cluster mask dock")

        self.Info = CustomAction(
            text="Info",
            light_icon_unchecked="icon-info-64.svg",
            parent=self.ui,
        )
        self.Info.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Info.setObjectName("actionInfo")
        self.Info.setToolTip("Open the data and plot info dock")

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
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
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

        self.Geochron = CustomAction(
            text="Geochronology",
            light_icon_unchecked="icon-dating-64.svg",
            dark_icon_unchecked="icon-dating-dark-64.svg",
            icon_text="Geochron",
            parent=self.ui,
        )
        self.Geochron.setCheckable(True)
        self.Geochron.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Geochron.setObjectName("actionGeochron")
        self.Geochron.setToolTip("Open geochronology (Lu-Hf dating) tools")

        self.Diffusion = CustomAction(
            text="Diffusion",
            light_icon_unchecked="icon-zoning-64.svg",
            parent=self.ui,
        )
        self.Diffusion.setCheckable(True)
        self.Diffusion.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Diffusion.setObjectName("actionDiffusion")
        self.Diffusion.setToolTip("Open 2-D multi-component diffusion modeling tools")

        self.Stoichiometry = CustomAction(
            text="Stoichiometry",
            light_icon_unchecked="icon-silicate-64.svg",
            parent=self.ui,
        )
        self.Stoichiometry.setCheckable(True)
        self.Stoichiometry.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.Stoichiometry.setObjectName("actionStoichiometry")
        self.Stoichiometry.setToolTip("Open the stoichiometric mineral formula calculator")

        self.ProjectFiles = CustomAction(
            text="Project\nFiles",
            light_icon_unchecked="icon-bullet-list-64.svg",
            dark_icon_unchecked="icon-bullet-list-dark-64.svg",
            parent=self.ui,
        )
        self.ProjectFiles.setCheckable(True)
        self.ProjectFiles.setMenuRole(QAction.MenuRole.TextHeuristicRole)
        self.ProjectFiles.setObjectName("actionProjectFiles")
        self.ProjectFiles.setToolTip("Show/hide the Project Files panel (samples in the current project)")

        self.connect_logger()

    def connect_actions(self):
        self.NewProject.triggered.connect(lambda: self.ui.project_manager.new_project())
        self.OpenProject.triggered.connect(lambda: self.ui.project_manager.open_project())
        self.AddSampleFiles.triggered.connect(lambda: self.ui.project_manager.add_sample_files_dialog())
        self.AddSampleDirectory.triggered.connect(lambda: self.ui.project_manager.add_sample_directory_dialog())
        self.SaveProject.triggered.connect(lambda: self.ui.project_manager.save_project())
        self.SaveProjectAs.triggered.connect(lambda: self.ui.project_manager.save_project_as())
        self.CloseProject.triggered.connect(lambda: self.ui.project_manager.close_project())

        self.UpdatePlot.triggered.connect(lambda: setattr(self.ui,"plot_flag",True)) # hopefully solve issues when plot stops updating
        self.UpdatePlot.triggered.connect(lambda: self.ui.control_dock.update_plot_type(force=True))
        self.UpdatePlot.triggered.connect(lambda: self.ui.style_dock.update_plot_type(force=True))

        # Plot menu -- each switches the control dock to the toolbox page
        # that plot type lives on, then selects that specific sub-type.
        self.Correlation.triggered.connect(lambda: self.select_plot_type('sample', 'correlation'))
        self.Histograms.triggered.connect(lambda: self.select_plot_type('sample', 'histogram'))
        self.BiPlot.triggered.connect(lambda: self.select_plot_type('scatter', 'scatter'))
        self.Ternary.triggered.connect(lambda: self.select_plot_type('scatter', 'ternary map'))
        self.TEC.triggered.connect(lambda: self.select_plot_type('ndim', 'TEC'))
        self.Radar.triggered.connect(lambda: self.select_plot_type('ndim', 'radar'))
        self.Cluster.triggered.connect(lambda: self.select_plot_type('cluster', 'cluster map'))
        # DimRed just opens the "Dimensional Reduction" toolbox page itself
        # (unlike the sub-type selectors above) -- toolbox_changed() picks
        # that page's own default plot type, no forced sub-type needed.
        self.DimRed.triggered.connect(
            lambda: self.ui.control_dock.toolbox.setCurrentIndex(self.ui.control_dock.tab_dict['dim_red'])
        )

        self.SpotTools.setChecked(False)
        self.SpotTools.triggered.connect(self.ui.control_dock.toggle_spot_tab)
        self.ImportSpots.setVisible(False)

        self.SpecialTools.setChecked(False)
        self.SpecialTools.triggered.connect(self.ui.control_dock.toggle_special_tab)

        self.Regression.setChecked(False)
        self.Regression.triggered.connect(self.ui.open_regression)

        self.Geochron.setChecked(False)
        self.Geochron.triggered.connect(self.ui.open_geochron_dock)

        self.Diffusion.setChecked(False)
        self.Diffusion.triggered.connect(self.ui.open_diffusion_dock)

        self.Stoichiometry.setChecked(False)
        self.Stoichiometry.triggered.connect(self.ui.open_stoichiometry_dock)

        self.ProjectFiles.setChecked(False)
        self.ProjectFiles.triggered.connect(self.ui.open_project_files_dock)

        if self.ui.data:
            self.toggle_actions(True)
        else:
            self.toggle_actions(False)

        self.SelectAnalytes.triggered.connect(lambda _: self.ui.open_select_analyte_dialog())

        self.Filters.triggered.connect(lambda _: self.ui.open_mask_dock('filter'))
        self.Polygons.triggered.connect(lambda _: self.ui.open_mask_dock('polygon'))
        self.Clusters.triggered.connect(lambda _: self.ui.open_mask_dock('cluster'))
        self.Profiles.triggered.connect(lambda _: self.ui.open_profile())

        # Restrict/unrestrict the analyzed dataset by each mask type (see
        # SampleObj.recompute_mask). ROIMask covers both the live filter-
        # table preview and committed/selected ROIs.
        self.PolygonMask.toggled.connect(self.ui.toggle_polygon_mask)
        self.ClusterMask.toggled.connect(self.ui.toggle_cluster_mask)
        self.ROIMask.toggled.connect(self.ui.toggle_roi_mask)

        self.Calculator.triggered.connect(lambda _: self.ui.open_calculator())
        self.Notes.triggered.connect(lambda _: self.ui.open_notes())
        self.RecordNotesToggle.toggled.connect(self.ui.toggle_notes_capture)
        self.Logger.triggered.connect(lambda _: self.ui.open_logger())
        self.WorkflowTool.triggered.connect(lambda _: self.ui.open_workflow())
        self.NewWorkflow.triggered.connect(lambda _: self.ui.new_workflow())
        self.OpenWorkflow.triggered.connect(lambda _: self.ui.open_workflow_file())
        self.SaveWorkflow.triggered.connect(lambda _: self.ui.save_workflow_file())
        self.CloseWorkflow.triggered.connect(lambda _: self.ui.close_workflow_file())
        self.Snapshot.triggered.connect(lambda _: self.ui.snapshot_workflow())
        self.CaptureToggle.toggled.connect(self.ui.toggle_action_capture)
        self.Info.triggered.connect(lambda _: self.ui.open_info_dock())

        self.Quit_LaME.triggered.connect(self.ui.quit)

        self.ReportBug.triggered.connect(lambda _: self.ui.open_browser('report_bug'))
        self.UserGuide.triggered.connect(lambda _: self.ui.open_browser('user_guide'))
        self.Tutorials.triggered.connect(lambda _: self.ui.open_browser('tutorials'))

        self.ViewMode.triggered.connect(self.ui.theme_manager.cycle_mode)

        self.ShowToolbarText.toggled.connect(self.ui.toolbar.set_show_button_text)


    @no_log
    def connect_logger(self):
        """Connects user interactions with widgets to the logger"""        
        ## MainWindow toolbar
        self.NewProject.triggered.connect(lambda: log("lame_action.NewProject", prefix="UI"))
        self.AddSampleFiles.triggered.connect(lambda: log("lame_action.AddSampleFiles", prefix="UI"))
        self.AddSampleDirectory.triggered.connect(lambda: log("lame_action.AddSampleDirectory", prefix="UI"))
        self.OpenProject.triggered.connect(lambda: log("lame_action.OpenProject", prefix="UI"))
        self.SaveProject.triggered.connect(lambda: log("lame_action.SaveProject", prefix="UI"))
        self.SaveProjectAs.triggered.connect(lambda: log("lame_action.SaveProjectAs", prefix="UI"))
        self.CloseProject.triggered.connect(lambda: log("lame_action.CloseProject", prefix="UI"))
        self.ProjectFiles.triggered.connect(lambda: log("lame_action.ProjectFiles", prefix="UI"))
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
        self.ROIMask.triggered.connect(lambda: log("lame_action.ROIMask", prefix="UI"))
        self.UpdatePlot.triggered.connect(lambda: log("lame_action.UpdatePlot", prefix="UI"))
        self.SavePlotToTree.triggered.connect(self._save_plot_to_tree)
        self.Correlation.triggered.connect(lambda: log("lame_action.Correlation", prefix="UI"))
        self.Histograms.triggered.connect(lambda: log("lame_action.Histograms", prefix="UI"))
        self.BiPlot.triggered.connect(lambda: log("lame_action.BiPlot", prefix="UI"))
        self.Ternary.triggered.connect(lambda: log("lame_action.Ternary", prefix="UI"))
        self.TEC.triggered.connect(lambda: log("lame_action.TEC", prefix="UI"))
        self.Radar.triggered.connect(lambda: log("lame_action.Radar", prefix="UI"))
        self.Cluster.triggered.connect(lambda: log("lame_action.Cluster", prefix="UI"))
        self.DimRed.triggered.connect(lambda: log("lame_action.DimRed", prefix="UI"))
        self.Notes.triggered.connect(lambda: log("lame_action.Notes", prefix="UI"))
        self.Calculator.triggered.connect(lambda: log("lame_action.Calculator", prefix="UI"))
        self.ReportBug.triggered.connect(lambda: log("lame_action.ReportBug", prefix="UI"))
        self.Help.triggered.connect(lambda: log("lame_action.Help", prefix="UI"))
        self.Reset.triggered.connect(lambda: log("lame_action.Reset", prefix="UI"))
        self.ViewMode.triggered.connect(lambda: log("lame_action.ViewMode", prefix="UI"))
        self.ShowToolbarText.triggered.connect(lambda: log("lame_action.ShowToolbarText", prefix="UI"))

    def open_preferences(self):
        dlg = PreferencesDialog(prefs, parent=self.ui)
        if dlg.exec():
            # dialog already updated prefs via accept, listeners will fire
            pass

    def select_plot_type(self, tab_key, plot_type):
        """Switch the control dock to the toolbox page for `tab_key` and
        select `plot_type` within it -- the composite action behind each
        Plot-menu action (BiPlot, Ternary, TEC, Radar, Cluster, Correlation,
        Histograms).

        Mirrors ``PlotTree._sync_ui_to_plot``: switching the toolbox page
        alone (``toolbox.setCurrentIndex``) only selects that page's
        *default* plot type (see ``ControlDock.toolbox_changed``) and is a
        no-op if the page is already current, so ``update_plot_type`` is
        always called afterward to select the specific sub-type regardless.

        Parameters
        ----------
        tab_key : str
            Key into ``ControlDock.tab_dict`` (e.g. ``'scatter'``, ``'ndim'``,
            ``'cluster'``, ``'sample'``).
        plot_type : str
            One of that page's ``plot_list`` entries (e.g. ``'scatter'``,
            ``'ternary map'``, ``'TEC'``, ``'radar'``, ``'cluster map'``).
        """
        control_dock = self.ui.control_dock
        control_dock.toolbox.setCurrentIndex(control_dock.tab_dict[tab_key])
        control_dock.update_plot_type(new_plot_type=plot_type, force=True)

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
        self.RecordNotesToggle.setEnabled(enable)
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

        # Project group -- New/Open (+ Recent Projects)/Add Samples, then
        # Save/Save As, then Close, each its own visually separated block.
        self.menuFile.addAction(lame_action.NewProject)
        self.menuFile.addAction(lame_action.OpenProject)

        self.menuRecentProjects = QMenu("Recent Projects", self.menuFile)
        self.menuRecentProjects.setObjectName("menuRecentProjects")
        self.menuRecentProjects.aboutToShow.connect(
            lambda: self._refresh_recent_projects_menu(ui)
        )
        self.menuFile.addMenu(self.menuRecentProjects)

        self.menuFile.addAction(lame_action.AddSampleFiles)
        self.menuFile.addAction(lame_action.AddSampleDirectory)
        self.menuFile.addSeparator()
        self.menuFile.addAction(lame_action.SaveProject)
        self.menuFile.addAction(lame_action.SaveProjectAs)
        self.menuFile.addSeparator()
        self.menuFile.addAction(lame_action.ProjectFiles)
        self.menuFile.addAction(lame_action.CloseProject)
        self.menuFile.addSeparator()

        # Import group
        self.menuFile.addAction(lame_action.SpotData)
        self.menuFile.addAction(lame_action.ImportFiles)
        self.menuFile.addAction(lame_action.ImportSpots)
        self.menuFile.addSeparator()

        self.menuFile.addAction(lame_action.SaveFigure)
        self.menuFile.addAction(lame_action.Reset)

        # Workflow Menu -- workflow files are explicitly reusable across
        # projects, not part of the project-open/close lifecycle, so they
        # get their own menu rather than living under File.
        self.menuWorkflow = QMenu(parent=self)
        self.menuWorkflow.setObjectName("menuWorkflow")
        self.menuWorkflow.setTitle("Workflow")

        self.menuWorkflow.addAction(lame_action.WorkflowTool)
        self.menuWorkflow.addSeparator()
        self.menuWorkflow.addAction(lame_action.NewWorkflow)
        self.menuWorkflow.addAction(lame_action.OpenWorkflow)
        self.menuWorkflow.addAction(lame_action.SaveWorkflow)
        self.menuWorkflow.addAction(lame_action.CloseWorkflow)
        self.menuWorkflow.addSeparator()
        self.menuWorkflow.addAction(lame_action.CaptureToggle)

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

        self.menuAnalyze.addAction(lame_action.PolygonMask)
        self.menuAnalyze.addAction(lame_action.ClusterMask)
        self.menuAnalyze.addAction(lame_action.ROIMask)
        self.menuAnalyze.addAction(lame_action.NoiseReduction)
        self.menuAnalyze.addSeparator()
        self.menuAnalyze.addAction(lame_action.Compare_Spot_Map)
        self.menuAnalyze.addAction(lame_action.Profiles)
        self.menuAnalyze.addAction(lame_action.Regression)
        self.menuAnalyze.addAction(lame_action.DimRed)
        self.menuAnalyze.addAction(lame_action.Geochron)
        self.menuAnalyze.addAction(lame_action.Diffusion)
        self.menuAnalyze.addAction(lame_action.Stoichiometry)

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
        self.menuTools.addAction(lame_action.ProjectFiles)
        self.menuTools.addSeparator()
        self.menuTools.addAction(lame_action.Info)
        self.menuTools.addAction(lame_action.Logger)
        self.menuTools.addAction(lame_action.Calculator)
        self.menuTools.addAction(lame_action.Notes)
        self.menuTools.addAction(lame_action.RecordNotesToggle)

        # View Menu -- the toolbar is now a single paged widget (pinned row +
        # page tabs + one swappable content row), so there's nothing left to
        # individually show/hide the way the old grouped toolbars were --
        # just the icon/text style toggle.
        self.menuView = QMenu(parent=self)
        self.menuView.setObjectName("menuView")
        self.menuView.setTitle("View")

        self.menuView.addAction(lame_action.ShowToolbarText)

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
        self.addMenu(self.menuView)
        self.addMenu(self.menuPlot)
        self.addMenu(self.menuAnalyze)
        self.addMenu(self.menuTools)
        self.addMenu(self.menuWorkflow)
        self.addMenu(self.menuHelp)

    def _refresh_recent_projects_menu(self, ui):
        """Rebuild the Recent Projects submenu just before it's shown, from
        ``ProjectManager.recent_projects()`` -- refreshed on demand rather
        than kept in sync incrementally, since it's cheap and only read
        right before display.
        """
        self.menuRecentProjects.clear()
        recents = ui.project_manager.recent_projects()
        if not recents:
            empty_action = self.menuRecentProjects.addAction("(No recent projects)")
            empty_action.setEnabled(False)
            return
        for path in recents:
            action = self.menuRecentProjects.addAction(path.stem)
            action.triggered.connect(lambda checked=False, p=path: ui.project_manager.open_project(p))

class MainToolbar(QToolBar):
    def __init__(self, ui, lame_action: MainActions):
        super().__init__(parent=ui)

        self.ui = ui
        self.lame_action = lame_action

        font = default_font()
        font.setPointSize(10)
        self.setFont(font)
        self.setToolTip("")
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setObjectName("toolBar")
        self.setMovable(False)

        ui.addToolBar(Qt.ToolBarArea.TopToolBarArea, self)

        self.paged = PagedToolBar(self)
        self.paged.pinned_bar.setFont(font)
        self.paged.pinned_bar.setIconSize(QSize(24, 24))
        self.paged.pinned_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.paged.page_bar.setFont(font)
        self.addWidget(self.paged)

        sample_widget = QWidget(self)

        sample_widget.setMaximumSize(QSize(16777215, 40))
        sample_widget.setObjectName("widgetSampleSelect")

        sample_widget_layout = QVBoxLayout(sample_widget)
        sample_widget_layout.setContentsMargins(0, 0, 0, 0)

        select_sample_label = QLabel(parent=sample_widget)
        select_sample_label.setText("Select sample")

        self.comboBoxSampleId = QComboBox(parent=sample_widget)
        self.comboBoxSampleId.setPlaceholderText("Load sample or directory...")
        self.comboBoxSampleId.setObjectName("comboBoxSampleId")

        sample_widget_layout.addWidget(select_sample_label)
        sample_widget_layout.addWidget(self.comboBoxSampleId)

        sample_widget.setLayout(sample_widget_layout)

        # Pinned row -- always visible regardless of which page is showing.
        # Kept lean on purpose: only things touched continuously no matter
        # what task is underway belong here.
        pinned = self.paged.pinned_bar
        pinned.addWidget(sample_widget)
        pinned.addAction(lame_action.SelectAnalytes)
        pinned.addSeparator()
        pinned.addAction(lame_action.UpdatePlot)
        pinned.addAction(lame_action.SavePlotToTree)
        pinned.addAction(lame_action.SaveProject)
        pinned.addSeparator()

        # Pages -- one row of content, swapped via the page tabs. Report Bug
        # and Reset aren't repeated here: both already live in the Help/File
        # menus (MainMenubar).
        self.paged.add_page("Home", self._build_home_page(lame_action))
        self.paged.add_page("Processing", self._build_processing_page(lame_action))
        self.paged.add_page("Plot", self._build_plot_page(lame_action))
        self.paged.add_page("Analysis", self._build_analysis_page(lame_action))
        self.paged.add_page("Log", self._build_log_page(lame_action))

        self.connect_observers()
        self.connect_actions()
        self.connect_logger()

    def _styled_page_toolbar(self):
        toolbar = QToolBar()
        toolbar.setFont(self.font())
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        return toolbar

    def _build_home_page(self, lame_action):
        """Builds the Home page of the toolbar, which contains actions related to project management and general functionality.

        Parameters
        ----------
        lame_action : QAction
            The action to be added to the toolbar.
            
        Returns
        -------
        QToolBar
            The configured toolbar.
        """
        toolbar = self._styled_page_toolbar()

        # Add Sample Files/Directory share one visual slot: clicking the
        # icon only ever opens the SampleMenu action's menu (CustomActionMenu
        # wires its own `triggered` to `menu.exec()`) -- no separate dropdown
        # arrow, no direct file-dialog trigger from the icon itself.
        toolbar.addAction(lame_action.OpenProject)
        toolbar.addAction(lame_action.SampleMenu)
        toolbar.addAction(lame_action.ImportFiles)
        toolbar.addAction(lame_action.Help)
        toolbar.addAction(lame_action.ViewMode)
        return toolbar

    def _build_plot_page(self, lame_action):
        """Builds the Plot page of the toolbar, which contains actions related to plotting and visualization.
        
        Parameters
        ----------
        lame_action : QAction
            The action to be added to the toolbar.
            
        Returns
        -------
        QToolBar
            The configured toolbar.
        """
        toolbar = self._styled_page_toolbar()
        toolbar.addAction(lame_action.FullMap)
        toolbar.addAction(lame_action.Crop)
        toolbar.addAction(lame_action.SwapAxes)
        toolbar.addAction(lame_action.Correlation)
        toolbar.addAction(lame_action.Histograms)
        toolbar.addAction(lame_action.BiPlot)
        toolbar.addAction(lame_action.Ternary)
        toolbar.addAction(lame_action.TEC)
        toolbar.addAction(lame_action.Radar)
        return toolbar

    def _build_processing_page(self, lame_action):
        """Builds the Processing page of the toolbar, which contains actions related to data processing.

        Parameters
        ----------
        lame_action : QAction
            The action to be added to the toolbar.
            
        Returns
        -------
        QToolBar
            The configured toolbar.
        """
        toolbar = self._styled_page_toolbar()
        toolbar.addAction(lame_action.NoiseReduction)
        toolbar.addAction(lame_action.ClearFilters)
        toolbar.addAction(lame_action.ROIMask)
        toolbar.addAction(lame_action.PolygonMask)
        toolbar.addAction(lame_action.ClusterMask)
        return toolbar

    def _build_log_page(self, lame_action):
        """Builds the Log page of the toolbar, which contains actions related to logging and reporting.
        
        Parameters
        ----------
        lame_action : QAction
            The action to be added to the toolbar.
            
        Returns
        -------
        QToolBar
            The configured toolbar.
        """
        toolbar = self._styled_page_toolbar()
        toolbar.addAction(lame_action.Notes)
        toolbar.addAction(lame_action.RecordNotesToggle)
        toolbar.addAction(lame_action.WorkflowTool)
        toolbar.addAction(lame_action.CaptureToggle)
        toolbar.addAction(lame_action.Snapshot)
        return toolbar

    def _build_analysis_page(self, lame_action):
        """Builds the Analysis page of the toolbar, which contains actions related to data analysis.
        
        Parameters
        ----------
        lame_action : QAction
            The action to be added to the toolbar.
            
        Returns
        -------
        QToolBar
            The configured toolbar.
        """
        toolbar = self._styled_page_toolbar()
        toolbar.addAction(lame_action.Calculator)
        toolbar.addAction(lame_action.Regression)
        toolbar.addAction(lame_action.DimRed)
        toolbar.addAction(lame_action.Cluster)
        toolbar.addAction(lame_action.Geochron)
        toolbar.addAction(lame_action.Profiles)
        toolbar.addAction(lame_action.Diffusion)
        toolbar.addAction(lame_action.Stoichiometry)
        return toolbar

    def set_show_button_text(self, show_text):
        """Show/hide the text labels beneath toolbar icons, across the
        pinned row and every page, to save vertical/horizontal space. The
        page-tab buttons themselves are always text-only, so they're not
        part of this sweep.
        """
        style = (
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon if show_text
            else Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self.paged.pinned_bar.setToolButtonStyle(style)
        for i in range(self.paged.pages.count()):
            self.paged.pages.widget(i).setToolButtonStyle(style)
        self.paged.sync_content_height()

    def _on_project_changed(self):
        if self.ui.project_manager.current_project is not None:
            self.paged.set_current_page("Plot")

    def connect_actions(self):
        self.comboBoxSampleId.activated.connect(lambda _: self.update_sample_id())
        self.ui.project_manager.projectChanged.connect(self._on_project_changed)

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
        """Updates ``app_data.sample_id``

        Dirty-tracking/save prompts are now project-scoped (``ProjectManager``),
        not per-sample-switch -- switching samples within an open project no
        longer itself prompts to save; only closing/exiting the project does.
        """
        if self.ui.app_data.sample_id == self.comboBoxSampleId.currentText():
            return

        self.ui.app_data.sample_id = self.comboBoxSampleId.currentText()
        self.ui.change_sample()
