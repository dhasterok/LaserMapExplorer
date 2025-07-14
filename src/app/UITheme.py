import os, darkdetect
from PyQt6.QtGui import QIcon, QFont
from src.app.config import ICONPATH, load_stylesheet

def default_font():
    # set default font for application
    font = QFont()
    font.setPointSize(11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferDefault)

    return font

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

                self.parent.actionViewMode.setIcon(QIcon(os.path.join(ICONPATH,'icon-sun-and-moon-64.svg')))
                self.parent.actionViewMode.setIconText('Auto')
            case 1: # dark
                self.set_dark_theme()
            case 2: # light
                self.set_light_theme()

    def set_dark_theme(self):
        ss = load_stylesheet('dark.qss')
        self.app.setStyleSheet(ss)

        parent = self.parent

        parent.actionViewMode.setIcon(QIcon(os.path.join(ICONPATH,'icon-moon-64.svg')))
        parent.actionViewMode.setIconText('Dark')

        parent.actionSelectAnalytes.setIcon(QIcon(os.path.join(ICONPATH,'icon-atom-dark-64.svg')))
        parent.actionOpenProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-open-session-dark-64.svg')))
        parent.actionSaveProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-save-session-dark-64.svg')))
        parent.actionFullMap.setIcon(QIcon(os.path.join(ICONPATH,'icon-fit-to-width-dark-64.svg')))
        parent.actionCrop.setIcon(QIcon(os.path.join(ICONPATH,'icon-crop-dark-64.svg')))
        parent.actionSwapAxes.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-dark-64.svg')))
        parent.toolButtonSwapResolution.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-resolution-dark-64.svg')))
        # Notes
        if hasattr(parent,'notes') and parent.notes.isVisible():
            parent.notes.header_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-heading-dark-64.svg')))
            parent.notes.bold_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-bold-dark-64.svg')))
            parent.notes.italic_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-italics-dark-64.svg')))
            parent.notes.bullet_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-bullet-list-dark-64.svg')))
            parent.notes.number_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-numbered-list-dark-64.svg')))
            parent.notes.image_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-image-64.svg')))
            parent.notes.save_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-pdf-dark-64.svg')))
        # Reset Buttons
        parent.toolButtonXAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        parent.toolButtonYAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        parent.toolButtonZAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        parent.toolButtonCAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        #parent.toolButtonClusterColorReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        parent.toolButtonHistogramReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        # Plot Tree
        parent.toolButtonSortAnalyte.setIcon(QIcon(os.path.join(ICONPATH,'icon-sort-dark-64.svg')))
        parent.toolButtonRemovePlot.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Samples
        parent.toolBox.setItemIcon(parent.left_tab['sample'],QIcon(os.path.join(ICONPATH,'icon-atom-dark-64.svg')))
        parent.toolButtonScaleEqualize.setIcon(QIcon(os.path.join(ICONPATH,'icon-histeq-dark-64.svg')))
        parent.toolButtonAutoScale.setIcon(QIcon(os.path.join(ICONPATH,'icon-autoscale-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['process'],QIcon(os.path.join(ICONPATH,'icon-histogram-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['multidim'],QIcon(os.path.join(ICONPATH,'icon-dimensional-analysis-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['cluster'],QIcon(os.path.join(ICONPATH,'icon-cluster-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['scatter'],QIcon(os.path.join(ICONPATH,'icon-ternary-dark-64.svg')))
        # Spot Data
        if hasattr(parent,"spot_tools"):
            parent.toolButtonSpotMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-dark-64.svg')))
            parent.toolButtonSpotToggle.setIcon(QIcon(os.path.join(ICONPATH,'icon-show-hide-dark-64.svg')))
            parent.toolButtonSpotSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
            parent.toolButtonSpotAnalysis.setIcon(QIcon(os.path.join(ICONPATH,'icon-analysis-dark-64.svg')))
            parent.toolButtonSpotRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # N-Dim
        parent.toolBox.setItemIcon(parent.left_tab['ndim'],QIcon(os.path.join(ICONPATH,'icon-TEC-dark-64.svg')))
        parent.toolButtonNDimDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-dark-64.svg')))
        parent.toolButtonNDimUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-dark-64.svg')))
        parent.toolButtonNDimSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        parent.toolButtonNDimRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Filter
        #parent.toolButtonFilterSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        #parent.toolButtonFilterUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-dark-64.svg')))
        #parent.toolButtonFilterDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-dark-64.svg')))
        #parent.toolButtonFilterRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Polygons
        #parent.toolBox.setItemIcon(parent.left_tab['polygons'],QIcon(os.path.join(ICONPATH,'icon-polygon-new-dark-64.svg')))
        #parent.toolButtonPolyCreate.setIcon(QIcon(os.path.join(ICONPATH,'icon-polygon-new-dark-64.svg')))
        #parent.toolButtonPolyAddPoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-add-point-dark-64.svg')))
        #parent.toolButtonPolyRemovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-remove-point-dark-64.svg')))
        #parent.toolButtonPolyMovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-dark-64.svg')))
        #parent.toolButtonPolyLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-dark-64.svg')))
        #parent.toolButtonPolyDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-dark-64.svg')))
        #parent.toolButtonPolyDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Profile
        #parent.toolBox.setItemIcon(parent.left_tab['profile'],QIcon(os.path.join(ICONPATH,'icon-profile-dark-64.svg')))
        #parent.toolButtonClearProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        #parent.toolButtonPointDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        #parent.toolButtonPointSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        #parent.toolButtonPointMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-dark-64.svg')))
        #parent.toolButtonProfileInterpolate.setIcon(QIcon(os.path.join(ICONPATH,'icon-interpolate-dark-64.svg')))
        #parent.toolButtonPlotProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-profile-dark-64.svg')))
        #parent.toolButtonPointDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-dark-64.svg')))
        #parent.toolButtonPointUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-dark-64.svg')))
        # Browser
        if hasattr(parent, 'browser'):
            parent.browser.home_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-dark-64.svg')))
            parent.browser.forward_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-forward-arrow-dark-64.svg')))
            parent.browser.back_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-back-arrow-dark-64.svg')))
        # Group Box Plot Tools
        parent.toolButtonHome.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-dark-64.svg')))
        parent.toolButtonRemoveAllMVPlots.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        parent.toolButtonPopFigure.setIcon(QIcon(os.path.join(ICONPATH,'icon-popout-dark-64.svg')))
        parent.toolButtonAnnotate.setIcon(QIcon(os.path.join(ICONPATH,'icon-annotate-dark-64.svg')))
        parent.toolButtonPan.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-dark-64.svg')))
        parent.toolButtonZoom.setIcon(QIcon(os.path.join(ICONPATH,'icon-zoom-dark-64.svg')))
        parent.toolButtonDistance.setIcon(QIcon(os.path.join(ICONPATH,'icon-distance-dark-64.svg')))
        # Calculator
        parent.actionCalculator.setIcon(QIcon(os.path.join(ICONPATH,'icon-calculator-dark-64.svg')))
        if hasattr(parent,'calculator'):
            parent.actionCalculate.setIcon(QIcon(os.path.join(ICONPATH,'icon-run-64.svg')))
            parent.toolButtonFormulaDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Style Toolbox
        parent.toolBoxStyle.setItemIcon(parent.style_tab['axes'],QIcon(os.path.join(ICONPATH,'icon-axes-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['text'],QIcon(os.path.join(ICONPATH,'icon-text-and-scales-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['markers'],QIcon(os.path.join(ICONPATH,'icon-marker-and-lines-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['colors'],QIcon(os.path.join(ICONPATH,'icon-rgb-dark-64.svg')))
        # Cluster tab
        #parent.tabWidgetMask.setItemIcon(parent.mask_tab['cluster'],QIcon(os.path.join(ICONPATH,'icon-cluster-dark-64.svg')))
        #parent.toolButtonClusterLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-dark-64.svg')))
        #parent.toolButtonClusterDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-dark-64.svg')))

    def set_light_theme(self):
        ss = load_stylesheet('light.qss')
        self.app.setStyleSheet(ss)

        parent = self.parent

        parent.actionViewMode.setIcon(QIcon(os.path.join(ICONPATH,'icon-sun-64.svg')))
        parent.actionViewMode.setIconText('Light')

        parent.actionSelectAnalytes.setIcon(QIcon(os.path.join(ICONPATH,'icon-atom-64.svg')))
        parent.actionOpenProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-open-session-64.svg')))
        parent.actionSaveProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-save-session-64.svg')))
        parent.actionFullMap.setIcon(QIcon(os.path.join(ICONPATH,'icon-fit-to-width-64.svg')))
        parent.actionCrop.setIcon(QIcon(os.path.join(ICONPATH,'icon-crop-64.svg')))
        parent.actionSwapAxes.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-64.svg')))
        parent.toolButtonSwapResolution.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-resolution-64.svg')))
        # Notes
        if hasattr(parent,'notes') and parent.notes.isVisible():
            parent.notes.header_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-heading-64.svg')))
            parent.notes.bold_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-bold-64.svg')))
            parent.notes.italic_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-italics-64.svg')))
            parent.notes.literal_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-literal-64.svg')))
            parent.notes.subscript_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-subscript-64.svg')))
            parent.notes.superscript_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-superscript-64.svg')))
            parent.notes.math_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-equation-64.svg')))
            parent.notes.hyperlink_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-hyperlink-64.svg')))
            parent.notes.cite_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-cite-64.svg')))
            parent.notes.bullet_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-bullet-list-64.svg')))
            parent.notes.number_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-numbered-list-64.svg')))
            parent.notes.image_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-image-dark-64.svg')))
            parent.notes.save_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-pdf-64.svg')))
        # Reset Buttons
        parent.toolButtonXAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        parent.toolButtonYAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        parent.toolButtonZAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        parent.toolButtonCAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        if hasattr(parent,"mask_dock"):
            parent.mask_dock.actionClusterColorReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        parent.toolButtonHistogramReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        # Plot Tree
        parent.toolButtonSortAnalyte.setIcon(QIcon(os.path.join(ICONPATH,'icon-sort-64.svg')))
        parent.toolButtonRemovePlot.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Samples
        parent.toolBox.setItemIcon(parent.left_tab['sample'],QIcon(os.path.join(ICONPATH,'icon-atom-64.svg')))
        parent.toolButtonScaleEqualize.setIcon(QIcon(os.path.join(ICONPATH,'icon-histeq-64.svg')))
        parent.toolButtonAutoScale.setIcon(QIcon(os.path.join(ICONPATH,'icon-autoscale-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['process'],QIcon(os.path.join(ICONPATH,'icon-histogram-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['multidim'],QIcon(os.path.join(ICONPATH,'icon-dimensional-analysis-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['cluster'],QIcon(os.path.join(ICONPATH,'icon-cluster-64.svg')))
        parent.toolBox.setItemIcon(parent.left_tab['scatter'],QIcon(os.path.join(ICONPATH,'icon-ternary-64.svg')))
        # Spot Data
        if hasattr(parent,"spot_tools"):
            parent.toolButtonSpotMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-64.svg')))
            parent.toolButtonSpotToggle.setIcon(QIcon(os.path.join(ICONPATH,'icon-show-hide-64.svg')))
            parent.toolButtonSpotSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
            parent.toolButtonSpotAnalysis.setIcon(QIcon(os.path.join(ICONPATH,'icon-analysis-64.svg')))
            parent.toolButtonSpotRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # N-Dim
        parent.toolBox.setItemIcon(parent.left_tab['ndim'],QIcon(os.path.join(ICONPATH,'icon-TEC-64.svg')))
        parent.toolButtonNDimDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-64.svg')))
        parent.toolButtonNDimUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-64.svg')))
        parent.toolButtonNDimSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
        parent.toolButtonNDimRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Filter
        if hasattr(parent,"mask_dock"):
            parent.actionFilterSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
            parent.actionFilterUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-64.svg')))
            parent.actionFilterDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-64.svg')))
            parent.actionFilterRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
            # Polygons
            parent.toolBox.setItemIcon(parent.mask_tab['polygon'],QIcon(os.path.join(ICONPATH,'icon-polygon-new-64.svg')))
            parent.actionPolyCreate.setIcon(QIcon(os.path.join(ICONPATH,'icon-polygon-new-64.svg')))
            parent.actionPolyAddPoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-add-point-64.svg')))
            parent.actionPolyRemovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-remove-point-64.svg')))
            parent.actionPolyMovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-64.svg')))
            parent.actionPolyLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-64.svg')))
            parent.actionPolyDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-64.svg')))
            parent.actionPolyDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Profile
        #parent.toolBox.setItemIcon(parent.left_tab['profile'],QIcon(os.path.join(ICONPATH,'icon-profile-64.svg')))
        #parent.toolButtonClearProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        #parent.toolButtonPointDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        #parent.toolButtonPointSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
        #parent.toolButtonPointMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-64.svg')))
        #parent.toolButtonProfileInterpolate.setIcon(QIcon(os.path.join(ICONPATH,'icon-interpolate-64.svg')))
        #parent.toolButtonPlotProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-profile-64.svg')))
        #parent.toolButtonPointDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-64.svg')))
        #parent.toolButtonPointUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-64.svg')))
        # Browser
        if hasattr(parent, 'browser'):
            parent.browser.home_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-64.svg')))
            parent.browser.forward_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-forward-arrow-64.svg')))
            parent.browser.back_button.setIcon(QIcon(os.path.join(ICONPATH,'icon-back-arrow-64.svg')))
        # Group Box Plot Tools
        parent.toolButtonHome.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-64.svg')))
        parent.toolButtonRemoveAllMVPlots.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        parent.toolButtonPopFigure.setIcon(QIcon(os.path.join(ICONPATH,'icon-popout-64.svg')))
        parent.toolButtonAnnotate.setIcon(QIcon(os.path.join(ICONPATH,'icon-annotate-64.svg')))
        parent.toolButtonPan.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-64.svg')))
        parent.toolButtonZoom.setIcon(QIcon(os.path.join(ICONPATH,'icon-zoom-64.svg')))
        parent.toolButtonDistance.setIcon(QIcon(os.path.join(ICONPATH,'icon-distance-64.svg')))
        # Calculator
        parent.actionCalculator.setIcon(QIcon(os.path.join(ICONPATH,'icon-calculator-64.svg')))
        if hasattr(parent,'calculator'):
            parent.calculator.actionCalculate.setIcon(QIcon(os.path.join(ICONPATH,'icon-run-64.svg')))
            parent.calculator.toolButtonFormulaDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Style Toolbox
        parent.toolBoxStyle.setItemIcon(parent.style_tab['axes'],QIcon(os.path.join(ICONPATH,'icon-axes-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['text'],QIcon(os.path.join(ICONPATH,'icon-text-and-scales-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['markers'],QIcon(os.path.join(ICONPATH,'icon-marker-and-lines-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['colors'],QIcon(os.path.join(ICONPATH,'icon-rgb-64.svg')))
        # Cluster tab
        if hasattr(parent, "mask_dock"):
            parent.mask_dock.cluster_tab.setTabIcon(parent.mask_tab['cluster'],QIcon(os.path.join(ICONPATH,'icon-cluster-64.svg')))
            parent.actionClusterLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-64.svg')))
            parent.actionClusterDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-64.svg')))


