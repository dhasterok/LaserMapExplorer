import os, re, copy, pickle
from PyQt5.QtWidgets import ( QColorDialog, QTableWidgetItem, QMessageBox, QInputDialog )
from PyQt5.QtGui import ( QDoubleValidator, QFont, QFontDatabase )
from pyqtgraph import colormap
import src.common.format as fmt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import src.common.csvdict as csvdict
from src.common.colorfunc import get_hex_color, get_rgb_color
from src.app.config import BASEDIR
from src.common.ScheduleTimer import Scheduler

class Styling():
    """Manages plot styling for different plot types and syncs with main window UI.

    Attributes
    ----------
    plot_type : str
        The plot type 
    xlim : list[float]
        X-axis limits, [lower_bound, upper_bound]
    xlabel : str
        X-axis label
    xscale : str
        X-axis scale function, ``linear``, ``log``, or ``logit``
    ylim : list[float]
        Y-axis limits, [lower_bound, upper_bound]
    ylabel : str
        Y-axis label
    yscale : str
        Y-axis scale function, ``linear``, ``log``, or ``logit``
    zlabel : str
        Z-axis label
    aspect_ratio : float
    tick_dir : str
    font : str
        Font used in plot
    font_size : float
        Font size in plot
    scale_dir : str
        Direction of scale bar
    scale_location : str
        Location of scale bar
    scale_length : float
        Length of scalebar on certain map-type plots (see map_plot_types)
    overlay_color : str
        Hex string used to color annotations
    marker : str
        Marker type (see marker_dict)
    marker_size : float
        Marker size
    marker_color : str
        Hex string used to color markers
    marker_alpha : int
        Marker alpha blending.
    line_width : float
        Line width
    line_multiplier : float
        Multiplier used to lengthen (>1) or shorten (0,1) lines.
    line_color : str
        Hex string used to color lines
    color_field :
        Field or analyte used to coloring markers or heatmap
    color_field_type :
        Field type used to set potential color fields
    cmap : str
        Color map
    cbar_reverse : Bool
        Inverts colormap when ``True``
    cbar_dir : str
        Direction of color bar, ``horizontal`` or ``vertical``
    clim : list[float]
        Color-axis limits, [lower_bound, upper_bound]
    clabel : str
        Color-axis label
    cscale : str
        Color-axis scale function, ``linear``, ``log``, or ``logit``
    resolution : int
        Resolution for heat maps

    map_plot_types : list
        A list of plots that result in a map, i.e., ['analyte map', 'ternary map', 'PCA score', 'cluster', 'cluster score'].  This list is generally used as a check when setting certain styles or other plotting behavior related to maps.

    marker_dict : dict
        Dictionary of marker names used to translate ``comboBoxMarker`` to a subset of matplotlib makers symbol, though not all matplotlib markers
        are used.

        - o : circle
        - s : square
        - d : diamond
        - ^ : triangle (up)
        - v : triangle (down)
        - h : hexagon
        - p : pentagon

    style_dict : dict of dict
        Dictionary with plot style information that saves the properties of style widgets.  There is a keyword
        for each plot type listed in ``comboBoxPlotType``.  The exact behavior of each style item may vary depending upon the
        plot type.  While data related to plot and color axes may be stored in *style_dict*, *axis_dict* stores labels, bounds and scale for most plot fields.

        style_dict[plot_type] -- plot types include ``analyte map``, ``histogram``, ``correlation``, ``gradient map``, ``scatter``, ``heatmap``, ``ternary map``
        ``TEC``, ``radar``, ``variance``, ``vectors``, ``pca scatter``, ``pca heatmap``, ``PCA Score``, ``Clusters``, ``Cluster Score``, ``profile``

        * associated with widgets in the toolBoxTreeView > Styling > Axes tab
        'XLabel' : (str) -- x-axis label, set in ``lineEditXLabel``
        'YLabel' : (str) -- y-axis label, set in ``lineEditYLabel``
        'ZLabel' : (str) -- z-axis label, set in ``lineEditZLabel``, used only for ternary plots
        'XLim' : (list of float) -- x-axis bounds, set by ``lineEditXLB`` and ``lineEditXUB`` for the lower and upper bounds
        'YLim' : (list of float) -- y-axis bounds, set by ``lineEditYLB`` and ``lineEditYUB`` for the lower and upper bounds
        'XScale' : (str) -- x-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxXScale``
        'YScale' : (str) -- y-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxYScale``
        'TickDir' : (str) -- tick direction for all axes, ``none``, ``in`` or ``out``, set by ``comboBoxTickDirection``
        'AspectRatio' : (float) -- aspect ratio of plot area (relative to figure units, not axes), set in ``lineEditAspectRatio``

        * associated with widgets in the toolBoxTreeView > Styling > Annotations tab
        'Font' : (str) -- font type, pulled from the system font library, set in ``fontComboBox``
        'Size' : (str) -- font size in points, set in ``doubleSpinBoxFontSize``

        * associated with widgets in the toolBoxTreeView > Styling > Annotations tab
        'ScaleDir' : (str) -- direction of distance scale bar on maps, options include ``none``, ``horizontal`` and ``vertical``, set by ``comboBoxScaleDirection``
        'ScaleLocation' : (str) -- position of scale bar on maps, options include ``southeast``, ``northeast``, ``northwest``, and ``southwest``, set by ``comboBoxScaleLocation``
        'ScaleLength' : (float) -- length of scale bar on certain map-type plots.
        'OverlayColor' : (hex str) -- color of overlay objects and annotations, also color of vectors on pca scatter/heatmap, set by ``toolButtonOverlayColor``

        * associated with widgets in the toolBoxTreeView > Styling > Markers tab
        'Marker' : (str) -- marker symbol defined by matplotlib styles in the attribute ``marker_dict``
        'MarkerSize' : (int) -- marker size in points, set by ``doubleSpinBoxMarkerSize``
        'MarkerColor' : (hex str) -- color of markers, set by ``toolButtonMarkerColor``
        'MarkerAlpha' : (int) -- marker transparency, set by ``horizontalSliderMarkerAlpha``

        * associated with widgets in the toolBoxTreeView > Styling > Lines tab
        'LineWidth' : (float) -- width of line objects, varies between plot types, set by ``comboBoxLineWidth``
        'LineColor' : (float) -- width of line objects, varies between plot types, set by ``comboBoxLineWidth``
        'Multiplier' : (hex str) -- color of markers, set by ``toolButtonLineColor``

        * associated with widgets in the toolBoxTreeView > Styling > Colors tab
        'ColorFieldType' : (str) -- field type used to set colors in a figure, set by ``comboBoxColorByField``
        'ColorField' : (str) -- field used to set colors in a figure, set by ``comboBoxColorField``
        'Colormap' : (str) -- colormap used in figure, set by ``comboBoxFieldColormap``
        'CbarReverse' : (bool) -- inverts colormap, set by ``checkBoxReverseColormap``
        'CLim' : (list of float) -- color bounds, set by ``lineEditXLB`` and ``lineEditXUB`` for the lower and upper bounds
        'CScale' : (str) -- c-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxYScale``
        'CbarDir' : (str) -- colorbar direction, options include ``none``, ``vertical``, and ``horizontal``, set by ``comboBoxCbarDirection``
        'CLabel' : (str) -- colorbar label, set in ``lineEditCbarLabel``
        'Resolution' : (int) -- used to set discritization in 2D and ternary heatmaps, set by ``spinBoxHeatmapResolution``

        Parameters
        ----------
        parent : QMainWindow
            MainWindow with UI controls
        debug : bool, optional
            Prints debugging messages to stdout, by default ``False``

    """    
    def __init__(self, parent, debug=False):
        #super().__init__(parent)

        self.parent = parent
        self.debug = debug

        self.scheduler = Scheduler(callback=self.parent.update_SV)

        parent.comboBoxHistType.activated.connect(self.scheduler.schedule_update)
        parent.toolButtonNDimAnalyteAdd.clicked.connect(self.scheduler.schedule_update)
        parent.toolButtonNDimAnalyteSetAdd.clicked.connect(self.scheduler.schedule_update)
        parent.toolButtonNDimUp.clicked.connect(self.scheduler.schedule_update)
        parent.toolButtonNDimDown.clicked.connect(self.scheduler.schedule_update)
        parent.toolButtonNDimRemove.clicked.connect(self.scheduler.schedule_update)

        self._signal_state = True

        # create the default style dictionary (self.style_dict for each plot type)
        self.reset_default_styles()
        self.map_plot_types = ['analyte map', 'ternary map', 'PCA score', 'cluster', 'cluster score']

        self.marker_dict = {'circle':'o', 'square':'s', 'diamond':'d', 'triangle (up)':'^', 'triangle (down)':'v', 'hexagon':'h', 'pentagon':'p'}
        parent.comboBoxMarker.clear()
        parent.comboBoxMarker.addItems(self.marker_dict.keys())

        self._plot_type = self.parent.comboBoxPlotType.currentText()

        # set style theme
        parent.comboBoxStyleTheme.activated.connect(self.read_theme)

        parent.comboBoxFieldX.activated.connect(lambda: self.axis_variable_changed(parent.comboBoxFieldTypeX.currentText(), parent.comboBoxFieldX.currentText(), 'x'))
        parent.comboBoxFieldY.activated.connect(lambda: self.axis_variable_changed(parent.comboBoxFieldTypeY.currentText(), parent.comboBoxFieldY.currentText(), 'y'))
        parent.comboBoxFieldZ.activated.connect(lambda: self.axis_variable_changed(parent.comboBoxFieldTypeZ.currentText(), parent.comboBoxFieldZ.currentText(), 'z'))

        # comboBox with plot type
        # overlay and annotation properties
        parent.toolButtonOverlayColor.clicked.connect(self.overlay_color_callback)
        parent.toolButtonMarkerColor.clicked.connect(self.marker_color_callback)
        parent.toolButtonLineColor.clicked.connect(self.line_color_callback)
        parent.toolButtonClusterColor.clicked.connect(self.cluster_color_callback)
        parent.toolButtonXAxisReset.clicked.connect(lambda: self.axis_reset_callback('x'))
        parent.toolButtonYAxisReset.clicked.connect(lambda: self.axis_reset_callback('y'))
        parent.toolButtonCAxisReset.clicked.connect(lambda: self.axis_reset_callback('c'))
        parent.toolButtonClusterColorReset.clicked.connect(self.set_default_cluster_colors)
        #self.toolButtonOverlayColor.setStyleSheet("background-color: white;")

        setattr(parent.comboBoxMarker, "allItems", lambda: [parent.comboBoxMarker.itemText(i) for i in range(parent.comboBoxMarker.count())])
        setattr(parent.comboBoxLineWidth, "allItems", lambda: [parent.comboBoxLineWidth.itemText(i) for i in range(parent.comboBoxLineWidth.count())])
        setattr(parent.comboBoxColorByField, "allItems", lambda: [parent.comboBoxColorByField.itemText(i) for i in range(parent.comboBoxColorByField.count())])
        setattr(parent.comboBoxColorField, "allItems", lambda: [parent.comboBoxColorField.itemText(i) for i in range(parent.comboBoxColorField.count())])
        setattr(parent.comboBoxFieldColormap, "allItems", lambda: [parent.comboBoxFieldColormap.itemText(i) for i in range(parent.comboBoxFieldColormap.count())])

        # colormaps
        # matplotlib colormaps
        self.mpl_colormaps = colormap.listMaps('matplotlib')
        for i in range(len(self.mpl_colormaps) - 1, -1, -1):
            if self.mpl_colormaps[i].endswith('_r'):
                # If the item ends with '_r', remove it from the list
                del self.mpl_colormaps[i]

        # custom colormaps
        self.custom_color_dict = csvdict.import_csv_to_dict(os.path.join(BASEDIR,'resources/app_data/custom_colormaps.csv'))
        for key in self.custom_color_dict:
            self.custom_color_dict[key] = [h for h in self.custom_color_dict[key] if h]

        # add list of colormaps to comboBoxFieldColormap and set callbacks
        parent.comboBoxFieldColormap.clear()
        parent.comboBoxFieldColormap.addItems(list(self.custom_color_dict.keys())+self.mpl_colormaps)
        parent.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        parent.checkBoxReverseColormap.stateChanged.connect(self.colormap_direction_callback)

        # callback functions
        parent.comboBoxPlotType.currentTextChanged.connect(lambda: setattr(self, 'plot_type', parent.comboBoxPlotType.currentText()))
        #parent.comboBoxPlotType.currentIndexChanged.connect(lambda: self.plot_type_callback(update=True))

        parent.toolButtonUpdatePlot.clicked.connect(parent.update_SV)
        parent.toolButtonSaveTheme.clicked.connect(self.input_theme_name_dlg)
        # axes
        parent.lineEditXLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('x',parent.lineEditXLabel.text()))
        parent.lineEditYLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('y',parent.lineEditYLabel.text()))
        parent.lineEditZLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('z',parent.lineEditZLabel.text()))
        parent.lineEditCbarLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('c',parent.lineEditCbarLabel.text()))

        parent.comboBoxXScale.activated.connect(lambda: self.axis_scale_callback(parent.comboBoxXScale,'x'))
        parent.comboBoxYScale.activated.connect(lambda: self.axis_scale_callback(parent.comboBoxYScale,'y'))
        parent.comboBoxColorScale.activated.connect(lambda: self.axis_scale_callback(parent.comboBoxColorScale,'c'))

        parent.lineEditXLB.setValidator(QDoubleValidator())
        parent.lineEditXLB.precision = 3
        parent.lineEditXLB.toward = 0
        parent.lineEditXUB.setValidator(QDoubleValidator())
        parent.lineEditXUB.precision = 3
        parent.lineEditXUB.toward = 1
        parent.lineEditYLB.setValidator(QDoubleValidator())
        parent.lineEditYLB.precision = 3
        parent.lineEditYLB.toward = 0
        parent.lineEditYUB.setValidator(QDoubleValidator())
        parent.lineEditYUB.precision = 3
        parent.lineEditYUB.toward = 1
        parent.lineEditZLB.setValidator(QDoubleValidator())
        parent.lineEditZLB.precision = 3
        parent.lineEditZLB.toward = 0
        parent.lineEditZUB.setValidator(QDoubleValidator())
        parent.lineEditZUB.precision = 3
        parent.lineEditZUB.toward = 1
        parent.lineEditColorLB.setValidator(QDoubleValidator())
        parent.lineEditColorLB.precision = 3
        parent.lineEditColorLB.toward = 0
        parent.lineEditColorUB.setValidator(QDoubleValidator())
        parent.lineEditColorUB.precision = 3
        parent.lineEditColorUB.toward = 1
        parent.lineEditAspectRatio.setValidator(QDoubleValidator())

        parent.lineEditXLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 0, float(parent.lineEditXLB.text())))
        parent.lineEditXUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 1, float(parent.lineEditXUB.text())))
        parent.lineEditYLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 0, float(parent.lineEditYLB.text())))
        parent.lineEditYUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 1, float(parent.lineEditYUB.text())))
        parent.lineEditZLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('z', 0, float(parent.lineEditZLB.text())))
        parent.lineEditZUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('z', 1, float(parent.lineEditZUB.text())))
        parent.lineEditColorLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 0, float(parent.lineEditColorLB.text())))
        parent.lineEditColorUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 1, float(parent.lineEditColorUB.text())))

        parent.lineEditAspectRatio.editingFinished.connect(self.aspect_ratio_callback)
        parent.comboBoxTickDirection.activated.connect(self.tickdir_callback)
        # annotations
        parent.fontComboBox.activated.connect(self.font_callback)
        parent.doubleSpinBoxFontSize.valueChanged.connect(self.font_size_callback)
        # ---------
        # These are tools are for future use, when individual annotations can be added
        parent.tableWidgetAnnotation.setVisible(False)
        parent.toolButtonAnnotationDelete.setVisible(False)
        parent.toolButtonAnnotationSelectAll.setVisible(False)
        # ---------

        # scales
        parent.lineEditScaleLength.setValidator(QDoubleValidator())
        parent.comboBoxScaleDirection.activated.connect(lambda: setattr(self, 'scale_dir', parent.comboBoxScaleDirection.currentText()))
        #parent.comboBoxScaleDirection.activated.connect(self.scale_direction_callback)
        parent.comboBoxScaleLocation.activated.connect(self.scale_location_callback)
        #parent.lineEditScaleLength.editingFinished.connect(self.scale_length_callback)
        parent.lineEditScaleLength.editingFinished.connect(lambda: setattr(self, 'scale_length', parent.lineEditScaleLength.value))
        #overlay color
        parent.comboBoxMarker.activated.connect(self.marker_symbol_callback)
        parent.doubleSpinBoxMarkerSize.valueChanged.connect(self.marker_size_callback)
        parent.horizontalSliderMarkerAlpha.sliderReleased.connect(self.slider_alpha_changed)
        # lines
        parent.comboBoxLineWidth.activated.connect(self.line_width_callback)
        parent.lineEditLengthMultiplier.editingFinished.connect(self.length_multiplier_callback)
        # colors
        # marker color
        parent.comboBoxColorByField.activated.connect(self.color_by_field_callback)
        parent.comboBoxColorField.activated.connect(self.color_field_callback)
        parent.spinBoxColorField.valueChanged.connect(self.color_field_update)
        parent.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        parent.comboBoxCbarDirection.activated.connect(self.cbar_direction_callback)
        # resolution
        parent.spinBoxHeatmapResolution.valueChanged.connect(lambda: self.resolution_callback(update_plot=True))
        # clusters
        parent.spinBoxClusterGroup.valueChanged.connect(self.select_cluster_group_callback)

        # ternary colormaps
        # create ternary colors dictionary
        df = pd.read_csv(os.path.join(BASEDIR,'resources/styles/ternary_colormaps.csv'))
        self.ternary_colormaps = df.to_dict(orient='records')
        parent.comboBoxTernaryColormap.clear()
        schemes = []
        for cmap in self.ternary_colormaps:
            schemes.append(cmap['scheme'])
        parent.comboBoxTernaryColormap.addItems(schemes)
        parent.comboBoxTernaryColormap.addItem('user defined')

        # dialog for adding and saving new colormaps
        parent.toolButtonSaveTernaryColormap.clicked.connect(parent.input_ternary_name_dlg)

        # select new ternary colors
        parent.toolButtonTCmapXColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapXColor))
        parent.toolButtonTCmapYColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapYColor))
        parent.toolButtonTCmapZColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapZColor))
        parent.toolButtonTCmapMColor.clicked.connect(lambda: self.button_color_select(parent.toolButtonTCmapMColor))
        parent.comboBoxTernaryColormap.currentIndexChanged.connect(lambda: self.ternary_colormap_changed())
        self.ternary_colormap_changed()

    # -------------------------------------
    # Styling properties
    # -------------------------------------
    @property
    def plot_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._plot_type

    @plot_type.setter
    def plot_type(self, new_plot_type):
        if new_plot_type != self._plot_type:
            self._plot_type = new_plot_type
            if self.parent.comboBoxPlotType.currentText() != new_plot_type:
                self.parent.comboBoxPlotType.setCurrentText(new_plot_type)
            self.plot_type_callback(update=True)

    # xlim
    @property
    def xlim(self):
        return self.style_dict[self._plot_type]['XLim']

    @xlim.setter
    def xlim(self, value):
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['XLim'] = value
        else:
            raise ValueError("xlim must be a list of two floats or None.")

    # xlabel
    @property
    def xlabel(self):
        return self.style_dict[self._plot_type]['XLabel']

    @xlabel.setter
    def xlabel(self, label):
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['XLabel'] = label
        else:
            raise TypeError("label must be of type str or None.")

    # xscale
    @property
    def xscale(self):
        return self.style_dict[self._plot_type]['XScale']

    @xscale.setter
    def xscale(self, scale):
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['XScale'] = scale
        else:
            raise TypeError("scale must be linear, log or logit.")

    # ylim
    @property
    def ylim(self):
        return self.style_dict[self._plot_type]['YLim']

    @ylim.setter
    def ylim(self, value):
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['YLim'] = value
        else:
            raise ValueError("ylim must be a list of two floats or None.")

    # ylabel
    @property
    def ylabel(self):
        return self.style_dict[self._plot_type]['YLabel']

    @ylabel.setter
    def ylabel(self, label):
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['YLabel'] = label
        else:
            raise TypeError("label must be of type str or None.")

    # yscale
    @property
    def yscale(self):
        return self.style_dict[self._plot_type]['YScale']

    @yscale.setter
    def yscale(self, scale):
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['YScale'] = scale
        else:
            raise TypeError("scale must be linear, log or logit.")

    # zlim
    @property
    def zlim(self):
        return self.style_dict[self._plot_type]['ZLim']

    @zlim.setter
    def zlim(self, value):
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['ZLim'] = value
        else:
            raise ValueError("zlim must be a list of two floats or None.")

    # zlabel
    @property
    def zlabel(self):
        return self.style_dict[self._plot_type]['ZLabel']

    @zlabel.setter
    def zlabel(self, label):
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['ZLabel'] = label
        else:
            raise TypeError("label must be of type str or None.")

    # zscale
    @property
    def zscale(self):
        return self.style_dict[self._plot_type]['ZScale']

    @yscale.setter
    def yscale(self, scale):
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['ZScale'] = scale
        else:
            raise TypeError("scale must be linear, log or logit.")

    # aspect_ratio
    @property
    def aspect_ratio(self):
        return self.style_dict[self._plot_type]['AspectRatio']
    
    @aspect_ratio.setter
    def aspect_ratio(self, value):
        if value is None or isinstance(value, float):
            self.style_dict[self._plot_type]['AspectRatio'] = value

    # tick_dir 
    @property
    def tick_dir(self):
        return self.style_dict[self._plot_type]['TickDir']

    @tick_dir.setter
    def tick_dir(self, tickdir):
        if isinstance(tickdir, str):
            self.style_dict[self._plot_type]['TickDir'] = tickdir
        else:
            raise TypeError("tickdir must be of type str.")

    # font
    @property
    def font(self):
        return self.style_dict[self._plot_type]['Font']

    @font.setter
    def font(self, font_family):
        if isinstance(font_family, str):
            self.style_dict[self._plot_type]['Font'] = font_family
        else:
            raise TypeError("font_family must be of type str.")

    # font_size
    @property
    def font_size(self):
        return self.style_dict[self._plot_type]['FontSize']

    @font_size.setter
    def font_size(self, font_size):
        if isinstance(font_size, float):
            self.style_dict[self._plot_type]['FontSize'] = font_size
        else:
            raise TypeError("font_size must be of type float.")

    # scale_dir
    @property
    def scale_dir(self):
        return self.style_dict[self._plot_type]['ScaleDir']

    @scale_dir.setter
    def scale_dir(self, direction):
        if (direction is not None) and isinstance(direction, str) and (direction in ['none', 'horizontal', 'vertical']):
            if direction != self.style_dict[self._plot_type]['ScaleDir']:
                if self.parent.comboBoxScaleDirection.currentText() != direction:
                    self.parent.comboBoxScaleDirection.setCurrentText(direction)
                self.style_dict[self._plot_type]['ScaleDir'] = direction
                self.scale_direction_callback()
        else:
            raise TypeError("direction must be of type str.")

    # scale_location
    @property
    def scale_location(self):
        return self.style_dict[self._plot_type]['ScaleLocation']

    @scale_location.setter
    def scale_location(self, location):
        if (location is not None) and isinstance(location, str) and (location in ['northeast', 'northwest', 'southwest', 'southeast']):
            self.style_dict[self._plot_type]['ScaleLocation'] = location
        else:
            raise TypeError("location must be of type str.")

    # scale_length
    @property
    def scale_length(self):
        return self.style_dict[self._plot_type]['ScaleLength']

    @scale_length.setter
    def scale_length(self, length):
        if length is None or isinstance(length, float):
            # check constraints on length
            data = self.parent.data[self.parent.sample_id]
            scale_dir = self.style_dict[self._plot_type]['ScaleDir']
            if (length is None) or ((length <= 0) or (scale_dir == 'horizontal' and length > data.x_range) or (scale_dir == 'vertical' and length > data.y_range)):
                length = self.default_scale_length()

            # set scale_length and associated widget
            if length != self.style_dict[self._plot_type]['ScaleLength']:
                if self.parent.lineEditScaleLength.value != length:
                    self.parent.lineEditScaleLength.value = length
                self.style_dict[self._plot_type]['ScaleLength'] = length
                self.scheduler.schedule_update()
        else:
            raise TypeError("length must be of type float.")

    # overlay_color
    @property
    def overlay_color(self):
        return self.style_dict[self._plot_type]['OverlayColor']

    @overlay_color.setter
    def overlay_color(self, color):
        if color is None or self._is_valid_hex_color(color):
            self.style_dict[self._plot_type]['OverlayColor'] = color
        else:
            raise TypeError("color must be a hex string, #rrggbb")

    # marker
    @property
    def marker(self):
        return self.style_dict[self._plot_type]['Marker']

    @marker.setter
    def marker(self, marker_symbol):
        if isinstance(marker_symbol, float):
            self.style_dict[self._plot_type]['Marker'] = marker_symbol
        else:
            raise TypeError("marker_symbol must be of type float.")

    # marker_size
    @property
    def marker_size(self):
        return self.style_dict[self._plot_type]['MarkerSize']

    @marker_size.setter
    def marker_size(self, size):
        if isinstance(size, float):
            self.style_dict[self._plot_type]['MarkerSize'] = size
        else:
            raise TypeError("size must be of type float.")

    # marker_color
    @property
    def marker_color(self):
        return self.style_dict[self._plot_type]['MarkerColor']

    @marker_color.setter
    def marker_color(self, hexstr):
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['MarkerColor'] = hexstr
        else:
            raise TypeError("hexstr must be a hex string, #rrggbb")

    # marker_alpha
    @property
    def marker_alpha(self):
        return self.style_dict[self._plot_type]['MarkerAlpha']

    @marker_alpha.setter
    def marker_alpha(self, alpha):
        if isinstance(alpha, float) and 0 <= alpha and alpha <= 1:
            self.style_dict[self._plot_type]['MarkerAlpha'] = alpha
        else:
            raise TypeError("alpha must be of type float and [0,1].")

    # line_width
    @property
    def line_width(self):
        return self.style_dict[self._plot_type]['LineWidth']

    @line_width.setter
    def line_width(self, width):
        if isinstance(width, float):
            self.style_dict[self._plot_type]['LineWidth'] = width
        else:
            raise TypeError("width must be of type float.")

    # line_multiplier (for things like arrow length)
    @property
    def line_multiplier(self):
        return self.style_dict[self._plot_type]['LineMultiplier']

    @line_multiplier.setter
    def line_multiplier(self, value):
        if value is None or isinstance(value, float):
            self.style_dict[self._plot_type]['LineMultiplier'] = value
        else:
            raise TypeError("value must be of type float or None.")

    # line_color
    @property
    def line_color(self):
        return self.style_dict[self._plot_type]['LineColor']

    @line_color.setter
    def line_color(self, hexstr):
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['LineColor'] = hexstr
        else:
            raise TypeError("hexstr must be a hex string, #rrggbb")

    # color_field_type
    @property
    def color_field_type(self):
        return self.style_dict[self._plot_type]['ColorFieldType']

    @color_field_type.setter
    def color_field_type(self, field_type):
        if (field_type is None) or isinstance(field_type, str):
            self.style_dict[self._plot_type]['ColorFieldType'] = field_type
        else:
            raise TypeError("field_type must be of type str.")

    # color_field
    @property
    def color_field(self):
        return self.style_dict[self._plot_type]['ColorField']

    @color_field.setter
    def color_field(self, field):
        if (field is None) or isinstance(field, str):
            self.style_dict[self._plot_type]['ColorField'] = field
        else:
            raise TypeError("field must be of type str or None.")

    # cmap - colormap
    @property
    def cmap(self):
        return self.style_dict[self._plot_type]['Colormap']

    @cmap.setter
    def cmap(self, name):
        if (name is None) or isinstance(name, str):
            self.style_dict[self._plot_type]['Colormap'] = name
        else:
            raise TypeError("name must be of type str or None.")

    # inverse
    @property
    def cbar_reverse(self):
        return self.style_dict[self._plot_type]['CbarReverse']

    @cbar_reverse.setter
    def cbar_reverse(self, flag):
        if (flag is None) or isinstance(flag, str):
            self.style_dict[self._plot_type]['CbarReverse'] = flag
        else:
            raise TypeError("flag must be of type str or None.")

    # cbar_dir
    @property
    def cbar_dir(self):
        return self.style_dict[self._plot_type]['CbarDir']

    @cbar_dir.setter
    def cbar_dir(self, direction):
        if (direction is not None) and isinstance(direction, str) and (direction in ['none', 'horizontal', 'vertical']):
            self.style_dict[self._plot_type]['CbarDir'] = direction
        else:
            raise TypeError("direction must be of type str.")

    # clim
    @property
    def clim(self):
        return self.style_dict[self._plot_type]['CLim']

    @clim.setter
    def clim(self, value):
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['CLim'] = value
        else:
            raise ValueError("xlim must be a list of two floats or None.")

    # clabel
    @property
    def clabel(self):
        return self.style_dict[self._plot_type]['CLabel']

    @clabel.setter
    def clabel(self, label):
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['CLabel'] = label
        else:
            raise TypeError("label must be of type str or None.")

    # cscale
    @property
    def cscale(self):
        return self.style_dict[self._plot_type]['CScale']

    @cscale.setter
    def cscale(self, scale):
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['CScale'] = scale
        else:
            raise TypeError("scale must be linear, log or logit.")

    # resolution
    @property
    def resolution(self):
        return self.style_dict[self._plot_type]['Resolution']

    @resolution.setter
    def resolution(self, value):
        if value is None or isinstance(value, int):
            self.style_dict[self._plot_type]['Resolution'] = value
        else:
            raise TypeError("value must be an integer or None.")

    @property
    def signal_state(self):
        return self._signal_state
    
    @signal_state.setter
    def signal_state(self, state):
        if not isinstance(state, bool):
            raise TypeError("signal_state must be a bool")
        
        self._signal_state = state
        self.toggle_signals()
        
    # -------------------------------------
    # Validation functions
    # -------------------------------------
    def _is_valid_bounds(self, value):
        """Validates if a the variable has properties consistent with bounds."""
        return isinstance(value, list) and len(value) == 2 and value[1] > value[0]

    def _is_valid_scale(self, text):
        """Validates if a the variable is a valid string."""
        return isinstance(text, str) and text in ['linear', 'log', 'logit']
    
    def _is_valid_hex_color(self, hex_color):
        """Validates if a given string is a valid hex color code."""
        if isinstance(hex_color, str):
            return bool(re.fullmatch(r"#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})", hex_color))
        return False

    # -------------------------------------
    # Debugging fuctions
    # -------------------------------------
    def print_properties(self):
        for attr, value in vars(self).items():
            print(f"{attr}: {value}")
    
    def toggle_signals(self):
        """Toggles signals from all style widgets.  Useful when updating many widgets."""        

        if self.debug:
            print(f"toggle_signals, _signal_state: {self._signal_state}")

        parent = self.parent

        parent.comboBoxPlotType.blockSignals(self._signal_state)

       # x-axis widgets
        parent.lineEditXLB.blockSignals(self._signal_state)
        parent.lineEditXUB.blockSignals(self._signal_state)
        parent.comboBoxXScale.blockSignals(self._signal_state)
        parent.lineEditXLabel.blockSignals(self._signal_state)

        # y-axis widgets
        parent.lineEditYLB.blockSignals(self._signal_state)
        parent.lineEditYUB.blockSignals(self._signal_state)
        parent.comboBoxYScale.blockSignals(self._signal_state)
        parent.lineEditYLabel.blockSignals(self._signal_state)

        # z-axis widgets
        parent.lineEditZLB.blockSignals(self._signal_state)
        parent.lineEditZUB.blockSignals(self._signal_state)
        parent.comboBoxZScale.blockSignals(self._signal_state)
        parent.lineEditZLabel.blockSignals(self._signal_state)

        # other axis properties
        parent.lineEditAspectRatio.blockSignals(self._signal_state)
        parent.comboBoxTickDirection.blockSignals(self._signal_state)

        # annotations
        parent.fontComboBox.blockSignals(self._signal_state)
        parent.doubleSpinBoxFontSize.blockSignals(self._signal_state)
        parent.checkBoxShowMass.blockSignals(self._signal_state)

        # scale
        parent.comboBoxScaleDirection.blockSignals(self._signal_state)
        parent.comboBoxScaleLocation.blockSignals(self._signal_state)
        parent.lineEditScaleLength.blockSignals(self._signal_state)
        parent.toolButtonOverlayColor.blockSignals(self._signal_state)

        # markers and lines
        parent.comboBoxMarker.blockSignals(self._signal_state)
        parent.doubleSpinBoxMarkerSize.blockSignals(self._signal_state)
        parent.toolButtonMarkerColor.blockSignals(self._signal_state)
        parent.horizontalSliderMarkerAlpha.blockSignals(self._signal_state)
        parent.comboBoxLineWidth.blockSignals(self._signal_state)
        parent.toolButtonLineColor.blockSignals(self._signal_state)
        parent.lineEditLengthMultiplier.blockSignals(self._signal_state)

        # coloring
        parent.comboBoxColorByField.blockSignals(self._signal_state)
        parent.comboBoxColorField.blockSignals(self._signal_state)
        parent.spinBoxHeatmapResolution.blockSignals(self._signal_state)
        parent.comboBoxFieldColormap.blockSignals(self._signal_state)
        parent.checkBoxReverseColormap.blockSignals(self._signal_state)
        parent.lineEditColorLB.blockSignals(self._signal_state)
        parent.lineEditColorUB.blockSignals(self._signal_state)
        parent.comboBoxColorScale.blockSignals(self._signal_state)
        parent.lineEditCbarLabel.blockSignals(self._signal_state)
        parent.comboBoxCbarDirection.blockSignals(self._signal_state)

    # -------------------------------------
    # Style related fuctions/callbacks
    # -------------------------------------
    def reset_default_styles(self):
        """Resets ``MainWindow.styles`` dictionary to default values."""

        if self.debug:
            print("reset_default_styles")

        parent = self.parent
        styles = {}

        default_plot_style = {
                'XLim': [0,1], 'XScale': 'linear', 'XLabel': '', 'YLim': [0,1], 'YScale': 'linear', 'YLabel': '', 'ZLim': [0,1], 'ZLabel': '', 'ZScale': 'linear', 'AspectRatio': '1.0', 'TickDir': 'out',
                'Font': '', 'FontSize': 11.0,
                'ScaleDir': 'none', 'ScaleLocation': 'northeast', 'ScaleLength': None, 'OverlayColor': '#ffffff',
                'Marker': 'circle', 'MarkerSize': 6, 'MarkerColor': '#1c75bc', 'MarkerAlpha': 30,
                'LineWidth': 1.5, 'LineMultiplier': 1, 'LineColor': '#1c75bc',
                'ColorFieldType': 'None', 'ColorField': '', 'Colormap': 'viridis', 'CbarReverse': False, 'CLim':[0,1], 'CScale':'linear', 'CbarDir': 'vertical', 'CLabel': '', 'Resolution': 10 }

        # try to load one of the preferred fonts
        default_font = ['Avenir','Candara','Myriad Pro','Myriad','Aptos','Calibri','Helvetica','Arial','Verdana']
        names = QFontDatabase().families()
        for font in default_font:
            if font in names:
                parent.fontComboBox.setCurrentFont(QFont(font, 11))
                default_plot_style['Font'] = parent.fontComboBox.currentFont().family()
                break
            # try:
            #     self.fontComboBox.setCurrentFont(QFont(font, 11))
            #     default_plot_style['Font'] = self.fontComboBox.currentFont().family()
            # except:
            #     print(f'Could not find {font} font')


        styles = {'analyte map': copy.deepcopy(default_plot_style),
                'correlation': copy.deepcopy(default_plot_style),
                'histogram': copy.deepcopy(default_plot_style),
                'gradient map': copy.deepcopy(default_plot_style),
                'scatter': copy.deepcopy(default_plot_style),
                'heatmap': copy.deepcopy(default_plot_style),
                'ternary map': copy.deepcopy(default_plot_style),
                'TEC': copy.deepcopy(default_plot_style),
                'Radar': copy.deepcopy(default_plot_style),
                'variance': copy.deepcopy(default_plot_style),
                'vectors': copy.deepcopy(default_plot_style),
                'PCA scatter': copy.deepcopy(default_plot_style),
                'PCA heatmap': copy.deepcopy(default_plot_style),
                'PCA score': copy.deepcopy(default_plot_style),
                'cluster': copy.deepcopy(default_plot_style),
                'cluster score': copy.deepcopy(default_plot_style),
                'cluster performance': copy.deepcopy(default_plot_style),
                'profile': copy.deepcopy(default_plot_style)}

        # update default styles
        for k in styles.keys():
            styles[k]['Font'] = parent.fontComboBox.currentFont().family()

        styles['analyte map']['Colormap'] = 'plasma'
        styles['analyte map']['ColorFieldType'] = 'Analyte'

        styles['correlation']['AspectRatio'] = 1.0
        styles['correlation']['FontSize'] = 8
        styles['correlation']['Colormap'] = 'RdBu'
        styles['correlation']['CbarDir'] = 'vertical'
        styles['correlation']['CLim'] = [-1,1]

        styles['vectors']['AspectRatio'] = 1.0
        styles['vectors']['Colormap'] = 'RdBu'

        styles['gradient map']['Colormap'] = 'RdYlBu'

        styles['cluster score']['Colormap'] = 'plasma'
        styles['cluster score']['CbarDir'] = 'vertical'
        styles['cluster score']['ColorFieldType'] = 'cluster score'
        styles['cluster score']['ColorField'] = 'cluster0'
        styles['cluster score']['CScale'] = 'linear'

        styles['cluster']['CScale'] = 'discrete'
        styles['cluster']['MarkerAlpha'] = 100

        styles['cluster performance']['AspectRatio'] = 0.62

        styles['PCA score']['CScale'] = 'linear'
        styles['PCA score']['ColorFieldType'] = 'PCA score'
        styles['PCA score']['ColorField'] = 'PC1'

        styles['scatter']['AspectRatio'] = 1

        styles['heatmap']['AspectRatio'] = 1
        styles['heatmap']['CLim'] = [1,1000]
        styles['heatmap']['CScale'] = 'log'
        styles['TEC']['AspectRatio'] = 0.62
        styles['variance']['AspectRatio'] = 0.62
        styles['vectors']['CLim'] = [-1,1]
        styles['PCA scatter']['LineColor'] = '#4d4d4d'
        styles['PCA scatter']['LineWidth'] = 0.5
        styles['PCA scatter']['AspectRatio'] = 1
        styles['PCA heatmap']['AspectRatio'] = 1
        styles['PCA heatmap']['LineColor'] = '#ffffff'

        styles['variance']['FontSize'] = 8

        styles['histogram']['AspectRatio'] = 0.62
        styles['histogram']['LineWidth'] = 0

        styles['profile']['AspectRatio'] = 0.62
        styles['profile']['LineWidth'] = 1.0
        styles['profile']['MarkerSize'] = 12
        styles['profile']['MarkerColor'] = '#d3d3d3'
        styles['profile']['LineColor'] = '#d3d3d3'

        self.style_dict = styles

    # Themes
    # -------------------------------------
    def load_theme_names(self):
        """Loads theme names and adds them to the theme comboBox
        
        Looks for saved style themes (*.sty) in ``resources/styles/`` directory and adds them to
        ``MainWindow.comboBoxStyleTheme``.  After setting list, the comboBox is set to default style.
        """
        if self.debug:
            print("load_theme_names")

        parent = self.parent

        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/styles/'))
        style_list = [file.replace('.sty','') for file in file_list if file.endswith('.sty')]

        # add default to list
        style_list.insert(0,'default')

        # update theme comboBox
        parent.comboBoxStyleTheme.clear()
        parent.comboBoxStyleTheme.addItems(style_list)
        parent.comboBoxStyleTheme.setCurrentIndex(0)

        self.reset_default_styles()

    def read_theme(self):
        """Reads a style theme
        
        Executes when the user changes the ``MainWindow.comboBoxStyleTheme.currentIndex()``.
        """
        if self.debug:
            print("load_theme_names")
        parent = self.parent
        name = parent.comboBoxStyleTheme.currentText()

        if name == 'default':
            self.reset_default_styles()
            return

        try:
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'rb') as file:
                self.style_dict = pickle.load(file)
        except:
            QMessageBox.warning(parent,'Error','Could not load style theme.')


    def input_theme_name_dlg(self):
        """Opens a dialog to save style theme

        Executes on ``MainWindow.toolButtonSaveTheme`` is clicked.  The theme is added to
        ``MainWindow.comboBoxStyleTheme`` and the style widget settings for each plot type (``MainWindow.styles``) are saved as a
        dictionary into the theme name with a ``.sty`` extension.
        """
        if self.debug:
            print("input_theme_name_dlg")
        parent = self.parent

        name, ok = QInputDialog.getText(parent, 'Save custom theme', 'Enter theme name:')
        if ok:
            # update comboBox
            parent.comboBoxStyleTheme.addItem(name)
            parent.comboBoxStyleTheme.setCurrentText(name)

            # append theme to file of saved themes
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'wb') as file:
                pickle.dump(self.style_dict, file, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(parent,'Error','Could not save theme.')

            return

    # general style functions
    # -------------------------------------
    def disable_style_widgets(self):
        """Disables all style related widgets."""        
        if self.debug:
            print("disable_style_widgets")
        parent = self.parent

        # x-axis widgets
        parent.lineEditXLB.setEnabled(False)
        parent.lineEditXUB.setEnabled(False)
        parent.comboBoxXScale.setEnabled(False)
        parent.lineEditXLabel.setEnabled(False)

        # y-axis widgets
        parent.lineEditYLB.setEnabled(False)
        parent.lineEditYUB.setEnabled(False)
        parent.comboBoxYScale.setEnabled(False)
        parent.lineEditYLabel.setEnabled(False)

        # z-axis widgets
        parent.lineEditZLB.setEnabled(False)
        parent.lineEditZUB.setEnabled(False)
        parent.comboBoxZScale.setEnabled(False)
        parent.lineEditZLabel.setEnabled(False)

        # other axis properties
        parent.lineEditAspectRatio.setEnabled(False)
        parent.comboBoxTickDirection.setEnabled(False)

        # annotations
        parent.fontComboBox.setEnabled(False)
        parent.doubleSpinBoxFontSize.setEnabled(False)
        parent.checkBoxShowMass.setEnabled(False)

        # scale
        parent.comboBoxScaleDirection.setEnabled(False)
        parent.comboBoxScaleLocation.setEnabled(False)
        parent.lineEditScaleLength.setEnabled(False)
        parent.toolButtonOverlayColor.setEnabled(False)

        # markers and lines
        parent.comboBoxMarker.setEnabled(False)
        parent.doubleSpinBoxMarkerSize.setEnabled(False)
        parent.toolButtonMarkerColor.setEnabled(False)
        parent.horizontalSliderMarkerAlpha.setEnabled(False)
        parent.comboBoxLineWidth.setEnabled(False)
        parent.toolButtonLineColor.setEnabled(False)
        parent.lineEditLengthMultiplier.setEnabled(False)

        # coloring
        parent.comboBoxColorByField.setEnabled(False)
        parent.comboBoxColorField.setEnabled(False)
        parent.spinBoxHeatmapResolution.setEnabled(False)
        parent.comboBoxFieldColormap.setEnabled(False)
        parent.checkBoxReverseColormap.setEnabled(False)
        parent.lineEditColorLB.setEnabled(False)
        parent.lineEditColorUB.setEnabled(False)
        parent.comboBoxColorScale.setEnabled(False)
        parent.lineEditCbarLabel.setEnabled(False)
        parent.comboBoxCbarDirection.setEnabled(False)

        # clusters

    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        if self.debug:
            print("toggle_style_widgets")

        parent = self.parent

        #print('toggle_style_widgets')
        plot_type = self.plot_type.lower()

        self.disable_style_widgets()

        # annotation properties
        parent.fontComboBox.setEnabled(True)
        parent.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type.lower():
            case 'analyte map' | 'gradient map':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)

                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(True)
                parent.comboBoxScaleLocation.setEnabled(True)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(parent.spotdata) != 0:
                    parent.comboBoxMarker.setEnabled(True)
                    parent.doubleSpinBoxMarkerSize.setEnabled(True)
                    parent.horizontalSliderMarkerAlpha.setEnabled(True)
                    parent.labelMarkerAlpha.setEnabled(True)

                    parent.toolButtonMarkerColor.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                parent.comboBoxColorField.setEnabled(True)
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.lineEditColorLB.setEnabled(True)
                parent.lineEditColorUB.setEnabled(True)
                parent.comboBoxColorScale.setEnabled(True)
                parent.comboBoxCbarDirection.setEnabled(True)
                parent.lineEditCbarLabel.setEnabled(True)

            case 'correlation' | 'vectors':
                # axes properties
                parent.comboBoxTickDirection.setEnabled(True)

                # color properties
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.lineEditColorLB.setEnabled(True)
                parent.lineEditColorUB.setEnabled(True)
                parent.comboBoxCbarDirection.setEnabled(True)
                if plot_type.lower() == 'correlation':
                    parent.comboBoxColorByField.setEnabled(True)
                    if parent.comboBoxColorByField.currentText() == 'cluster':
                        parent.comboBoxColorField.setEnabled(True)

            case 'histogram':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.comboBoxXScale.setEnabled(True)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)
                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # marker properties
                parent.horizontalSliderMarkerAlpha.setEnabled(True)
                parent.labelMarkerAlpha.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                if parent.comboBoxColorByField.currentText().lower() == 'none':
                    parent.toolButtonMarkerColor.setEnabled(True)
                else:
                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)

            case 'scatter' | 'PCA scatter':
                # axes properties
                if (parent.toolBox.currentIndex() != parent.left_tab['scatter']) or (parent.comboBoxFieldZ.currentText() == ''):
                    parent.lineEditXLB.setEnabled(True)
                    parent.lineEditXUB.setEnabled(True)
                    parent.comboBoxXScale.setEnabled(True)
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.comboBoxYScale.setEnabled(True)

                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                if parent.comboBoxFieldZ.currentText() != '':
                    parent.lineEditZLB.setEnabled(True)
                    parent.lineEditZUB.setEnabled(True)
                    parent.comboBoxZScale.setEnabled(True)
                    parent.lineEditZLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # marker properties
                parent.comboBoxMarker.setEnabled(True)
                parent.doubleSpinBoxMarkerSize.setEnabled(True)
                parent.horizontalSliderMarkerAlpha.setEnabled(True)
                parent.labelMarkerAlpha.setEnabled(True)

                # line properties
                if parent.comboBoxFieldZ.currentText() == '':
                    parent.comboBoxLineWidth.setEnabled(True)
                    parent.toolButtonLineColor.setEnabled(True)

                if plot_type == 'PCA scatter':
                    parent.lineEditLengthMultiplier.setEnabled(True)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if parent.comboBoxColorByField.currentText().lower() == 'none':
                    parent.toolButtonMarkerColor.setEnabled(True)

                elif parent.comboBoxColorByField.currentText() == 'cluster':

                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)

                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxFieldColormap.setEnabled(True)
                    parent.lineEditColorLB.setEnabled(True)
                    parent.lineEditColorUB.setEnabled(True)
                    parent.comboBoxColorScale.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)
                    parent.lineEditCbarLabel.setEnabled(True)

            case 'heatmap' | 'PCA heatmap':
                # axes properties
                if (parent.toolBox.currentIndex() != parent.left_tab['scatter']) or (parent.comboBoxFieldZ.currentText() == ''):
                    parent.lineEditXLB.setEnabled(True)
                    parent.lineEditXUB.setEnabled(True)
                    parent.comboBoxXScale.setEnabled(True)
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.comboBoxYScale.setEnabled(True)

                parent.lineEditXLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                if (parent.toolBox.currentIndex() == parent.left_tab['scatter']) and (parent.comboBoxFieldZ.currentText() == ''):
                    parent.lineEditZLB.setEnabled(True)
                    parent.lineEditZUB.setEnabled(True)
                    parent.comboBoxZScale.setEnabled(True)
                    parent.lineEditZLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # line properties
                if parent.comboBoxFieldZ.currentText() == '':
                    parent.comboBoxLineWidth.setEnabled(True)
                    parent.toolButtonLineColor.setEnabled(True)

                if plot_type == 'PCA heatmap':
                    parent.lineEditLengthMultiplier.setEnabled(True)

                # color properties
                parent.comboBoxFieldColormap.setEnabled(True)
                parent.lineEditColorLB.setEnabled(True)
                parent.lineEditColorUB.setEnabled(True)
                parent.comboBoxColorScale.setEnabled(True)
                parent.comboBoxCbarDirection.setEnabled(True)
                parent.lineEditCbarLabel.setEnabled(True)

                parent.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.comboBoxXScale.setEnabled(True)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)
                parent.comboBoxYScale.setEnabled(True)
                parent.lineEditZLB.setEnabled(True)
                parent.lineEditZUB.setEnabled(True)
                parent.comboBoxZScale.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                parent.lineEditYLabel.setEnabled(True)
                parent.lineEditZLabel.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(True)
                parent.comboBoxScaleLocation.setEnabled(True)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if not parent.spotdata.empty:
                    parent.comboBoxMarker.setEnabled(True)
                    parent.doubleSpinBoxMarkerSize.setEnabled(True)
                    parent.horizontalSliderMarkerAlpha.setEnabled(True)
                    parent.labelMarkerAlpha.setEnabled(True)

                    parent.toolButtonMarkerColor.setEnabled(True)

            case 'tec' | 'radar':
                # axes properties
                if plot_type == 'tec':
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.lineEditYLabel.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.lineEditScaleLength.setEnabled(True)

                # marker properties
                parent.labelMarkerAlpha.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)

                # color properties
                parent.comboBoxColorByField.setEnabled(True)
                if parent.comboBoxColorByField.currentText().lower() == 'none':
                    parent.toolButtonMarkerColor.setEnabled(True)
                elif parent.comboBoxColorByField.currentText().lower() == 'cluster':
                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)

            case 'variance' | 'cluster performance':
                # axes properties
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                parent.comboBoxMarker.setEnabled(True)
                parent.doubleSpinBoxMarkerSize.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)

                # color properties
                parent.toolButtonMarkerColor.setEnabled(True)

            case 'pca score' | 'cluster score' | 'cluster':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.lineEditYLB.setEnabled(True)
                parent.lineEditYUB.setEnabled(True)

                # scalebar properties
                parent.comboBoxScaleDirection.setEnabled(True)
                parent.comboBoxScaleLocation.setEnabled(True)
                parent.lineEditScaleLength.setEnabled(True)
                parent.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(parent.spotdata) != 0:
                    parent.comboBoxMarker.setEnabled(True)
                    parent.doubleSpinBoxMarkerSize.setEnabled(True)
                    parent.horizontalSliderMarkerAlpha.setEnabled(True)
                    parent.labelMarkerAlpha.setEnabled(True)
                    parent.toolButtonMarkerColor.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)

                # color properties
                if plot_type != 'clusters':
                    parent.comboBoxColorByField.setEnabled(True)
                    parent.comboBoxColorField.setEnabled(True)
                    parent.comboBoxFieldColormap.setEnabled(True)
                    parent.lineEditColorLB.setEnabled(True)
                    parent.lineEditColorUB.setEnabled(True)
                    parent.comboBoxColorScale.setEnabled(True)
                    parent.comboBoxCbarDirection.setEnabled(True)
                    parent.lineEditCbarLabel.setEnabled(True)
            case 'profile':
                # axes properties
                parent.lineEditXLB.setEnabled(True)
                parent.lineEditXUB.setEnabled(True)
                parent.lineEditAspectRatio.setEnabled(True)
                parent.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                parent.lineEditScaleLength.setEnabled(True)

                # marker properties
                parent.comboBoxMarker.setEnabled(True)
                parent.doubleSpinBoxMarkerSize.setEnabled(True)

                # line properties
                parent.comboBoxLineWidth.setEnabled(True)
                parent.toolButtonLineColor.setEnabled(True)

                # color properties
                parent.toolButtonMarkerColor.setEnabled(True)
                parent.comboBoxFieldColormap.setEnabled(True)
        
        # enable/disable labels
        self.toggle_style_labels()

    def toggle_style_labels(self):
        """Toggles style labels based on enabled/disabled style widgets."""        
        if self.debug:
            print("toggle_style_labels")
        parent = self.parent

        # axes properties
        parent.labelXLim.setEnabled(parent.lineEditXLB.isEnabled())
        parent.toolButtonXAxisReset.setEnabled(parent.labelXLim.isEnabled())
        parent.labelXScale.setEnabled(parent.comboBoxXScale.isEnabled())
        parent.labelYLim.setEnabled(parent.lineEditYLB.isEnabled())
        parent.toolButtonYAxisReset.setEnabled(parent.labelYLim.isEnabled())
        parent.labelYScale.setEnabled(parent.comboBoxYScale.isEnabled())
        parent.labelZLim.setEnabled(parent.lineEditZLB.isEnabled())
        parent.toolButtonZAxisReset.setEnabled(parent.labelZLim.isEnabled())
        parent.labelZScale.setEnabled(parent.comboBoxZScale.isEnabled())
        parent.labelXLabel.setEnabled(parent.lineEditXLabel.isEnabled())
        parent.labelYLabel.setEnabled(parent.lineEditYLabel.isEnabled())
        parent.labelZLabel.setEnabled(parent.lineEditZLabel.isEnabled())
        parent.labelAspectRatio.setEnabled(parent.lineEditAspectRatio.isEnabled())
        parent.labelTickDirection.setEnabled(parent.comboBoxTickDirection.isEnabled())

        # scalebar properties
        parent.labelScaleLocation.setEnabled(parent.comboBoxScaleLocation.isEnabled())
        parent.labelScaleDirection.setEnabled(parent.comboBoxScaleDirection.isEnabled())
        if parent.toolButtonOverlayColor.isEnabled():
            parent.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % self.style_dict[self.plot_type]['OverlayColor'])
            parent.labelOverlayColor.setEnabled(True)
        else:
            parent.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            parent.labelOverlayColor.setEnabled(False)
        parent.labelScaleLength.setEnabled(parent.lineEditScaleLength.isEnabled())

        # marker properties
        parent.labelMarker.setEnabled(parent.comboBoxMarker.isEnabled())
        parent.labelMarkerSize.setEnabled(parent.doubleSpinBoxMarkerSize.isEnabled())
        parent.labelMarkerAlpha.setEnabled(parent.horizontalSliderMarkerAlpha.isEnabled())
        parent.labelTransparency.setEnabled(parent.horizontalSliderMarkerAlpha.isEnabled())

        # line properties
        parent.labelLineWidth.setEnabled(parent.comboBoxLineWidth.isEnabled())
        if parent.toolButtonLineColor.isEnabled():
            parent.toolButtonLineColor.setStyleSheet("background-color: %s;" % self.style_dict[self.plot_type]['LineColor'])
            parent.labelLineColor.setEnabled(True)
        else:
            parent.toolButtonLineColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            parent.labelLineColor.setEnabled(False)
        parent.labelLengthMultiplier.setEnabled(parent.lineEditLengthMultiplier.isEnabled())

        # color properties
        if parent.toolButtonMarkerColor.isEnabled():
            parent.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.style_dict[self.plot_type]['MarkerColor'])
            parent.labelMarkerColor.setEnabled(True)
        else:
            parent.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            parent.labelMarkerColor.setEnabled(False)
        parent.labelColorByField.setEnabled(parent.comboBoxColorByField.isEnabled())
        parent.labelColorField.setEnabled(parent.comboBoxColorField.isEnabled())
        parent.checkBoxReverseColormap.setEnabled(parent.comboBoxFieldColormap.isEnabled())
        parent.labelReverseColormap.setEnabled(parent.checkBoxReverseColormap.isEnabled())
        parent.labelFieldColormap.setEnabled(parent.comboBoxFieldColormap.isEnabled())
        parent.labelColorScale.setEnabled(parent.comboBoxColorScale.isEnabled())
        parent.labelColorBounds.setEnabled(parent.lineEditColorLB.isEnabled())
        parent.toolButtonCAxisReset.setEnabled(parent.labelColorBounds.isEnabled())
        parent.labelCbarDirection.setEnabled(parent.comboBoxCbarDirection.isEnabled())
        parent.labelCbarLabel.setEnabled(parent.lineEditCbarLabel.isEnabled())
        parent.labelHeatmapResolution.setEnabled(parent.spinBoxHeatmapResolution.isEnabled())

    def set_style_widgets(self, plot_type=None, style=None):
        """Sets values in right toolbox style page

        Parameters
        ----------
        plot_type : str, optional
            Dictionary key into ``MainWindow.styles``, Defaults to ``None``
        style : dict, optional
            Style dictionary for the current plot type. Defaults to ``None``
        """
        if self.debug:
            print("set_style_widgets")
        #print('set_style_widgets')
        parent = self.parent
        data = parent.data[parent.sample_id]

        tab_id = parent.toolBox.currentIndex()

        if plot_type is None:
            plot_type = parent.plot_types[tab_id][parent.plot_types[tab_id][0]+1]
            parent.comboBoxPlotType.blockSignals(True)
            parent.comboBoxPlotType.clear()
            parent.comboBoxPlotType.addItems(parent.plot_types[tab_id][1:])
            parent.comboBoxPlotType.setCurrentText(plot_type)
            parent.comboBoxPlotType.blockSignals(False)
        elif plot_type == '':
            return

        # toggle actionSwapAxes
        match plot_type:
            case 'analyte map' | 'gradient map':
                parent.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                parent.actionSwapAxes.setEnabled(True)
            case _:
                parent.actionSwapAxes.setEnabled(False)

        style = self.style_dict[self.plot_type]

        # axes properties
        # for map plots, check to see that 'X' and 'Y' are initialized
        if plot_type.lower() in self.map_plot_types:
            if ('X' not in list(data.axis_dict.keys())) or ('Y' not in list(data.axis_dict.keys())):
                # initialize 'X' and 'Y' axes
                # all plot types use the same map dimensions so just use Analyte for the field_type
                self.initialize_axis_values('Analyte','X')
                self.initialize_axis_values('Analyte','Y')
            xmin,xmax,xscale,xlabel = self.get_axis_values('Analyte','X')
            ymin,ymax,yscale,ylabel = self.get_axis_values('Analyte','Y')

            # set style dictionary values for X and Y
            style['XLim'] = [xmin, xmax]
            style['XScale'] = xscale
            style['XLabel'] = 'X'
            style['YLim'] = [ymin, ymax]
            style['YScale'] = yscale
            style['YLabel'] = 'Y'
            style['AspectRatio'] = parent.data[parent.sample_id].aspect_ratio

            # do not round axes limits for maps
            parent.lineEditXLB.precision = None
            parent.lineEditXUB.precision = None
            parent.lineEditXLB.value = style['XLim'][0]
            parent.lineEditXUB.value = style['XLim'][1]

            parent.lineEditYLB.value = style['YLim'][0]
            parent.lineEditYUB.value = style['YLim'][1]

            parent.lineEditZLB.value = style['ZLim'][0]
            parent.lineEditZUB.value = style['ZLim'][1]
        else:
            # round axes limits for everything that isn't a map
            parent.lineEditXLB.value = style['XLim'][0]
            parent.lineEditXUB.value = style['XLim'][1]

            parent.lineEditYLB.value = style['YLim'][0]
            parent.lineEditYUB.value = style['YLim'][1]

            parent.lineEditZLB.value = style['ZLim'][0]
            parent.lineEditZUB.value = style['ZLim'][1]

        parent.comboBoxXScale.setCurrentText(style['XScale'])
        parent.lineEditXLabel.setText(style['XLabel'])

        parent.comboBoxYScale.setCurrentText(style['YScale'])
        parent.lineEditYLabel.setText(style['YLabel'])

        parent.comboBoxYScale.setCurrentText(style['ZScale'])
        parent.lineEditZLabel.setText(style['ZLabel'])

        parent.lineEditAspectRatio.setText(str(style['AspectRatio']))

        # annotation properties
        #parent.fontComboBox.setCurrentFont(style['Font'])
        parent.doubleSpinBoxFontSize.blockSignals(True)
        parent.doubleSpinBoxFontSize.setValue(style['FontSize'])
        parent.doubleSpinBoxFontSize.blockSignals(False)

        # scalebar properties
        parent.comboBoxScaleLocation.setCurrentText(style['ScaleLocation'])
        parent.comboBoxScaleDirection.setCurrentText(style['ScaleDir'])
        if (style['ScaleLength'] is None) and (plot_type in self.map_plot_types):
            style['ScaleLength'] = self.default_scale_length()

            parent.lineEditScaleLength.value = style['ScaleLength']
        else:
            parent.lineEditScaleLength.value = None
            
        parent.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % style['OverlayColor'])

        # marker properties
        parent.comboBoxMarker.setCurrentText(style['Marker'])

        parent.doubleSpinBoxMarkerSize.blockSignals(True)
        parent.doubleSpinBoxMarkerSize.setValue(style['MarkerSize'])
        parent.doubleSpinBoxMarkerSize.blockSignals(False)

        parent.horizontalSliderMarkerAlpha.setValue(int(style['MarkerAlpha']))
        parent.labelMarkerAlpha.setText(str(parent.horizontalSliderMarkerAlpha.value()))

        # line properties
        parent.comboBoxLineWidth.setCurrentText(str(style['LineWidth']))
        parent.lineEditLengthMultiplier.value = style['LineMultiplier']
        parent.toolButtonLineColor.setStyleSheet("background-color: %s;" % style['LineColor'])

        # color properties
        parent.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % style['MarkerColor'])
        parent.update_field_type_combobox(parent.comboBoxColorByField,addNone=True,plot_type=plot_type)
        parent.comboBoxColorByField.setCurrentText(style['ColorFieldType'])

        if style['ColorFieldType'] == '':
            parent.comboBoxColorField.clear()
        else:
            parent.update_field_combobox(parent.comboBoxColorByField, parent.comboBoxColorField)
            parent.spinBoxColorField.setMinimum(0)
            parent.spinBoxColorField.setMaximum(parent.comboBoxColorField.count() - 1)

        if style['ColorField'] in parent.comboBoxColorField.allItems():
            parent.comboBoxColorField.setCurrentText(style['ColorField'])
            self.update_color_field_spinbox()
        else:
            style['ColorField'] = parent.comboBoxColorField.currentText()

        parent.comboBoxFieldColormap.setCurrentText(style['Colormap'])
        parent.checkBoxReverseColormap.blockSignals(True)
        parent.checkBoxReverseColormap.setChecked(style['CbarReverse'])
        parent.checkBoxReverseColormap.blockSignals(False)
        if style['ColorField'] in list(data.axis_dict.keys()):
            style['CLim'] = [data.axis_dict[style['ColorField']]['min'], data.axis_dict[style['ColorField']]['max']]
            style['CLabel'] = data.axis_dict[style['ColorField']]['label']
        parent.lineEditColorLB.value = style['CLim'][0]
        parent.lineEditColorUB.value = style['CLim'][1]
        if style['ColorFieldType'] == 'cluster':
            # set ColorField to active cluster method
            parent.comboBoxColorField.setCurrentText(parent.cluster_dict['active method'])

            # set color scale to discrete
            parent.comboBoxColorScale.clear()
            parent.comboBoxColorScale.addItem('discrete')
            parent.comboBoxColorScale.setCurrentText('discrete')

            style['CScale'] = 'discrete'
        else:
            # set color scale options to linear/log
            parent.comboBoxColorScale.clear()
            parent.comboBoxColorScale.addItems(['linear','log'])
            style['CScale'] = 'linear'
            parent.comboBoxColorScale.setCurrentText(style['CScale'])
            
        parent.comboBoxColorScale.setCurrentText(style['CScale'])
        parent.comboBoxCbarDirection.setCurrentText(style['CbarDir'])
        parent.lineEditCbarLabel.setText(style['CLabel'])

        parent.spinBoxHeatmapResolution.blockSignals(True)
        parent.spinBoxHeatmapResolution.setValue(style['Resolution'])
        parent.spinBoxHeatmapResolution.blockSignals(False)

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        # update plot (is this line needed)
        # self.update_SV()

    def get_style_dict(self):
        """Get style properties"""        
        if self.debug:
            print("get_style_dict")
        parent = self.parent

        plot_type = self.plot_type
        parent.plot_types[parent.toolBox.currentIndex()][0] = parent.comboBoxPlotType.currentIndex()

        
        self.style_dict[plot_type] = {
                # axes properties
                'XLim': [float(parent.lineEditXLB.text()), float(parent.lineEditXUB.text())],
                'XLabel': parent.lineEditXLabel.text(),
                'YLim': [float(parent.lineEditYLB.text()), float(parent.lineEditYUB.text())],
                'YLabel': parent.lineEditYLabel.text(),
                'ZLabel': parent.lineEditZLabel.text(),
                'AspectRatio': float(parent.lineEditAspectRatio.text()),
                'TickDir': parent.comboBoxTickDirection.text(),

                # annotation properties
                'Font': parent.fontComboBox.currentFont(),
                'FontSize': parent.doubleSpinBoxFontSize.value(),

                # scale properties
                'ScaleLocation': parent.comboBoxScaleLocation.currentText(),
                'ScaleDir': parent.comboBoxScaleDirection.currentText(),
                'ScaleLength': parent.lineEditScaleLength.value,
                'OverlayColor': get_hex_color(parent.toolButtonOverlayColor.palette().button().color()),

                # update marker properties
                'Marker': parent.comboBoxMarker.currentText(),
                'MarkerSize': parent.doubleSpinBoxMarkerSize.value(),
                'MarkerAlpha': float(parent.horizontalSliderMarkerAlpha.value()),
                'MarkerColor': get_hex_color(parent.toolButtonMarkerColor.palette().button().color()),

                # update line properties
                'LineWidth': float(parent.comboBoxLineWidth.currentText()),
                'LineMultiplier': float(parent.lineEditLengthMultiplier.text()),
                'LineColor': get_hex_color(parent.toolButtonLineColor.palette().button().color()),

                # update color properties
                'ColorFieldType': parent.comboBoxColorByField.currentText(),
                'ColorField': parent.comboBoxColorField.currentText(),
                'Colormap': parent.comboBoxFieldColormap.currentText(),
                'CbarReverse': parent.checkBoxReverseColormap.isChecked(),
                'CLim': [float(parent.lineEditColorLB.text()), float(parent.lineEditColorUB.text())],
                'CScale': parent.comboBoxColorScale.currentText(),
                'CbarDir': parent.comboBoxCbarDirection.currentText(),
                'CLabel': parent.lineEditCbarLabel.text(),
                'Resolution': parent.spinBoxHeatmapResolution.value()}

    # style widget callbacks
    # -------------------------------------
    def plot_type_callback(self, update=False):
        """Updates styles when plot type is changed

        Executes on change of ``MainWindow.comboBoxPlotType``.  Updates ``MainWindow.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        if self.debug:
            print("plot_type_callback")
        #print('plot_type_callback')
        # set plot flag to false
        parent = self.parent
        parent.plot_types[parent.toolBox.currentIndex()][0] = parent.comboBoxPlotType.currentIndex()

        match self.plot_type.lower():
            case 'analyte map' | 'gradient map':
                parent.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                parent.actionSwapAxes.setEnabled(True)
            case 'correlation':
                parent.actionSwapAxes.setEnabled(False)
                if parent.comboBoxCorrelationMethod.currentText() == 'None':
                    parent.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case 'cluster performance':
                parent.labelClusterMax.show()
                parent.spinBoxClusterMax.show()
                parent.labelNClusters.hide()
                parent.spinBoxNClusters.hide()
            case 'cluster' | 'cluster score':
                parent.labelClusterMax.hide()
                parent.spinBoxClusterMax.hide()
                parent.labelNClusters.show()
                parent.spinBoxNClusters.show()
            case _:
                parent.actionSwapAxes.setEnabled(False)

        self.signal_state = False
        self.set_style_widgets(plot_type=self.plot_type)
        self.signal_state = True
        #self.check_analysis_type()

        if update:
            self.scheduler.schedule_update()

    # axes
    # -------------------------------------
    def axis_variable_changed(self, fieldtype, field, ax="None"):
        """Updates axis variables when the field is changed.

        Parameters
        ----------
        fieldtype : str
            _description_
        field : str
            _description_
        ax : str, optional
            axis for plotting, by default "None"
        """
        if self.debug:
            print("axis_variable_changed")

        parent = self.parent
        if field == '' or field.lower() == 'none':
            match ax:
                case 'x':
                    parent.lineEditXLB.setEnabled(False)
                    parent.lineEditXUB.setEnabled(False)
                    parent.comboBoxXScale.setEnabled(False)
                    parent.lineEditXLabel.setEnabled(False)
                    parent.lineEditXLB.setText('')
                    parent.lineEditXUB.setText('')
                    parent.comboBoxXScale.setCurrentText('')
                    parent.lineEditXLabel.setText('')
                case 'y':
                    parent.lineEditYLB.setEnabled(False)
                    parent.lineEditYUB.setEnabled(False)
                    parent.comboBoxYScale.setEnabled(False)
                    parent.lineEditYLabel.setEnabled(False)
                    parent.lineEditYLB.setText('')
                    parent.lineEditYUB.setText('')
                    parent.comboBoxYScale.setCurrentText('')
                    parent.lineEditYLabel.setText('')
                case 'z':
                    parent.lineEditZLB.setEnabled(False)
                    parent.lineEditZUB.setEnabled(False)
                    parent.comboBoxZScale.setEnabled(False)
                    parent.lineEditZLabel.setEnabled(False)
                    parent.lineEditZLB.setText('')
                    parent.lineEditZUB.setText('')
                    parent.comboBoxZScale.setCurrentText('')
                    parent.lineEditZLabel.setText('')
            return
        else:
            amin, amax, scale, label = self.get_axis_values(fieldtype, field, ax)

            plot_type = self.plot_type

            self.style_dict[plot_type][ax+'Lim'] = [amin, amax]
            self.style_dict[plot_type][ax+'Scale'] = scale
            self.style_dict[plot_type][ax+'Label'] = label

            match ax:
                case 'x':
                    parent.lineEditXLB.setEnabled(True)
                    parent.lineEditXUB.setEnabled(True)
                    parent.comboBoxXScale.setEnabled(True)
                    parent.lineEditXLabel.setEnabled(True)
                    parent.lineEditXLB.value = amin
                    parent.lineEditXUB.value = amax
                    parent.comboBoxXScale.setCurrentText(scale)
                    parent.lineEditXLabel.setText(label)
                case 'y':
                    parent.lineEditYLB.setEnabled(True)
                    parent.lineEditYUB.setEnabled(True)
                    parent.comboBoxYScale.setEnabled(True)
                    parent.lineEditYLabel.setEnabled(True)
                    parent.lineEditYLB.value = amin
                    parent.lineEditYUB.value = amax
                    parent.comboBoxYScale.setCurrentText(scale)
                    parent.lineEditYLabel.setText(label)
                case 'z':
                    parent.lineEditZLB.setEnabled(True)
                    parent.lineEditZUB.setEnabled(True)
                    parent.comboBoxZScale.setEnabled(True)
                    parent.lineEditZLabel.setEnabled(True)
                    parent.lineEditZLB.value = amin
                    parent.lineEditZUB.value = amax
                    parent.comboBoxZScale.setCurrentText(scale)
                    parent.lineEditZLabel.setText(label)

            self.scheduler.schedule_update()

        parent.labelXLim.setEnabled(parent.lineEditXLB.isEnabled()) 
        parent.labelYLim.setEnabled(parent.lineEditYLB.isEnabled()) 
        parent.labelZLim.setEnabled(parent.lineEditZLB.isEnabled()) 
        parent.labelXScale.setEnabled(parent.comboBoxXScale.isEnabled())
        parent.labelYScale.setEnabled(parent.comboBoxYScale.isEnabled())
        parent.labelZScale.setEnabled(parent.comboBoxZScale.isEnabled())
        parent.labelXLabel.setEnabled(parent.lineEditXLabel.isEnabled())
        parent.labelYLabel.setEnabled(parent.lineEditYLabel.isEnabled())
        parent.labelZLabel.setEnabled(parent.lineEditZLabel.isEnabled())
        parent.toolButtonXAxisReset.setEnabled(parent.lineEditXLB.isEnabled()) 
        parent.toolButtonYAxisReset.setEnabled(parent.lineEditYLB.isEnabled()) 
        parent.toolButtonZAxisReset.setEnabled(parent.lineEditZLB.isEnabled()) 

    def get_axis_field(self, ax):
        """Grabs the field name from a given axis

        The field name for a given axis comes from a comboBox, and depends upon the plot type.
        Parameters
        ----------
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        """
        if self.debug:
            print("get_axis_field")
        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if ax == 'c':
            return parent.comboBoxColorField.currentText()

        match plot_type:
            case 'histogram':
                if ax in ['x', 'y']:
                    return parent.comboBoxHistField.currentText()
            case 'scatter' | 'heatmap':
                match ax:
                    case 'x':
                        return parent.comboBoxFieldX.currentText()
                    case 'y':
                        return parent.comboBoxFieldY.currentText()
                    case 'z':
                        return parent.comboBoxFieldZ.currentText()
            case 'PCA scatter' | 'PCA heatmap':
                match ax:
                    case 'x':
                        return f'PC{parent.spinBoxPCX.value()}'
                    case 'y':
                        return f'PC{parent.spinBoxPCY.value()}'
            case 'analyte map' | 'ternary map' | 'PCA score' | 'cluster' | 'cluster score':
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
        if self.debug:
            print("axis_label_edit_callback")

        parent = self.parent
        plot_type = parent.comboBoxPlotType.currentText()

        if ax == 'c':
            old_label = self.style_dict[plot_type][ax.upper()+'Label']
        else:
            old_label = self.style_dict[plot_type][ax.upper()+'Label']

        # if label has not changed return
        if old_label == new_label:
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        parent.data[parent.sample_id].axis_dict[field]['label'] = new_label
        if ax == 'c':
            self.style_dict[plot_type][ax.upper()+'Label'] = new_label
        else:
            self.style_dict[plot_type][ax.upper()+'Label'] = new_label

        # update plot
        self.scheduler.schedule_update()

    def axis_limit_edit_callback(self, ax, bound, new_value):
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
        if self.debug:
            print("axis_limit_edit_callback")

        parent = self.parent
        axis_dict = parent.data[parent.sample_id].axis_dict
        plot_type = parent.comboBoxPlotType.currentText()

        if ax == 'c':
            old_value = self.style_dict[plot_type]['CLim'][bound]
        else:
            old_value = self.style_dict[plot_type][ax.upper()+'Lim'][bound]

        # if label has not changed return
        if old_value == new_value:
            return

        if ax == 'c' and plot_type in ['heatmap', 'correlation']:
            self.scheduler.schedule_update()
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        if bound:
            if plot_type == 'histogram' and ax == 'y':
                axis_dict[field]['pmax'] = new_value
                axis_dict[field]['pstatus'] = 'custom'
            else:
                axis_dict[field]['max'] = new_value
                axis_dict[field]['status'] = 'custom'
        else:
            if plot_type == 'histogram' and ax == 'y':
                axis_dict[field]['pmin'] = new_value
                axis_dict[field]['pstatus'] = 'custom'
            else:
                axis_dict[field]['min'] = new_value
                axis_dict[field]['status'] = 'custom'

        if ax == 'c':
            self.style_dict[plot_type][f'{ax.upper()}Lim'][bound] = new_value
        else:
            self.style_dict[plot_type][f'{ax.upper()}Lim'][bound] = new_value

        # update plot
        self.scheduler.schedule_update()

    def axis_scale_callback(self, comboBox, ax):
        """Updates axis scale when a scale comboBox has changed.

        Parameters
        ----------
        comboBox : QComboBox
            Widget whos scale has changed.
        ax : str
            Axis whos scale been set from comboBox, options include ``x``, ``y``, ``z``, and ``c``.
        """        
        if self.debug:
            print("axis_scale_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        styles = self.style_dict[plot_type]

        new_value = comboBox.currentText()
        if ax == 'c':
            if styles['CLim'] == new_value:
                return
        elif styles[ax.upper()+'Scale'] == new_value:
            return

        field = self.get_axis_field(ax)

        if plot_type != 'heatmap':
            parent.data[parent.sample_id].axis_dict[field]['scale'] = new_value

        if ax == 'c':
            styles['CScale'] = new_value
        else:
            styles[ax.upper()+'Scale'] = new_value

        # update plot
        self.scheduler.schedule_update()

    def set_color_axis_widgets(self):
        """Sets the color axis limits and label widgets."""
        if self.debug:
            print("set_color_axis_widgets")

        #print('set_color_axis_widgets')
        parent = self.parent

        axis_dict = parent.data[parent.sample_id].axis_dict

        field = parent.comboBoxColorField.currentText()
        if field == '':
            return
        parent.lineEditColorLB.value = axis_dict[field]['min']
        parent.lineEditColorUB.value = axis_dict[field]['max']
        parent.comboBoxColorScale.setCurrentText(axis_dict[field]['scale'])

    def set_axis_widgets(self, ax, field):
        """Sets axis widgets in the style toolbox

        Updates axes limits and labels.

        Parameters
        ----------
        ax : str
            Axis 'x', 'y', or 'z'
        field : str
            Field plotted on axis, used as key to ``MainWindow.axis_dict``
        """
        if self.debug:
            print("set_axis_widgets")

        #print('set_axis_widgets')
        parent = self.parent
        if field == '':
            return

        match ax:
            case 'x':
                if field == 'X':
                    parent.lineEditXLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                    parent.lineEditXUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                else:
                    parent.lineEditXLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                    parent.lineEditXUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                parent.lineEditXLabel.setText(parent.data[parent.sample_id].axis_dict[field]['label'])
                parent.comboBoxXScale.setCurrentText(parent.data[parent.sample_id].axis_dict[field]['scale'])
            case 'y':
                if parent.comboBoxPlotType.currentText() == 'histogram':
                    parent.lineEditYLB.value = parent.data[parent.sample_id].axis_dict[field]['pmin']
                    parent.lineEditYUB.value = parent.data[parent.sample_id].axis_dict[field]['pmax']
                    parent.lineEditYLabel.setText(parent.comboBoxHistType.currentText())
                    parent.comboBoxYScale.setCurrentText('linear')
                else:
                    if field == 'X':
                        parent.lineEditYLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                        parent.lineEditYUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                    else:
                        parent.lineEditYLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                        parent.lineEditYUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                    parent.lineEditYLabel.setText(parent.data[parent.sample_id].axis_dict[field]['label'])
                    parent.comboBoxYScale.setCurrentText(parent.data[parent.sample_id].axis_dict[field]['scale'])
            case 'z':
                parent.lineEditZLB.value = parent.data[parent.sample_id].axis_dict[field]['min']
                parent.lineEditZUB.value = parent.data[parent.sample_id].axis_dict[field]['max']
                parent.lineEditZLabel.setText(parent.data[parent.sample_id].axis_dict[field]['label'])
                parent.comboBoxZScale.setCurrentText(parent.data[parent.sample_id].axis_dict[field]['scale'])

    def axis_reset_callback(self, ax):
        """Resets axes widgets and plot axes to auto values

        Axes parameters with ``MainWindow.axis_dict['status']`` can be ``auto`` or ``custom``, where ``custom``
        is set by the user in the appropriate *lineEdit* widgets.  The ``auto`` status is set by the full range
        of values of a data column.        

        Parameters
        ----------
        ax : str
            axis to reset values, can be ``x``, ``y``, and ``c``

        .. seealso::
            :ref: `initialize_axis_values` for initializing the axis dictionary
        """
        if self.debug:
            print(f"axis_reset_callback, axis: {ax}")

        #print('axis_reset_callback')
        parent = self.parent

        if ax == 'c':
            if parent.comboBoxPlotType.currentText() == 'vectors':
                self.style_dict['vectors']['CLim'] = [np.amin(parent.pca_results.components_), np.amax(parent.pca_results.components_)]
            elif not (parent.comboBoxColorByField.currentText() in ['None','cluster']):
                field_type = parent.comboBoxColorByField.currentText()
                field = parent.comboBoxColorField.currentText()
                if field == '':
                    return
                self.initialize_axis_values(field_type, field)

            self.set_color_axis_widgets()
        else:
            match parent.comboBoxPlotType.currentText().lower():
                case 'analyte map' | 'cluster' | 'cluster score' | 'pca score':
                    field = ax.upper()
                    self.initialize_axis_values('Analyte', field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = parent.comboBoxHistField.currentText()
                    if ax == 'x':
                        field_type = parent.comboBoxHistFieldType.currentText()
                        self.initialize_axis_values(field_type, field)
                        self.set_axis_widgets(ax, field)
                    else:
                        parent.data[parent.sample_id].axis_dict[field].update({'pstatus':'auto', 'pmin':None, 'pmax':None})

                case 'scatter' | 'heatmap':
                    match ax:
                        case 'x':
                            field_type = parent.comboBoxFieldTypeX.currentText()
                            field = parent.comboBoxFieldX.currentText()
                        case 'y':
                            field_type = parent.comboBoxFieldTypeY.currentText()
                            field = parent.comboBoxFieldY.currentText()
                        case 'z':
                            field_type = parent.comboBoxFieldTypeZ.currentText()
                            field = parent.comboBoxFieldZ.currentText()
                    if (field_type == '') | (field == ''):
                        return
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case 'PCA scatter' | 'PCA heatmap':
                    field_type = 'PCA score'
                    if ax == 'x':
                        field = parent.spinBoxPCX.currentText()
                    else:
                        field = parent.spinBoxPCY.currentText()
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.set_style_widgets()
        self.scheduler.schedule_update()

    def get_axis_values(self, field_type, field, ax=None):
        """Gets axis values

        Returns the axis parameters *field_type* > *field* for plotting, including the minimum and maximum vales,
        the scale (``linear`` or ``log``) and the axis label.  For x, y and color axes associated with the plot,
        no axis needs to be supplied.  For a probability axis associated with histogram PDF plots, ``ax=p``.

        Parameters
        ----------
        field_type : str
            Field type of axis data
        field : str
            Field name of axis data
        ax : str, optional
            stored axis: ``p`` for probability axis, otherwise all are same, by default None

        Returns
        -------
        float, float, str, float
            Axis parameters: minimum, maximum, scale (``linear`` or ``log``), axis label
        """ 
        if self.debug:
            print(f"get_axis_values\n  field_type: {field_type}\n  field: {field}\n  axis: {ax}")

        #print('get_axis_values')
        axis_dict = self.parent.data[self.parent.sample_id].axis_dict

        if field not in axis_dict.keys():
            self.initialize_axis_values(field_type, field)

        # get axis values from axis_dict
        amin = axis_dict[field]['min']
        amax = axis_dict[field]['max']
        scale = axis_dict[field]['scale']
        label = axis_dict[field]['label']

        # if probability axis associated with histogram
        if ax == 'p':
            pmin = axis_dict[field]['pmin']
            pmax = axis_dict[field]['pmax']
            return amin, amax, scale, label, pmin, pmax

        return amin, amax, scale, label

    def initialize_axis_values(self, field_type, field):
        """Initialize axis dict for a given field_type and field

        Parameters
        ----------
        field_type : str
            Field type, generally determined by a field type combobox.
        field : str
            Field, generally determined by a field combobox.
        """        
        if self.debug:
            print(f"get_axis_values\n  field_type: {field_type}\n  field: {field}")

        #print('initialize_axis_values')
        data = self.parent.data[self.parent.sample_id]

        # initialize variables
        if field not in data.axis_dict.keys():
            #print('initialize data.axis_dict["field"]')
            data.axis_dict.update({field:{'status':'auto', 'label':field, 'min':None, 'max':None}})

        #current_plot_df = pd.DataFrame()
        if field not in ['X','Y']:
            df = data.get_map_data(field, field_type)
            array = df['array'][data.mask].values if not df.empty else []
        else:
            # field 'X' and 'Y' require separate extraction
            array = data.processed_data[field].values

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                if field in ['X','Y']:
                    scale = 'linear'
                else:
                    symbol, mass = self.parse_field(field)
                    if field_type == 'Analyte':
                        data.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol} ({self.parent.preferences['Units']['Concentration']})"
                    else:
                        data.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol}$_N$ ({self.parent.preferences['Units']['Concentration']})"

                    scale = data.processed_data.get_attribute(field, 'norm')

                amin = np.nanmin(array)
                amax = np.nanmax(array)
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
                symbol_1, mass_1 = self.parse_field(field_1)
                symbol_2, mass_2 = self.parse_field(field_2)
                if field_type == 'Ratio':
                    data.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1} / $^{{{mass_2}}}${symbol_2}"
                else:
                    data.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1}$_N$ / $^{{{mass_2}}}${symbol_2}$_N$"

                amin = np.nanmin(array)
                amax = np.nanmax(array)
                scale = data.processed_data.get_attribute(field, 'norm')
            case _:
                scale = 'linear'

                amin = np.nanmin(array)
                amax = np.nanmax(array)

        # do not round 'X' and 'Y' so full extent of map is viewable
        if field not in ['X','Y']:
            amin = fmt.oround(amin, order=2, toward=0)
            amax = fmt.oround(amax, order=2, toward=1)

        d = {'status':'auto', 'min':amin, 'max':amax, 'scale':scale}

        data.axis_dict[field].update(d)
        #print(data.axis_dict[field])

    def parse_field(self,field):
        """Converts a field to symbol and mass.

        Separates an analyte field with a element symbol-mass name to its separate parts.

        Parameters
        ----------
        field : str
            Field name to separate into symbol and mass.

        Returns
        -------
        str, int
            Returns the element symbol and mass.
        """
        if self.debug:
            print(f"parse_field, field: {field}")

        match = re.match(r"([A-Za-z]+)(\d*)", field)
        symbol = match.group(1) if match else field
        mass = int(match.group(2)) if match.group(2) else None

        return symbol, mass

    def aspect_ratio_callback(self):
        """Update aspect ratio

        Updates ``MainWindow.style`` dictionary after user change
        """
        if self.debug:
            print(f"aspect_ratio_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['AspectRatio'] == parent.lineEditAspectRatio.text():
            return

        self.style_dict[plot_type]['AspectRatio'] = parent.lineEditAspectRatio.text()
        self.scheduler.schedule_update()

    def tickdir_callback(self):
        """Updates tick directions in style dictionary from change of ``MainWindow.comboBoxTickDirection``."""        
        if self.debug:
            print("tickdir_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['TickDir'] == parent.comboBoxTickDirection.currentText():
            return

        self.style_dict[plot_type]['TickDir'] = parent.comboBoxTickDirection.currentText()
        self.scheduler.schedule_update()

    # text and annotations
    # -------------------------------------
    def font_callback(self):
        """Updates figure fonts"""        
        if self.debug:
            print("font_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['Font'] == parent.fontComboBox.currentFont().family():
            return

        self.style_dict[plot_type]['Font'] = parent.fontComboBox.currentFont().family()
        self.scheduler.schedule_update()

    def font_size_callback(self):
        """Updates figure font sizes"""        
        if self.debug:
            print("font_size_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['FontSize'] == parent.doubleSpinBoxFontSize.value():
            return

        self.style_dict[plot_type]['FontSize'] = parent.doubleSpinBoxFontSize.value()
        self.scheduler.schedule_update()

    def update_figure_font(self, canvas, font_name):
        """updates figure fonts without the need to recreate the figure.

        Parameters
        ----------
        canvas : MplCanvas
            Canvas object displayed in UI.
        font_name : str
            Font used on plot.
        """        
        if self.debug:
            print("update_figure_font")

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
        if self.debug:
            print("toggle_mass")

        if not self.parent.checkBoxShowMass.isChecked():
            labels = [re.sub(r'\d', '', col) for col in labels]

        return labels

    # scales
    # -------------------------------------
    def scale_direction_callback(self):
        """Sets scale direction on figure"""        
        if self.debug:
            print("scale_direction_callback")

        parent = self.parent

        if self.style_dict[self._plot_type]['ScaleDir'] == 'none':
            parent.labelScaleLocation.setEnabled(False)
            parent.comboBoxScaleLocation.setEnabled(False)
            parent.labelScaleLength.setEnabled(False)
            parent.lineEditScaleLength.setEnabled(False)
            parent.lineEditScaleLength.value = None
        else:
            plot_type = self._plot_type
            parent.labelScaleLocation.setEnabled(True)
            parent.comboBoxScaleLocation.setEnabled(True)
            parent.labelScaleLength.setEnabled(True)
            parent.lineEditScaleLength.setEnabled(True)
            # set scalebar length if plot is a map type
            if plot_type not in self.map_plot_types:
                self.scale_length = None
            else:
                self.scale_length = self.default_scale_length()

        self.scheduler.schedule_update()

    def default_scale_length(self):
        """Sets default length of a scale bar for map-type plots

        Returns
        -------
        float
            Length of scalebar dependent on direction of scalebar.
        """        
        if self.debug:
            print("default_scale_length")

        if (self._plot_type not in self.map_plot_types) or (self.style_dict[self._plot_type]['ScaleDir'] == 'none'):
            return None

        data = self.parent.data[self.parent.sample_id]

        x_range = data.x_range
        y_range = data.y_range

        if self.style_dict[self._plot_type]['ScaleDir'] == 'vertical':
            length = 10**np.floor(np.log10(y_range))
            if length > x_range:
                length = 0.2 * y_range
        else: # scale_dir == horizontal
            length = 10**np.floor(np.log10(x_range))
            if length > x_range:
                length = 0.2 * x_range

        return length

    def scale_location_callback(self):
        """Sets scalebar location on map from ``MainWindow.comboBoxScaleLocation``"""        
        if self.debug:
            print("scale_location_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()

        if self.style_dict[plot_type]['ScaleLocation'] == parent.comboBoxScaleLocation.currentText():
            return

        self.style_dict[plot_type]['ScaleLocation'] = parent.comboBoxScaleLocation.currentText()
        self.scheduler.schedule_update()

    def scale_length_callback(self):
        """Updates length of scalebar on map-type plots
        
        Executes on change of ``MainWindow.lineEditScaleLength``, updates length if within bounds set by plot dimensions, then updates plot.
        """ 
        if self.debug:
            print("scale_length_callback")

        parent = self.parent
        data = parent.data[parent.sample_id]

        if self._plot_type in self.map_plot_types:
            # make sure user input is within bounds, do not change
            if ((parent.comboBoxScaleDirection.currentText() == 'horizontal') and (scale_length  > data.x_range)) or (scale_length <= 0):
                scale_length = self.style_dict[self._plot_type]['ScaleLength']
                parent.lineEditScaleLength.value = scale_length
                return
            elif ((parent.comboBoxScaleDirection.currentText() == 'vertical') and (scale_length > data.y_range)) or (scale_length <= 0):
                scale_length = self.style_dict[self._plot_type]['ScaleLength']
                parent.lineEditScaleLength.value = scale_length
                return
        else:
            if self.style_dict[self._plot_type]['ScaleLength'] is not None:
                self.scale_length = None
                return

        # update plot
        self.scheduler.schedule_update()

    def overlay_color_callback(self):
        """Updates color of overlay markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonOverlayColor`` color.
        """
        if self.debug:
            print("overlay_color_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(parent.toolButtonOverlayColor)

        color = get_hex_color(parent.toolButtonOverlayColor.palette().button().color())
        # update style
        if self.style_dict[plot_type]['OverlayColor'] == color:
            return

        self.style_dict[plot_type]['OverlayColor'] = color
        # update plot
        self.scheduler.schedule_update()

    # markers
    # -------------------------------------
    def marker_symbol_callback(self):
        """Updates marker symbol

        Updates marker symbols on current plot on change of ``MainWindow.comboBoxMarker.currentText()``.
        """
        if self.debug:
            print("marker_symbol_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['Marker'] == parent.comboBoxMarker.currentText():
            return
        self.style_dict[plot_type]['Marker'] = parent.comboBoxMarker.currentText()

        self.scheduler.schedule_update()

    def marker_size_callback(self):
        """Updates marker size

        Updates marker size on current plot on change of ``MainWindow.doubleSpinBoxMarkerSize.value()``.
        """
        if self.debug:
            print("marker_size_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['MarkerSize'] == parent.doubleSpinBoxMarkerSize.value():
            return
        self.style_dict[plot_type]['MarkerSize'] = parent.doubleSpinBoxMarkerSize.value()

        self.scheduler.schedule_update()

    def slider_alpha_changed(self):
        """Updates transparency on scatter plots.

        Executes on change of ``MainWindow.horizontalSliderMarkerAlpha.value()``.
        """
        if self.debug:
            print("slider_alpha_changed")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        parent.labelMarkerAlpha.setText(str(parent.horizontalSliderMarkerAlpha.value()))

        if parent.horizontalSliderMarkerAlpha.isEnabled():
            self.style_dict[plot_type]['MarkerAlpha'] = float(parent.horizontalSliderMarkerAlpha.value())
            self.scheduler.schedule_update()

    # lines
    # -------------------------------------
    def line_width_callback(self):
        """Updates line width

        Updates line width on current plot on change of ``MainWindow.comboBoxLineWidth.currentText().
        """
        if self.debug:
            print("line_width_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['LineWidth'] == float(parent.comboBoxLineWidth.currentText()):
            return

        self.style_dict[plot_type]['LineWidth'] = float(parent.comboBoxLineWidth.currentText())
        self.scheduler.schedule_update()

    def length_multiplier_callback(self):
        """Updates line length multiplier

        Used when plotting vector components in multidimensional plots.  Values entered by the user must be (0,10]
        """
        if self.debug:
            print("length_multiplier_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if not float(parent.lineEditLengthMultiplier.text()):
            parent.lineEditLengthMultiplier.values = self.style_dict[plot_type]['LineMultiplier']

        value = float(parent.lineEditLengthMultiplier.text())
        if self.style_dict[plot_type]['LineMultiplier'] == value:
            return
        elif (value < 0) or (value >= 100):
            parent.lineEditLengthMultiplier.values = self.style_dict[plot_type]['LineMultiplier']
            return

        self.style_dict[plot_type]['LineMultiplier'] = value
        self.scheduler.schedule_update()

    def line_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonLineColor`` color.
        """
        if self.debug:
            print("line_color_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(parent.toolButtonLineColor)
        color = get_hex_color(parent.toolButtonLineColor.palette().button().color())
        if self.style_dict[plot_type]['LineColor'] == color:
            return

        # update style
        self.style_dict[plot_type]['LineColor'] = color

        # update plot
        self.scheduler.schedule_update()

    # colors
    # -------------------------------------
    def marker_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonMarkerColor`` color.
        """
        if self.debug:
            print("marker_color_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(parent.toolButtonMarkerColor)
        color = get_hex_color(parent.toolButtonMarkerColor.palette().button().color())
        if self.style_dict[plot_type]['MarkerColor'] == color:
            return

        # update style
        self.style_dict[plot_type]['MarkerColor'] = color

        # update plot
        self.scheduler.schedule_update()

    def resolution_callback(self, update_plot=False):
        """Updates heatmap resolution

        Updates the resolution of heatmaps when ``MainWindow.spinBoxHeatmapResolution`` is changed.

        Parameters
        ----------
        update_plot : bool, optional
            Sets the resolution of a heatmap for either Cartesian or ternary plots and both *heatmap* and *pca heatmap*, by default ``False``
        """
        if self.debug:
            print("resolution_callback")

        parent = self.parent

        style = self.style_dict[parent.comboBoxPlotType.currentText()]

        style['Resolution'] = parent.spinBoxHeatmapResolution.value()

        if update_plot:
            self.scheduler.schedule_update()

    # updates scatter styles when ColorByField comboBox is changed
    def color_by_field_callback(self):
        """Executes on change to *ColorByField* combobox
        
        Updates style associated with ``MainWindow.comboBoxColorByField``.  Also updates
        ``MainWindow.comboBoxColorField`` and ``MainWindow.comboBoxColorScale``."""
        if self.debug:
            print("color_by_field_callback")

        #print('color_by_field_callback')
        parent = self.parent

        # need this line to update field comboboxes when colorby field is updated
        parent.update_field_combobox(parent.comboBoxColorByField, parent.comboBoxColorField)
        self.update_color_field_spinbox()
        plot_type = parent.comboBoxPlotType.currentText()
        if plot_type == '':
            return

        style = self.style_dict[plot_type]
        if style['ColorFieldType'] == parent.comboBoxColorByField.currentText():
            return

        style['ColorFieldType'] = parent.comboBoxColorByField.currentText()
        if parent.comboBoxColorByField.currentText() != '':
            self.set_style_widgets(plot_type)

        if parent.comboBoxPlotType.isEnabled() == False | parent.comboBoxColorByField.isEnabled() == False:
            return

        # only run update current plot if color field is selected or the color by field is clusters
        if parent.comboBoxColorByField.currentText() != 'None' or parent.comboBoxColorField.currentText() != '' or parent.comboBoxColorByField.currentText() in ['cluster']:
            self.scheduler.schedule_update()

    def color_field_callback(self, plot=True):
        """Updates color field and plot

        Executes on change of ``MainWindow.comboBoxColorField``
        """
        if self.debug:
            print("color_field_callback")

        parent = self.parent

        #print('color_field_callback')
        data = parent.data[parent.sample_id]

        plot_type = parent.comboBoxPlotType.currentText()
        field = parent.comboBoxColorField.currentText()
        self.update_color_field_spinbox()
        
        if self.style_dict[plot_type]['ColorField'] == field:
            return

        self.style_dict[plot_type]['ColorField'] = field

        if field != '' and field is not None:
            if field not in data.axis_dict.keys():
                self.initialize_axis_values(parent.comboBoxColorByField.currentText(), field)

            self.set_color_axis_widgets()
            if plot_type not in ['correlation']:
                self.style_dict[plot_type]['CLim'] = [data.axis_dict[field]['min'], data.axis_dict[field]['max']]
                self.style_dict[plot_type]['CLabel'] = data.axis_dict[field]['label']
        else:
            parent.lineEditCbarLabel.setText('')

        # update plot
        if plot:
            self.scheduler.schedule_update()

    def color_field_update(self):
        """Updates ``MainWindow.comboBoxColorField``"""        
        if self.debug:
            print("color_field_update")

        parent = self.parent

        parent.spinBoxColorField.blockSignals(True)
        parent.comboBoxColorField.setCurrentIndex(parent.spinBoxColorField.value())
        self.color_field_callback(plot=True)
        parent.spinBoxColorField.blockSignals(False)

    def field_colormap_callback(self):
        """Sets the color map

        Sets the colormap in ``MainWindow.styles`` for the current plot type, set from ``MainWindow.comboBoxFieldColormap``.
        """
        if self.debug:
            print("field_colormap_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['Colormap'] == parent.comboBoxFieldColormap.currentText():
            return

        self.toggle_style_widgets()
        self.style_dict[parent.comboBoxPlotType.currentText()]['Colormap'] = parent.comboBoxFieldColormap.currentText()

        self.scheduler.schedule_update()
    
    def update_color_field_spinbox(self):
        """Updates ``spinBoxColorField`` using the index of ``comboBoxColorField``"""        
        if self.debug:
            print("update_color_field_spinbox")

        self.parent.spinBoxColorField.setValue(self.parent.comboBoxColorField.currentIndex())

    def colormap_direction_callback(self):
        """Set colormap direction (normal/reverse)

        Reverses colormap if ``MainWindow.checkBoxReverseColormap.isChecked()`` is ``True``."""
        if self.debug:
            print("colormap_direction_callback")

        parent = self.parent

        plot_type = self.parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['CbarReverse'] == parent.checkBoxReverseColormap.isChecked():
            return

        self.style_dict[plot_type]['CbarReverse'] = parent.checkBoxReverseColormap.isChecked()

        self.scheduler.schedule_update()

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
        if self.debug:
            print("get_cluster_colormap")

        n = cluster_dict['n_clusters']
        cluster_color = [None]*n
        cluster_label = [None]*n
        
        # convert colors from hex to rgb and add to cluster_color list
        for i in range(n):
            color = get_rgb_color(cluster_dict[i]['color'])
            cluster_color[i] = tuple(float(c)/255 for c in color) + (float(alpha)/100,)
            cluster_label[i] = cluster_dict[i]['name']

        # mask
        if 99 in list(cluster_dict.keys()):
            color = get_rgb_color(cluster_dict[99]['color'])
            cluster_color.append(tuple(float(c)/255 for c in color) + (float(alpha)/100,))
            cluster_label.append(cluster_dict[99]['name'])
            cmap = colors.ListedColormap(cluster_color, N=n+1)
        else:
            cmap = colors.ListedColormap(cluster_color, N=n)

        return cluster_color, cluster_label, cmap

    def color_norm(self, N=None):
        """Normalize colors for colormap

        Parameters
        ----------
        N : int, optional
            The number of colors for discrete color maps, Defaults to None
        
        Returns
        -------
            matplotlib.colors.Norm
                Color norm for plotting.
        """
        if self.debug:
            print("color_norm")

        norm = None
        match self.cscale:
            case 'linear':
                norm = colors.Normalize(vmin=self.clim[0], vmax=self.clim[1])
            case 'log':
                norm = colors.LogNorm(vmin=self.clim[0], vmax=self.clim[1])
            case 'discrete':
                if N is None:
                    QMessageBox(self,"Warning","N must not be None when color scale is discrete.")
                    return
                boundaries = np.arange(-0.5, N, 1)
                norm = colors.BoundaryNorm(boundaries, N, clip=True)

        #scalarMappable = plt.cm.ScalarMappable(cmap=self.style.get_colormap(), norm=norm)

        return norm

    def get_colormap(self, N=None):
        """Gets the color map

        Gets the colormap from ``MainWindow.styles`` for the current plot type and reverses or sets as discrete in needed.

        Parameters
        ----------
        N : int, optional
            Creates a discrete color map, if not supplied, the colormap is continuous, Defaults to None.

        Returns
        -------
        matplotlib.colormap.ListedColormap : colormap
        """
        if self.debug:
            print("get_colormap")

        parent = self.parent

        if parent.canvasWindow.currentIndex() == parent.canvas_tab['qv']:
            plot_type = 'analyte map'
        else:
            plot_type = self.parent.comboBoxPlotType.currentText()

        name = self.style_dict[plot_type]['Colormap']
        if name in self.mpl_colormaps:
            if N is not None:
                cmap = plt.get_cmap(name, N)
            else:
                cmap = plt.get_cmap(name)
        else:
            cmap = self.create_custom_colormap(name, N)

        if self.style_dict[plot_type]['CbarReverse']:
            cmap = cmap.reversed()

        return cmap

    def create_custom_colormap(self, name, N=None):
        """Creates custom colormaps

        Custom colormaps as found in ``resources/appdata/custom_colormaps.xlsx``.

        Parameters
        ----------
        name : str
            Name of colormap
        N : int, optional
            Number of colors to compute using colormap, by default None

        Returns
        -------
        matplotlib.LinearSegmentedColormap
            Colormap
        """
        if self.debug:
            print("create_custom_colormap")

        if N is None:
            N = 256

        color_list = get_rgb_color(self.custom_color_dict[name])

        cmap = colors.LinearSegmentedColormap.from_list(name, color_list, N=N)

        return cmap

    def cbar_direction_callback(self):
        """Sets the colorbar direction

        Sets the colorbar direction in ``MainWindow.styles`` for the current plot type.
        """
        if self.debug:
            print("cbar_direction_callback")

        parent = self.parent

        plot_type = self.parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['CbarDir'] == parent.comboBoxCbarDirection.currentText():
            return
        self.style_dict[plot_type]['CbarDir'] = parent.comboBoxCbarDirection.currentText()

        self.scheduler.schedule_update()

    def cbar_label_callback(self):
        """Sets color label

        Sets the color label in ``MainWindow.styles`` for the current plot type.
        """
        if self.debug:
            print("cbar_label_callback")

        parent = self.parent

        plot_type = parent.comboBoxPlotType.currentText()
        if self.style_dict[plot_type]['CLabel'] == parent.lineEditCbarLabel.text():
            return
        self.style_dict[plot_type]['CLabel'] = parent.lineEditCbarLabel.text()

        if parent.comboBoxCbarLabel.isEnabled():
            self.scheduler.schedule_update()

    # cluster styles
    # -------------------------------------
    def cluster_color_callback(self):
        """Updates color of a cluster

        Uses ``QColorDialog`` to select new cluster color and then updates plot on change of
        backround ``MainWindow.toolButtonClusterColor`` color.  Also updates ``MainWindow.tableWidgetViewGroups``
        color associated with selected cluster.  The selected cluster is determined by ``MainWindow.spinBoxClusterGroup.value()``
        """
        if self.debug:
            print("cluster_color_callback")

        parent = self.parent
        #print('cluster_color_callback')
        if parent.tableWidgetViewGroups.rowCount() == 0:
            return

        selected_cluster = parent.spinBoxClusterGroup.value()-1

        # change color
        self.button_color_select(parent.toolButtonClusterColor)
        color = get_hex_color(parent.toolButtonClusterColor.palette().button().color())
        parent.cluster_dict[parent.cluster_dict['active method']][selected_cluster]['color'] = color
        if parent.tableWidgetViewGroups.item(selected_cluster,2).text() == color:
            return

        # update_table
        parent.tableWidgetViewGroups.setItem(selected_cluster,2,QTableWidgetItem(color))

        # update plot
        if parent.comboBoxColorByField.currentText() == 'cluster':
            self.scheduler.schedule_update()

    def set_default_cluster_colors(self, mask=False):
        """Sets cluster group to default colormap

        Sets the colors in ``MainWindow.tableWidgetViewGroups`` to the default colormap in
        ``MainWindow.styles['cluster']['Colormap'].  Change the default colormap
        by changing ``MainWindow.comboBoxColormap``, when ``MainWindow.comboBoxColorByField.currentText()`` is ``Cluster``.

        Returns
        -------
            str : hexcolor
        """
        if self.debug:
            print("set_default_cluster_colors")

        #print('set_default_cluster_colors')
        parent = self.parent

        # cluster colormap
        cmap = self.get_colormap(N=self.parent.tableWidgetViewGroups.rowCount())

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(parent.tableWidgetViewGroups.rowCount()):
            hexcolor.append(get_hex_color(colors[i]))
            parent.tableWidgetViewGroups.blockSignals(True)
            parent.tableWidgetViewGroups.setItem(i,2,QTableWidgetItem(hexcolor[i]))
            parent.tableWidgetViewGroups.blockSignals(False)

        if mask:
            hexcolor.append(self.style_dict['cluster']['OverlayColor'])

        parent.toolButtonClusterColor.setStyleSheet("background-color: %s;" % parent.tableWidgetViewGroups.item(parent.spinBoxClusterGroup.value()-1,2).text())

        return hexcolor

    def select_cluster_group_callback(self):
        """Set cluster color button background after change of selected cluster group

        Sets ``MainWindow.toolButtonClusterColor`` background on change of ``MainWindow.spinBoxClusterGroup``
        """
        if self.debug:
            print("select_cluster_group_callback")

        parent = self.parent
        if parent.tableWidgetViewGroups.rowCount() == 0:
            return
        parent.toolButtonClusterColor.setStyleSheet("background-color: %s;" % parent.tableWidgetViewGroups.item(parent.spinBoxClusterGroup.value()-1,2).text())

    def ternary_colormap_changed(self):
        """Changes toolButton backgrounds associated with ternary colormap

        Updates ternary colormap when swatch colors are changed in the Scatter and Heatmaps >
        Map from Ternary groupbox.  The ternary colored chemical map is updated.
        """
        if self.debug:
            print("ternary_colormap_changed")

        parent = self.parent
        for cmap in self.ternary_colormaps:
            if cmap['scheme'] == parent.comboBoxTernaryColormap.currentText():
                parent.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % cmap['top'])
                parent.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % cmap['left'])
                parent.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % cmap['right'])
                parent.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % cmap['center'])
    
    def button_color_select(self, button):
        """Select background color of button

        Parameters
        ----------
        button : QPushbutton, QToolbutton
            Button object that was clicked
        """
        if self.debug:
            print("button_color_select")

        old_color = button.palette().color(button.backgroundRole())
        color_dlg = QColorDialog(self.parent)
        color_dlg.setCurrentColor(old_color)
        color_dlg.setCustomColor(int(1),old_color)

        color = color_dlg.getColor()

        if color.isValid():
            button.setStyleSheet("background-color: %s;" % color.name())
            QColorDialog.setCustomColor(int(1),color)
            if button.accessibleName().startswith('Ternary'):
                button.setCurrentText('user defined')