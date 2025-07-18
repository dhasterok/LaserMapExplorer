import os, re, copy, pickle
from PyQt6.QtWidgets import ( QColorDialog, QTableWidgetItem, QMessageBox, QInputDialog )
from PyQt6.QtGui import ( QDoubleValidator, QFont, QFontDatabase )
from pyqtgraph import colormap
import src.common.format as fmt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import src.common.csvdict as csvdict
from src.common.colorfunc import get_hex_color, get_rgb_color
from src.app.config import BASEDIR
from src.app.StyleToolbox import StyleData, StyleTheme
from src.common.ScheduleTimer import Scheduler
from src.common.Logger import auto_log_methods, log


@auto_log_methods(logger_key='Style')
class StylingDock(StyleData, StyleTheme):
    def __init__(self, parent):
        self.ui = parent
        self.app_data = parent.app_data

        super().__init__(self)

        self.logger_key = 'Style'

        self.axis_widget_dict = {
            'label': [parent.labelX, parent.labelY, parent.labelZ, parent.labelC],
            'parentbox': [parent.comboBoxFieldTypeX, parent.comboBoxFieldTypeY, parent.comboBoxFieldTypeZ, parent.comboBoxFieldTypeC],
            'childbox': [parent.comboBoxFieldX, parent.comboBoxFieldY, parent.comboBoxFieldZ, parent.comboBoxFieldC],
            'spinbox': [parent.spinBoxFieldX, parent.spinBoxFieldY, parent.spinBoxFieldZ, parent.spinBoxFieldC],
            'scalebox': [parent.comboBoxXScale, parent.comboBoxYScale, parent.comboBoxZScale, parent.comboBoxCScale],
            'axis_label': [parent.lineEditXLabel, parent.lineEditYLabel, parent.lineEditZLabel, parent.lineEditCLabel],
            'lbound': [parent.lineEditXLB, parent.lineEditYLB, parent.lineEditZLB, parent.lineEditCLB],
            'ubound': [parent.lineEditXUB, parent.lineEditYUB, parent.lineEditZUB, parent.lineEditCUB],
        }


        # initialize style themes and associated widgets
        parent.comboBoxStyleTheme.clear()
        parent.comboBoxStyleTheme.addItems(self.load_theme_names())
        parent.comboBoxStyleTheme.setCurrentIndex(0)
        
        self.ui.comboBoxStyleTheme.activated.connect(lambda: setattr(self, "style_dict", self.read_theme(self.ui.comboBoxStyleTheme.currentText())))
        self.ui.toolButtonSaveTheme.clicked.connect(self.save_style_theme)

        self.style_dict = self.default_style_dict()

        # toggles signals from widgets, if false, blocks widgets from sending signals
        self._signal_state = True

        # used to schedule plot updates
        self.scheduler = Scheduler(callback=self.ui.update_SV)

        self.ui.fontComboBox.setCurrentFont(QFont(self.default_plot_style['Font'], 11))

        self.ui.comboBoxHistType.activated.connect(self.schedule_update)
        self.ui.toolButtonNDimAnalyteAdd.clicked.connect(self.schedule_update)
        self.ui.toolButtonNDimAnalyteSetAdd.clicked.connect(self.schedule_update)
        self.ui.toolButtonNDimUp.clicked.connect(self.schedule_update)
        self.ui.toolButtonNDimDown.clicked.connect(self.schedule_update)
        self.ui.toolButtonNDimRemove.clicked.connect(self.schedule_update)
        
        self.ui.comboBoxMarker.clear()
        self.ui.comboBoxMarker.addItems(self.marker_dict.keys())

        self._plot_type = "field map"

        self.ui.comboBoxFieldX.activated.connect(lambda: self.axis_variable_changed(self.ui.comboBoxFieldTypeX.currentText(), self.ui.comboBoxFieldX.currentText(), 'x'))
        self.ui.comboBoxFieldY.activated.connect(lambda: self.axis_variable_changed(self.ui.comboBoxFieldTypeY.currentText(), self.ui.comboBoxFieldY.currentText(), 'y'))
        self.ui.comboBoxFieldZ.activated.connect(lambda: self.axis_variable_changed(self.ui.comboBoxFieldTypeZ.currentText(), self.ui.comboBoxFieldZ.currentText(), 'z'))

        # comboBox with plot type
        # overlay and annotation properties
        #self.ui.checkBoxShowMass.stateChanged.connect(self.ui.update_show_mass)
        #self.ui.toolButtonOverlayColor.clicked.connect(self.overlay_color_callback)
        #self.ui.toolButtonMarkerColor.clicked.connect(self.marker_color_callback)
        #self.ui.toolButtonLineColor.clicked.connect(self.line_color_callback)
        #self.ui.toolButtonXAxisReset.clicked.connect(lambda: self.axis_reset_callback('x'))
        #self.ui.toolButtonYAxisReset.clicked.connect(lambda: self.axis_reset_callback('y'))
        #self.ui.toolButtonCAxisReset.clicked.connect(lambda: self.axis_reset_callback('c'))
        #self.toolButtonOverlayColor.setStyleSheet("background-color: white;")

        # add list of colormaps to comboBoxFieldColormap and set callbacks
        self.ui.comboBoxFieldColormap.clear()
        self.ui.comboBoxFieldColormap.addItems(list(self.custom_color_dict.keys())+self.mpl_colormaps)
        #self.ui.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        #self.ui.checkBoxReverseColormap.stateChanged.connect(self.colormap_direction_callback)

        # callback functions
        self.ui.comboBoxPlotType.currentTextChanged.connect(lambda: setattr(self, 'plot_type', self.ui.comboBoxPlotType.currentText()))
        self.ui.actionUpdatePlot.triggered.connect(lambda: self.update_plot_type(force=True))


        # axes
        #self.ui.lineEditXLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('x',self.ui.lineEditXLabel.text()))
        #self.ui.lineEditYLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('y',self.ui.lineEditYLabel.text()))
        #self.ui.lineEditZLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('z',self.ui.lineEditZLabel.text()))
        #self.ui.lineEditCLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('c',self.ui.lineEditCLabel.text()))

        #self.ui.comboBoxXScale.activated.connect(lambda: self.axis_scale_callback(self.ui.comboBoxXScale,'x'))
        #self.ui.comboBoxYScale.activated.connect(lambda: self.axis_scale_callback(self.ui.comboBoxYScale,'y'))
        #self.ui.comboBoxCScale.activated.connect(lambda: self.axis_scale_callback(self.ui.comboBoxCScale,'c'))

        self.ui.lineEditXLB.setValidator(QDoubleValidator())
        self.ui.lineEditXLB.precision = 3
        self.ui.lineEditXLB.toward = 0
        self.ui.lineEditXUB.setValidator(QDoubleValidator())
        self.ui.lineEditXUB.precision = 3
        self.ui.lineEditXUB.toward = 1
        self.ui.lineEditYLB.setValidator(QDoubleValidator())
        self.ui.lineEditYLB.precision = 3
        self.ui.lineEditYLB.toward = 0
        self.ui.lineEditYUB.setValidator(QDoubleValidator())
        self.ui.lineEditYUB.precision = 3
        self.ui.lineEditYUB.toward = 1
        self.ui.lineEditZLB.setValidator(QDoubleValidator())
        self.ui.lineEditZLB.precision = 3
        self.ui.lineEditZLB.toward = 0
        self.ui.lineEditZUB.setValidator(QDoubleValidator())
        self.ui.lineEditZUB.precision = 3
        self.ui.lineEditZUB.toward = 1
        self.ui.lineEditCLB.setValidator(QDoubleValidator())
        self.ui.lineEditCLB.precision = 3
        self.ui.lineEditCLB.toward = 0
        self.ui.lineEditCUB.setValidator(QDoubleValidator())
        self.ui.lineEditCUB.precision = 3
        self.ui.lineEditCUB.toward = 1
        self.ui.lineEditAspectRatio.setValidator(QDoubleValidator())
        self.ui.lineEditAspectRatio.precision = 3
        self.ui.lineEditAspectRatio.toward = 1

        #self.ui.lineEditXLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 0, float(self.ui.lineEditXLB.text())))
        #self.ui.lineEditXUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 1, float(self.ui.lineEditXUB.text())))
        #self.ui.lineEditYLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 0, float(self.ui.lineEditYLB.text())))
        #self.ui.lineEditYUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 1, float(self.ui.lineEditYUB.text())))
        #self.ui.lineEditZLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('z', 0, float(self.ui.lineEditZLB.text())))
        #self.ui.lineEditZUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('z', 1, float(self.ui.lineEditZUB.text())))
        #self.ui.lineEditCLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 0, float(self.ui.lineEditCLB.text())))
        #self.ui.lineEditCUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 1, float(self.ui.lineEditCUB.text())))

        #self.ui.lineEditAspectRatio.editingFinished.connect(self.aspect_ratio_callback)
        #self.ui.comboBoxTickDirection.activated.connect(self.tickdir_callback)
        # annotations
        #self.ui.fontComboBox.activated.connect(self.font_callback)
        #self.ui.doubleSpinBoxFontSize.valueChanged.connect(self.font_size_callback)
        # ---------
        # These are tools are for future use, when individual annotations can be added
        self.ui.tableWidgetAnnotation.setVisible(False)
        self.ui.toolButtonAnnotationDelete.setVisible(False)
        self.ui.toolButtonAnnotationSelectAll.setVisible(False)
        # ---------

        # scales
        #self.ui.lineEditScaleLength.setValidator(QDoubleValidator())
        #self.ui.comboBoxScaleDirection.activated.connect(self.update_scale_direction)
        #self.ui.comboBoxScaleLocation.activated.connect(self.scale_location_callback)
        #self.ui.lineEditScaleLength.editingFinished.connect(lambda: setattr(self, 'scale_length', self.ui.lineEditScaleLength.value))
        #overlay color
        #self.ui.comboBoxMarker.activated.connect(self.marker_symbol_callback)
        #self.ui.doubleSpinBoxMarkerSize.valueChanged.connect(self.marker_size_callback)
        #self.ui.horizontalSliderMarkerAlpha.sliderReleased.connect(self.slider_alpha_changed)
        # lines
        #self.ui.doubleSpinBoxLineWidth.valueChanged.connect(self.line_width_callback)
        #self.ui.lineEditLengthMultiplier.editingFinished.connect(self.length_multiplier_callback)
        # colors
        # marker color
        #self.ui.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        #self.ui.comboBoxCbarDirection.activated.connect(self.cbar_direction_callback)
        # resolution
        #self.ui.spinBoxHeatmapResolution.valueChanged.connect(self.resolution_callback)

        # ternary colormaps
        self._ternary_colormap = ""
        self._ternary_color_x = ""
        self._ternary_color_y = ""
        self._ternary_color_z = ""
        self._ternary_color_m = ""
        
        self.ui.comboBoxTernaryColormap.clear()

        self.ui.comboBoxTernaryColormap.addItems(self.color_schemes)
        self.ui.comboBoxTernaryColormap.addItem('user defined')

        # dialog for adding and saving new colormaps
        self.ui.toolButtonSaveTernaryColormap.clicked.connect(self.input_ternary_name_dlg)

        # select new ternary colors
        self.ui.toolButtonTCmapXColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapXColor))
        self.ui.toolButtonTCmapYColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapYColor))
        self.ui.toolButtonTCmapZColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapZColor))
        self.ui.toolButtonTCmapMColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapMColor))
        self.ui.comboBoxTernaryColormap.currentIndexChanged.connect(lambda: self.ternary_colormap_changed())

        self.connect_observer()
        self.connect_logger()

        self.ternary_colormap_changed()

        self._signal_state = False

        self.set_style_widgets()

    def connect_observer(self):
        """Connects properties to observer functions."""
        self.add_observer("plot_type", self.update_plot_type)
        self.add_observer("xlim", self.update_xlim_lineedits)
        self.add_observer("xlabel", self.update_xlabel_lineedit)
        self.add_observer("xscale", self.update_xscale_combobox)
        self.add_observer("ylim", self.update_ylim_lineedits)
        self.add_observer("ylabel", self.update_ylabel_lineedit)
        self.add_observer("yscale", self.update_yscale_combobox)
        self.add_observer("zlim", self.update_zlim_lineedits)
        self.add_observer("zlabel", self.update_zlabel_lineedit)
        self.add_observer("zscale", self.update_zscale_combobox)
        self.add_observer("aspect_ratio", self.update_aspect_ratio_lineedit)
        self.add_observer("tick_dir", self.update_tick_dir_combobox)
        self.add_observer("font_family", self.update_font_family_combobox)
        self.add_observer("font_size", self.update_font_size_spinbox)
        self.add_observer("scale_dir", self.update_scale_direction_combobox)
        self.add_observer("scale_location", self.update_scale_location_combobox)
        self.add_observer("scale_length", self.update_scale_length_lineedit)
        self.add_observer("overlay_color", self.update_overlay_color_toolbutton)
        self.add_observer("show_mass", self.update_show_mass_checkbox)
        self.add_observer("marker_symbol", self.update_marker_symbol_combobox)
        self.add_observer("marker_size", self.update_marker_size_spinbox)
        self.add_observer("marker_color", self.update_marker_color_toolbutton)
        self.add_observer("marker_alpha", self.update_marker_alpha_slider)
        self.add_observer("line_width", self.update_line_width_combobox)
        self.add_observer("line_multiplier", self.update_line_multiplier_lineedit)
        self.add_observer("line_color", self.update_line_color_toolbutton)
        self.add_observer("cmap", self.update_cmap_combobox)
        self.add_observer("cbar_reverse", self.update_cbar_reverse_checkbox)
        self.add_observer("cbar_direction", self.update_cbar_direction_combobox)
        self.add_observer("clim", self.update_clim_lineedits)
        self.add_observer("clabel", self.update_clabel_lineedit)
        self.add_observer("cscale", self.update_cscale_combobox)
        self.add_observer("resolution", self.update_resolution_spinbox)

        # ternary maps
        self.add_observer("ternary_colormap", self.update_ternary_colormap)
        self.add_observer("ternary_color_x", self.update_ternary_color_x)
        self.add_observer("ternary_color_y", self.update_ternary_color_y)
        self.add_observer("ternary_color_z", self.update_ternary_color_z)
        self.add_observer("ternary_color_m", self.update_ternary_color_m)

    def connect_logger(self):
        """Connects widgets to logger."""
        self.ui.comboBoxStyleTheme.activated.connect(lambda: log(f"comboBoxStyleTheme value=[{self.ui.comboBoxStyleTheme.currentText()}]", prefix="UI"))
        self.ui.toolButtonSaveTheme.clicked.connect(lambda: log("toolButtonTheme", prefix="UI"))

        # axes and labels
        self.ui.lineEditXLabel.editingFinished.connect(lambda: log(f"lineEditXLabel value=[{self.ui.lineEditXLabel.text()}]", prefix="UI"))
        self.ui.lineEditXLB.editingFinished.connect(lambda: log(f"lineEditXLB value=[{self.ui.lineEditXLB.value}]", prefix="UI"))
        self.ui.lineEditXUB.editingFinished.connect(lambda: log(f"lineEditXUB value=[{self.ui.lineEditXUB.value}]", prefix="UI"))
        self.ui.toolButtonXAxisReset.clicked.connect(lambda: log("toolButtonXAxisReset", prefix="UI"))
        self.ui.comboBoxXScale.activated.connect(lambda: log(f"comboBoxXScale value=[{self.ui.comboBoxXScale.currentText()}]", prefix="UI"))
        self.ui.lineEditYLabel.editingFinished.connect(lambda: log(f"lineEditYLabel value=[{self.ui.lineEditYLabel.text()}]", prefix="UI"))
        self.ui.lineEditYLB.editingFinished.connect(lambda: log(f"lineEditYLB value=[{self.ui.lineEditYLB.value}]", prefix="UI"))
        self.ui.lineEditYUB.editingFinished.connect(lambda: log(f"lineEditYUB value=[{self.ui.lineEditYUB.value}]", prefix="UI"))
        self.ui.toolButtonYAxisReset.clicked.connect(lambda: log("toolButtonYAxisReset", prefix="UI"))
        self.ui.comboBoxYScale.activated.connect(lambda: log(f"comboBoxYScale value=[{self.ui.comboBoxYScale.currentText()}]", prefix="UI"))
        self.ui.lineEditZLabel.editingFinished.connect(lambda: log(f"lineEditZLabel value=[{self.ui.lineEditZLabel.text()}]", prefix="UI"))
        self.ui.lineEditZLB.editingFinished.connect(lambda: log(f"lineEditZLB value=[{self.ui.lineEditZLB.value}]", prefix="UI"))
        self.ui.lineEditZUB.editingFinished.connect(lambda: log(f"lineEditZUB value=[{self.ui.lineEditZUB.value}]", prefix="UI"))
        self.ui.toolButtonZAxisReset.clicked.connect(lambda: log("toolButtonZAxisReset", prefix="UI"))
        self.ui.comboBoxZScale.activated.connect(lambda: log(f"comboBoxZScale value=[{self.ui.comboBoxZScale.currentText()}]", prefix="UI"))
        self.ui.lineEditAspectRatio.editingFinished.connect(lambda: log(f"lineEditAspectRatio value=[{self.ui.lineEditAspectRatio.text()}]", prefix="UI"))
        self.ui.comboBoxTickDirection.activated.connect(lambda: log(f"comboBoxTickDirection value=[{self.ui.comboBoxTickDirection.currentText()}]", prefix="UI"))

        # annotations and scale
        self.ui.comboBoxScaleDirection.activated.connect(lambda: log(f"comboBoxScaleDirection value=[{self.ui.comboBoxScaleDirection.currentText()}]", prefix="UI"))
        self.ui.comboBoxScaleLocation.activated.connect(lambda: log(f"comboBoxScaleLocation value=[{self.ui.comboBoxScaleLocation.currentText()}]", prefix="UI"))
        self.ui.lineEditScaleLength.editingFinished.connect(lambda: log(f"lineEditScaleLength value=[{self.ui.lineEditScaleLength.value}]", prefix="UI"))
        self.ui.toolButtonOverlayColor.clicked.connect(lambda: log("toolButtonOverlayColor", prefix="UI"))
        self.ui.fontComboBox.activated.connect(lambda: log(f"fontComboBox value=[{self.ui.fontComboBox.currentText()}]", prefix="UI"))
        self.ui.doubleSpinBoxFontSize.valueChanged.connect(lambda: log(f"doubleSpinBoxFontSize value=[{self.ui.doubleSpinBoxFontSize.value()}]", prefix="UI"))
        self.ui.checkBoxShowMass.checkStateChanged.connect(lambda: log(f"checkBoxShowMass value=[{self.ui.checkBoxShowMass.isChecked()}]", prefix="UI"))

        # markers and lines
        self.ui.comboBoxMarker.activated.connect(lambda: log(f"comboBoxMarker value=[{self.ui.comboBoxMarker.currentText()}]", prefix="UI"))
        self.ui.doubleSpinBoxMarkerSize.valueChanged.connect(lambda: log(f"doubleSpinBoxMarkerSize value=[{self.ui.doubleSpinBoxMarkerSize.value()}]", prefix="UI"))
        self.ui.toolButtonMarkerColor.clicked.connect(lambda: log("toolButtonMarkerColor", prefix="UI"))
        self.ui.horizontalSliderMarkerAlpha.valueChanged.connect(lambda: log(f"horizontalSliderMarkerAlpha value=[{self.ui.horizontalSliderMarkerAlpha.value()}]", prefix="UI"))
        self.ui.doubleSpinBoxLineWidth.valueChanged.connect(lambda: log(f"doubleSpinBoxLineWidth value=[{self.ui.doubleSpinBoxLineWidth.value()}]", prefix="UI"))
        self.ui.toolButtonLineColor.clicked.connect(lambda: log("toolButtonLineColor", prefix="UI"))
        self.ui.lineEditLengthMultiplier.editingFinished.connect(lambda: log(f"lineEditLengthMultiplier value=[{self.ui.lineEditLengthMultiplier.value}]", prefix="UI"))

        # coloring
        self.ui.lineEditCLabel.editingFinished.connect(lambda: log(f"lineEditCLabel value=[{self.ui.lineEditCLabel.text()}]", prefix="UI"))
        self.ui.lineEditCLB.editingFinished.connect(lambda: log(f"lineEditCLB value=[{self.ui.lineEditCLB.value}]", prefix="UI"))
        self.ui.lineEditCUB.editingFinished.connect(lambda: log(f"lineEditCUB value=[{self.ui.lineEditCUB.value}]", prefix="UI"))
        self.ui.toolButtonCAxisReset.clicked.connect(lambda: log("toolButtonCAxisReset", prefix="UI"))
        self.ui.comboBoxCScale.activated.connect(lambda: log(f"comboBoxCScale value=[{self.ui.comboBoxCScale.currentText()}]", prefix="UI"))
        self.ui.comboBoxFieldColormap.activated.connect(lambda: log(f"comboBoxFieldColormap value=[{self.ui.comboBoxFieldColormap.currentText()}]", prefix="UI"))
        self.ui.comboBoxCbarDirection.activated.connect(lambda: log(f"comboBoxCbarDirection value=[{self.ui.comboBoxCbarDirection.currentText()}]", prefix="UI"))
        self.ui.checkBoxReverseColormap.checkStateChanged.connect(lambda: log(f"checkBoxReverseColormap value=[{self.ui.checkBoxReverseColormap.isChecked()}]", prefix="UI"))
        self.ui.spinBoxHeatmapResolution.valueChanged.connect(lambda: log(f"spinBoxHeatmapResolution value=[{self.ui.spinBoxHeatmapResolution.value()}]", prefix="UI"))

        # ternary colormap
        self.ui.comboBoxTernaryColormap.activated.connect(lambda: log(f"comboBoxTernaryColormap value=[{self.ui.comboBoxTernaryColormap.currentText()}]", prefix="UI"))
        self.ui.toolButtonTCmapXColor.clicked.connect(lambda: log("toolButtonTCmapXColor", prefix="UI"))
        self.ui.toolButtonTCmapYColor.clicked.connect(lambda: log("toolButtonTCmapYColor", prefix="UI"))
        self.ui.toolButtonTCmapZColor.clicked.connect(lambda: log("toolButtonTCmapZColor", prefix="UI"))
        self.ui.toolButtonTCmapMColor.clicked.connect(lambda: log("toolButtonTCmapMColor", prefix="UI"))
        self.ui.toolButtonSaveTernaryColormap.clicked.connect(lambda: log("toolButtonSaveTernaryColormap", prefix="UI"))
        self.ui.toolButtonTernaryMap.clicked.connect(lambda: log("toolButtonTernaryMap", prefix="UI"))

    @property
    def signal_state(self):
        """
        Signal state for styling related widgets.
        
        When ``signal_state == False``, signals from widgets are blocked.
        """
        return self._signal_state
    
    @signal_state.setter
    def signal_state(self, state):
        if not isinstance(state, bool):
            raise TypeError("signal_state must be a bool")
        
        self._signal_state = state
        self.toggle_signals()

    def schedule_update(self):
        """Schedules an update to a plot only when ``self.ui.plot_flag == True``."""
        if self.ui.plot_flag:
            self.scheduler.schedule_update()

    def save_style_theme(self):
        """Saves a style dictionary to a theme.
        
        The theme is added to ``MainWindow.comboBoxStyleTheme`` and the style widget
        settings for each plot type (``MainWindow.styles``) are saved as a
        dictionary into the theme name with a ``.sty`` extension."""
        name = self.input_theme_name_dlg(self.style_dict)
        self.ui.comboBoxStyleTheme.addItem(name)

    def toggle_signals(self):
        """Toggles signals from all style widgets.  Useful when updating many widgets."""        
        ui = self.ui

        ui.comboBoxPlotType.blockSignals(self._signal_state)

       # x-axis widgets
        ui.lineEditXLB.blockSignals(self._signal_state)
        ui.lineEditXUB.blockSignals(self._signal_state)
        ui.comboBoxXScale.blockSignals(self._signal_state)
        ui.lineEditXLabel.blockSignals(self._signal_state)

        # y-axis widgets
        ui.lineEditYLB.blockSignals(self._signal_state)
        ui.lineEditYUB.blockSignals(self._signal_state)
        ui.comboBoxYScale.blockSignals(self._signal_state)
        ui.lineEditYLabel.blockSignals(self._signal_state)

        # z-axis widgets
        ui.lineEditZLB.blockSignals(self._signal_state)
        ui.lineEditZUB.blockSignals(self._signal_state)
        ui.comboBoxZScale.blockSignals(self._signal_state)
        ui.lineEditZLabel.blockSignals(self._signal_state)

        # other axis properties
        ui.lineEditAspectRatio.blockSignals(self._signal_state)
        ui.comboBoxTickDirection.blockSignals(self._signal_state)

        # annotations
        ui.fontComboBox.blockSignals(self._signal_state)
        ui.doubleSpinBoxFontSize.blockSignals(self._signal_state)
        ui.checkBoxShowMass.blockSignals(self._signal_state)

        # scale
        ui.comboBoxScaleDirection.blockSignals(self._signal_state)
        ui.comboBoxScaleLocation.blockSignals(self._signal_state)
        ui.lineEditScaleLength.blockSignals(self._signal_state)
        ui.toolButtonOverlayColor.blockSignals(self._signal_state)

        # markers and lines
        ui.comboBoxMarker.blockSignals(self._signal_state)
        ui.doubleSpinBoxMarkerSize.blockSignals(self._signal_state)
        ui.toolButtonMarkerColor.blockSignals(self._signal_state)
        ui.horizontalSliderMarkerAlpha.blockSignals(self._signal_state)
        ui.doubleSpinBoxLineWidth.blockSignals(self._signal_state)
        ui.toolButtonLineColor.blockSignals(self._signal_state)
        ui.lineEditLengthMultiplier.blockSignals(self._signal_state)

        # coloring
        ui.comboBoxFieldTypeC.blockSignals(self._signal_state)
        ui.comboBoxFieldC.blockSignals(self._signal_state)
        ui.spinBoxHeatmapResolution.blockSignals(self._signal_state)
        ui.comboBoxFieldColormap.blockSignals(self._signal_state)
        ui.checkBoxReverseColormap.blockSignals(self._signal_state)
        ui.lineEditCLB.blockSignals(self._signal_state)
        ui.lineEditCUB.blockSignals(self._signal_state)
        ui.comboBoxCScale.blockSignals(self._signal_state)
        ui.lineEditCLabel.blockSignals(self._signal_state)
        ui.comboBoxCbarDirection.blockSignals(self._signal_state)

    # update functions
    # -------------------------------------
    # ------------------------------------------------------------------
    # Axes – X
    # ------------------------------------------------------------------
    def update_xlim_lineedits(self, value):
        if value == [self.ui.lineEditXLB.value, self.ui.lineEditXUB.value]:
            return
        self.ui.lineEditXLB.value = value[0]
        self.ui.lineEditXUB.value = value[1]
        self.schedule_update()

    def update_xlabel_lineedit(self, new_label):
        if new_label == self.ui.lineEditXLabel.text():
            return
        self.ui.lineEditXLabel.setText(new_label)
        self.schedule_update()

    def update_xscale_combobox(self, new_scale):
        if new_scale == self.ui.comboBoxXScale.currentText():
            return
        self.ui.comboBoxXScale.setCurrentText(new_scale)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Axes – Y
    # ------------------------------------------------------------------
    def update_ylim_lineedits(self, new_ylim):
        if new_ylim == [self.ui.lineEditYLB.value, self.ui.lineEditYUB.value]:
            return
        self.ui.lineEditYLB.value = new_ylim[0]
        self.ui.lineEditYUB.value = new_ylim[1]
        self.schedule_update()

    def update_ylabel_lineedit(self, new_label):
        if new_label == self.ui.lineEditYLabel.text():
            return
        self.ui.lineEditYLabel.setText(new_label)
        self.schedule_update()

    def update_yscale_combobox(self, new_scale):
        if new_scale == self.ui.comboBoxYScale.currentText():
            return
        self.ui.comboBoxYScale.setCurrentText(new_scale)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Axes – Z
    # ------------------------------------------------------------------
    def update_zlim_lineedits(self, new_zlim):
        if list(new_zlim) == [self.ui.lineEditZLB.value, self.ui.lineEditZUB.value]:
            return
        self.ui.lineEditZLB.value = new_zlim[0]
        self.ui.lineEditZUB.value = new_zlim[1]
        self.schedule_update()

    def update_zlabel_lineedit(self, new_label):
        if new_label == self.ui.lineEditZLabel.text():
            return
        self.ui.lineEditZLabel.setText(new_label)
        self.schedule_update()

    def update_zscale_combobox(self, new_scale):
        if new_scale == self.ui.comboBoxZScale.currentText():
            return
        self.ui.comboBoxZScale.setCurrentText(new_scale)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Aspect ratio & tick direction
    # ------------------------------------------------------------------
    def update_aspect_ratio_lineedit(self, new_aspect_ratio):
        if new_aspect_ratio == self.ui.lineEditAspectRatio.value:
            return
        self.ui.lineEditAspectRatio.value = new_aspect_ratio
        self.schedule_update()

    def update_tick_dir_combobox(self, new_tick_dir):
        if new_tick_dir == self.ui.comboBoxTickDirection.currentText():
            return
        self.ui.comboBoxTickDirection.setCurrentText(new_tick_dir)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Scale‑bar
    # ------------------------------------------------------------------
    def update_scale_location_combobox(self, new_scale_location):
        if new_scale_location == self.ui.comboBoxScaleLocation.currentText():
            return
        self.ui.comboBoxScaleLocation.setCurrentText(new_scale_location)
        self.schedule_update()

    def update_scale_length_lineedit(self, new_scale_length):
        if new_scale_length == self.ui.lineEditScaleLength.value:
            return
        self.ui.lineEditScaleLength.value = new_scale_length
        self.schedule_update()

    def update_overlay_color_toolbutton(self, new_color):
        desired = f"background-color: {new_color};"
        if desired == self.ui.toolButtonOverlayColor.styleSheet():
            return
        self.ui.toolButtonOverlayColor.setStyleSheet(desired)
        self.schedule_update()

    def update_show_mass_checkbox(self, new_value):
        if new_value == self.ui.checkBoxShowMass.isChecked():
            return
        self.ui.checkBoxShowMass.setChecked(new_value)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Marker
    # ------------------------------------------------------------------
    def update_marker_symbol_combobox(self, new_marker_symbol):
        if new_marker_symbol == self.ui.comboBoxMarker.currentText():
            return
        self.ui.comboBoxMarker.setCurrentText(new_marker_symbol)
        self.schedule_update()

    def update_marker_size_spinbox(self, new_marker_size):
        if new_marker_size == self.ui.doubleSpinBoxMarkerSize.value():
            return
        self.ui.doubleSpinBoxMarkerSize.setValue(new_marker_size)
        self.schedule_update()

    def update_marker_color_toolbutton(self, new_color):
        desired = f"background-color: {new_color};"
        if desired == self.ui.toolButtonMarkerColor.styleSheet():
            return
        self.ui.toolButtonMarkerColor.setStyleSheet(desired)
        self.schedule_update()

    def update_marker_alpha_slider(self, new_alpha):
        if new_alpha == self.ui.horizontalSliderMarkerAlpha.value():
            return
        self.ui.horizontalSliderMarkerAlpha.setValue(new_alpha)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Line
    # ------------------------------------------------------------------
    def update_line_width_combobox(self, new_line_width):
        if new_line_width == self.ui.doubleSpinBoxLineWidth.value():
            return
        self.ui.doubleSpinBoxLineWidth.setValue(new_line_width)
        self.schedule_update()

    def update_line_multiplier_lineedit(self, new_multiplier):
        if new_multiplier == self.ui.lineEditLengthMultiplier.value:
            return
        self.ui.lineEditLengthMultiplier.value = new_multiplier
        self.schedule_update()

    def update_line_color_toolbutton(self, new_color):
        desired = f"background-color: {new_color};"
        if desired == self.ui.toolButtonLineColor.styleSheet():
            return
        self.ui.toolButtonLineColor.setStyleSheet(desired)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------
    def update_font_family_combobox(self, new_font_family):
        if new_font_family == self.ui.fontComboBox.currentText():
            return
        self.ui.fontComboBox.setCurrentText(new_font_family)
        self.schedule_update()

    def update_font_size_spinbox(self, new_font_size):
        if new_font_size == self.ui.doubleSpinBoxFontSize.value():
            return
        self.ui.doubleSpinBoxFontSize.blockSignals(True)
        self.ui.doubleSpinBoxFontSize.setValue(new_font_size)
        self.ui.doubleSpinBoxFontSize.blockSignals(False)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Colormap / colour‑bar
    # ------------------------------------------------------------------
    def update_cmap_combobox(self, new_colormap):
        if new_colormap == self.ui.comboBoxFieldColormap.currentText():
            return
        self.ui.comboBoxFieldColormap.setCurrentText(new_colormap)
        self.schedule_update()

    def update_cbar_reverse_checkbox(self, new_value):
        if new_value == self.ui.checkBoxReverseColormap.isChecked():
            return
        self.ui.checkBoxReverseColormap.setChecked(new_value)
        self.schedule_update()

    def update_cbar_direction_combobox(self, new_cbar_direction):
        if new_cbar_direction == self.ui.comboBoxCbarDirection.currentText():
            return
        self.ui.comboBoxCbarDirection.setCurrentText(new_cbar_direction)
        self.schedule_update()

    def update_clim_lineedits(self, new_xlim):
        if list(new_xlim) == [self.ui.lineEditCLB.value, self.ui.lineEditCUB.value]:
            return
        self.ui.lineEditCLB.value = new_xlim[0]
        self.ui.lineEditCUB.value = new_xlim[1]
        self.schedule_update()

    def update_clabel_lineedit(self, new_label):
        if new_label == self.ui.lineEditCLabel.text():
            return
        self.ui.lineEditCLabel.setText(new_label)
        self.schedule_update()

    def update_cscale_combobox(self, new_scale):
        if new_scale == self.ui.comboBoxCScale.currentText():
            return
        self.ui.comboBoxCScale.setCurrentText(new_scale)
        self.schedule_update()

    # ------------------------------------------------------------------
    # Heat‑map resolution
    # ------------------------------------------------------------------
    def update_resolution_spinbox(self, new_resolution):
        if new_resolution == self.ui.spinBoxHeatmapResolution.value():
            return
        self.ui.spinBoxHeatmapResolution.setValue(new_resolution)
        if self.plot_type.lower() == "heatmap":
            self.schedule_update()


    # general style functions
    # -------------------------------------
 

    def disable_style_widgets(self):
        """Disables all style related widgets."""        
        ui = self.ui

        # x-axis widgets
        ui.lineEditXLB.setEnabled(False)
        ui.lineEditXUB.setEnabled(False)
        ui.comboBoxXScale.setEnabled(False)
        ui.lineEditXLabel.setEnabled(False)

        # y-axis widgets
        ui.lineEditYLB.setEnabled(False)
        ui.lineEditYUB.setEnabled(False)
        ui.comboBoxYScale.setEnabled(False)
        ui.lineEditYLabel.setEnabled(False)

        # z-axis widgets
        ui.lineEditZLB.setEnabled(False)
        ui.lineEditZUB.setEnabled(False)
        ui.comboBoxZScale.setEnabled(False)
        ui.lineEditZLabel.setEnabled(False)

        # other axis properties
        ui.lineEditAspectRatio.setEnabled(False)
        ui.comboBoxTickDirection.setEnabled(False)

        # annotations
        ui.fontComboBox.setEnabled(False)
        ui.doubleSpinBoxFontSize.setEnabled(False)
        ui.checkBoxShowMass.setEnabled(False)

        # scale
        ui.comboBoxScaleDirection.setEnabled(False)
        ui.comboBoxScaleLocation.setEnabled(False)
        ui.lineEditScaleLength.setEnabled(False)
        ui.toolButtonOverlayColor.setEnabled(False)

        # markers and lines
        ui.comboBoxMarker.setEnabled(False)
        ui.doubleSpinBoxMarkerSize.setEnabled(False)
        ui.toolButtonMarkerColor.setEnabled(False)
        ui.horizontalSliderMarkerAlpha.setEnabled(False)
        ui.doubleSpinBoxLineWidth.setEnabled(False)
        ui.toolButtonLineColor.setEnabled(False)
        ui.lineEditLengthMultiplier.setEnabled(False)

        # coloring
        ui.spinBoxHeatmapResolution.setEnabled(False)
        ui.comboBoxFieldColormap.setEnabled(False)
        ui.checkBoxReverseColormap.setEnabled(False)
        ui.lineEditCLB.setEnabled(False)
        ui.lineEditCUB.setEnabled(False)
        ui.comboBoxCScale.setEnabled(False)
        ui.lineEditCLabel.setEnabled(False)
        ui.comboBoxCbarDirection.setEnabled(False)

        # clusters

    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        ui = self.ui

        #print('toggle_style_widgets')
        plot_type = self.plot_type.lower()

        self.disable_style_widgets()

        # annotation properties
        ui.fontComboBox.setEnabled(True)
        ui.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type.lower():
            case 'field map' | 'gradient map':
                # axes properties
                ui.lineEditXLB.setEnabled(True)
                ui.lineEditXUB.setEnabled(True)

                ui.lineEditYLB.setEnabled(True)
                ui.lineEditYUB.setEnabled(True)

                # scalebar properties
                ui.comboBoxScaleDirection.setEnabled(True)
                ui.comboBoxScaleLocation.setEnabled(True)
                ui.lineEditScaleLength.setEnabled(True)
                ui.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if ui.app_data.sample_id != '' and len(ui.data[ui.app_data.sample_id].spotdata) != 0:
                    ui.comboBoxMarker.setEnabled(True)
                    ui.doubleSpinBoxMarkerSize.setEnabled(True)
                    ui.horizontalSliderMarkerAlpha.setEnabled(True)
                    ui.labelMarkerAlpha.setEnabled(True)

                    ui.toolButtonMarkerColor.setEnabled(True)

                # line properties
                ui.doubleSpinBoxLineWidth.setEnabled(True)
                ui.toolButtonLineColor.setEnabled(True)

                # color properties
                ui.comboBoxFieldColormap.setEnabled(True)
                ui.lineEditCLB.setEnabled(True)
                ui.lineEditCUB.setEnabled(True)
                ui.comboBoxCScale.setEnabled(True)
                ui.comboBoxCbarDirection.setEnabled(True)
                ui.lineEditCLabel.setEnabled(True)

            case 'correlation' | 'basis vectors':
                # axes properties
                ui.comboBoxTickDirection.setEnabled(True)

                # color properties
                ui.comboBoxFieldColormap.setEnabled(True)
                ui.lineEditCLB.setEnabled(True)
                ui.lineEditCUB.setEnabled(True)
                ui.comboBoxCbarDirection.setEnabled(True)

            case 'histogram':
                # axes properties
                ui.lineEditXLB.setEnabled(True)
                ui.lineEditXUB.setEnabled(True)
                ui.comboBoxXScale.setEnabled(True)
                ui.lineEditYLB.setEnabled(True)
                ui.lineEditYUB.setEnabled(True)
                ui.lineEditXLabel.setEnabled(True)
                ui.lineEditYLabel.setEnabled(True)
                ui.lineEditAspectRatio.setEnabled(True)
                ui.comboBoxTickDirection.setEnabled(True)

                # marker properties
                ui.horizontalSliderMarkerAlpha.setEnabled(True)
                ui.labelMarkerAlpha.setEnabled(True)

                # line properties
                ui.doubleSpinBoxLineWidth.setEnabled(True)
                ui.toolButtonLineColor.setEnabled(True)

                # color properties
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                if ui.comboBoxFieldTypeC.currentText().lower() == 'none':
                    ui.toolButtonMarkerColor.setEnabled(True)
                else:
                    ui.comboBoxCbarDirection.setEnabled(True)

            case 'scatter' | 'PCA scatter':
                # axes properties
                if (ui.toolBox.currentIndex() != ui.left_tab['scatter']) or (ui.comboBoxFieldZ.currentText() == ''):
                    ui.lineEditXLB.setEnabled(True)
                    ui.lineEditXUB.setEnabled(True)
                    ui.comboBoxXScale.setEnabled(True)
                    ui.lineEditYLB.setEnabled(True)
                    ui.lineEditYUB.setEnabled(True)
                    ui.comboBoxYScale.setEnabled(True)

                ui.lineEditXLabel.setEnabled(True)
                ui.lineEditYLabel.setEnabled(True)
                if ui.comboBoxFieldZ.currentText() != '':
                    ui.lineEditZLB.setEnabled(True)
                    ui.lineEditZUB.setEnabled(True)
                    ui.comboBoxZScale.setEnabled(True)
                    ui.lineEditZLabel.setEnabled(True)
                ui.lineEditAspectRatio.setEnabled(True)
                ui.comboBoxTickDirection.setEnabled(True)

                # marker properties
                ui.comboBoxMarker.setEnabled(True)
                ui.doubleSpinBoxMarkerSize.setEnabled(True)
                ui.horizontalSliderMarkerAlpha.setEnabled(True)
                ui.labelMarkerAlpha.setEnabled(True)

                # line properties
                if ui.comboBoxFieldZ.currentText() == '':
                    ui.doubleSpinBoxLineWidth.setEnabled(True)
                    ui.toolButtonLineColor.setEnabled(True)

                if plot_type == 'PCA scatter':
                    ui.lineEditLengthMultiplier.setEnabled(True)

                # color properties
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if ui.comboBoxFieldTypeC.currentText().lower() == 'none':
                    ui.toolButtonMarkerColor.setEnabled(True)

                elif ui.comboBoxFieldTypeC.currentText() == 'cluster':

                    ui.comboBoxCbarDirection.setEnabled(True)

                    ui.comboBoxFieldColormap.setEnabled(True)
                    ui.lineEditCLB.setEnabled(True)
                    ui.lineEditCUB.setEnabled(True)
                    ui.comboBoxCScale.setEnabled(True)
                    ui.comboBoxCbarDirection.setEnabled(True)
                    ui.lineEditCLabel.setEnabled(True)

            case 'heatmap' | 'PCA heatmap':
                # axes properties
                if (ui.toolBox.currentIndex() != ui.left_tab['scatter']) or (ui.comboBoxFieldZ.currentText() == ''):
                    ui.lineEditXLB.setEnabled(True)
                    ui.lineEditXUB.setEnabled(True)
                    ui.comboBoxXScale.setEnabled(True)
                    ui.lineEditYLB.setEnabled(True)
                    ui.lineEditYUB.setEnabled(True)
                    ui.comboBoxYScale.setEnabled(True)

                ui.lineEditXLabel.setEnabled(True)
                ui.lineEditYLabel.setEnabled(True)
                if (ui.toolBox.currentIndex() == ui.left_tab['scatter']) and (ui.comboBoxFieldZ.currentText() == ''):
                    ui.lineEditZLB.setEnabled(True)
                    ui.lineEditZUB.setEnabled(True)
                    ui.comboBoxZScale.setEnabled(True)
                    ui.lineEditZLabel.setEnabled(True)
                ui.lineEditAspectRatio.setEnabled(True)
                ui.comboBoxTickDirection.setEnabled(True)

                # line properties
                if ui.comboBoxFieldZ.currentText() == '':
                    ui.doubleSpinBoxLineWidth.setEnabled(True)
                    ui.toolButtonLineColor.setEnabled(True)

                if plot_type == 'PCA heatmap':
                    ui.lineEditLengthMultiplier.setEnabled(True)

                # color properties
                ui.comboBoxFieldColormap.setEnabled(True)
                ui.lineEditCLB.setEnabled(True)
                ui.lineEditCUB.setEnabled(True)
                ui.comboBoxCScale.setEnabled(True)
                ui.comboBoxCbarDirection.setEnabled(True)
                ui.lineEditCLabel.setEnabled(True)

                ui.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                ui.lineEditXLB.setEnabled(True)
                ui.lineEditXUB.setEnabled(True)
                ui.comboBoxXScale.setEnabled(True)
                ui.lineEditYLB.setEnabled(True)
                ui.lineEditYUB.setEnabled(True)
                ui.comboBoxYScale.setEnabled(True)
                ui.lineEditZLB.setEnabled(True)
                ui.lineEditZUB.setEnabled(True)
                ui.comboBoxZScale.setEnabled(True)
                ui.lineEditYLabel.setEnabled(True)
                ui.lineEditYLabel.setEnabled(True)
                ui.lineEditZLabel.setEnabled(True)

                # scalebar properties
                ui.comboBoxScaleDirection.setEnabled(True)
                ui.comboBoxScaleLocation.setEnabled(True)
                ui.lineEditScaleLength.setEnabled(True)
                ui.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if not ui.data[self.app_data.sample_id].spotdata.empty:
                    ui.comboBoxMarker.setEnabled(True)
                    ui.doubleSpinBoxMarkerSize.setEnabled(True)
                    ui.horizontalSliderMarkerAlpha.setEnabled(True)
                    ui.labelMarkerAlpha.setEnabled(True)

                    ui.toolButtonMarkerColor.setEnabled(True)

            case 'tec' | 'radar':
                # axes properties
                if plot_type == 'tec':
                    ui.lineEditYLB.setEnabled(True)
                    ui.lineEditYUB.setEnabled(True)
                    ui.lineEditYLabel.setEnabled(True)
                ui.lineEditAspectRatio.setEnabled(True)
                ui.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                ui.lineEditScaleLength.setEnabled(True)

                # marker properties
                ui.labelMarkerAlpha.setEnabled(True)

                # line properties
                ui.doubleSpinBoxLineWidth.setEnabled(True)
                ui.toolButtonLineColor.setEnabled(True)

                # color properties
                if ui.comboBoxFieldTypeC.currentText().lower() == 'none':
                    ui.toolButtonMarkerColor.setEnabled(True)
                elif ui.comboBoxFieldTypeC.currentText().lower() == 'cluster':
                    ui.comboBoxCbarDirection.setEnabled(True)

            case 'variance' | 'cluster performance':
                # axes properties
                ui.lineEditAspectRatio.setEnabled(True)
                ui.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                ui.lineEditScaleLength.setEnabled(True)
                ui.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                ui.comboBoxMarker.setEnabled(True)
                ui.doubleSpinBoxMarkerSize.setEnabled(True)

                # line properties
                ui.doubleSpinBoxLineWidth.setEnabled(True)
                ui.toolButtonLineColor.setEnabled(True)

                # color properties
                ui.toolButtonMarkerColor.setEnabled(True)

            case 'pca score' | 'cluster score' | 'cluster map':
                # axes properties
                ui.lineEditXLB.setEnabled(True)
                ui.lineEditXUB.setEnabled(True)
                ui.lineEditYLB.setEnabled(True)
                ui.lineEditYUB.setEnabled(True)

                # scalebar properties
                ui.comboBoxScaleDirection.setEnabled(True)
                ui.comboBoxScaleLocation.setEnabled(True)
                ui.lineEditScaleLength.setEnabled(True)
                ui.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                # if len(ui.spotdata) != 0:
                #     ui.comboBoxMarker.setEnabled(True)
                #     ui.doubleSpinBoxMarkerSize.setEnabled(True)
                #     ui.horizontalSliderMarkerAlpha.setEnabled(True)
                #     ui.labelMarkerAlpha.setEnabled(True)
                #     ui.toolButtonMarkerColor.setEnabled(True)

                # line properties
                ui.doubleSpinBoxLineWidth.setEnabled(True)
                ui.toolButtonLineColor.setEnabled(True)

                # color properties
                if plot_type != 'clusters':
                    ui.comboBoxFieldColormap.setEnabled(True)
                    ui.lineEditCLB.setEnabled(True)
                    ui.lineEditCUB.setEnabled(True)
                    ui.comboBoxCScale.setEnabled(True)
                    ui.comboBoxCbarDirection.setEnabled(True)
                    ui.lineEditCLabel.setEnabled(True)
            case 'profile':
                # axes properties
                ui.lineEditXLB.setEnabled(True)
                ui.lineEditXUB.setEnabled(True)
                ui.lineEditAspectRatio.setEnabled(True)
                ui.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                ui.lineEditScaleLength.setEnabled(True)

                # marker properties
                ui.comboBoxMarker.setEnabled(True)
                ui.doubleSpinBoxMarkerSize.setEnabled(True)

                # line properties
                ui.doubleSpinBoxLineWidth.setEnabled(True)
                ui.toolButtonLineColor.setEnabled(True)

                # color properties
                ui.toolButtonMarkerColor.setEnabled(True)
                ui.comboBoxFieldColormap.setEnabled(True)
        
        # enable/disable labels
        self.toggle_style_labels()

    def toggle_style_labels(self):
        """Toggles style labels based on enabled/disabled style widgets."""        
        ui = self.ui

        # axes properties
        ui.labelXLim.setEnabled(ui.lineEditXLB.isEnabled())
        ui.toolButtonXAxisReset.setEnabled(ui.labelXLim.isEnabled())
        ui.labelXScale.setEnabled(ui.comboBoxXScale.isEnabled())
        ui.labelYLim.setEnabled(ui.lineEditYLB.isEnabled())
        ui.toolButtonYAxisReset.setEnabled(ui.labelYLim.isEnabled())
        ui.labelYScale.setEnabled(ui.comboBoxYScale.isEnabled())
        ui.labelZLim.setEnabled(ui.lineEditZLB.isEnabled())
        ui.toolButtonZAxisReset.setEnabled(ui.labelZLim.isEnabled())
        ui.labelZScale.setEnabled(ui.comboBoxZScale.isEnabled())
        ui.labelXLabel.setEnabled(ui.lineEditXLabel.isEnabled())
        ui.labelYLabel.setEnabled(ui.lineEditYLabel.isEnabled())
        ui.labelZLabel.setEnabled(ui.lineEditZLabel.isEnabled())
        ui.labelAspectRatio.setEnabled(ui.lineEditAspectRatio.isEnabled())
        ui.labelTickDirection.setEnabled(ui.comboBoxTickDirection.isEnabled())

        # scalebar properties
        ui.labelScaleLocation.setEnabled(ui.comboBoxScaleLocation.isEnabled())
        ui.labelScaleDirection.setEnabled(ui.comboBoxScaleDirection.isEnabled())
        if ui.toolButtonOverlayColor.isEnabled():
            ui.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % self.style_dict[self.plot_type]['OverlayColor'])
            ui.labelOverlayColor.setEnabled(True)
        else:
            ui.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            ui.labelOverlayColor.setEnabled(False)
        ui.labelScaleLength.setEnabled(ui.lineEditScaleLength.isEnabled())

        # marker properties
        ui.labelMarker.setEnabled(ui.comboBoxMarker.isEnabled())
        ui.labelMarkerSize.setEnabled(ui.doubleSpinBoxMarkerSize.isEnabled())
        ui.labelMarkerAlpha.setEnabled(ui.horizontalSliderMarkerAlpha.isEnabled())
        ui.labelTransparency.setEnabled(ui.horizontalSliderMarkerAlpha.isEnabled())

        # line properties
        ui.labelLineWidth.setEnabled(ui.doubleSpinBoxLineWidth.isEnabled())
        if ui.toolButtonLineColor.isEnabled():
            ui.toolButtonLineColor.setStyleSheet("background-color: %s;" % self.style_dict[self.plot_type]['LineColor'])
            ui.labelLineColor.setEnabled(True)
        else:
            ui.toolButtonLineColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            ui.labelLineColor.setEnabled(False)
        ui.labelLengthMultiplier.setEnabled(ui.lineEditLengthMultiplier.isEnabled())

        # color properties
        if ui.toolButtonMarkerColor.isEnabled():
            ui.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.style_dict[self.plot_type]['MarkerColor'])
            ui.labelMarkerColor.setEnabled(True)
        else:
            ui.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            ui.labelMarkerColor.setEnabled(False)
        ui.checkBoxReverseColormap.setEnabled(ui.comboBoxFieldColormap.isEnabled())
        ui.labelReverseColormap.setEnabled(ui.checkBoxReverseColormap.isEnabled())
        ui.labelFieldColormap.setEnabled(ui.comboBoxFieldColormap.isEnabled())
        ui.labelCScale.setEnabled(ui.comboBoxCScale.isEnabled())
        ui.labelCBounds.setEnabled(ui.lineEditCLB.isEnabled())
        ui.toolButtonCAxisReset.setEnabled(ui.labelCBounds.isEnabled())
        ui.labelCbarDirection.setEnabled(ui.comboBoxCbarDirection.isEnabled())
        ui.labelCLabel.setEnabled(ui.lineEditCLabel.isEnabled())
        ui.labelHeatmapResolution.setEnabled(ui.spinBoxHeatmapResolution.isEnabled())

   

    def set_style_widgets(self):
        """Sets values in right toolbox style page

        Parameters
        ----------
        plot_type : str, optional
            Dictionary key into ``MainWindow.styles``, Defaults to ``None``
        style : dict, optional
            Style dictionary for the current plot type. Defaults to ``None``
        """
        if self.app_data.sample_id == '' or self.plot_type =='':
            return

        ui = self.ui
        data = ui.data[self.app_data.sample_id]

        self.signal_state = True

        style = self.style_dict[self.plot_type]

        # toggle actionSwapAxes
        match self.plot_type:
            case 'field map' | 'gradient map'| 'scatter' | 'heatmap':
                ui.actionSwapAxes.setEnabled(True)
            case _:
                ui.actionSwapAxes.setEnabled(False)

        if (self.scale_length is None) and (self.plot_type.lower() in self.map_plot_types):
            self.scale_length = self.default_scale_length()

        # axes properties
        # for map plots, check to see that 'X' and 'Y' are initialized
        if self.plot_type.lower() in self.map_plot_types:
            xmin,xmax,xscale,_ = self.get_axis_values(data,'Analyte','Xc')
            ymin,ymax,yscale,_ = self.get_axis_values(data,'Analyte','Yc')

            # set style dictionary values for X and Y
            self.xlim = [xmin, xmax]
            self.xlabel = 'X'
            style['XFieldType'] = 'Coordinate'
            style['XField'] = 'Xc'

            self.ylim = [ymin, ymax]
            self.ylabel = 'Y'
            style['YFieldType'] = 'Coordinate'
            style['YField'] = 'Yc'

            self.aspect_ratio = data.aspect_ratio


            if self.scale_length is None:
                self.scale_length = self.default_scale_length()
        else:
            ui.lineEditXLB.precision = 3
            ui.lineEditXUB.precision = 3
            # round axes limits for everything that isn't a map
            # Non-map plots might still need axes
            self.xlim = style.get('XLim')
            self.yscale = style.get('ZScale')

            self.ylim = style.get('YLim')
            self.yscale = style.get('ZScale')

            self.scale_length = None

        # do not round axes limits for maps
        ui.lineEditXLB.precision = None
        ui.lineEditXUB.precision = None

        # Set Z axis details if available
        self.zlabel = style.get('ZLabel')
        self.zscale = style.get('ZScale')
        self.zlim = style.get('ZLim')

        self.aspect_ratio = data.aspect_ratio

        # annotation properties
        # Font
        self.font_size = style.get('FontSize')

        # scalebar properties
        self.scale_dir = style.get('ScaleDir')
        self.scale_location = style.get('ScaleLocation')
            
        self.overlay_color = style.get('OverlayColor')

        # Marker
        self.marker = style.get('Marker')
        self.marker_size = style.get('MarkerSize')
        self.marker_alpha = style.get('MarkerAlpha')
        self.marker_color = style.get('MarkerColor')

        # Line
        self.line_width = style.get('LineWidth')
        self.line_color = style.get('LineColor')
        self.line_multiplier = style.get('LineMultiplier')

        # color properties
        ui.update_field_type_combobox_options(ui.comboBoxFieldTypeC, ui.comboBoxFieldC, ax=3)
        if self.app_data.c_field_type is None or self.app_data.c_field_type == '':
            ui.comboBoxFieldTypeC.setCurrentIndex(1)
            self.app_data.c_field_type = ui.comboBoxFieldTypeC.currentText()
        else:
            ui.comboBoxFieldTypeC.setCurrentText(self.app_data.c_field_type)

        if self.app_data.c_field_type == '':
            ui.comboBoxFieldC.clear()
        else:
            ui.update_field_combobox_options(ui.comboBoxFieldC, ui.comboBoxFieldTypeC)
            ui.spinBoxFieldC.setMinimum(0)
            ui.spinBoxFieldC.setMaximum(ui.comboBoxFieldC.count() - 1)

        if self.app_data.c_field in ui.comboBoxFieldC.allItems():
            ui.comboBoxFieldC.setCurrentText(self.app_data.c_field)
            #self.ui.c_field_spinbox_changed()
        else:
            self.app_data.c_field = ui.comboBoxFieldC.currentText()

        self.cmap = style.get('Colormap')
        self.cbar_reverse = style.get('CbarReverse')
        
        field = self.app_data.c_field
        if field in list(data.processed_data.column_attributes.keys()):
            self.clim = [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')]
            self.clabel = data.processed_data.get_attribute(field,'label')
        else:
            self.clim = style['CLim']
            self.clabel = style['CLabel']
        
        if self.app_data.c_field_type == 'cluster':
            # set color field to active cluster method
            ui.comboBoxFieldC.setCurrentText(ui.cluster_dict['active method'])

            # set color scale to discrete
            ui.comboBoxCScale.clear()
            ui.comboBoxCScale.addItem('discrete')
            ui.comboBoxCScale.setCurrentText('discrete')

            self.cscale = 'discrete'
        else:
            # set color scale options to linear/log
            ui.comboBoxCScale.clear()
            ui.comboBoxCScale.addItems(data.scale_options)
            self.cscale = 'linear'
            ui.comboBoxCScale.setCurrentText(self.cscale)
            
        self.cbar_dir = style.get('CbarDir')
        self.clabel = style['CLabel']

        self.resolution = style.get('Resolution')

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        self.signal_state = False

    def set_style_widgets_new(self):
        """
        Set style_dict properties based on the current sample_id and plot_type.
        This function updates style_dict fields only — no UI updates are performed here.
        """
        if self.app_data.sample_id == '' or self.plot_type == '':
            return

        data = self.ui.data[self.app_data.sample_id]
        style = self.style_dict[self.plot_type]
        
        self.signal_state = True

        # toggle actionSwapAxes
        match self.plot_type:
            case 'field map' | 'gradient map' | 'scatter' | 'heatmap':
                self._set_widget_state("swap_axes", True)
            case _:
                self._set_widget_state("swap", False)

        if self.plot_type.lower() in self.map_plot_types:
            # Set X and Y axis values for map plots
            xmin, xmax, xscale, xlabel = self.get_axis_values(data, 'Analyte', 'Xc')
            ymin, ymax, yscale, ylabel = self.get_axis_values(data, 'Analyte', 'Yc')

            self.xlim = [xmin, xmax]
            # self.xscale = xscale
            self.xlabel = 'X'
            style['XFieldType'] = 'Coordinate'
            style['XField'] = 'Xc'

            self.ylim = [ymin, ymax]
            # self.yscale = yscale
            self.ylabel = 'Y'
            style['YFieldType'] = 'Coordinate'
            style['YField'] = 'Yc'

            self.aspect_ratio = data.aspect_ratio

            if self.scale_length is None:
                self.scale_length = self.default_scale_length()
        else:
            # Non-map plots might still need axes
            self.xlim = style.get('XLim')
            self.ylim = style.get('YLim')
            self.zlim = style.get('ZLim')
        
        # Set Z axis details if available
        self.zlabel = style.get('ZLabel')
        self.zscale = style.get('ZScale')

        # Font and annotation
        self.font_size = style.get('FontSize')
        self.scale_dir = style.get('ScaleDir')
        self.scale_location = style.get('ScaleLocation')
        if self.scale_length is None and self.plot_type.lower() in self.map_plot_types:
            self.scale_length = self.default_scale_length()

        self.overlay_color = style.get('OverlayColor')

        # Marker
        self.marker = style.get('Marker')
        self.marker_size = style.get('MarkerSize')
        self.marker_alpha = style.get('MarkerAlpha')
        self.marker_color = style.get('MarkerColor')

        # Line
        self.line_width = style.get('LineWidth')
        self.line_color = style.get('LineColor')
        self.line_multiplier = style.get('LineMultiplier')

        # Colorbar/Colormap
        field = self.app_data.c_field
        if field and field in data.processed_data.column_attributes:
            style['CLim'] = [
                data.processed_data.get_attribute(field, 'plot_min'),
                data.processed_data.get_attribute(field, 'plot_max')
            ]
            style['CLabel'] = data.processed_data.get_attribute(field, 'label')

        self.clim = style['CLim']
        self.clabel = style['CLabel']
        self.cscale = 'discrete' if self.app_data.c_field_type == 'cluster' else 'linear'
        self.cmap = style.get('Colormap', 'viridis')
        self.cbar_reverse = style.get('CbarReverse', False)
        self.cbar_dir = style.get('CbarDir', 'vertical')
        self.resolution = style.get('Resolution', 100)

        


    # style widget callbacks
    # -------------------------------------
    def init_field_widgets(self, plot_axis_dict, widget_dict, plot_type=None):
        """
        Initializes widgets associated with axes for plotting

        Enables and sets visibility of labels, comboboxes, and spinboxes associated with
        axes for choosing plot dimensions, including color.

        Parameters
        ----------
        widget_dict : dict
            Dictionary with field associated widgets and properties
        
        :see also: self.axis_widget_dict
        """
        if plot_type is None:
            setting = plot_axis_dict[self.plot_type]
        else:
            setting = plot_axis_dict[plot_type]

        # enable and set visibility of widgets
        for ax in range(4):
            # set field label text
            widget_dict['label'][ax].setEnabled(setting['axis'][ax])
            widget_dict['label'][ax].setVisible(setting['axis'][ax])

            # set parent and child comboboxes
            widget_dict['parentbox'][ax].setEnabled(setting['axis'][ax])
            widget_dict['parentbox'][ax].setVisible(setting['axis'][ax])

            widget_dict['childbox'][ax].setEnabled(setting['axis'][ax])
            widget_dict['childbox'][ax].setVisible(setting['axis'][ax])

            # set field spinboxes
            if widget_dict['spinbox'][ax] is not None:
                widget_dict['spinbox'][ax].setEnabled(setting['spinbox'][ax])
                widget_dict['spinbox'][ax].setVisible(setting['spinbox'][ax])

    def update_plot_type(self, new_plot_type=None, force=False):
        """Updates styles when plot type is changed

        Executes on change of ``MainWindow.comboBoxPlotType``.  Updates ``MainWindow.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        #if not force:
        #    if self._plot_type == self.ui.comboBoxPlotType.currentText()
        #        return

        # set plot flag to false
        if new_plot_type is not None and new_plot_type != '':
            if new_plot_type != self.ui.comboBoxPlotType.currentText():
                self.ui.comboBoxPlotType.setCurrentText(new_plot_type)
                self.ui.plot_types[self.ui.toolBox.currentIndex()][0] = self.ui.comboBoxPlotType.currentIndex()

        else:
            self.plot_type = self.ui.comboBoxPlotType.currentText()

        ui = self.ui

        self.init_field_widgets(self.plot_axis_dict, self.axis_widget_dict, plot_type=self.plot_type)

        # update ui
        match self.plot_type.lower():
            case 'field map' | 'gradient map':
                ui.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                ui.actionSwapAxes.setEnabled(True)
            case 'correlation':
                ui.actionSwapAxes.setEnabled(False)
                if ui.comboBoxCorrelationMethod.currentText() == 'none':
                    ui.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case 'cluster performance' | 'cluster map' | 'cluster score ':
                self.ui.clustering.toggle_cluster_widgets()
            case _:
                ui.actionSwapAxes.setEnabled(False)

        # update field widgets
        self.update_field_widgets()

        # update all plot widgets
        self.set_style_widgets()

        self.ui.plot_flag = False
        for ax in range(4):
            if self.plot_axis_dict[self.plot_type]['axis'][ax]:
                self.update_field(ax, self.axis_widget_dict['childbox'][ax].currentText())
                self.update_field(ax, self.axis_widget_dict['childbox'][ax].currentText())
        self.ui.plot_flag = True

        if self.plot_type != '':
            self.schedule_update()

    def update_field_widgets(self):
        """Updates field widgets with saved settings
         
        Updates the label text, field type combobox, and field combobox with saved values associated with a
        control toolbox tab.
        """
        idx = None
        if (hasattr(self, 'profile_dock') and self.ui.profile_dock.actionProfileToggle.isChecked()) or (hasattr(self, 'mask_dock') and self.ui.mask_dock.polygon_tab.actionPolyToggle.isChecked()):
            idx = -1
        else:
            idx = self.ui.toolBox.currentIndex()

        # prevent updating of plot as all the changes are made
        flag = False
        if self.ui.plot_flag:
            flag = True
            self.ui.plot_flag = False

        widget_dict = self.axis_widget_dict
        setting = self.ui.field_control_settings[idx]
        for ax in range(4):
            widget_dict['label'][ax].setText(setting['label'][ax])

            if setting['saved_field_type'][ax] is not None:
                self.app_data.set_field_type(ax, setting['save_field_type'][ax])
            else:
                parentbox = widget_dict['parentbox'][ax]
                childbox = widget_dict['childbox'][ax]
                self.ui.update_field_type_combobox_options(parentbox, childbox, ax=ax)

            if setting['saved_field'][ax] is not None:
                self.app_data.set_field(ax, setting['save_field'][ax])

        if flag:
            self.ui.plot_flag = True

    # axes
    # -------------------------------------
    def axis_variable_changed(self, field_type, field, ax="None"):
        """Updates axis variables when the field is changed.

        Parameters
        ----------
        field_type : str
            field type
        field : str
            field
        ax : str, optional
            axis for plotting, by default "None"
        """
        ui = self.ui

        if field == '' or field.lower() == 'none':
            match ax:
                case 'x':
                    ui.lineEditXLB.setEnabled(False)
                    ui.lineEditXUB.setEnabled(False)
                    ui.comboBoxXScale.setEnabled(False)
                    ui.lineEditXLabel.setEnabled(False)
                    ui.lineEditXLB.setText('')
                    ui.lineEditXUB.setText('')
                    ui.comboBoxXScale.setCurrentText('')
                    ui.lineEditXLabel.setText('')
                case 'y':
                    ui.lineEditYLB.setEnabled(False)
                    ui.lineEditYUB.setEnabled(False)
                    ui.comboBoxYScale.setEnabled(False)
                    ui.lineEditYLabel.setEnabled(False)
                    ui.lineEditYLB.setText('')
                    ui.lineEditYUB.setText('')
                    ui.comboBoxYScale.setCurrentText('')
                    ui.lineEditYLabel.setText('')
                case 'z':
                    ui.lineEditZLB.setEnabled(False)
                    ui.lineEditZUB.setEnabled(False)
                    ui.comboBoxZScale.setEnabled(False)
                    ui.lineEditZLabel.setEnabled(False)
                    ui.lineEditZLB.setText('')
                    ui.lineEditZUB.setText('')
                    ui.comboBoxZScale.setCurrentText('')
                    ui.lineEditZLabel.setText('')
            return
        else:
            amin, amax, scale, label = self.get_axis_values(self.ui.data[self.app_data.sample_id],field_type, field, ax)

            plot_type = self.plot_type

            self.style_dict[plot_type][ax+'Lim'] = [amin, amax]
            self.style_dict[plot_type][ax+'norm'] = scale
            self.style_dict[plot_type][ax+'Label'] = label

            match ax:
                case 'x':
                    ui.lineEditXLB.setEnabled(True)
                    ui.lineEditXUB.setEnabled(True)
                    ui.comboBoxXScale.setEnabled(True)
                    ui.lineEditXLabel.setEnabled(True)
                    ui.lineEditXLB.value = amin
                    ui.lineEditXUB.value = amax
                    ui.comboBoxXScale.setCurrentText(scale)
                    ui.lineEditXLabel.setText(label)
                case 'y':
                    ui.lineEditYLB.setEnabled(True)
                    ui.lineEditYUB.setEnabled(True)
                    ui.comboBoxYScale.setEnabled(True)
                    ui.lineEditYLabel.setEnabled(True)
                    ui.lineEditYLB.value = amin
                    ui.lineEditYUB.value = amax
                    ui.comboBoxYScale.setCurrentText(scale)
                    ui.lineEditYLabel.setText(label)
                case 'z':
                    ui.lineEditZLB.setEnabled(True)
                    ui.lineEditZUB.setEnabled(True)
                    ui.comboBoxZScale.setEnabled(True)
                    ui.lineEditZLabel.setEnabled(True)
                    ui.lineEditZLB.value = amin
                    ui.lineEditZUB.value = amax
                    ui.comboBoxZScale.setCurrentText(scale)
                    ui.lineEditZLabel.setText(label)

            self.schedule_update()

        ui.labelXLim.setEnabled(ui.lineEditXLB.isEnabled()) 
        ui.labelYLim.setEnabled(ui.lineEditYLB.isEnabled()) 
        ui.labelZLim.setEnabled(ui.lineEditZLB.isEnabled()) 
        ui.labelXScale.setEnabled(ui.comboBoxXScale.isEnabled())
        ui.labelYScale.setEnabled(ui.comboBoxYScale.isEnabled())
        ui.labelZScale.setEnabled(ui.comboBoxZScale.isEnabled())
        ui.labelXLabel.setEnabled(ui.lineEditXLabel.isEnabled())
        ui.labelYLabel.setEnabled(ui.lineEditYLabel.isEnabled())
        ui.labelZLabel.setEnabled(ui.lineEditZLabel.isEnabled())
        ui.toolButtonXAxisReset.setEnabled(ui.lineEditXLB.isEnabled()) 
        ui.toolButtonYAxisReset.setEnabled(ui.lineEditYLB.isEnabled()) 
        ui.toolButtonZAxisReset.setEnabled(ui.lineEditZLB.isEnabled()) 

    def get_axis_field(self, ax):
        """Grabs the field name from a given axis

        The field name for a given axis comes from a comboBox, and depends upon the plot type.
        Parameters
        ----------
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        """
        plot_type = self.ui.comboBoxPlotType.currentText()
        if ax == 'c':
            return self.ui.comboBoxFieldC.currentText()

        match plot_type:
            case 'histogram':
                if ax in ['x', 'y']:
                    return self.ui.comboBoxFieldC.currentText()
            case 'scatter' | 'heatmap':
                match ax:
                    case 'x':
                        return self.ui.comboBoxFieldX.currentText()
                    case 'y':
                        return self.ui.comboBoxFieldY.currentText()
                    case 'z':
                        return self.ui.comboBoxFieldZ.currentText()
            case 'PCA scatter' | 'PCA heatmap':
                match ax:
                    case 'x':
                        return f'PC{self.ui.spinBoxPCX.value()}'
                    case 'y':
                        return f'PC{self.ui.spinBoxPCY.value()}'
            case 'field map' | 'ternary map' | 'PCA score' | 'cluster map' | 'cluster score':
                return ax.upper()

    def axis_label_edit_callback(self, ax, new_label):
        """Updates axis label in dictionaries from widget

        Parameters
        ----------
        ax : str
            Axis that has changed, options include ``x``, ``y``, ``z``, and ``c``.
        new_label : str
            New label for bound set by user.
        """
        data = self.ui.data[self.app_data.sample_id]

        if ax == 'c':
            old_label = self.style_dict[self.plot_type][ax.upper()+'Label']
        else:
            old_label = self.style_dict[self.plot_type][ax.upper()+'Label']

        # if label has not changed return
        if old_label == new_label:
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        data.processed_data.set_attribute(field,'label', new_label)
        if ax == 'c':
            self.style_dict[self.plot_type][ax.upper()+'Label'] = new_label
        else:
            self.style_dict[self.plot_type][ax.upper()+'Label'] = new_label

        # update plot
        self.schedule_update()

    def axis_limit_edit_callback(self, ax, bound, new_value,field= None, ui_update= True):
        """Updates axis limit in dictionaries from widget

        Parameters
        ----------
        ax : str
            Axis that has changed, options include ``x``, ``y``, ``z``, and ``c``.
        bound : int
            Indicates whether the bound to set is a lower (``0``) or upper (``1``).
        new_value : float
            New value for bound set by user.
        """
        data = self.ui.data[self.app_data.sample_id]

        if ui_update:
            plot_type = self.ui.comboBoxPlotType.currentText()
        else:
            plot_type = self.plot_type

        if ax == 'c':
            old_value = self.style_dict[plot_type]['CLim'][bound]
        else:
            old_value = self.style_dict[plot_type][ax.upper()+'Lim'][bound]

        # if label has not changed return
        if old_value == new_value:
            return

        if ui_update:
            if ax == 'c' and plot_type in ['heatmap', 'correlation']:
                self.schedule_update()
                return
        if not field:
            # change label in dictionary
            field = self.get_axis_field(ax)
        if bound:
            if plot_type == 'histogram' and ax == 'y':
                data.processed_data.set_attribute(field,'p_max', new_value)
                
            else:
                data.processed_data.set_attribute(field,'plot_max', new_value)
                
        else:
            if plot_type == 'histogram' and ax == 'y':
                data.processed_data.set_attribute(field,'p_min', new_value)
            else:
                data.processed_data.set_attribute(field,'plot_min', new_value)

        if ax == 'c':
            self.style_dict[plot_type][f'{ax.upper()}Lim'][bound] = new_value
        else:
            self.style_dict[plot_type][f'{ax.upper()}Lim'][bound] = new_value

        # update plot
        self.schedule_update()

    def axis_scale_callback(self, comboBox, ax):
        """Updates axis scale when a scale comboBox has changed.

        Parameters
        ----------
        comboBox : QComboBox
            Widget whos scale has changed.
        ax : str
            Axis whos scale been set from comboBox, options include ``x``, ``y``, ``z``, and ``c``.
        """        
        data = self.ui.data[self.app_data.sample_id]

        styles = self.style_dict[self._plot_type]

        new_value = comboBox.currentText()
        if ax == 'c':
            if styles['CLim'] == new_value:
                return
        elif styles[ax.upper()+'norm'] == new_value:
            return

        field = self.get_axis_field(ax)

        if self._plot_type != 'heatmap':
            data.processed_data.set_attribute(field,'norm',new_value)

        if ax == 'c':
            styles['CScale'] = new_value
        else:
            styles[ax.upper()+'norm'] = new_value

        # update plot
        self.schedule_update()

    def set_color_axis_widgets(self):
        """Sets the color axis limits and label widgets."""
        data = self.ui.data[self.app_data.sample_id]

        field = self.ui.comboBoxFieldC.currentText()
        if field == '':
            return
        self.ui.lineEditCLB.value = data.processed_data.get_attribute(field,'plot_min')
        self.ui.lineEditCUB.value = data.processed_data.get_attribute(field,'plot_max')
        self.ui.comboBoxCScale.setCurrentText(data.processed_data.get_attribute(field,'norm'))

    def set_axis_widgets(self, ax, field):
        """Sets axis widgets in the style toolbox

        Updates axes limits and labels.

        Parameters
        ----------
        ax : str
            Axis 'x', 'y', or 'z'
        field : str
            Field plotted on axis, used as column name to ``MainWindow.data.processed_data`` dataframe.
        """
        data = self.ui.data[self.app_data.sample_id]

        if field == '':
            return

        match ax:
            case 'x':
                if field == 'Xc':
                    self.ui.lineEditXLB.value = data.processed_data.get_attribute(field,'plot_min')
                    self.ui.lineEditXUB.value = data.processed_data.get_attribute(field,'plot_max')
                else:
                    self.ui.lineEditXLB.value = data.processed_data.get_attribute(field,'plot_min')
                    self.ui.lineEditXUB.value = data.processed_data.get_attribute(field,'plot_max')
                self.ui.lineEditXLabel.setText(data.processed_data.get_attribute(field,'label'))
                self.ui.comboBoxXScale.setCurrentText(data.processed_data.get_attribute(field,'norm'))
            case 'y':
                if self.ui.comboBoxPlotType.currentText() == 'histogram':
                    self.ui.lineEditYLB.value = data.processed_data.get_attribute(field,'p_min')
                    self.ui.lineEditYUB.value = data.processed_data.get_attribute(field,'p_max')
                    self.ui.lineEditYLabel.setText(self.ui.comboBoxHistType.currentText())
                    self.ui.comboBoxYScale.setCurrentText('linear')
                else:
                    if field == 'Xc':
                        self.ui.lineEditYLB.value = data.processed_data.get_attribute(field,'plot_min')
                        self.ui.lineEditYUB.value = data.processed_data.get_attribute(field,'plot_max')
                    else:
                        self.ui.lineEditYLB.value = data.processed_data.get_attribute(field,'plot_min')
                        self.ui.lineEditYUB.value = data.processed_data.get_attribute(field,'plot_max')
                    self.ui.lineEditYLabel.setText(data.processed_data.get_attribute(field,'label'))
                    self.ui.comboBoxYScale.setCurrentText(data.processed_data.get_attribute(field,'norm'))
            case 'z':
                self.ui.lineEditZLB.value = data.processed_data.get_attribute(field,'plot_min')
                self.ui.lineEditZUB.value = data.processed_data.get_attribute(field,'plot_max')
                self.ui.lineEditZLabel.setText(data.processed_data.get_attribute(field,'label'))
                self.ui.comboBoxZScale.setCurrentText(data.processed_data.get_attribute(field,'norm'))

    def axis_reset_callback(self, ax):
        """Resets axes widgets and plot axes to auto values

        Resets the axis limits and scales to auto values, and updates the style dictionary.     

        Parameters
        ----------
        ax : str
            axis to reset values, can be ``x``, ``y``, and ``c``

        """
        data = self.ui.data[self.app_data.sample_id]

        if ax == 'c':
            if self.ui.comboBoxPlotType.currentText() == 'basis vectors':
                self.style_dict['basis vectors']['CLim'] = [np.amin(self.ui.pca_results.components_), np.amax(self.ui.pca_results.components_)]
            elif not (self.ui.comboBoxFieldTypeC.currentText() in ['none','cluster']):
                field_type = self.ui.comboBoxFieldTypeC.currentText()
                field = self.ui.comboBoxFieldC.currentText()
                if field == '':
                    return
                data.processed_data.prep_data(field)

            self.set_color_axis_widgets()
        else:
            match self.ui.comboBoxPlotType.currentText().lower():
                case 'field map' | 'cluster map' | 'cluster score map' | 'pca score':
                    field = ax.upper()
                    data.processed_data.prep_data(field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = self.ui.comboBoxFieldC.currentText()
                    if ax == 'x':
                        field_type = self.ui.comboBoxFieldTypeC.currentText()
                        data.processed_data.prep_data(field)
                        self.set_axis_widgets(ax, field)
                    else:
                        data.processed_data.set_attribute(field, 'p_min', None)
                        data.processed_data.set_attribute(field, 'p_max', None)

                case 'scatter' | 'heatmap':
                    match ax:
                        case 'x':
                            field_type = self.ui.comboBoxFieldTypeX.currentText()
                            field = self.ui.comboBoxFieldX.currentText()
                        case 'y':
                            field_type = self.ui.comboBoxFieldTypeY.currentText()
                            field = self.ui.comboBoxFieldY.currentText()
                        case 'z':
                            field_type = self.ui.comboBoxFieldTypeZ.currentText()
                            field = self.ui.comboBoxFieldZ.currentText()
                    if (field_type == '') | (field == ''):
                        return
                    data.processed_data.prep_data(field)
                    self.set_axis_widgets(ax, field)

                case 'PCA scatter' | 'PCA heatmap':
                    field_type = 'PCA score'
                    if ax == 'x':
                        field = self.ui.spinBoxPCX.currentText()
                    else:
                        field = self.ui.spinBoxPCY.currentText()
                    data.processed_data.prep_data(field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.set_style_widgets()
        self.schedule_update()


    def aspect_ratio_callback(self):
        """Update aspect ratio

        Updates ``MainWindow.style`` dictionary after user change
        """
        if self.aspect_ratio == self.ui.lineEditAspectRatio.value:
            return

        self.aspect_ratio = self.ui.lineEditAspectRatio.value
        self.schedule_update()

    def tickdir_callback(self):
        """Updates tick directions in style dictionary from change of ``MainWindow.comboBoxTickDirection``."""        
        if self.tick_dir == self.ui.comboBoxTickDirection.currentText():
            return

        self.tick_dir = self.ui.comboBoxTickDirection.currentText()
        self.schedule_update()

    # text and annotations
    # -------------------------------------
    def font_callback(self):
        """Updates figure fonts"""        
        if self.font == self.ui.fontComboBox.currentFont().family():
            return

        self.font = self.ui.fontComboBox.currentFont().family()
        self.schedule_update()

    def font_size_callback(self):
        """Updates figure font sizes"""        
        if self.font_size == self.ui.doubleSpinBoxFontSize.value():
            return

        self.font_size = self.ui.doubleSpinBoxFontSize.value()
        self.schedule_update()

    def update_figure_font(self, canvas, font_name):
        """updates figure fonts without the need to recreate the figure.

        Parameters
        ----------
        canvas : MplCanvas
            Canvas object displayed in UI.
        font_name : str
            Font used on plot.
        """        
        if font_name == '':
            return

        # Update font of all text elements in the figure
        try:
            for text_obj in canvas.fig.findobj(match=plt.Text):
                text_obj.set_fontname(font_name)
        except:
            print('Unable to update figure font.')

    def toggle_mass(self, labels):
        """Removes mass from labels

        Removes mass if ``MainWindow.checkBoxShowMass.isChecked()`` is False

        Parameters
        ----------
        labels : str
            Input labels

        Returns
        -------
        list
            Output labels with or without mass
        """
        if not self.show_mass:
            labels = [re.sub(r'\d', '', col) for col in labels]

        return labels

    # scales
    # -------------------------------------
    def update_scale_direction_combobox(self, new_dir):
        """Sets scale direction on figure"""        
        if new_dir == self.ui.comboBoxScaleDirection.currentText():
            return
        self.ui.comboBoxScaleDirection.setCurrentText(new_dir)
        self.toggle_scale_widgets()

        self.schedule_update()

    def toggle_scale_widgets(self):
        """Toggles state of scale widgets.
         
        Enables/disables widgets based on ``self.scale_dir``, including the scale location and scale length."""
        if self.scale_dir == 'none':
            self.ui.labelScaleLocation.setEnabled(False)
            self.ui.comboBoxScaleLocation.setEnabled(False)
            self.ui.labelScaleLength.setEnabled(False)
            self.ui.lineEditScaleLength.setEnabled(False)
            self.ui.lineEditScaleLength.value = None
        else:
            self.ui.labelScaleLocation.setEnabled(True)
            self.ui.comboBoxScaleLocation.setEnabled(True)
            self.ui.labelScaleLength.setEnabled(True)
            self.ui.lineEditScaleLength.setEnabled(True)
            # set scalebar length if plot is a map type
            if self.plot_type not in self.map_plot_types:
                self.scale_length = None
            else:
                self.scale_length = self.default_scale_length()


    def scale_location_callback(self):
        """Sets scalebar location on map from ``MainWindow.comboBoxScaleLocation``"""        
        if self.scale_location == self.ui.comboBoxScaleLocation.currentText():
            return

        self.scale_location = self.ui.comboBoxScaleLocation.currentText()
        self.schedule_update()

    def scale_length_callback(self):
        """Updates length of scalebar on map-type plots
        
        Executes on change of ``MainWindow.lineEditScaleLength``, updates length if within bounds set by plot dimensions, then updates plot.
        """ 
        if self._plot_type in self.map_plot_types:
            # make sure user input is within bounds, do not change
            if ((self.ui.comboBoxScaleDirection.currentText() == 'horizontal') and (scale_length  > data.x_range)) or (scale_length <= 0):
                scale_length = self.style_dict[self._plot_type]['ScaleLength']
                self.ui.lineEditScaleLength.value = scale_length
                return
            elif ((self.ui.comboBoxScaleDirection.currentText() == 'vertical') and (scale_length > data.y_range)) or (scale_length <= 0):
                scale_length = self.style_dict[self._plot_type]['ScaleLength']
                self.ui.lineEditScaleLength.value = scale_length
                return
        else:
            if self.style_dict[self._plot_type]['ScaleLength'] is not None:
                self.scale_length = None
                return

        # update plot
        self.schedule_update()

    def overlay_color_callback(self):
        """Updates color of overlay markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonOverlayColor`` color.
        """
        plot_type = self.ui.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(self.ui.toolButtonOverlayColor)

        color = get_hex_color(self.ui.toolButtonOverlayColor.palette().button().color())
        # update style
        if self.style_dict[plot_type]['OverlayColor'] == color:
            return

        self.style_dict[plot_type]['OverlayColor'] = color
        # update plot
        self.schedule_update()

    # markers
    # -------------------------------------
    def marker_symbol_callback(self):
        """Updates marker symbol

        Updates marker symbols on current plot on change of ``MainWindow.comboBoxMarker.currentText()``.
        """
        if self.marker == self.ui.comboBoxMarker.currentText():
            return
        self.marker = self.ui.comboBoxMarker.currentText()

        self.schedule_update()

    def marker_size_callback(self):
        """Updates marker size

        Updates marker size on current plot on change of ``MainWindow.doubleSpinBoxMarkerSize.value()``.
        """
        if self.marker_size == self.ui.doubleSpinBoxMarkerSize.value():
            return
        self.marker_size = self.ui.doubleSpinBoxMarkerSize.value()

        self.schedule_update()

    def slider_alpha_changed(self):
        """Updates transparency on scatter plots.

        Executes on change of ``MainWindow.horizontalSliderMarkerAlpha.value()``.
        """
        self.ui.labelMarkerAlpha.setText(str(self.ui.horizontalSliderMarkerAlpha.value()))

        if self.ui.horizontalSliderMarkerAlpha.isEnabled():
            self.marker_alpha = float(self.ui.horizontalSliderMarkerAlpha.value())
            self.schedule_update()

    # lines
    # -------------------------------------
    def line_width_callback(self):
        """Updates line width

        Updates line width on current plot on change of ``MainWindow.doubleSpinBoxLineWidth.value().
        """
        if self.line_width == float(self.ui.doubleSpinBoxLineWidth.value()):
            return

        self.line_width = float(self.ui.doubleSpinBoxLineWidth.value())
        self.schedule_update()

    def length_multiplier_callback(self):
        """Updates line length multiplier

        Used when plotting vector components in multidimensional plots.  Values entered by the user must be (0,10]
        """
        if not float(self.ui.lineEditLengthMultiplier.text()):
            self.ui.lineEditLengthMultiplier.values = self.line_multiplier

        value = float(self.ui.lineEditLengthMultiplier.text())
        if self.line_multiplier == value:
            return
        elif (value < 0) or (value >= 100):
            self.ui.lineEditLengthMultiplier.values = self.line_multiplier
            return

        self.line_multiplier = value
        self.schedule_update()

    def line_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonLineColor`` color.
        """
        # change color
        self.button_color_select(self.ui.toolButtonLineColor)
        color = get_hex_color(self.ui.toolButtonLineColor.palette().button().color())
        if self.line_color == color:
            return

        # update style
        self.line_color = color

        # update plot
        self.schedule_update()

    # colors
    # -------------------------------------
    def marker_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonMarkerColor`` color.
        """
        # change color
        self.button_color_select(self.ui.toolButtonMarkerColor)
        color = get_hex_color(self.ui.toolButtonMarkerColor.palette().button().color())
        if self.marker_color == color:
            return

        # update style
        self.marker_color = color

        # update plot
        self.schedule_update()

    def resolution_callback(self):
        """Updates heatmap resolution

        Updates the resolution of heatmaps when ``MainWindow.spinBoxHeatmapResolution`` is changed.
        """
        self.resolution = self.ui.spinBoxHeatmapResolution.value()

        self.schedule_update()

    # updates scatter styles when ColorByField comboBox is changed
    def update_color_field_type(self):
        """Executes on change to *ColorByField* combobox
        
        Updates style associated with ``MainWindow.comboBoxFieldTypeC``.  Also updates
        ``MainWindow.comboBoxFieldC`` and ``MainWindow.comboBoxCScale``."""
        self.color_field_type = self.ui.comboBoxFieldTypeCType.currentText()

        # need this line to update field comboboxes when colorby field is updated
        self.ui.update_field_combobox(self.ui.comboBoxFieldTypeC, self.ui.comboBoxFieldC)
        self.update_color_field_spinbox()
        if self.plot_type == '':
            return

        style = self.style_dict[self.plot_type]
        if self.app_data.c_field_type == self.ui.comboBoxFieldTypeC.currentText():
            return

        self.app_data.c_field_type = self.ui.comboBoxFieldTypeC.currentText()
        if self.ui.comboBoxFieldTypeC.currentText() != '':
            self.set_style_widgets()

        if self.ui.comboBoxPlotType.isEnabled() == False | self.ui.comboBoxFieldTypeC.isEnabled() == False:
            return

        # only run update current plot if color field is selected or the color by field is clusters
        if self.ui.comboBoxFieldTypeC.currentText() != 'none' or self.ui.comboBoxFieldC.currentText() != '' or self.ui.comboBoxFieldTypeC.currentText() in ['cluster']:
            self.schedule_update()

    def update_field_type(self, ax, field_type=None, *args, **kwargs):
        # only update field if the axis is enabled 
        if not self.plot_axis_dict[self.plot_type]['axis'][ax]:
            return
            #self.set_axis_lim(ax, [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')])
            #self.set_axis_label(ax, data.processed_data.get_attribute(field,'label'])
            #self.set_axis_scale(ax, data.processed_data.get_attribute(field,'norm'])

        parentbox = self.axis_widget_dict['parentbox'][ax]

        if field_type is None:   # user interaction, or direct setting of combobox
            # set field type property to combobox
            self.app_data.set_field_type(ax, parentbox.currentText())
        else:   # direct setting of property
            if field_type == parentbox.currentText() and field_type == self.app_data.get_field_type(ax):
                return

            # set combobox to field
            parentbox.setCurrentText(field_type)

        # update plot
        self.schedule_update()


    def update_field(self, ax, field=None):
        """Used to update widgets associated with an axis after a field change to either the combobox or underlying data.

        Used to update, x, y, z, and c axes related widgets including fields, spinboxes, labels, limits and scale.  

        Parameters
        ----------
        ax : int
            Axis to update, [x,y,z,c] should be supplied as an integer, [0,1,2,3], respectively
        field : str, optional
            New field value for axis to update ``app_data`` or combobox, by default None
        """
        # only update field if the axis is enabled 
        if not self.plot_axis_dict[self.plot_type]['axis'][ax]:
            return
            #self.set_axis_lim(ax, [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')])
            #self.set_axis_label(ax, data.processed_data.get_attribute(field,'label'])
            #self.set_axis_scale(ax, data.processed_data.get_attribute(field,'norm'])

        parentbox = self.axis_widget_dict['parentbox'][ax]
        childbox = self.axis_widget_dict['childbox'][ax]
        spinbox = self.axis_widget_dict['spinbox'][ax]

        if field is None:   # user interaction, or direct setting of combobox
            # set field property to combobox
            self.app_data.set_field(ax, childbox.currentText())
            #field = childbox.currentText()
        else:   # direct setting of property
            if not (field == childbox.currentText() and field == self.app_data.get_field(ax)):

                # set combobox to field
                childbox.blockSignals(True)
                childbox.setCurrentText(field)
                childbox.blockSignals(False)

            # check if c_field property needs to be updated too
            if self.app_data.get_field(ax) != childbox.currentText():
                self.app_data.set_field(ax, childbox.currentText())

        if spinbox is not None and spinbox.value() != childbox.currentIndex():
            spinbox.setValue(childbox.currentIndex())

        # update autoscale widgets
        if ax == 3 and self.ui.toolBox.currentIndex() == self.ui.left_tab['process']:
            self.ui.update_autoscale_widgets(self.app_data.get_field(ax), self.app_data.get_field_type(ax))

        if field not in [None, '','none','None']:
            data = self.ui.data[self.app_data.sample_id]

            # update bin width for histograms
            if ax == 0 and self.plot_type == 'histogram':
                # update hist_bin_width
                self.app_data.update_num_bins = False
                self.app_data.update_hist_bin_width()
                self.app_data.update_num_bins = True

            # initialize color widgets
            if ax == 3:
                self.set_color_axis_widgets()

            # update axes properties
            if ax == 3 and self._plot_type not in ['correlation']:
                self.clim = [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')]
                self.clabel = data.processed_data.get_attribute(field,'label')
                self.cscale = data.processed_data.get_attribute(field,'norm')
            elif self._plot_type not in []:
                self.set_axis_lim(ax, [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')])
                self.set_axis_label(ax, data.processed_data.get_attribute(field,'label'))
                self.set_axis_scale(ax, data.processed_data.get_attribute(field,'norm'))

        else:
            self.clabel = ''

        # update plot
        self.schedule_update()
        
    def field_colormap_callback(self):
        """Sets the color map

        Sets the colormap in ``MainWindow.styles`` for the current plot type, set from ``MainWindow.comboBoxFieldColormap``.
        """
        if self.cmap == self.ui.comboBoxFieldColormap.currentText():
            return

        self.toggle_style_widgets()
        self.style_dict[self.ui.comboBoxPlotType.currentText()]['Colormap'] = self.ui.comboBoxFieldColormap.currentText()

        self.schedule_update()
    
    def colormap_direction_callback(self):
        """Set colormap direction (normal/reverse)

        Reverses colormap if ``MainWindow.checkBoxReverseColormap.isChecked()`` is ``True``."""
        if self.cbar_reverse == self.ui.checkBoxReverseColormap.isChecked():
            return

        self.cbar_reverse = self.ui.checkBoxReverseColormap.isChecked()

        self.schedule_update()

    def get_cluster_colormap(self, cluster_dict, alpha=100):
        """Converts hex colors to a colormap

        Creates a discrete colormap given a list of hex color strings.  The colors in cluster_dict are set/changed in the ``MainWindow.tableWidgetViewGroups``.

        Parameters
        ----------
        cluster_dict : dict
            Dictionary with cluster information    
        alpha : int, optional
            Transparency to be added to color, by default 100

        Returns
        -------
        matplotlib.colormap
            A discrete (colors.ListedColormap) colormap
        """
        n = cluster_dict['n_clusters']
        cluster_color = [None]*n
        cluster_label = [None]*n
        
        # convert colors from hex to rgb and add to cluster_color list
        for i in range(n):
            color = get_rgb_color(cluster_dict[i]['color'])
            cluster_color[i] = tuple(float(c)/255 for c in color) + (float(alpha)/100,)
            cluster_label[i] = cluster_dict[i]['name']

        # mask
        if 99 in cluster_dict:
            color = get_rgb_color(cluster_dict[99]['color'])
            cluster_color.append(tuple(float(c)/255 for c in color) + (float(alpha)/100,))
            cluster_label.append(cluster_dict[99]['name'])
            cmap = colors.ListedColormap(cluster_color, N=n+1)
        else:
            cmap = colors.ListedColormap(cluster_color, N=n)

        return cluster_color, cluster_label, cmap


    

    def cbar_direction_callback(self):
        """Sets the colorbar direction

        Sets the colorbar direction in ``MainWindow.styles`` for the current plot type.
        """
        if self.cbar_dir == self.ui.comboBoxCbarDirection.currentText():
            return
        self.cbar_dir = self.ui.comboBoxCbarDirection.currentText()

        self.schedule_update()

    def cbar_label_callback(self):
        """Sets color label

        Sets the color label in ``MainWindow.styles`` for the current plot type.
        """
        if self.clabel == self.ui.lineEditCLabel.text():
            return
        self.clabel = self.ui.lineEditCLabel.text()

        if self.ui.comboBoxCLabel.isEnabled():
            self.schedule_update()

    # cluster styles
    # -------------------------------------

    def set_default_cluster_colors(self,n, mask=False):
        """Sets cluster group to default colormap

        Sets the colors in ``self.tableWidgetViewGroups`` to the default colormap in
        ``self.styles['cluster map']['Colormap'].  Change the default colormap
        by changing ``self.comboBoxColormap``, when ``self.comboBoxFieldTypeC.currentText()`` is ``Cluster``.

        Returns
        -------
            N : number of cluster groups
            str : hexcolor
        """

        #print('set_default_cluster_colors')
        # cluster_tab = self.parent.mask_dock.cluster_tab

        # cluster colormap
        cmap = self.get_colormap(N=n)

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(n):
            hexcolor.append(get_hex_color(colors[i]))
            
        if mask:
            hexcolor.append(self.style_dict['cluster map']['OverlayColor'])

        return hexcolor

    def update_ternary_colormap(self, new_colormap=None):
        """Updates ternary colormap used to make ternary maps.

        Updates the colors for the vertices and centroid of a ternary colormap
        that is used to produce a map-style image colored by pixel locations
        within a ternary diagram.

        Parameters
        ----------
        new_colormap : str, optional
            New color map name, by default None
        """
        if new_colormap is None:
             # use current value of widget
             self.ternary_colormap = self.ui.comboBoxTernaryColormap.currentText()
        else:
             # update combobox with new value
             if self.ui.comboBoxTernaryColormap.currentText() == new_colormap:
                 return
             # block signals to prevent infinite loop
             self.ui.comboBoxTernaryColormap.blockSignals(True)
             self.ui.comboBoxTernaryColormap.setCurrentText(new_colormap)
             self.ui.comboBoxTernaryColormap.blockSignals(False)
        
        # update plot if required
        if self.ui.toolBox.currentIndex() == self.ui.left_tab['scatter'] and self.plot_type == 'ternary map':
            self.schedule_update()

    def update_ternary_color_x(self, new_color):
        self.ui.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.schedule_update()

    def update_ternary_color_y(self, new_color):
        self.ui.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.schedule_update()

    def update_ternary_color_z(self, new_color):
        self.ui.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.schedule_update()

    def update_ternary_color_m(self, new_color):
        self.ui.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % new_color)
        if self.ui.toolbox.currentIndex() == self.ui.left_tab['scatter']:
            self.schedule_update()

    def input_ternary_name_dlg(self):
        """Opens a dialog to save new colormap

        Executes on ``MainWindow.toolButtonSaveTernaryColormap`` is clicked.  Saves the current
        colors of `MainWindow.toolButtonTCmap*Color` into
        `resources/styles/ternary_colormaps_new.csv`.
        """
        name, ok = QInputDialog.getText(self.ui, 'Custom ternary colormap', 'Enter new colormap name:')
        if ok:
            # update colormap structure
            self.ternary_colormaps.append({'scheme': name,
                    'top': get_hex_color(self.ui.toolButtonTCmapXColor.palette().button().color()),
                    'left': get_hex_color(self.ui.toolButtonTCmapYColor.palette().button().color()),
                    'right': get_hex_color(self.ui.toolButtonTCmapZColor.palette().button().color()),
                    'center': get_hex_color(self.ui.toolButtonTCmapMColor.palette().button().color())})
            # update comboBox
            self.ui.comboBoxTernaryColormap.addItem(name)
            self.ui.comboBoxTernaryColormap.setText(name)
            # add new row to file
            df = pd.DataFrame.from_dict(self.ternary_colormaps)
            try:
                df.to_csv('resources/styles/ternary_colormaps_new.csv', index=False)
            except Exception as e:
                QMessageBox.warning(self.ui,'Error',f"Could not save style theme.\nError: {e}")

        else:
            QMessageBox.warning(self.ui,'Warning',f"Style theme not saved.\n")
            return


    def ternary_colormap_changed(self):
        """Changes toolButton backgrounds associated with ternary colormap

        Updates ternary colormap when swatch colors are changed in the Scatter and Heatmaps >
        Map from Ternary groupbox.  The ternary colored chemical map is updated.
        """
        for cmap in self.ternary_colormaps:
            if cmap['scheme'] == self.ui.comboBoxTernaryColormap.currentText():
                self.ui.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % cmap['top'])
                self.ui.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % cmap['left'])
                self.ui.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % cmap['right'])
                self.ui.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % cmap['center'])
    
    def button_color_select(self, button):
        """Select background color of button

        Parameters
        ----------
        button : QPushbutton, QToolbutton
            Button object that was clicked
        """
        old_color = button.palette().color(button.backgroundRole())
        color_dlg = QColorDialog(self.ui)
        color_dlg.setCurrentColor(old_color)
        color_dlg.setCustomColor(int(1),old_color)

        color = color_dlg.getColor()

        if color.isValid():
            button.setStyleSheet("background-color: %s;" % color.name())
            QColorDialog.setCustomColor(int(1),color)
            if button.accessibleName().startswith('Ternary'):
                button.setCurrentText('user defined')
