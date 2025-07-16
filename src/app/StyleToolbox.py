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
from src.common.Observable import Observable
from src.common.Logger import auto_log_methods, log

class StyleObj():
    pass

@auto_log_methods(logger_key='Style')
class StyleData(Observable):
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
        X-axis scale function, ``linear``, ``log``, ``logit``, or ``symlog``
    ylim : list[float]
        Y-axis limits, [lower_bound, upper_bound]
    ylabel : str
        Y-axis label
    yscale : str
        Y-axis scale function, ``linear``, ``log``, ``logit``, or ``symlog``
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
        Color-axis scale function, ``linear``, ``log``, ``logit``, or ``symlog``
    resolution : int
        Resolution for heat maps
    map_plot_types : list
        A list of plots that result in a map, i.e., ['field map', 'ternary map', 'PCA score', 'cluster map', 'cluster score'].  This list is generally used as a check when setting certain styles or other plotting behavior related to maps.
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
        plot type.  While data related to plot and color axes may be stored in *style_dict*, *data.processed_data.column_attributes* stores labels, bounds and scale for most plot fields.

        style_dict[plot_type] -- plot types include ``field map``, ``histogram``, ``correlation``, ``gradient map``, ``scatter``, ``heatmap``, ``ternary map``
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
        'LineWidth' : (float) -- width of line objects, varies between plot types, set by ``doubleSpinBoxLineWidth``
        'LineColor' : (float) -- width of line objects, varies between plot types, set by ``doubleSpinBoxLineWidth``
        'Multiplier' : (hex str) -- color of markers, set by ``toolButtonLineColor``

        * associated with widgets in the toolBoxTreeView > Styling > Colors tab
        'CLabel' : (str) -- colorbar label, set in ``lineEditCLabel``
        'CLim' : (list of float) -- color bounds, set by ``lineEditXLB`` and ``lineEditXUB`` for the lower and upper bounds
        'CScale' : (str) -- c-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxYScale``
        'Colormap' : (str) -- colormap used in figure, set by ``comboBoxFieldColormap``
        'CbarReverse' : (bool) -- inverts colormap, set by ``checkBoxReverseColormap``
        'CbarDir' : (str) -- colorbar direction, options include ``none``, ``vertical``, and ``horizontal``, set by ``comboBoxCbarDirection``
        'Resolution' : (int) -- used to set discritization in 2D and ternary heatmaps, set by ``spinBoxHeatmapResolution``

        Parameters
        ----------
        parent : QMainWindow
            MainWindow with UI controls
        debug : bool, optional
            Prints debugging messages to stdout, by default ``False``

    """    
    def __init__(self,parent):
        super().__init__()

        self.logger_key = 'Style'


        self.ui = parent.ui
        self.app_data = parent.app_data
        # create the default style dictionary (self.style_dict for each plot type)
        self.style_dict = {}
        self.map_plot_types = [
            'field map',
            'ternary map',
            'PCA score',
            'cluster map',
            'cluster score'
        ]

        self.marker_dict = {
            'circle':'o',
            'square':'s',
            'diamond':'d',
            'triangle (up)':'^',
            'triangle (down)':'v',
            'hexagon':'h',
            'pentagon':'p'
        }

        # keep track of the plot type.
        self._plot_type = ''

        self._show_mass = False

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

        # create ternary colors dictionary
        df = pd.read_csv(os.path.join(BASEDIR,'resources/styles/ternary_colormaps.csv'))
        self.ternary_colormaps = df.to_dict(orient='records')


        self.color_schemes = []
        for cmap in self.ternary_colormaps:
            self.color_schemes.append(cmap['scheme'])

        self.axis = ['x','y','z','c']

        self.default_plot_axis_dict()


    # -------------------------------------
    # Styling properties
    # -------------------------------------
    @property
    def plot_type(self):
        return self._plot_type

    @plot_type.setter
    def plot_type(self, value):
        if value == self._plot_type:
            return
        self._plot_type = value
        self.notify_observers("plot_type", value)

    @property
    def xlim(self):
        return self.style_dict[self._plot_type]['XLim']

    @xlim.setter
    def xlim(self, value):
        if value == self.style_dict[self._plot_type]['XLim']:
            return
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['XLim'] = value
            self.notify_observers("xlim", value)
        else:
            raise ValueError("xlim must be a list of two floats or None.")

    @property
    def xlabel(self):
        return self.style_dict[self._plot_type]['XLabel']

    @xlabel.setter
    def xlabel(self, label):
        if label == self.style_dict[self._plot_type]['XLabel']:
            return
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['XLabel'] = label
            self.notify_observers("xlabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    @property
    def xscale(self):
        return self.style_dict[self._plot_type]['XScale']

    @xscale.setter
    def xscale(self, scale):
        if scale == self.style_dict[self._plot_type]['XScale']:
            return
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['XScale'] = scale
            self.notify_observers("xscale", scale)
        else:
            raise TypeError("scale must be linear, log, logit, or symlog.")

    @property
    def ylim(self):
        return self.style_dict[self._plot_type]['YLim']

    @ylim.setter
    def ylim(self, value):
        if value == self.style_dict[self._plot_type]['YLim']:
            return
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['YLim'] = value
            self.notify_observers("ylim", value)
        else:
            raise ValueError("ylim must be a list of two floats or None.")

    @property
    def ylabel(self):
        return self.style_dict[self._plot_type]['YLabel']

    @ylabel.setter
    def ylabel(self, label):
        if label == self.style_dict[self._plot_type]['YLabel']:
            return
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['YLabel'] = label
            self.notify_observers("ylabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    @property
    def yscale(self):
        return self.style_dict[self._plot_type]['YScale']

    @yscale.setter
    def yscale(self, scale):
        if scale == self.style_dict[self._plot_type]['YScale']:
            return
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['YScale'] = scale
            self.notify_observers("yscale", scale)
        else:
            raise TypeError("scale must be linear, log, logit, or symlog.")

    @property
    def zlim(self):
        return self.style_dict[self._plot_type]['ZLim']

    @zlim.setter
    def zlim(self, value):
        if value == self.style_dict[self._plot_type]['ZLim']:
            return
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['ZLim'] = value
            self.notify_observers("zlim", value)
        else:
            raise ValueError("zlim must be a list of two floats or None.")

    @property
    def zlabel(self):
        return self.style_dict[self._plot_type]['ZLabel']

    @zlabel.setter
    def zlabel(self, label):
        if label == self.style_dict[self._plot_type]['ZLabel']:
            return
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['ZLabel'] = label
            self.notify_observers("zlabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    @property
    def zscale(self):
        return self.style_dict[self._plot_type]['ZScale']

    @zscale.setter
    def zscale(self, scale):
        if scale == self.style_dict[self._plot_type]['ZScale']:
            return
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['ZScale'] = scale
            self.notify_observers("zscale", scale)
        else:
            raise TypeError("scale must be linear, log, logit,  or symlog.")

    @property
    def aspect_ratio(self):
        return self.style_dict[self._plot_type]['AspectRatio']

    @aspect_ratio.setter
    def aspect_ratio(self, value):
        if value == self.style_dict[self._plot_type]['AspectRatio']:
            return
        if value is None or isinstance(value, float):
            self.style_dict[self._plot_type]['AspectRatio'] = value
            self.notify_observers("aspect_ratio", value)
        else:
            raise TypeError("aspect_ratio must be of type float or None.")

    @property
    def tick_dir(self):
        return self.style_dict[self._plot_type]['TickDir']

    @tick_dir.setter
    def tick_dir(self, new_dir):
        if new_dir == self.style_dict[self._plot_type]['TickDir']:
            return
        if isinstance(new_dir, str):
            self.style_dict[self._plot_type]['TickDir'] = new_dir
            self.notify_observers("tick_dir", new_dir)
        else:
            raise TypeError("tickdir must be of type str.")

    @property
    def font(self):
        return self.style_dict[self._plot_type]['Font']

    @font.setter
    def font(self, font_family):
        if font_family == self.style_dict[self._plot_type]['Font']:
            return
        if isinstance(font_family, str):
            self.style_dict[self._plot_type]['Font'] = font_family
            self.notify_observers("font_family", font_family)
        else:
            raise TypeError("font_family must be of type str.")

    @property
    def font_size(self):
        return self.style_dict[self._plot_type]['FontSize']

    @font_size.setter
    def font_size(self, value):
        if value == self.style_dict[self._plot_type]['FontSize']:
            return
        if isinstance(value, float):
            self.style_dict[self._plot_type]['FontSize'] = value
            self.notify_observers("font_size", value)
        else:
            raise TypeError("font_size must be of type float.")

    @property
    def scale_dir(self):
        return self.style_dict[self._plot_type]['ScaleDir']

    @scale_dir.setter
    def scale_dir(self, new_dir):
        if new_dir == self.style_dict[self._plot_type]['ScaleDir']:
            return
        if (new_dir is not None) and isinstance(new_dir, str) and (new_dir in ['none', 'horizontal', 'vertical']):
            self.style_dict[self._plot_type]['ScaleDir'] = new_dir
            self.notify_observers("scale_dir", new_dir)
        else:
            raise TypeError("new_dir must be of type str.")

    @property
    def scale_location(self):
        return self.style_dict[self._plot_type]['ScaleLocation']

    @scale_location.setter
    def scale_location(self, location):
        if location == self.style_dict[self._plot_type]['ScaleLocation']:
            return
        if (location is not None) and isinstance(location, str) and (location in ['northeast', 'northwest', 'southwest', 'southeast']):
            self.style_dict[self._plot_type]['ScaleLocation'] = location
        else:
            raise TypeError("location must be of type str.")

    @property
    def scale_length(self):
        return self.style_dict[self._plot_type]['ScaleLength']

    @scale_length.setter
    def scale_length(self, length):
        if length == self.style_dict[self._plot_type]['ScaleLength']:
            return
        if length is None or isinstance(length, float):
            x_range = self.xlim[1] - self.xlim[0] if self.xlim else None
            y_range = self.ylim[1] - self.ylim[0] if self.ylim else None
            scale_dir = self.style_dict[self._plot_type]['ScaleDir']
            if (length is None) or ((length <= 0) or (scale_dir == 'horizontal' and x_range and length > x_range) or (scale_dir == 'vertical' and y_range and length > y_range)):
                length = self.default_scale_length()
            self.style_dict[self._plot_type]['ScaleLength'] = length
        else:
            raise TypeError("length must be of type float.")

    @property
    def overlay_color(self):
        return self.style_dict[self._plot_type]['OverlayColor']

    @overlay_color.setter
    def overlay_color(self, hexstr):
        if hexstr == self.style_dict[self._plot_type]['OverlayColor']:
            return
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['OverlayColor'] = hexstr
        else:
            raise TypeError("color must be a hex string, #rrggbb")

    @property
    def show_mass(self):
        return self._show_mass

    @show_mass.setter
    def show_mass(self, flag):
        if flag == self._show_mass:
            return
        self._show_mass = flag
        self.notify_observers("show_mass", flag)

    @property
    def marker(self):
        return self.style_dict[self._plot_type]['Marker']

    @marker.setter
    def marker(self, symbol):
        if symbol == self.style_dict[self._plot_type]['Marker']:
            return
        if isinstance(symbol, float):
            self.style_dict[self._plot_type]['Marker'] = symbol
        else:
            raise TypeError("marker_symbol must be of type float.")

    @property
    def marker_size(self):
        return self.style_dict[self._plot_type]['MarkerSize']

    @marker_size.setter
    def marker_size(self, size):
        if size == self.style_dict[self._plot_type]['MarkerSize']:
            return
        if isinstance(size, float):
            self.style_dict[self._plot_type]['MarkerSize'] = size
        else:
            raise TypeError("size must be of type float.")

    @property
    def marker_color(self):
        return self.style_dict[self._plot_type]['MarkerColor']

    @marker_color.setter
    def marker_color(self, hexstr):
        if hexstr == self.style_dict[self._plot_type]['MarkerColor']:
            return
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['MarkerColor'] = hexstr
        else:
            raise TypeError("hexstr must be a hex string, #rrggbb")

    @property
    def marker_alpha(self):
        return self.style_dict[self._plot_type]['MarkerAlpha']

    @marker_alpha.setter
    def marker_alpha(self, alpha):
        if alpha == self.style_dict[self._plot_type]['MarkerAlpha']:
            return
        if isinstance(alpha, float) and 0 <= alpha <= 1:
            self.style_dict[self._plot_type]['MarkerAlpha'] = alpha
        else:
            raise TypeError("alpha must be of type float and [0,1].")

    @property
    def line_width(self):
        return self.style_dict[self._plot_type]['LineWidth']

    @line_width.setter
    def line_width(self, width):
        if width == self.style_dict[self._plot_type]['LineWidth']:
            return
        if isinstance(width, float):
            self.style_dict[self._plot_type]['LineWidth'] = width
        else:
            raise TypeError("width must be of type float.")

    @property
    def line_multiplier(self):
        return self.style_dict[self._plot_type]['LineMultiplier']

    @line_multiplier.setter
    def line_multiplier(self, value):
        if value == self.style_dict[self._plot_type]['LineMultiplier']:
            return
        if value is None or isinstance(value, float):
            self.style_dict[self._plot_type]['LineMultiplier'] = value
        else:
            raise TypeError("value must be of type float or None.")

    @property
    def line_color(self):
        return self.style_dict[self._plot_type]['LineColor']

    @line_color.setter
    def line_color(self, hexstr):
        if hexstr == self.style_dict[self._plot_type]['LineColor']:
            return
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['LineColor'] = hexstr
        else:
            raise TypeError("hexstr must be a hex string, #rrggbb")

    @property
    def cmap(self):
        return self.style_dict[self._plot_type]['Colormap']

    @cmap.setter
    def cmap(self, name):
        if name == self.style_dict[self._plot_type]['Colormap']:
            return
        if (name is None) or isinstance(name, str):
            self.style_dict[self._plot_type]['Colormap'] = name
        else:
            raise TypeError("name must be of type str or None.")

    @property
    def cbar_reverse(self):
        return self.style_dict[self._plot_type]['CbarReverse']

    @cbar_reverse.setter
    def cbar_reverse(self, flag):
        if flag == self.style_dict[self._plot_type]['CbarReverse']:
            return
        if (flag is None) or isinstance(flag, str):
            self.style_dict[self._plot_type]['CbarReverse'] = flag
        else:
            raise TypeError("flag must be of type str or None.")

    @property
    def cbar_dir(self):
        return self.style_dict[self._plot_type]['CbarDir']

    @cbar_dir.setter
    def cbar_dir(self, new_dir):
        if new_dir == self.style_dict[self._plot_type]['CbarDir']:
            return
        if (new_dir is not None) and isinstance(new_dir, str) and (new_dir in ['none', 'horizontal', 'vertical']):
            self.style_dict[self._plot_type]['CbarDir'] = new_dir
        else:
            raise TypeError("new_dir must be of type str.")

    @property
    def clim(self):
        return self.style_dict[self._plot_type]['CLim']

    @clim.setter
    def clim(self, value):
        if value == self.style_dict[self._plot_type]['CLim']:
            return
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['CLim'] = value
            self.notify_observers("clim", value)
        else:
            raise ValueError("clim must be a list of two floats or None.")

    @property
    def clabel(self):
        return self.style_dict[self._plot_type]['CLabel']

    @clabel.setter
    def clabel(self, label):
        if label == self.style_dict[self._plot_type]['CLabel']:
            return
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['CLabel'] = label
            self.notify_observers("clabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    @property
    def cscale(self):
        return self.style_dict[self._plot_type]['CScale']

    @cscale.setter
    def cscale(self, scale):
        if scale == self.style_dict[self._plot_type]['CScale']:
            return
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['CScale'] = scale
            self.notify_observers("cscale", scale)
        else:
            raise TypeError("scale must be linear, log, logit, or symlog.")

    @property
    def resolution(self):
        return self.style_dict[self._plot_type]['Resolution']

    @resolution.setter
    def resolution(self, value):
        if value == self.style_dict[self._plot_type]['Resolution']:
            return
        if value is None or isinstance(value, int):
            self.style_dict[self._plot_type]['Resolution'] = value
        else:
            raise TypeError("value must be an integer or None.")

    def get_axis_label(self, ax):
        return getattr(self, f"{self.axis[ax]}label")

    def set_axis_label(self, ax, new_label):
        setattr(self, f"{self.axis[ax]}label", new_label)

    def get_axis_lim(self, ax):
        return getattr(self, f"{self.axis[ax]}lim")

    def set_axis_lim(self, ax, new_lim):
        setattr(self, f"{self.axis[ax]}lim", new_lim)

    def get_axis_scale(self, ax):
        return getattr(self, f"{self.axis[ax]}scale")

    def set_axis_scale(self, ax, new_scale):
        setattr(self, f"{self.axis[ax]}scale", new_scale)

    def default_scale_length(self):
        """Sets default length of a scale bar for map-type plots

        Returns
        -------
        float
            Length of scalebar dependent on direction of scalebar.
        """        
        if (self._plot_type not in self.map_plot_types) or (self.scale_dir == 'none'):
            return None

        x_range = self.xlim[1] - self.xlim[0]
        y_range = self.ylim[1] - self.ylim[0]

        if self.scale_dir == 'vertical':
            length = 10**np.floor(np.log10(y_range))
            if length > x_range:
                length = 0.2 * y_range
        else: # scale_dir == horizontal
            length = 10**np.floor(np.log10(x_range))
            if length > x_range:
                length = 0.2 * x_range

        return length

    def default_plot_axis_dict(self):
        self.plot_axis_dict = {
            '': {
                'axis': [False, False, False, False],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, False],
                'field_type': [''],
                },
            'field map': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, True],
                },
            'gradient map': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, True],
                'field_type': ['Analyte','Ratio','Calculated','Special']
                },
            'correlation': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, True],
                'spinbox': [False, False, False, True],
                'cfield_type': ['Cluster']
                },
            'histogram': {
                'axis': [True, False, False, True],
                'add_none': [False, False, False, True],
                'spinbox': [True, False, False, True],
                'cfield_type': ['Cluster']
                },
            'scatter': {
                'axis': [True, True, True, True],
                'add_none': [False, False, True, True],
                'spinbox': [False, False, False, True],
                'field_type': ['Analyte','Ratio','Calculated','PCA score','Cluster score','Special']
                },
            'heatmap': {
                'axis': [True, True, True, False],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, False],
                'field_type': ['Analyte','Ratio','Calculated','PCA score','Cluster score','Special']
                },
            'ternary map': {
                'axis': [True, True, True, False],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, False],
                'field_type': ['Analyte','Ratio','Calculated','PCA score','Special']
                },
            'TEC': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, True],
                'spinbox': [False, False, False, False],
                'field_type': ['Analyte'],
                'cfield_type': ['Cluster']
                },
            'radar': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, True],
                'spinbox': [False, False, False, False],
                'field_type': ['Analyte','Ratio','Calculated','PCA score','Special']
                },
            'variance': {
                'axis': [False, False, False, False],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, False]
                },
            'basis vectors': {
                'axis': [False, False, False, False],
                'add_none': [False, False, False, False],
                'spinbox': [True, True, False, False]
                },
            'dimension score map': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, True],
                'field_type': ['PCA score']
                },
            'dimension scatter': {
                'axis': [True, True, False, True],
                'add_none': [False, False, False, True],
                'spinbox': [True, True, False, True],
                'field_type': ['PCA score']
                }, 
            'dimension heatmap': {
                'axis': [True, True, False, False],
                'add_none': [False, False, False, False],
                'spinbox': [True, True, False, False],
                'field_type': ['PCA score']
                },
            'cluster map': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, False],
                'field_type': ['Cluster']
                },
            'cluster score map': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, True],
                'field_type': ['Cluster score']
                },
            'cluster performance': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, False],
                'field_type': ['Cluster']
                },
            'profile': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, True],
                'field_type': ['Analyte','Ratio','Calculated','PCA score','Cluster','Cluster score','Special']
                },
            'polygon': {
                'axis': [False, False, False, True],
                'add_none': [False, False, False, False],
                'spinbox': [False, False, False, True],
                'field_type': ['Analyte','Ratio','Calculated','PCA score','Cluster','Cluster score','Special']
                }
        }
    
    def set_style_dictionary(self,data, app_data, plot_type=None, style=None):
        """Sets values in style dictionary

        Parameters
        ----------
        plot_type : str, optional
            Dictionary key into ``MainWindow.styles``, Defaults to ``None``
        style : dict, optional
            Style dictionary for the current plot type. Defaults to ``None``
        """
        if not plot_type:
            plot_type = self._plot_type
        
        style = self.style_dict[plot_type]
                
        if plot_type.lower() in self.map_plot_types:
            if ('Xc' not in list(data.column_attrributes)) or ('Yc' not in list(data.column_attrributes)):
                return

            
            xmin,xmax,xscale,_ = self.get_axis_values(data,'Analyte','Xc')
            ymin,ymax,yscale,_ = self.get_axis_values(data,'Analyte','Yc')

            # set style dictionary values for X and Y
            style['XLim'] = [xmin, xmax]
            style['XScale'] = xscale
            style['XLabel'] = 'X'
            style['YLim'] = [ymin, ymax]
            style['YScale'] = yscale
            style['YLabel'] = 'Y'
            style['AspectRatio'] = data.aspect_ratio

        if (style['ScaleLength'] is None) and (plot_type in self.map_plot_types):
            style['ScaleLength'] = self.default_scale_length()

        if app_data.c_field in list(data.column_attrributes):
            field = app_data.c_field
            style['CLim'] = [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')]
            style['CLabel'] = data.processed_data.get_attribute(field,'label')

        if app_data.c_field_type == 'cluster':
            style['CScale'] = 'discrete'
        else:
            style['CScale'] = 'linear'

    def get_axis_values(self, data, field_type, field, ax=None):
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

        # get axis values from processed data
        amin = data.processed_data.get_attribute(field,'plot_min')
        amax = data.processed_data.get_attribute(field,'plot_max')
        scale = data.processed_data.get_attribute(field,'norm')
        label = data.processed_data.get_attribute(field,'label')

        # if probability axis associated with histogram
        if ax == 'p':
            pmin = data.processed_data.get_attribute(field,'p_min')
            pmax = data.processed_data.get_attribute(field,'p_max')
            return amin, amax, scale, label, pmin, pmax

        return amin, amax, scale, label
    
    # color functions 
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
        norm = None
        match self.cscale:
            case 'linear':
                norm = colors.Normalize(vmin=self.clim[0], vmax=self.clim[1])
            case 'log':
                norm = colors.LogNorm(vmin=self.clim[0], vmax=self.clim[1])
            case 'syslog':
                norm = colors.SymLogNorm(linthresh=1.0, vmin=self.clim[0], vmax=self.clim[1])
            case 'discrete':
                if N is None:
                    if hasattr(self,'ui'):
                        QMessageBox(self.ui, "Warning","N must not be None when color scale is discrete.")
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
        if hasattr(self,'ui') and hasattr(self,'ui'):
            if self.ui.canvasWindow.currentIndex() == self.ui.canvas_tab['qv']:
                plot_type = 'field map'


        if self.cmap in self.mpl_colormaps:
            if N is not None:
                cmap = plt.get_cmap(self.cmap, N)
            else:
                cmap = plt.get_cmap(self.cmap)
        else:
            cmap = self.create_custom_colormap(self.cmap, N)

        if self.cbar_reverse:
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
        if N is None:
            N = 256

        color_list = get_rgb_color(self.custom_color_dict[name])
        cmap = colors.LinearSegmentedColormap.from_list(name, color_list, N=N)

        return cmap

    # -------------------------------------
    # Validation functions
    # -------------------------------------
    def _is_valid_bounds(self, value):
        """Validates if a the variable has properties consistent with bounds."""
        return (value is None or value == [None, None]) or (isinstance(value, list) and len(value) == 2 and value[1] >= value[0])

    def _is_valid_scale(self, text):
        """Validates if a the variable is a valid string."""
        return isinstance(text, str) and text in self.ui.data[self.app_data.sample_id].scale_options
    
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
            log(f"{attr}: {value}", prefix="DEBUG")


class StyleTheme():
    def __init__(self, parent=None):

        self.logger_key = 'Style'
        self.ui = parent.ui

    # Themes
    # -------------------------------------
    def load_theme_names(self):
        """Loads theme names and adds them to the theme comboBox
        
        Looks for saved style themes (*.sty) in ``resources/styles/`` directory and adds them to

        Returns
        -------
        list :
            List of style themes
        """
        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/styles/'))
        style_list = [file.replace('.sty','') for file in file_list if file.endswith('.sty')]

        # add default to list
        style_list.insert(0,'default')

        return style_list

    def read_theme(self, name):
        """Reads a style theme
        
        Parameters
        ----------
        name : str
            Name of a style theme.
        
        Returns
        -------
        dict :
            Style dictionary for all plot types.
        """
        if name == 'default':
            return self.default_style_dict()

        try:
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'rb') as file:
                style_dict = pickle.load(file)
        except:
            QMessageBox.warning(self.ui,'Error','Could not load style theme.')

        return style_dict


    def input_theme_name_dlg(self, style_dict):
        """Opens a dialog to save style theme
        
        Style themes are saved as a dictionary into the theme name with a ``.sty`` extension
        and the name is returned, so it can be added to a list of style themes.

        Parameters
        ----------
        style_dict : dict
            Style settings for each plot type
        
        Returns
        -------
        str :
            Name of style theme.
        """
        name, ok = QInputDialog.getText(None, 'Save custom theme', 'Enter theme name:')
        if ok:
            # append theme to file of saved themes
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'wb') as file:
                pickle.dump(style_dict, file, protocol=pickle.HIGHEST_PROTOCOL)

            return name
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.ui,'Error','Could not save theme.')

            return None

    def default_style_dict(self):
        """
        Generates a dictionary of default plot styles for various plot types.

        This method resets the internal `default_plot_style` to a base set of defaults,
        applies preferred font detection from system fonts, and then clones and customizes
        this style for multiple predefined plot types (e.g., field map, scatter, histogram).

        The resulting dictionary contains one style dictionary per plot type.

        Returns
        -------
        dict
            A dictionary mapping plot type names to their corresponding style dictionaries.

        Notes
        -----
        The base style template (`default_plot_style`) contains the following keys and default values:

        +------------------+------------------+--------------------------------------------------+
        | Key              | Default Value    | Description                                      |
        +==================+==================+==================================================+
        | XFieldType       | 'none'           | Type of field for x-axis (e.g., 'Analyte')       |
        | XField           | 'none'           | Name of x-axis field                             |
        | XLim             | [0, 1]           | Limits for x-axis                                |
        | XScale           | 'linear'         | Scale for x-axis ('linear' or 'log')             |
        | XLabel           | ''               | Label for x-axis                                 |
        | YFieldType       | 'none'           | Type of field for y-axis                         |
        | YField           | 'none'           | Name of y-axis field                             |
        | YLim             | [0, 1]           | Limits for y-axis                                |
        | YScale           | 'linear'         | Scale for y-axis                                 |
        | YLabel           | ''               | Label for y-axis                                 |
        | ZFieldType       | 'none'           | Type of field for z-axis                         |
        | ZField           | 'none'           | Name of z-axis field                             |
        | ZLim             | [0, 1]           | Limits for z-axis                                |
        | ZScale           | 'linear'         | Scale for z-axis                                 |
        | ZLabel           | ''               | Label for z-axis                                 |
        | CFieldType       | 'none'           | Type of color-mapped data                        |
        | CField           | 'none'           | Field name for color-mapping                     |
        | CLim             | [0, 1]           | Colorbar limits                                  |
        | CScale           | 'linear'         | Colorbar scale                                   |
        | CLabel           | ''               | Label for colorbar                               |
        | AspectRatio      | 1.0              | Aspect ratio of the plot                         |
        | TickDir          | 'out'            | Tick direction                                   |
        | Font             | ''               | Preferred font (auto-selected from system)       |
        | FontSize         | 11.0             | Font size in points                              |
        | ScaleDir         | 'none'           | Scale bar direction                              |
        | ScaleLocation    | 'northeast'      | Position of scale bar                            |
        | ScaleLength      | None             | Length of the scale bar                          |
        | OverlayColor     | '#ffffff'        | Overlay color (e.g., for text/annotation)        |
        | Marker           | 'circle'         | Marker shape                                     |
        | MarkerSize       | 6                | Marker size in points                            |
        | MarkerColor      | '#1c75bc'        | Marker color                                     |
        | MarkerAlpha      | 30               | Marker transparency (0–100)                      |
        | LineWidth        | 1.5              | Width of lines in the plot                       |
        | LineMultiplier   | 1                | Multiplier for line width                        |
        | LineColor        | '#1c75bc'        | Line color                                       |
        | Colormap         | 'viridis'        | Name of the colormap                             |
        | CbarReverse      | False            | Whether to reverse the colormap                  |
        | CbarDir          | 'vertical'       | Direction of colorbar                            |
        | Resolution       | 10               | Grid resolution                                  |
        +------------------+------------------+--------------------------------------------------+

        Specific plot types (e.g., 'field map', 'scatter', 'correlation') override some of
        these values, such as setting `Colormap`, axis fields, aspect ratio, etc.
        """
        styles = {}

        self.default_plot_style = {
                'XFieldType': 'none',
                'XField': 'none',
                'XLim': [0,1],
                'XScale': 'linear',
                'XLabel': '',
                'YFieldType': 'none',
                'YField': 'none',
                'YLim': [0,1],
                'YScale': 'linear',
                'YLabel': '',
                'ZFieldType': 'none',
                'ZField': 'none',
                'ZLim': [0,1],
                'ZLabel': '',
                'ZScale': 'linear',
                'CFieldType': 'none',
                'CField': 'none',
                'CLim': [0,1],
                'CScale': 'linear',
                'CLabel': '',
                'AspectRatio': 1.0,
                'TickDir': 'out',
                'Font': '',
                'FontSize': 11.0,
                'ScaleDir': 'none',
                'ScaleLocation': 'northeast',
                'ScaleLength': None,
                'OverlayColor': '#ffffff',
                'Marker': 'circle',
                'MarkerSize': 6,
                'MarkerColor': '#1c75bc',
                'MarkerAlpha': 30,
                'LineWidth': 1.5,
                'LineMultiplier': 1,
                'LineColor': '#1c75bc',
                'Colormap': 'viridis',
                'CbarReverse': False,
                'CbarDir': 'vertical',
                'Resolution': 10
                }

        # try to load one of the preferred fonts
        default_font = ['Avenir','Candara','Myriad Pro','Myriad','Aptos','Calibri','Helvetica','Arial','Verdana']
        names = QFontDatabase.families()

        for font in default_font:
            if font in names:
                self.default_plot_style['Font'] = QFont(font, 11).family()
                break


        styles = {'field map': copy.deepcopy(self.default_plot_style),
                'correlation': copy.deepcopy(self.default_plot_style),
                'histogram': copy.deepcopy(self.default_plot_style),
                'gradient map': copy.deepcopy(self.default_plot_style),
                'scatter': copy.deepcopy(self.default_plot_style),
                'heatmap': copy.deepcopy(self.default_plot_style),
                'ternary map': copy.deepcopy(self.default_plot_style),
                'TEC': copy.deepcopy(self.default_plot_style),
                'radar': copy.deepcopy(self.default_plot_style),
                'variance': copy.deepcopy(self.default_plot_style),
                'basis vectors': copy.deepcopy(self.default_plot_style),
                'dimension scatter': copy.deepcopy(self.default_plot_style),
                'dimension heatmap': copy.deepcopy(self.default_plot_style),
                'dimension score map': copy.deepcopy(self.default_plot_style),
                'cluster map': copy.deepcopy(self.default_plot_style),
                'cluster score map': copy.deepcopy(self.default_plot_style),
                'cluster performance': copy.deepcopy(self.default_plot_style),
                'profile': copy.deepcopy(self.default_plot_style),
                'polygon': copy.deepcopy(self.default_plot_style)
                }

        styles['field map']['Colormap'] = 'plasma'
        styles['field map']['XField'] = 'Xc'
        styles['field map']['YField'] = 'Yc'

        styles['correlation']['AspectRatio'] = 1.0
        styles['correlation']['FontSize'] = 8
        styles['correlation']['Colormap'] = 'RdBu'
        styles['correlation']['CbarDir'] = 'vertical'
        styles['correlation']['CLim'] = [-1,1]

        styles['basis vectors']['AspectRatio'] = 1.0
        styles['basis vectors']['Colormap'] = 'RdBu'

        styles['gradient map']['Colormap'] = 'RdYlBu'
        styles['gradient map']['XField'] = 'Xc'
        styles['gradient map']['YField'] = 'Yc'

        styles['cluster score map']['Colormap'] = 'plasma'
        styles['cluster score map']['XField'] = 'Xc'
        styles['cluster score map']['YField'] = 'Yc'

        styles['dimension score map']['Colormap'] = 'viridis'
        styles['dimension score map']['XField'] = 'Xc'
        styles['dimension score map']['YField'] = 'Yc'

        styles['cluster map']['CScale'] = 'discrete'
        styles['cluster map']['MarkerAlpha'] = 100
        styles['cluster map']['FieldType'] = 'Cluster'

        styles['cluster performance']['AspectRatio'] = 0.62

        styles['scatter']['AspectRatio'] = 1
        styles['scatter']['XFieldType'] = 'Analyte'
        styles['scatter']['YFieldType'] = 'Analyte'
        styles['scatter']['ZFieldType'] = 'none'
        styles['scatter']['CFieldType'] = 'none'

        styles['heatmap']['AspectRatio'] = 1
        styles['heatmap']['CLim'] = [1,1000]
        styles['heatmap']['CScale'] = 'log'
        styles['heatmap']['XFieldType'] = 'Analyte'
        styles['heatmap']['YFieldType'] = 'Analyte'

        styles['TEC']['AspectRatio'] = 0.62
        styles['variance']['AspectRatio'] = 0.62
        styles['basis vectors']['CLim'] = [-1,1]

        styles['dimension scatter']['LineColor'] = '#4d4d4d'
        styles['dimension scatter']['LineWidth'] = 0.5
        styles['dimension scatter']['AspectRatio'] = 1
        styles['dimension scatter']['XFieldType'] = 'PCA score'
        styles['dimension scatter']['YFieldType'] = 'PCA score'

        styles['dimension heatmap']['AspectRatio'] = 1
        styles['dimension heatmap']['LineColor'] = '#ffffff'
        styles['dimension scatter']['XFieldType'] = 'PCA score'
        styles['dimension scatter']['YFieldType'] = 'PCA score'

        styles['variance']['FontSize'] = 8

        styles['histogram']['AspectRatio'] = 0.62
        styles['histogram']['LineWidth'] = 0
        styles['histogram']['XFieldType'] = 'Analyte'
        styles['histogram']['CFieldType'] = 'none'

        styles['profile']['AspectRatio'] = 0.62
        styles['profile']['LineWidth'] = 1.0
        styles['profile']['MarkerSize'] = 12
        styles['profile']['MarkerColor'] = '#d3d3d3'
        styles['profile']['LineColor'] = '#d3d3d3'

        return styles