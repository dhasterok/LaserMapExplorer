import darkdetect
from pathlib import Path
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import QObject, pyqtSignal

from src.app.config import ICONPATH, load_stylesheet

def default_font():
    # set default font for application
    font = QFont()
    font.setPointSize(11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferDefault)

    return font

class ThemeManager(QObject):
    themeChanged = pyqtSignal(str)  # 'dark' or 'light'

    def __init__(self):
        super().__init__()
        self.current_theme = 'light'

    def set_theme(self, theme):
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self.apply_theme()
        self.themeChanged.emit(theme)

    def apply_theme(self):
        if self.current_theme == 'dark':
            app.setStyleSheet(open('dark.qss').read())
        else:
            app.setStyleSheet(open('light.qss').read())

class UIThemes():
    def __init__(self, app, parent):

        self.app = app
        self.parent = parent

        # set theme
        self.view_mode = 0
        self.switch_view_mode(self.view_mode)
        parent.actionViewMode.triggered.connect(lambda: self.switch_view_mode(self.view_mode+1))

        self.highlight_color_dark = '#696880'
        self.highlight_color_light = '#FFFFC8'

    def switch_view_mode(self, view_mode):
        if view_mode > 2:
            view_mode = 0
        self.view_mode = view_mode

        match self.view_mode:
            case 0: # auto
                if darkdetect.isDark():
                    self.set_dark_theme()
                else:
                    self.set_light_theme()

                self.parent.actionViewMode.setIcon(QIcon(str(ICONPATH / 'icon-sun-and-moon-64.svg')))
                self.parent.actionViewMode.setIconText('Auto')
            case 1: # dark
                self.set_dark_theme()
            case 2: # light
                self.set_light_theme()

    def set_dark_theme(self):
        ss = load_stylesheet('dark.qss')
        self.app.setStyleSheet(ss)

        parent = self.parent

        parent.actionViewMode.setIcon(QIcon(str(ICONPATH / 'icon-moon-64.svg')))
        parent.actionViewMode.setIconText('Dark')

        parent.actionSelectAnalytes.setIcon(QIcon(str(ICONPATH / 'icon-atom-dark-64.svg')))
        parent.actionOpenProject.setIcon(QIcon(str(ICONPATH / 'icon-open-session-dark-64.svg')))
        parent.actionSaveProject.setIcon(QIcon(str(ICONPATH / 'icon-save-session-dark-64.svg')))
        parent.actionFullMap.setIcon(QIcon(str(ICONPATH / 'icon-fit-to-width-dark-64.svg')))
        parent.actionCrop.setIcon(QIcon(str(ICONPATH / 'icon-crop-dark-64.svg')))
        parent.actionSwapAxes.setIcon(QIcon(str(ICONPATH / 'icon-swap-dark-64.svg')))
        parent.toolButtonSwapResolution.setIcon(QIcon(str(ICONPATH / 'icon-swap-resolution-dark-64.svg')))
        # Notes
        if hasattr(parent,'notes') and parent.notes.isVisible():
            parent.notes.header_button.setIcon(QIcon(str(ICONPATH / 'icon-heading-dark-64.svg')))
            parent.notes.bold_button.setIcon(QIcon(str(ICONPATH / 'icon-bold-dark-64.svg')))
            parent.notes.italic_button.setIcon(QIcon(str(ICONPATH / 'icon-italics-dark-64.svg')))
            parent.notes.bullet_button.setIcon(QIcon(str(ICONPATH / 'icon-bullet-list-dark-64.svg')))
            parent.notes.number_button.setIcon(QIcon(str(ICONPATH / 'icon-numbered-list-dark-64.svg')))
            parent.notes.image_button.setIcon(QIcon(str(ICONPATH / 'icon-image-64.svg')))
            parent.notes.save_button.setIcon(QIcon(str(ICONPATH / 'icon-pdf-dark-64.svg')))
        # Reset Buttons
        parent.toolButtonXAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonYAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonZAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonCAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        #parent.toolButtonClusterColorReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonHistogramReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        # Plot Tree
        if hasattr(parent,"plot_tree"):
            parent.plot_tree.actionSortMenu.setIcon(QIcon(str(ICONPATH / 'icon-sort-dark-64.svg')))
            parent.plot_tree.actionRemovePlot.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
            parent.plot_tree.actionRemoveAllPlots.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # Samples
        parent.toolBox.setItemIcon(parent.left_tab['sample'],QIcon(str(ICONPATH / 'icon-atom-dark-64.svg')))
        parent.toolButtonScaleEqualize.setIcon(QIcon(str(ICONPATH / 'icon-histeq-dark-64.svg')))
        parent.toolButtonAutoScale.setIcon(QIcon(str(ICONPATH / 'icon-autoscale-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['process'],QIcon(str(ICONPATH / 'icon-histogram-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['multidim'],QIcon(str(ICONPATH / 'icon-dimensional-analysis-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['cluster'],QIcon(str(ICONPATH / 'icon-cluster-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['scatter'],QIcon(str(ICONPATH / 'icon-ternary-dark-64.svg')))
        # Spot Data
        if hasattr(parent,"spot_tools"):
            parent.toolButtonSpotMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-dark-64.svg')))
            parent.toolButtonSpotToggle.setIcon(QIcon(str(ICONPATH / 'icon-show-hide-dark-64.svg')))
            parent.toolButtonSpotSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
            parent.toolButtonSpotAnalysis.setIcon(QIcon(str(ICONPATH / 'icon-analysis-dark-64.svg')))
            parent.toolButtonSpotRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # N-Dim
        parent.toolBox.setItemIcon(parent.left_tab['ndim'],QIcon(str(ICONPATH / 'icon-TEC-dark-64.svg')))
        parent.toolButtonNDimDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-dark-64.svg')))
        parent.toolButtonNDimUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-dark-64.svg')))
        parent.toolButtonNDimSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
        parent.toolButtonNDimRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # Filter
        #parent.toolButtonFilterSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
        #parent.toolButtonFilterUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-dark-64.svg')))
        #parent.toolButtonFilterDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-dark-64.svg')))
        #parent.toolButtonFilterRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # Polygons
        #parent.toolBox.setItemIcon(parent.left_tab['polygons'],QIcon(str(ICONPATH / 'icon-polygon-new-dark-64.svg')))
        #parent.toolButtonPolyCreate.setIcon(QIcon(str(ICONPATH / 'icon-polygon-new-dark-64.svg')))
        #parent.toolButtonPolyAddPoint.setIcon(QIcon(str(ICONPATH / 'icon-add-point-dark-64.svg')))
        #parent.toolButtonPolyRemovePoint.setIcon(QIcon(str(ICONPATH / 'icon-remove-point-dark-64.svg')))
        #parent.toolButtonPolyMovePoint.setIcon(QIcon(str(ICONPATH / 'icon-move-point-dark-64.svg')))
        #parent.toolButtonPolyLink.setIcon(QIcon(str(ICONPATH / 'icon-link-dark-64.svg')))
        #parent.toolButtonPolyDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-dark-64.svg')))
        #parent.toolButtonPolyDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # Profile
        #parent.toolBox.setItemIcon(parent.left_tab['profile'],QIcon(str(ICONPATH / 'icon-profile-dark-64.svg')))
        #parent.toolButtonClearProfile.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        #parent.toolButtonPointDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        #parent.toolButtonPointSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
        #parent.toolButtonPointMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-dark-64.svg')))
        #parent.toolButtonProfileInterpolate.setIcon(QIcon(str(ICONPATH / 'icon-interpolate-dark-64.svg')))
        #parent.toolButtonPlotProfile.setIcon(QIcon(str(ICONPATH / 'icon-profile-dark-64.svg')))
        #parent.toolButtonPointDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-dark-64.svg')))
        #parent.toolButtonPointUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-dark-64.svg')))
        # Browser
        if hasattr(parent, 'browser'):
            parent.browser.home_button.setIcon(QIcon(str(ICONPATH / 'icon-home-dark-64.svg')))
            parent.browser.forward_button.setIcon(QIcon(str(ICONPATH / 'icon-forward-arrow-dark-64.svg')))
            parent.browser.back_button.setIcon(QIcon(str(ICONPATH / 'icon-back-arrow-dark-64.svg')))
        # Group Box Plot Tools
        parent.toolButtonHome.setIcon(QIcon(str(ICONPATH / 'icon-home-dark-64.svg')))
        parent.toolButtonRemoveAllMVPlots.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        parent.toolButtonPopFigure.setIcon(QIcon(str(ICONPATH / 'icon-popout-dark-64.svg')))
        parent.toolButtonAnnotate.setIcon(QIcon(str(ICONPATH / 'icon-annotate-dark-64.svg')))
        parent.toolButtonPan.setIcon(QIcon(str(ICONPATH / 'icon-move-dark-64.svg')))
        parent.toolButtonZoom.setIcon(QIcon(str(ICONPATH / 'icon-zoom-dark-64.svg')))
        parent.toolButtonDistance.setIcon(QIcon(str(ICONPATH / 'icon-distance-dark-64.svg')))
        # Calculator
        parent.actionCalculator.setIcon(QIcon(str(ICONPATH / 'icon-calculator-dark-64.svg')))
        # Style Toolbox
        parent.toolBoxStyle.setItemIcon(parent.style_tab['axes'],QIcon(str(ICONPATH / 'icon-axes-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['text'],QIcon(str(ICONPATH / 'icon-text-and-scales-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['markers'],QIcon(str(ICONPATH / 'icon-marker-and-lines-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['colors'],QIcon(str(ICONPATH / 'icon-rgb-dark-64.svg')))
        # Cluster tab
        #parent.tabWidgetMask.setItemIcon(parent.mask_tab['cluster'],QIcon(str(ICONPATH / 'icon-cluster-dark-64.svg')))
        #parent.toolButtonClusterLink.setIcon(QIcon(str(ICONPATH / 'icon-link-dark-64.svg')))
        #parent.toolButtonClusterDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-dark-64.svg')))

    def set_light_theme(self):
        ss = load_stylesheet('light.qss')
        self.app.setStyleSheet(ss)

        parent = self.parent

        parent.actionViewMode.setIcon(QIcon(str(ICONPATH / 'icon-sun-64.svg')))
        parent.actionViewMode.setIconText('Light')

        parent.actionSelectAnalytes.setIcon(QIcon(str(ICONPATH / 'icon-atom-64.svg')))
        parent.actionOpenProject.setIcon(QIcon(str(ICONPATH / 'icon-open-session-64.svg')))
        parent.actionSaveProject.setIcon(QIcon(str(ICONPATH / 'icon-save-session-64.svg')))
        parent.actionFullMap.setIcon(QIcon(str(ICONPATH / 'icon-fit-to-width-64.svg')))
        parent.actionCrop.setIcon(QIcon(str(ICONPATH / 'icon-crop-64.svg')))
        parent.actionSwapAxes.setIcon(QIcon(str(ICONPATH / 'icon-swap-64.svg')))
        parent.toolButtonSwapResolution.setIcon(QIcon(str(ICONPATH / 'icon-swap-resolution-64.svg')))
        # Notes
        if hasattr(parent,'notes') and parent.notes.isVisible():
            parent.notes.header_button.setIcon(QIcon(str(ICONPATH / 'icon-heading-64.svg')))
            parent.notes.bold_button.setIcon(QIcon(str(ICONPATH / 'icon-bold-64.svg')))
            parent.notes.italic_button.setIcon(QIcon(str(ICONPATH / 'icon-italics-64.svg')))
            parent.notes.literal_button.setIcon(QIcon(str(ICONPATH / 'icon-literal-64.svg')))
            parent.notes.subscript_button.setIcon(QIcon(str(ICONPATH / 'icon-subscript-64.svg')))
            parent.notes.superscript_button.setIcon(QIcon(str(ICONPATH / 'icon-superscript-64.svg')))
            parent.notes.math_button.setIcon(QIcon(str(ICONPATH / 'icon-equation-64.svg')))
            parent.notes.hyperlink_button.setIcon(QIcon(str(ICONPATH / 'icon-hyperlink-64.svg')))
            parent.notes.cite_button.setIcon(QIcon(str(ICONPATH / 'icon-cite-64.svg')))
            parent.notes.bullet_button.setIcon(QIcon(str(ICONPATH / 'icon-bullet-list-64.svg')))
            parent.notes.number_button.setIcon(QIcon(str(ICONPATH / 'icon-numbered-list-64.svg')))
            parent.notes.image_button.setIcon(QIcon(str(ICONPATH / 'icon-image-dark-64.svg')))
            parent.notes.save_button.setIcon(QIcon(str(ICONPATH / 'icon-pdf-64.svg')))
        # Reset Buttons
        parent.toolButtonXAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonYAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonZAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonCAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        if hasattr(parent,"mask_dock"):
            parent.mask_dock.actionClusterColorReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonHistogramReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        # Plot Tree
        if hasattr(parent,"plot_tree"):
            parent.plot_tree.actionSortMenu.setIcon(QIcon(str(ICONPATH / 'icon-sort-64.svg')))
            parent.plot_tree.actionRemovePlot.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
            parent.plot_tree.actionRemoveAllPlots.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))

        # Samples
        parent.toolBox.setItemIcon(parent.left_tab['sample'],QIcon(str(ICONPATH / 'icon-atom-64.svg')))
        parent.toolButtonScaleEqualize.setIcon(QIcon(str(ICONPATH / 'icon-histeq-64.svg')))
        parent.toolButtonAutoScale.setIcon(QIcon(str(ICONPATH / 'icon-autoscale-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['process'],QIcon(str(ICONPATH / 'icon-histogram-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['multidim'],QIcon(str(ICONPATH / 'icon-dimensional-analysis-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['cluster'],QIcon(str(ICONPATH / 'icon-cluster-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['scatter'],QIcon(str(ICONPATH / 'icon-ternary-64.svg')))
        # Spot Data
        if hasattr(parent,"spot_tools"):
            parent.toolButtonSpotMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-64.svg')))
            parent.toolButtonSpotToggle.setIcon(QIcon(str(ICONPATH / 'icon-show-hide-64.svg')))
            parent.toolButtonSpotSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
            parent.toolButtonSpotAnalysis.setIcon(QIcon(str(ICONPATH / 'icon-analysis-64.svg')))
            parent.toolButtonSpotRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        # N-Dim
        parent.toolBox.setItemIcon(parent.left_tab['ndim'],QIcon(str(ICONPATH / 'icon-TEC-64.svg')))
        parent.toolButtonNDimDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-64.svg')))
        parent.toolButtonNDimUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-64.svg')))
        parent.toolButtonNDimSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
        parent.toolButtonNDimRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        # Filter
        if hasattr(parent,"mask_dock"):
            parent.actionFilterSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
            parent.actionFilterUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-64.svg')))
            parent.actionFilterDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-64.svg')))
            parent.actionFilterRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
            # Polygons
            parent.toolBox.setItemIcon(parent.mask_tab['polygon'],QIcon(str(ICONPATH / 'icon-polygon-new-64.svg')))
            parent.actionPolyCreate.setIcon(QIcon(str(ICONPATH / 'icon-polygon-new-64.svg')))
            parent.actionPolyAddPoint.setIcon(QIcon(str(ICONPATH / 'icon-add-point-64.svg')))
            parent.actionPolyRemovePoint.setIcon(QIcon(str(ICONPATH / 'icon-remove-point-64.svg')))
            parent.actionPolyMovePoint.setIcon(QIcon(str(ICONPATH / 'icon-move-point-64.svg')))
            parent.actionPolyLink.setIcon(QIcon(str(ICONPATH / 'icon-link-64.svg')))
            parent.actionPolyDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-64.svg')))
            parent.actionPolyDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        # Profile
        #parent.toolBox.setItemIcon(parent.left_tab['profile'],QIcon(str(ICONPATH / 'icon-profile-64.svg')))
        #parent.toolButtonClearProfile.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        #parent.toolButtonPointDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        #parent.toolButtonPointSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
        #parent.toolButtonPointMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-64.svg')))
        #parent.toolButtonProfileInterpolate.setIcon(QIcon(str(ICONPATH / 'icon-interpolate-64.svg')))
        #parent.toolButtonPlotProfile.setIcon(QIcon(str(ICONPATH / 'icon-profile-64.svg')))
        #parent.toolButtonPointDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-64.svg')))
        #parent.toolButtonPointUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-64.svg')))
        # Browser
        if hasattr(parent, 'browser'):
            parent.browser.home_button.setIcon(QIcon(str(ICONPATH / 'icon-home-64.svg')))
            parent.browser.forward_button.setIcon(QIcon(str(ICONPATH / 'icon-forward-arrow-64.svg')))
            parent.browser.back_button.setIcon(QIcon(str(ICONPATH / 'icon-back-arrow-64.svg')))
        # Group Box Plot Tools
        parent.toolButtonHome.setIcon(QIcon(str(ICONPATH / 'icon-home-64.svg')))
        parent.toolButtonRemoveAllMVPlots.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        parent.toolButtonPopFigure.setIcon(QIcon(str(ICONPATH / 'icon-popout-64.svg')))
        parent.toolButtonAnnotate.setIcon(QIcon(str(ICONPATH / 'icon-annotate-64.svg')))
        parent.toolButtonPan.setIcon(QIcon(str(ICONPATH / 'icon-move-64.svg')))
        parent.toolButtonZoom.setIcon(QIcon(str(ICONPATH / 'icon-zoom-64.svg')))
        parent.toolButtonDistance.setIcon(QIcon(str(ICONPATH / 'icon-distance-64.svg')))
        # Calculator
        parent.actionCalculator.setIcon(QIcon(str(ICONPATH / 'icon-calculator-64.svg')))
        # Style Toolbox
        parent.toolBoxStyle.setItemIcon(parent.style_tab['axes'],QIcon(str(ICONPATH / 'icon-axes-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['text'],QIcon(str(ICONPATH / 'icon-text-and-scales-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['markers'],QIcon(str(ICONPATH / 'icon-marker-and-lines-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['colors'],QIcon(str(ICONPATH / 'icon-rgb-64.svg')))
        # Cluster tab
        if hasattr(parent, "mask_dock"):
            parent.mask_dock.cluster_tab.setTabIcon(parent.mask_tab['cluster'],QIcon(str(ICONPATH / 'icon-cluster-64.svg')))
            parent.actionClusterLink.setIcon(QIcon(str(ICONPATH / 'icon-link-64.svg')))
            parent.actionClusterDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-64.svg')))


