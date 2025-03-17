import os, re, copy, pickle, inspect
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
from src.common.ScheduleTimer import Scheduler
from src.common.Logger import LogCounter

class StyleObj():
    pass

class Styling(Observable):
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
        A list of plots that result in a map, i.e., ['field map', 'ternary map', 'PCA score', 'cluster', 'cluster score'].  This list is generally used as a check when setting certain styles or other plotting behavior related to maps.
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
        'CLabel' : (str) -- colorbar label, set in ``lineEditCbarLabel``
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
    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug
        self.logger = LogCounter()
        
        # create the default style dictionary (self.style_dict for each plot type)
        self.style_dict = {}
        self.map_plot_types = ['field map', 'ternary map', 'PCA score', 'cluster', 'cluster score']

        self.marker_dict = {'circle':'o', 'square':'s', 'diamond':'d', 'triangle (up)':'^', 'triangle (down)':'v', 'hexagon':'h', 'pentagon':'p'}

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


    # -------------------------------------
    # Styling properties
    # -------------------------------------
    @property
    def plot_type(self):
        """str : Plot type used to determine plot method and associated style settings."""
        return self._plot_type

    @plot_type.setter
    def plot_type(self, plot_type):
        if self.debug:
            self.logger.print(f"@plot_type:\n  old value: {self._plot_type}\n  new value: {plot_type}")
        if plot_type == self._plot_type:
            return
        self._plot_type = plot_type

        self.notify_observers("plot_type", plot_type)

    # xlim
    @property
    def xlim(self):
        return self.style_dict[self._plot_type]['XLim']

    @xlim.setter
    def xlim(self, value):
        if self.debug:
            self.logger.print(f"@xlim:\n  old value: {self.style_dict[self._plot_type]['XLim']}\n  new value: {value}")
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['XLim'] = value
            self.notify_observers("xlim", value)
        else:
            raise ValueError("xlim must be a list of two floats or None.")

    # xlabel
    @property
    def xlabel(self):
        return self.style_dict[self._plot_type]['XLabel']

    @xlabel.setter
    def xlabel(self, label):
        if self.debug:
            self.logger.print(f"@xlabel:\n  old value: {self.style_dict[self._plot_type]['XLabel']}\n  new value: {label}")
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['XLabel'] = label
            self.notify_observers("xlabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    # xscale
    @property
    def xscale(self):
        return self.style_dict[self._plot_type]['XScale']

    @xscale.setter
    def xscale(self, scale):
        if self.debug:
            self.logger.print(f"@xscale:\n  old value: {self.style_dict[self._plot_type]['XScale']}\n  new value: {scale}")
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['XScale'] = scale
            self.notify_observers("xscale", scale)
        else:
            raise TypeError("scale must be linear, log or logit.")

    # ylim
    @property
    def ylim(self):
        return self.style_dict[self._plot_type]['YLim']

    @ylim.setter
    def ylim(self, value):
        if self.debug:
            self.logger.print(f"@ylim:\n  old value: {self.style_dict[self._plot_type]['YLim']}\n  new value: {value}")
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['YLim'] = value
            self.notify_observers("ylim", value)
        else:
            raise ValueError("ylim must be a list of two floats or None.")

    # ylabel
    @property
    def ylabel(self):
        return self.style_dict[self._plot_type]['YLabel']

    @ylabel.setter
    def ylabel(self, label):
        if self.debug:
            self.logger.print(f"@ylabel:\n  old value: {self.style_dict[self._plot_type]['YLabel']}\n  new value: {label}")
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['YLabel'] = label
            self.notify_observers("ylabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    # yscale
    @property
    def yscale(self):
        return self.style_dict[self._plot_type]['YScale']

    @yscale.setter
    def yscale(self, scale):
        if self.debug:
            self.logger.print(f"@yscale:\n  old value: {self.style_dict[self._plot_type]['YScale']}\n  new value: {scale}")
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['YScale'] = scale
            self.notify_observers("yscale", scale)
        else:
            raise TypeError("scale must be linear, log or logit.")

    # zlim
    @property
    def zlim(self):
        return self.style_dict[self._plot_type]['ZLim']

    @zlim.setter
    def zlim(self, value):
        if self.debug:
            self.logger.print(f"@zlim:\n  old value: {self.style_dict[self._plot_type]['ZLim']}\n  new value: {value}")
        if value is None or self._is_valid_bounds(value):
            self.style_dict[self._plot_type]['ZLim'] = value
            self.notify_observers("zscale", value)
        else:
            raise ValueError("zlim must be a list of two floats or None.")

    # zlabel
    @property
    def zlabel(self):
        return self.style_dict[self._plot_type]['ZLabel']

    @zlabel.setter
    def zlabel(self, label):
        if self.debug:
            self.logger.print(f"@zlabel:\n  old value: {self.style_dict[self._plot_type]['ZLabel']}\n  new value: {label}")
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['ZLabel'] = label
            self.notify_observers("zlabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    # zscale
    @property
    def zscale(self):
        return self.style_dict[self._plot_type]['ZScale']

    @zscale.setter
    def zscale(self, scale):
        if self.debug:
            self.logger.print(f"@zscale:\n  old value: {self.style_dict[self._plot_type]['ZScale']}\n  new value: {scale}")
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['ZScale'] = scale
            self.notify_observers("zscale", scale)
        else:
            raise TypeError("scale must be linear, log or logit.")

    # aspect_ratio
    @property
    def aspect_ratio(self):
        return self.style_dict[self._plot_type]['AspectRatio']
    
    @aspect_ratio.setter
    def aspect_ratio(self, value):
        if self.debug:
            self.logger.print(f"@aspect_ratio:\n  old value: {self.style_dict[self._plot_type]['AspectRatio']}\n  new value: {value}")
        if value is None or isinstance(value, float):
            self.style_dict[self._plot_type]['AspectRatio'] = value
            self.notify_observers("aspect_ratio", value)

    # tick_dir 
    @property
    def tick_dir(self):
        return self.style_dict[self._plot_type]['TickDir']

    @tick_dir.setter
    def tick_dir(self, new_dir):
        if self.debug:
            self.logger.print(f"@tick_dir:\n  old value: {self.style_dict[self._plot_type]['TickDir']}\n  new value: {new_dir}")
        if isinstance(new_dir, str):
            self.style_dict[self._plot_type]['TickDir'] = new_dir
            self.notify_observers("tick_dir", new_dir)
        else:
            raise TypeError("tickdir must be of type str.")

    # font
    @property
    def font(self):
        return self.style_dict[self._plot_type]['Font']

    @font.setter
    def font(self, font_family):
        if self.debug:
            self.logger.print(f"@font:\n  old value: {self.style_dict[self._plot_type]['Font']}\n  new value: {font_family}")
        if isinstance(font_family, str):
            self.style_dict[self._plot_type]['Font'] = font_family
            self.notify_observers("font_family", font_family)
        else:
            raise TypeError("font_family must be of type str.")

    # font_size
    @property
    def font_size(self):
        return self.style_dict[self._plot_type]['FontSize']

    @font_size.setter
    def font_size(self, value):
        if self.debug:
            self.logger.print(f"@font_size:\n  old value: {self.style_dict[self._plot_type]['FontSize']}\n  new value: {value}")
        if isinstance(value, float):
            self.style_dict[self._plot_type]['FontSize'] = value
            self.notify_observers("font_size", value)
        else:
            raise TypeError("font_size must be of type float.")

    # scale_dir
    @property
    def scale_dir(self):
        return self.style_dict[self._plot_type]['ScaleDir']

    @scale_dir.setter
    def scale_dir(self, new_dir):
        if self.debug:
            self.logger.print(f"@scale_dir:\n  old value: {self.style_dict[self._plot_type]['ScaleDir']}\n  new value: {new_dir}")
        if (new_dir is not None) and isinstance(new_dir, str) and (new_dir in ['none', 'horizontal', 'vertical']):
            if new_dir != self.style_dict[self._plot_type]['ScaleDir']:
                self.style_dict[self._plot_type]['ScaleDir'] = new_dir
                self.notify_observers("scale_dir", new_dir)
        else:
            raise TypeError("new_dir must be of type str.")

    # scale_location
    @property
    def scale_location(self):
        return self.style_dict[self._plot_type]['ScaleLocation']

    @scale_location.setter
    def scale_location(self, location):
        if self.debug:
            self.logger.print(f"@scale_location:\n  old value: {self.style_dict[self._plot_type]['ScaleLocation']}\n  new value: {location}")
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
        if self.debug:
            self.logger.print(f"@scale_length:\n  old value: {self.style_dict[self._plot_type]['ScaleLength']}\n  new value: {length}")
        if length is None or isinstance(length, float):
            # check constraints on length
            x_range = self.xlim[1] - self.xlim[0]
            y_range = self.ylim[1] - self.ylim[0]
            scale_dir = self.style_dict[self._plot_type]['ScaleDir']
            if (length is None) or ((length <= 0) or (scale_dir == 'horizontal' and length > x_range) or (scale_dir == 'vertical' and length > y_range)):
                length = self.default_scale_length()

            # set scale_length and associated widget
            if length != self.style_dict[self._plot_type]['ScaleLength']:
                self.style_dict[self._plot_type]['ScaleLength'] = length
        else:
            raise TypeError("length must be of type float.")

    # overlay_color
    @property
    def overlay_color(self):
        return self.style_dict[self._plot_type]['OverlayColor']

    @overlay_color.setter
    def overlay_color(self, hexstr):
        if self.debug:
            self.logger.print(f"@overlay_color:\n  old value: {self.style_dict[self._plot_type]['OverlayColor']}\n  new value: {hexstr}")
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['OverlayColor'] = hexstr
        else:
            raise TypeError("color must be a hex string, #rrggbb")

    @property
    def show_mass(self):
        return self._show_mass
    
    @show_mass.setter
    def show_mass(self, flag):
        if self.debug:
            self.logger.print(f"@show_mass:\n  old state: {self._show_mass}\n  new state: {flag}")
        if flag == self._show_mass:
            return
    
        self._show_mass = flag
        self.notify_observers("show_mass", flag)

    # marker
    @property
    def marker(self):
        return self.style_dict[self._plot_type]['Marker']

    @marker.setter
    def marker(self, symbol):
        if self.debug:
            self.logger.print(f"@marker:\n  old value: {self.style_dict[self._plot_type]['Marker']}\n  new value: {symbol}")
        if isinstance(symbol, float):
            self.style_dict[self._plot_type]['Marker'] = symbol
        else:
            raise TypeError("marker_symbol must be of type float.")

    # marker_size
    @property
    def marker_size(self):
        return self.style_dict[self._plot_type]['MarkerSize']

    @marker_size.setter
    def marker_size(self, size):
        if self.debug:
            self.logger.print(f"@marker_size:\n  old value: {self.style_dict[self._plot_type]['MarkerSize']}\n  new value: {size}")
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
        if self.debug:
            self.logger.print(f"@marker_color:\n  old value: {self.style_dict[self._plot_type]['MarkerColor']}\n  new value: {hexstr}")
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
        if self.debug:
            self.logger.print(f"@marker_alpha:\n  old value: {self.style_dict[self._plot_type]['MarkerAlpha']}\n  new value: {alpha}")
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
        if self.debug:
            self.logger.print(f"@line_width:\n  old value: {self.style_dict[self._plot_type]['LineWidth']}\n  new value: {width}")
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
        if self.debug:
            self.logger.print(f"@line_multiplier:\n  old value: {self.style_dict[self._plot_type]['LineMultiplier']}\n  new value: {value}")
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
        if self.debug:
            self.logger.print(f"@line_color:\n  old value: {self.style_dict[self._plot_type]['LineColor']}\n  new value: {hexstr}")
        if hexstr is None or self._is_valid_hex_color(hexstr):
            self.style_dict[self._plot_type]['LineColor'] = hexstr
        else:
            raise TypeError("hexstr must be a hex string, #rrggbb")

    # cmap - colormap
    @property
    def cmap(self):
        return self.style_dict[self._plot_type]['Colormap']

    @cmap.setter
    def cmap(self, name):
        if self.debug:
            self.logger.print(f"@cmap:\n  old value: {self.style_dict[self._plot_type]['Colormap']}\n  new value: {name}")
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
        if self.debug:
            self.logger.print(f"@cbar_reverse:\n  old value: {self.style_dict[self._plot_type]['CbarReverse']}\n  new value: {flag}")
        if (flag is None) or isinstance(flag, str):
            self.style_dict[self._plot_type]['CbarReverse'] = flag
        else:
            raise TypeError("flag must be of type str or None.")

    # cbar_dir
    @property
    def cbar_dir(self):
        return self.style_dict[self._plot_type]['CbarDir']

    @cbar_dir.setter
    def cbar_dir(self, new_dir):
        if self.debug:
            self.logger.print(f"@cbar_dir:\n  old value: {self.style_dict[self._plot_type]['CbarDir']}\n  new value: {new_dir}")
        if (new_dir is not None) and isinstance(new_dir, str) and (new_dir in ['none', 'horizontal', 'vertical']):
            self.style_dict[self._plot_type]['CbarDir'] = new_dir
        else:
            raise TypeError("new_dir must be of type str.")

    # clim
    @property
    def clim(self):
        return self.style_dict[self._plot_type]['CLim']

    @clim.setter
    def clim(self, value):
        if self.debug:
            self.logger.print(f"@clim:\n  old value: {self.style_dict[self._plot_type]['CLim']}\n  new value: {value}")
        if value is None or self._is_valid_bounds(value):
            if value == self.style_dict[self._plot_type]['CLim']:
                return
            else:
                self.style_dict[self._plot_type]['CLim'] = value
                self.notify_observers("clim", value)
        else:
            raise ValueError("xlim must be a list of two floats or None.")

    # clabel
    @property
    def clabel(self):
        return self.style_dict[self._plot_type]['CLabel']

    @clabel.setter
    def clabel(self, label):
        if self.debug:
            self.logger.print(f"@clabel:\n  old value: {self.style_dict[self._plot_type]['CLabel']}\n  new value: {label}")
        if label is None or isinstance(label, str):
            self.style_dict[self._plot_type]['CLabel'] = label
            self.notify_observers("clabel", label)
        else:
            raise TypeError("label must be of type str or None.")

    # cscale
    @property
    def cscale(self):
        return self.style_dict[self._plot_type]['CScale']

    @cscale.setter
    def cscale(self, scale):
        if self.debug:
            self.logger.print(f"@cscale:\n  old value: {self.style_dict[self._plot_type]['CScale']}\n  new value: {scale}")
        if self._is_valid_scale(scale):
            self.style_dict[self._plot_type]['CScale'] = scale
            self.notify_observers("cscale", scale)
        else:
            raise TypeError("scale must be linear, log or logit.")

    # resolution
    @property
    def resolution(self):
        return self.style_dict[self._plot_type]['Resolution']

    @resolution.setter
    def resolution(self, value):
        if self.debug:
            self.logger.print(f"@resolution:\n  old value: {self.style_dict[self._plot_type]['Resolution']}\n  new value: {value}")
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
        if self.debug:
            self.logger.print("default_scale_length")

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

    # -------------------------------------
    # Validation functions
    # -------------------------------------
    def _is_valid_bounds(self, value):
        """Validates if a the variable has properties consistent with bounds."""
        return isinstance(value, list) and len(value) == 2 and value[1] >= value[0]

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
            self.logger.print(f"{attr}: {value}")


class StyleTheme():
    def __init__(self, parent=None, debug=False):
        self.parent = parent
        self.debug = debug
        self.logger = LogCounter()

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
        if self.debug:
            self.logger.print("load_theme_names")

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
        if self.debug:
            self.logger.print(f"read_theme: {name}")

        if name == 'default':
            return self.default_style_dict()

        try:
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'rb') as file:
                style_dict = pickle.load(file)
        except:
            QMessageBox.warning(self.parent,'Error','Could not load style theme.')

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
        if self.debug:
            self.logger.print("input_theme_name_dlg")
        
        name, ok = QInputDialog.getText(None, 'Save custom theme', 'Enter theme name:')
        if ok:
            # append theme to file of saved themes
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'wb') as file:
                pickle.dump(style_dict, file, protocol=pickle.HIGHEST_PROTOCOL)

            return name
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.parent,'Error','Could not save theme.')

            return None

    def default_style_dict(self):
        """Resets style dictionary to default values.
        
        Returns
        -------
        dict :
            Default style dictionary.
        """

        if self.debug:
            self.logger.print("default_style_dict")

        styles = {}

        self.default_plot_style = {
                'XLim': [0,1], 'XScale': 'linear', 'XLabel': '', 'YLim': [0,1], 'YScale': 'linear', 'YLabel': '', 'ZLim': [0,1], 'ZLabel': '', 'ZScale': 'linear', 'AspectRatio': 1.0, 'TickDir': 'out',
                'Font': '', 'FontSize': 11.0,
                'ScaleDir': 'none', 'ScaleLocation': 'northeast', 'ScaleLength': None, 'OverlayColor': '#ffffff',
                'Marker': 'circle', 'MarkerSize': 6, 'MarkerColor': '#1c75bc', 'MarkerAlpha': 30,
                'LineWidth': 1.5, 'LineMultiplier': 1, 'LineColor': '#1c75bc',
                'CLim': [0,1], 'CScale': 'linear', 'CLabel': '', 'Colormap': 'viridis', 'CbarReverse': False, 'CbarDir': 'vertical', 'Resolution': 10 }

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
                'cluster': copy.deepcopy(self.default_plot_style),
                'cluster score map': copy.deepcopy(self.default_plot_style),
                'cluster performance': copy.deepcopy(self.default_plot_style),
                'profile': copy.deepcopy(self.default_plot_style),
                'polygon': copy.deepcopy(self.default_plot_style)
                }

        styles['field map']['Colormap'] = 'plasma'

        styles['correlation']['AspectRatio'] = 1.0
        styles['correlation']['FontSize'] = 8
        styles['correlation']['Colormap'] = 'RdBu'
        styles['correlation']['CbarDir'] = 'vertical'
        styles['correlation']['CLim'] = [-1,1]

        styles['basis vectors']['AspectRatio'] = 1.0
        styles['basis vectors']['Colormap'] = 'RdBu'

        styles['gradient map']['Colormap'] = 'RdYlBu'

        styles['cluster score map']['Colormap'] = 'plasma'
        styles['dimension score map']['Colormap'] = 'viridis'

        styles['cluster']['CScale'] = 'discrete'
        styles['cluster']['MarkerAlpha'] = 100

        styles['cluster performance']['AspectRatio'] = 0.62

        styles['scatter']['AspectRatio'] = 1

        styles['heatmap']['AspectRatio'] = 1
        styles['heatmap']['CLim'] = [1,1000]
        styles['heatmap']['CScale'] = 'log'
        styles['TEC']['AspectRatio'] = 0.62
        styles['variance']['AspectRatio'] = 0.62
        styles['basis vectors']['CLim'] = [-1,1]
        styles['dimension scatter']['LineColor'] = '#4d4d4d'
        styles['dimension scatter']['LineWidth'] = 0.5
        styles['dimension scatter']['AspectRatio'] = 1
        styles['dimension heatmap']['AspectRatio'] = 1
        styles['dimension heatmap']['LineColor'] = '#ffffff'

        styles['variance']['FontSize'] = 8

        styles['histogram']['AspectRatio'] = 0.62
        styles['histogram']['LineWidth'] = 0

        styles['profile']['AspectRatio'] = 0.62
        styles['profile']['LineWidth'] = 1.0
        styles['profile']['MarkerSize'] = 12
        styles['profile']['MarkerColor'] = '#d3d3d3'
        styles['profile']['LineColor'] = '#d3d3d3'

        return styles
    

class StylingDock(Styling):
    def __init__(self, parent, debug=False):
        super().__init__(debug)

        self.axis_widget_dict = {
            'label': [parent.labelX, parent.labelY, parent.labelZ, parent.labelC],
            'parentbox': [parent.comboBoxFieldTypeX, parent.comboBoxFieldTypeY, parent.comboBoxFieldTypeZ, parent.comboBoxFieldTypeC],
            'childbox': [parent.comboBoxFieldX, parent.comboBoxFieldY, parent.comboBoxFieldZ, parent.comboBoxFieldC],
            'spinbox': [parent.spinBoxFieldX, parent.spinBoxFieldY, None, parent.spinBoxFieldC],
            'scalebox': [parent.comboBoxXScale, parent.comboBoxYScale, parent.comboBoxZScale, parent.comboBoxColorScale],
            'axis_label': [parent.lineEditXLabel, parent.lineEditYLabel, parent.lineEditZLabel, parent.lineEditCbarLabel],
            'lbound': [parent.lineEditXLB, parent.lineEditYLB, parent.lineEditZLB, parent.lineEditColorLB],
            'ubound': [parent.lineEditXUB, parent.lineEditYUB, parent.lineEditZUB, parent.lineEditColorUB],
            'plot type': {
                '': {'axis': [False, False, False, False], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, False]},
                'field map': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, True]},
                'gradient map': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, True]},
                'correlation': {'axis': [True, False, False, True], 'add_none': [False, False, False, True], 'spinbox': [False, False, False, True]},
                'histogram': {'axis': [True, False, False, True], 'add_none': [False, False, False, True], 'spinbox': [True, False, False, True]},
                'scatter': {'axis': [True, True, True, True], 'add_none': [False, False, True, True], 'spinbox': [False, False, False, True]},
                'heatmap': {'axis': [True, True, True, False], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, False]},
                'ternary map': {'axis': [True, True, True, False], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, False]},
                'TEC': {'axis': [False, False, False, True], 'add_none': [False, False, False, True], 'spinbox': [False, False, False, False]},
                'radar': {'axis': [False, False, False, True], 'add_none': [False, False, False, True], 'spinbox': [False, False, False, False]},
                'variance': {'axis': [False, False, False, False], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, False]},
                'basis vectors': {'axis': [False, False, False, False], 'add_none': [False, False, False, False], 'spinbox': [True, True, False, False]},
                'dimension score map': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, True]},
                'dimension scatter': {'axis': [True, True, False, True], 'add_none': [False, False, False, True], 'spinbox': [True, True, False, True]}, 
                'dimension heatmap': {'axis': [True, True, False, False], 'add_none': [False, False, False, False], 'spinbox': [True, True, False, False]},
                'cluster': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, False]},
                'cluster score map': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, True]},
                'cluster performance': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, False]},
                'profile': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, True]},
                'polygon': {'axis': [False, False, False, True], 'add_none': [False, False, False, False], 'spinbox': [False, False, False, True]}
            }
        }

        self.ui = parent
        self.app_data = parent.app_data

        self.debug = debug
        self.logger = LogCounter()
        
        # initialize style themes and associated widgets
        self.style_themes = StyleTheme(parent, debug=self.debug)

        parent.comboBoxStyleTheme.clear()
        parent.comboBoxStyleTheme.addItems(self.style_themes.load_theme_names())
        parent.comboBoxStyleTheme.setCurrentIndex(0)
        
        self.ui.comboBoxStyleTheme.activated.connect(lambda: setattr(self, "style_dict", self.style_themes.read_theme(self.ui.comboBoxStyleTheme.currentText())))
        self.ui.toolButtonSaveTheme.clicked.connect(self.save_style_theme)

        self.style_dict = self.style_themes.default_style_dict()


        self._signal_state = True

        self.scheduler = Scheduler(callback=self.ui.update_SV)

        self.ui.fontComboBox.setCurrentFont(QFont(self.style_themes.default_plot_style['Font'], 11))

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
        #self.ui.lineEditCbarLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('c',self.ui.lineEditCbarLabel.text()))

        #self.ui.comboBoxXScale.activated.connect(lambda: self.axis_scale_callback(self.ui.comboBoxXScale,'x'))
        #self.ui.comboBoxYScale.activated.connect(lambda: self.axis_scale_callback(self.ui.comboBoxYScale,'y'))
        #self.ui.comboBoxColorScale.activated.connect(lambda: self.axis_scale_callback(self.ui.comboBoxColorScale,'c'))

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
        self.ui.lineEditColorLB.setValidator(QDoubleValidator())
        self.ui.lineEditColorLB.precision = 3
        self.ui.lineEditColorLB.toward = 0
        self.ui.lineEditColorUB.setValidator(QDoubleValidator())
        self.ui.lineEditColorUB.precision = 3
        self.ui.lineEditColorUB.toward = 1
        self.ui.lineEditAspectRatio.setValidator(QDoubleValidator())
        self.ui.lineEditAspectRatio.precision = 3
        self.ui.lineEditAspectRatio.toward = 1

        #self.ui.lineEditXLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 0, float(self.ui.lineEditXLB.text())))
        #self.ui.lineEditXUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 1, float(self.ui.lineEditXUB.text())))
        #self.ui.lineEditYLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 0, float(self.ui.lineEditYLB.text())))
        #self.ui.lineEditYUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 1, float(self.ui.lineEditYUB.text())))
        #self.ui.lineEditZLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('z', 0, float(self.ui.lineEditZLB.text())))
        #self.ui.lineEditZUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('z', 1, float(self.ui.lineEditZUB.text())))
        #self.ui.lineEditColorLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 0, float(self.ui.lineEditColorLB.text())))
        #self.ui.lineEditColorUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 1, float(self.ui.lineEditColorUB.text())))

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
        
        self.ui.comboBoxTernaryColormap.clear()

        self.ui.comboBoxTernaryColormap.addItems(self.color_schemes)
        self.ui.comboBoxTernaryColormap.addItem('user defined')

        # dialog for adding and saving new colormaps
        #self.ui.toolButtonSaveTernaryColormap.clicked.connect(self.ui.input_ternary_name_dlg)

        # select new ternary colors
        #self.ui.toolButtonTCmapXColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapXColor))
        #self.ui.toolButtonTCmapYColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapYColor))
        #self.ui.toolButtonTCmapZColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapZColor))
        #self.ui.toolButtonTCmapMColor.clicked.connect(lambda: self.button_color_select(self.ui.toolButtonTCmapMColor))
        #self.ui.comboBoxTernaryColormap.currentIndexChanged.connect(lambda: self.ternary_colormap_changed())
        self.ternary_colormap_changed()

        self._signal_state = False

        self.set_style_widgets()


    @property
    def signal_state(self):
        """Signal state for styling related widgets.
        
        When ``signal_state == False``, signals from widgets are blocked. """
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

        name = self.style_themes.input_theme_name_dlg(self.style_dict)
        self.ui.comboBoxStyleTheme.addItem(name)

    def toggle_signals(self):
        """Toggles signals from all style widgets.  Useful when updating many widgets."""        

        if self.debug:
            self.logger.print(f"toggle_signals, _signal_state: {self._signal_state}")

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
        ui.lineEditColorLB.blockSignals(self._signal_state)
        ui.lineEditColorUB.blockSignals(self._signal_state)
        ui.comboBoxColorScale.blockSignals(self._signal_state)
        ui.lineEditCbarLabel.blockSignals(self._signal_state)
        ui.comboBoxCbarDirection.blockSignals(self._signal_state)


    # general style functions
    # -------------------------------------
 

    def disable_style_widgets(self):
        """Disables all style related widgets."""        
        if self.debug:
            self.logger.print("disable_style_widgets")
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
        ui.lineEditColorLB.setEnabled(False)
        ui.lineEditColorUB.setEnabled(False)
        ui.comboBoxColorScale.setEnabled(False)
        ui.lineEditCbarLabel.setEnabled(False)
        ui.comboBoxCbarDirection.setEnabled(False)

        # clusters

    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        if self.debug:
            self.logger.print("toggle_style_widgets")

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
                ui.lineEditColorLB.setEnabled(True)
                ui.lineEditColorUB.setEnabled(True)
                ui.comboBoxColorScale.setEnabled(True)
                ui.comboBoxCbarDirection.setEnabled(True)
                ui.lineEditCbarLabel.setEnabled(True)

            case 'correlation' | 'basis vectors':
                # axes properties
                ui.comboBoxTickDirection.setEnabled(True)

                # color properties
                ui.comboBoxFieldColormap.setEnabled(True)
                ui.lineEditColorLB.setEnabled(True)
                ui.lineEditColorUB.setEnabled(True)
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
                    ui.lineEditColorLB.setEnabled(True)
                    ui.lineEditColorUB.setEnabled(True)
                    ui.comboBoxColorScale.setEnabled(True)
                    ui.comboBoxCbarDirection.setEnabled(True)
                    ui.lineEditCbarLabel.setEnabled(True)

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
                ui.lineEditColorLB.setEnabled(True)
                ui.lineEditColorUB.setEnabled(True)
                ui.comboBoxColorScale.setEnabled(True)
                ui.comboBoxCbarDirection.setEnabled(True)
                ui.lineEditCbarLabel.setEnabled(True)

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
                if not ui.spotdata.empty:
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

            case 'pca score' | 'cluster score' | 'cluster':
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
                    ui.lineEditColorLB.setEnabled(True)
                    ui.lineEditColorUB.setEnabled(True)
                    ui.comboBoxColorScale.setEnabled(True)
                    ui.comboBoxCbarDirection.setEnabled(True)
                    ui.lineEditCbarLabel.setEnabled(True)
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
        if self.debug:
            self.logger.print("toggle_style_labels")
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
        ui.labelColorScale.setEnabled(ui.comboBoxColorScale.isEnabled())
        ui.labelColorBounds.setEnabled(ui.lineEditColorLB.isEnabled())
        ui.toolButtonCAxisReset.setEnabled(ui.labelColorBounds.isEnabled())
        ui.labelCbarDirection.setEnabled(ui.comboBoxCbarDirection.isEnabled())
        ui.labelCbarLabel.setEnabled(ui.lineEditCbarLabel.isEnabled())
        ui.labelHeatmapResolution.setEnabled(ui.spinBoxHeatmapResolution.isEnabled())

    def set_style_dictionary(self, plot_type=None, style=None):
        """Sets values in style dictionary

        Parameters
        ----------
        plot_type : str, optional
            Dictionary key into ``MainWindow.styles``, Defaults to ``None``
        style : dict, optional
            Style dictionary for the current plot type. Defaults to ``None``
        """
        style = self.style_dict[self.plot_type]

        if not plot_type:
            plot_type = self.plot_type

        data = self.ui.data[self.app_data.sample_id]
                
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
            style['AspectRatio'] = data.aspect_ratio

        if (style['ScaleLength'] is None) and (plot_type in self.map_plot_types):
            style['ScaleLength'] = self.default_scale_length()

        if self.app_data.c_field in list(data.axis_dict.keys()):
            field = self.app_data.c_field
            style['CLim'] = [data.axis_dict[field]['min'], data.axis_dict[field]['max']]
            style['CLabel'] = data.axis_dict[field]['label']

        if self.app_data.c_field_type == 'cluster':
            style['CScale'] = 'discrete'
        else:
            style['CScale'] = 'linear'

    def set_style_widgets(self):
        """Sets values in right toolbox style page

        Parameters
        ----------
        plot_type : str, optional
            Dictionary key into ``MainWindow.styles``, Defaults to ``None``
        style : dict, optional
            Style dictionary for the current plot type. Defaults to ``None``
        """
        if self.debug:
            self.logger.print("set_style_widgets")

        if self.app_data.sample_id == '':
            return

        ui = self.ui
        data = ui.data[self.app_data.sample_id]

        # tab_id = ui.toolBox.currentIndex()
        # if self.plot_type is None:
        #     self.plot_type = ui.plot_types[tab_id][ui.plot_types[tab_id][0]+1]
        #     ui.comboBoxPlotType.blockSignals(True)
        #     ui.comboBoxPlotType.clear()
        #     ui.comboBoxPlotType.addItems(ui.plot_types[tab_id][1:])
        #     ui.comboBoxPlotType.setCurrentText(plot_type)
        #     ui.comboBoxPlotType.blockSignals(False)
        # elif plot_type == '':
        #     return

        self.signal_state = True

        style = self.style_dict[self.plot_type]

        # toggle actionSwapAxes
        match self.plot_type:
            case 'field map' | 'gradient map':
                ui.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                ui.actionSwapAxes.setEnabled(True)
            case _:
                ui.actionSwapAxes.setEnabled(False)

        if (self.scale_length is None) and (self.plot_type.lower() in self.map_plot_types):
            self.scale_length = self.default_scale_length()

        # axes properties
        # for map plots, check to see that 'X' and 'Y' are initialized
        if self.plot_type.lower() in self.map_plot_types:
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
            style['AspectRatio'] = data.aspect_ratio

            # do not round axes limits for maps
            ui.lineEditXLB.precision = None
            ui.lineEditXUB.precision = None
            ui.lineEditXLB.value = style['XLim'][0]
            ui.lineEditXUB.value = style['XLim'][1]

            ui.lineEditYLB.value = style['YLim'][0]
            ui.lineEditYUB.value = style['YLim'][1]

            ui.lineEditZLB.value = style['ZLim'][0]
            ui.lineEditZUB.value = style['ZLim'][1]
        else:
            # round axes limits for everything that isn't a map
            ui.lineEditXLB.value = style['XLim'][0]
            ui.lineEditXUB.value = style['XLim'][1]

            ui.lineEditYLB.value = style['YLim'][0]
            ui.lineEditYUB.value = style['YLim'][1]

            ui.lineEditZLB.value = style['ZLim'][0]
            ui.lineEditZUB.value = style['ZLim'][1]

        ui.comboBoxXScale.setCurrentText(style['XScale'])
        ui.lineEditXLabel.setText(style['XLabel'])

        ui.comboBoxYScale.setCurrentText(style['YScale'])
        ui.lineEditYLabel.setText(style['YLabel'])

        ui.comboBoxYScale.setCurrentText(style['ZScale'])
        ui.lineEditZLabel.setText(style['ZLabel'])

        ui.lineEditAspectRatio.setText(str(style['AspectRatio']))

        # annotation properties
        #ui.fontComboBox.setCurrentFont(style['Font'])
        ui.doubleSpinBoxFontSize.blockSignals(True)
        ui.doubleSpinBoxFontSize.setValue(style['FontSize'])
        ui.doubleSpinBoxFontSize.blockSignals(False)

        # scalebar properties
        ui.comboBoxScaleLocation.setCurrentText(style['ScaleLocation'])
        ui.comboBoxScaleDirection.setCurrentText(style['ScaleDir'])
        if (style['ScaleLength'] is None) and (self.plot_type in self.map_plot_types):
            style['ScaleLength'] = self.default_scale_length()

            ui.lineEditScaleLength.value = style['ScaleLength']
        else:
            ui.lineEditScaleLength.value = None
            
        ui.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % style['OverlayColor'])

        # marker properties
        ui.comboBoxMarker.setCurrentText(style['Marker'])

        ui.doubleSpinBoxMarkerSize.blockSignals(True)
        ui.doubleSpinBoxMarkerSize.setValue(style['MarkerSize'])
        ui.doubleSpinBoxMarkerSize.blockSignals(False)

        ui.horizontalSliderMarkerAlpha.setValue(int(style['MarkerAlpha']))
        ui.labelMarkerAlpha.setText(str(ui.horizontalSliderMarkerAlpha.value()))

        # line properties
        ui.doubleSpinBoxLineWidth.setValue(style['LineWidth'])
        ui.lineEditLengthMultiplier.value = style['LineMultiplier']
        ui.toolButtonLineColor.setStyleSheet("background-color: %s;" % style['LineColor'])

        # color properties
        ui.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % style['MarkerColor'])
        add_none = True
        if self.plot_type in self.map_plot_types:
            add_none = False
        ui.update_field_type_combobox_options(ui.comboBoxFieldTypeC, ui.comboBoxFieldC, add_none=add_none)
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

        ui.comboBoxFieldColormap.setCurrentText(style['Colormap'])
        ui.checkBoxReverseColormap.blockSignals(True)
        ui.checkBoxReverseColormap.setChecked(style['CbarReverse'])
        ui.checkBoxReverseColormap.blockSignals(False)
        field = self.app_data.c_field
        if field in list(data.axis_dict.keys()):
            style['CLim'] = [data.axis_dict[field]['min'], data.axis_dict[field]['max']]
            style['CLabel'] = data.axis_dict[field]['label']
        ui.lineEditColorLB.value = style['CLim'][0]
        ui.lineEditColorUB.value = style['CLim'][1]
        if self.app_data.c_field_type == 'cluster':
            # set color field to active cluster method
            ui.comboBoxFieldC.setCurrentText(ui.cluster_dict['active method'])

            # set color scale to discrete
            ui.comboBoxColorScale.clear()
            ui.comboBoxColorScale.addItem('discrete')
            ui.comboBoxColorScale.setCurrentText('discrete')

            style['CScale'] = 'discrete'
        else:
            # set color scale options to linear/log
            ui.comboBoxColorScale.clear()
            ui.comboBoxColorScale.addItems(['linear','log'])
            style['CScale'] = 'linear'
            ui.comboBoxColorScale.setCurrentText(style['CScale'])
            
        ui.comboBoxColorScale.setCurrentText(style['CScale'])
        ui.comboBoxCbarDirection.setCurrentText(style['CbarDir'])
        ui.lineEditCbarLabel.setText(style['CLabel'])

        ui.spinBoxHeatmapResolution.blockSignals(True)
        ui.spinBoxHeatmapResolution.setValue(style['Resolution'])
        ui.spinBoxHeatmapResolution.blockSignals(False)

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        self.signal_state = False

    # def update_style_dict(self):
    #     """Get style properties"""        
    #     if self.debug:
    #         self.logger.print("update_style_dict")
    #     self.ui = self.self.ui

    #     parent.plot_types[parent.toolBox.currentIndex()][0] = parent.comboBoxPlotType.currentIndex()

        
    #     self.style_dict[self.plot_type] = {
    #             # axes properties
    #             'XLim': [float(parent.lineEditXLB.text()), float(parent.lineEditXUB.text())],
    #             'XLabel': parent.lineEditXLabel.text(),
    #             'YLim': [float(parent.lineEditYLB.text()), float(parent.lineEditYUB.text())],
    #             'YLabel': parent.lineEditYLabel.text(),
    #             'ZLabel': parent.lineEditZLabel.text(),
    #             'AspectRatio': float(parent.lineEditAspectRatio.text()),
    #             'TickDir': parent.comboBoxTickDirection.text(),

    #             # annotation properties
    #             'Font': parent.fontComboBox.currentFont(),
    #             'FontSize': parent.doubleSpinBoxFontSize.value(),

    #             # scale properties
    #             'ScaleLocation': parent.comboBoxScaleLocation.currentText(),
    #             'ScaleDir': parent.comboBoxScaleDirection.currentText(),
    #             'ScaleLength': parent.lineEditScaleLength.value,
    #             'OverlayColor': get_hex_color(parent.toolButtonOverlayColor.palette().button().color()),

    #             # update marker properties
    #             'Marker': parent.comboBoxMarker.currentText(),
    #             'MarkerSize': parent.doubleSpinBoxMarkerSize.value(),
    #             'MarkerAlpha': float(parent.horizontalSliderMarkerAlpha.value()),
    #             'MarkerColor': get_hex_color(parent.toolButtonMarkerColor.palette().button().color()),

    #             # update line properties
    #             'LineWidth': float(parent.doubleSpinBoxLineWidth.value()),
    #             'LineMultiplier': float(parent.lineEditLengthMultiplier.text()),
    #             'LineColor': get_hex_color(parent.toolButtonLineColor.palette().button().color()),

    #             # update color properties
    #             'CLabel': parent.lineEditCbarLabel.text(),
    #             'CLim': [float(parent.lineEditColorLB.text()), float(parent.lineEditColorUB.text())],
    #             'CScale': parent.comboBoxColorScale.currentText(),
    #             'Colormap': parent.comboBoxFieldColormap.currentText(),
    #             'CbarReverse': parent.checkBoxReverseColormap.isChecked(),
    #             'CbarDir': parent.comboBoxCbarDirection.currentText(),
    #             'Resolution': parent.spinBoxHeatmapResolution.value()}

    # style widget callbacks
    # -------------------------------------
    def init_field_widgets(self, widget_dict, plot_type=None):
        """Initializes widgets associated with axes for plotting

        Enables and sets visibility of labels, comboboxes, and spinboxes associated with axes for choosing plot dimensions, including color.

        Parameters
        ----------
        widget_dict : dict
            Dictionary with field associated widgets and properties
        
        :see also: self.axis_widget_dict
        """
        if self.debug:
            self.ui.logger.print(f"init_field_widgets: plot_type={plot_type}")
        if plot_type is None:
            setting = widget_dict['plot type'][self.plot_type]
        else:
            setting = widget_dict['plot type']['none']

        for ax in range(3):
            widget_dict['label'][ax].setEnabled(setting['axis'][ax])
            widget_dict['label'][ax].setVisible(setting['axis'][ax])

            widget_dict['parentbox'][ax].setEnabled(setting['axis'][ax])
            widget_dict['parentbox'][ax].setVisible(setting['axis'][ax])

            widget_dict['childbox'][ax].setEnabled(setting['axis'][ax])
            widget_dict['childbox'][ax].setVisible(setting['axis'][ax])

            if widget_dict['spinbox'][ax] is not None:
                widget_dict['spinbox'][ax].setEnabled(setting['spinbox'][ax])
                widget_dict['spinbox'][ax].setVisible(setting['spinbox'][ax])

    def update_plot_type(self, new_plot_type=None, force=False):
        """Updates styles when plot type is changed

        Executes on change of ``MainWindow.comboBoxPlotType``.  Updates ``MainWindow.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        if self.debug:
            self.logger.print(f"plot_type_callback:\n  new_plot_type={new_plot_type}\n  force={force}")

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

        self.init_field_widgets(self.axis_widget_dict)

        # update ui
        match self.plot_type.lower():
            case 'field map' | 'gradient map':
                ui.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                ui.actionSwapAxes.setEnabled(True)
            case 'correlation':
                ui.actionSwapAxes.setEnabled(False)
                if ui.comboBoxCorrelationMethod.currentText() == 'None':
                    ui.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case 'cluster performance':
                ui.labelClusterMax.show()
                ui.spinBoxClusterMax.show()
                ui.labelNClusters.hide()
                ui.spinBoxNClusters.hide()
            case 'cluster' | 'cluster score':
                ui.labelClusterMax.hide()
                ui.spinBoxClusterMax.hide()
                ui.labelNClusters.show()
                ui.spinBoxNClusters.show()
            case _:
                ui.actionSwapAxes.setEnabled(False)

        # update field widgets
        self.update_field_widgets()

        # update all plot widgets
        self.set_style_widgets()

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
        for ax in range(3):
            widget_dict['label'][ax].setText(setting['label'][ax])

            if setting['saved_field_type'][ax] is not None:
                self.app_data.set_field_type(ax, setting['save_field_type'][ax])
            else:
                parentbox = widget_dict['parentbox'][ax]
                childbox = widget_dict['childbox'][ax]
                add_none = widget_dict['plot type'][self.plot_type]['add_none'][ax]
                self.ui.update_field_type_combobox_options(parentbox, childbox, add_none=add_none, global_list=True)

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
        if self.debug:
            self.logger.print(f"axis_variable_changed:\n  field_type={field_type}\n  field={field}\n  ax={ax}")

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
            amin, amax, scale, label = self.get_axis_values(field_type, field, ax)

            plot_type = self.plot_type

            self.style_dict[plot_type][ax+'Lim'] = [amin, amax]
            self.style_dict[plot_type][ax+'Scale'] = scale
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
        if self.debug:
            self.logger.print(f"get_axis_field: ax={ax}")

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
            case 'field map' | 'ternary map' | 'PCA score' | 'cluster' | 'cluster score':
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
            self.logger.print("axis_label_edit_callback")

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
        data.axis_dict[field]['label'] = new_label
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
        if self.debug:
            self.logger.print("axis_limit_edit_callback")

        data = self.ui.data[self.app_data.sample_id]

        axis_dict = data.axis_dict
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
        if self.debug:
            self.logger.print("axis_scale_callback")

        data = self.ui.data[self.app_data.sample_id]

        styles = self.style_dict[self._plot_type]

        new_value = comboBox.currentText()
        if ax == 'c':
            if styles['CLim'] == new_value:
                return
        elif styles[ax.upper()+'Scale'] == new_value:
            return

        field = self.get_axis_field(ax)

        if self._plot_type != 'heatmap':
            data.axis_dict[field]['scale'] = new_value

        if ax == 'c':
            styles['CScale'] = new_value
        else:
            styles[ax.upper()+'Scale'] = new_value

        # update plot
        self.schedule_update()

    def set_color_axis_widgets(self):
        """Sets the color axis limits and label widgets."""
        if self.debug:
            self.logger.print("set_color_axis_widgets")

        data = self.ui.data[self.app_data.sample_id]

        field = self.ui.comboBoxFieldC.currentText()
        if field == '':
            return
        self.ui.lineEditColorLB.value = data.axis_dict[field]['min']
        self.ui.lineEditColorUB.value = data.axis_dict[field]['max']
        self.ui.comboBoxColorScale.setCurrentText(data.axis_dict[field]['scale'])

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
            self.logger.print("set_axis_widgets")

        data = self.ui.data[self.app_data.sample_id]

        if field == '':
            return

        match ax:
            case 'x':
                if field == 'X':
                    self.ui.lineEditXLB.value = data.axis_dict[field]['min']
                    self.ui.lineEditXUB.value = data.axis_dict[field]['max']
                else:
                    self.ui.lineEditXLB.value = data.axis_dict[field]['min']
                    self.ui.lineEditXUB.value = data.axis_dict[field]['max']
                self.ui.lineEditXLabel.setText(data.axis_dict[field]['label'])
                self.ui.comboBoxXScale.setCurrentText(data.axis_dict[field]['scale'])
            case 'y':
                if self.ui.comboBoxPlotType.currentText() == 'histogram':
                    self.ui.lineEditYLB.value = data.axis_dict[field]['pmin']
                    self.ui.lineEditYUB.value = data.axis_dict[field]['pmax']
                    self.ui.lineEditYLabel.setText(self.ui.comboBoxHistType.currentText())
                    self.ui.comboBoxYScale.setCurrentText('linear')
                else:
                    if field == 'X':
                        self.ui.lineEditYLB.value = data.axis_dict[field]['min']
                        self.ui.lineEditYUB.value = data.axis_dict[field]['max']
                    else:
                        self.ui.lineEditYLB.value = data.axis_dict[field]['min']
                        self.ui.lineEditYUB.value = data.axis_dict[field]['max']
                    self.ui.lineEditYLabel.setText(data.axis_dict[field]['label'])
                    self.ui.comboBoxYScale.setCurrentText(data.axis_dict[field]['scale'])
            case 'z':
                self.ui.lineEditZLB.value = data.axis_dict[field]['min']
                self.ui.lineEditZUB.value = data.axis_dict[field]['max']
                self.ui.lineEditZLabel.setText(data.axis_dict[field]['label'])
                self.ui.comboBoxZScale.setCurrentText(data.axis_dict[field]['scale'])

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
            self.logger.print(f"axis_reset_callback, axis: {ax}")

        data = self.ui.data[self.app_data.sample_id]

        if ax == 'c':
            if self.ui.comboBoxPlotType.currentText() == 'basis vectors':
                self.style_dict['basis vectors']['CLim'] = [np.amin(self.ui.pca_results.components_), np.amax(self.ui.pca_results.components_)]
            elif not (self.ui.comboBoxFieldTypeC.currentText() in ['None','cluster']):
                field_type = self.ui.comboBoxFieldTypeC.currentText()
                field = self.ui.comboBoxFieldC.currentText()
                if field == '':
                    return
                self.initialize_axis_values(field_type, field)

            self.set_color_axis_widgets()
        else:
            match self.ui.comboBoxPlotType.currentText().lower():
                case 'field map' | 'cluster' | 'cluster score' | 'pca score':
                    field = ax.upper()
                    self.initialize_axis_values('Analyte', field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = self.ui.comboBoxFieldC.currentText()
                    if ax == 'x':
                        field_type = self.ui.comboBoxFieldTypeC.currentText()
                        self.initialize_axis_values(field_type, field)
                        self.set_axis_widgets(ax, field)
                    else:
                        data.axis_dict[field].update({'pstatus':'auto', 'pmin':None, 'pmax':None})

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
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case 'PCA scatter' | 'PCA heatmap':
                    field_type = 'PCA score'
                    if ax == 'x':
                        field = self.ui.spinBoxPCX.currentText()
                    else:
                        field = self.ui.spinBoxPCY.currentText()
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.set_style_widgets()
        self.schedule_update()

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
            self.logger.print(f"get_axis_values\n  field_type: {field_type}\n  field: {field}\n  axis: {ax}")

        data = self.ui.data[self.app_data.sample_id]

        axis_dict = data.axis_dict

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
            self.logger.print(f"initialize_axis_values\n  field_type: {field_type}\n  field: {field}")

        data = self.ui.data[self.app_data.sample_id]

        # initialize variables
        if field not in data.axis_dict.keys():
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
                        data.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol} ({self.app_data.preferences['Units']['Concentration']})"
                    else:
                        data.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol}$_N$ ({self.app_data.preferences['Units']['Concentration']})"

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
            self.logger.print(f"parse_field, field: {field}")

        match = re.match(r"([A-Za-z]+)(\d*)", field)
        symbol = match.group(1) if match else field
        mass = int(match.group(2)) if match.group(2) else None

        return symbol, mass

    def aspect_ratio_callback(self):
        """Update aspect ratio

        Updates ``MainWindow.style`` dictionary after user change
        """
        if self.debug:
            self.logger.print(f"aspect_ratio_callback")

        if self.aspect_ratio == self.ui.lineEditAspectRatio.value:
            return

        self.aspect_ratio = self.ui.lineEditAspectRatio.value
        self.schedule_update()

    def tickdir_callback(self):
        """Updates tick directions in style dictionary from change of ``MainWindow.comboBoxTickDirection``."""        
        if self.debug:
            self.logger.print("tickdir_callback")

        if self.tick_dir == self.ui.comboBoxTickDirection.currentText():
            return

        self.tick_dir = self.ui.comboBoxTickDirection.currentText()
        self.schedule_update()

    # text and annotations
    # -------------------------------------
    def font_callback(self):
        """Updates figure fonts"""        
        if self.debug:
            self.logger.print("font_callback")

        if self.font == self.ui.fontComboBox.currentFont().family():
            return

        self.font = self.ui.fontComboBox.currentFont().family()
        self.schedule_update()

    def font_size_callback(self):
        """Updates figure font sizes"""        
        if self.debug:
            self.logger.print("font_size_callback")

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
        if self.debug:
            self.logger.print("update_figure_font")

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
            self.logger.print("toggle_mass")
    
        if not self.show_mass:
            labels = [re.sub(r'\d', '', col) for col in labels]

        return labels

    # scales
    # -------------------------------------
    def update_scale_direction_combobox(self, new_dir):
        """Sets scale direction on figure"""        
        if self.debug:
            self.logger.print("update_scale_direction")
            
        self.ui.comboBoxScaleDirection.setCurrentText(new_dir)
        self.toggle_scale_widgets()

        self.schedule_update()

    def update_scale_direction(self):
        self.scale_direction = self.ui.comboBoxScaleDirection.currentText()
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
        if self.debug:
            self.logger.print("scale_location_callback")

        if self.scale_location == self.ui.comboBoxScaleLocation.currentText():
            return

        self.scale_location = self.ui.comboBoxScaleLocation.currentText()
        self.schedule_update()

    def scale_length_callback(self):
        """Updates length of scalebar on map-type plots
        
        Executes on change of ``MainWindow.lineEditScaleLength``, updates length if within bounds set by plot dimensions, then updates plot.
        """ 
        if self.debug:
            self.logger.print("scale_length_callback")

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
        if self.debug:
            self.logger.print("overlay_color_callback")

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
        if self.debug:
            self.logger.print("marker_symbol_callback")

        if self.marker == self.ui.comboBoxMarker.currentText():
            return
        self.marker = self.ui.comboBoxMarker.currentText()

        self.schedule_update()

    def marker_size_callback(self):
        """Updates marker size

        Updates marker size on current plot on change of ``MainWindow.doubleSpinBoxMarkerSize.value()``.
        """
        if self.debug:
            self.logger.print("marker_size_callback")

        if self.marker_size == self.ui.doubleSpinBoxMarkerSize.value():
            return
        self.marker_size = self.ui.doubleSpinBoxMarkerSize.value()

        self.schedule_update()

    def slider_alpha_changed(self):
        """Updates transparency on scatter plots.

        Executes on change of ``MainWindow.horizontalSliderMarkerAlpha.value()``.
        """
        if self.debug:
            self.logger.print("slider_alpha_changed")

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
        if self.debug:
            self.logger.print("line_width_callback")

        if self.line_width == float(self.ui.doubleSpinBoxLineWidth.value()):
            return

        self.line_width = float(self.ui.doubleSpinBoxLineWidth.value())
        self.schedule_update()

    def length_multiplier_callback(self):
        """Updates line length multiplier

        Used when plotting vector components in multidimensional plots.  Values entered by the user must be (0,10]
        """
        if self.debug:
            self.logger.print("length_multiplier_callback")

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
        if self.debug:
            self.logger.print("line_color_callback")

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
        if self.debug:
            self.logger.print("marker_color_callback")

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
        if self.debug:
            self.logger.print("resolution_callback")

        self.resolution = self.ui.spinBoxHeatmapResolution.value()

        self.schedule_update()

    # updates scatter styles when ColorByField comboBox is changed
    def update_color_field_type(self):
        """Executes on change to *ColorByField* combobox
        
        Updates style associated with ``MainWindow.comboBoxFieldTypeC``.  Also updates
        ``MainWindow.comboBoxFieldC`` and ``MainWindow.comboBoxColorScale``."""
        if self.debug:
            self.logger.print("update_color_field_type")

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
        if self.ui.comboBoxFieldTypeC.currentText() != 'None' or self.ui.comboBoxFieldC.currentText() != '' or self.ui.comboBoxFieldTypeC.currentText() in ['cluster']:
            self.schedule_update()

    def update_field_type(self, ax, field_type=None):
        if self.debug:
            self.logger.print(f"update_field_type:\n  ax={ax}\n  field_type={field_type}")

        # only update field if the axis is enabled 
        if not self.axis_widget_dict['plot type'][self.plot_type]['axis'][ax]:
            return
            #self.set_axis_lim(ax, [data.axis_dict[field]['min'], data.axis_dict[field]['max']])
            #self.set_axis_label(ax, data.axis_dict[field]['label'])
            #self.set_axis_scale(ax, data.axis_dict[field]['scale'])

        parentbox = self.axis_widget_dict['parentbox'][ax]

        if field_type is None:   # user interaction, or direct setting of combobox
            # set field property to combobox
            self.app_data.set_field(ax, parentbox.currentText())
        else:   # direct setting of property
            if field_type == parentbox.currentText() and field_type == self.app_data.get_field_type(ax):
                return

            # set combobox to field
            parentbox.setCurrentText(field_type)

        # update plot
        self.schedule_update()


    def update_field(self, ax, field=None):
        """Used to update widgets associaed with an axis after a field change to either the combobox or underlying data.

        Used to update, x, y, z, and c axes related widgets including fields, spinboxes, labels, limits and scale.  

        Parameters
        ----------
        ax : int
            Axis to update, [x,y,z,c] should be supplied as an integer, [0,1,2,3], respectively
        field : str, optional
            New field value for axis to update ``app_data`` or combobox, by default None
        """
        if self.debug:
            self.logger.print(f"update_field:\n  ax={ax}\n  field={field}")

        # only update field if the axis is enabled 
        if not self.axis_widget_dict['plot type'][self.plot_type]['axis'][ax]:
            return
            #self.set_axis_lim(ax, [data.axis_dict[field]['min'], data.axis_dict[field]['max']])
            #self.set_axis_label(ax, data.axis_dict[field]['label'])
            #self.set_axis_scale(ax, data.axis_dict[field]['scale'])

        parentbox = self.axis_widget_dict['parentbox'][ax]
        childbox = self.axis_widget_dict['childbox'][ax]
        spinbox = self.axis_widget_dict['spinbox'][ax]

        if field is None:   # user interaction, or direct setting of combobox
            # set field property to combobox
            self.app_data.set_field(ax, childbox.currentText())
        else:   # direct setting of property
            if field == childbox.currentText() and field == self.app_data.get_field(ax):
                return

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

            # initialize axis values for plotting
            if field not in data.axis_dict.keys():
                self.initialize_axis_values(parentbox.currentText(), field)

            # initialize color widgets
            if ax == 3:
                self.set_color_axis_widgets()

            # update axes properties
            if ax == 3 and self._plot_type not in ['correlation']:
                self.clim = [data.axis_dict[field]['min'], data.axis_dict[field]['max']]
                self.clabel = data.axis_dict[field]['label']
                self.cscale = data.axis_dict[field]['scale']
            elif self._plot_type not in []:
                self.set_axis_lim(ax, [data.axis_dict[field]['min'], data.axis_dict[field]['max']])
                self.set_axis_label(ax, data.axis_dict[field]['label'])
                self.set_axis_scale(ax, data.axis_dict[field]['scale'])

        else:
            self.clabel = ''

        # update plot
        self.schedule_update()
        
    def field_colormap_callback(self):
        """Sets the color map

        Sets the colormap in ``MainWindow.styles`` for the current plot type, set from ``MainWindow.comboBoxFieldColormap``.
        """
        if self.debug:
            self.logger.print("field_colormap_callback")

        if self.cmap == self.ui.comboBoxFieldColormap.currentText():
            return

        self.toggle_style_widgets()
        self.style_dict[self.ui.comboBoxPlotType.currentText()]['Colormap'] = self.ui.comboBoxFieldColormap.currentText()

        self.schedule_update()
    
    def colormap_direction_callback(self):
        """Set colormap direction (normal/reverse)

        Reverses colormap if ``MainWindow.checkBoxReverseColormap.isChecked()`` is ``True``."""
        if self.debug:
            self.logger.print("colormap_direction_callback")

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
        if self.debug:
            self.logger.print("get_cluster_colormap")

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
            self.logger.print("color_norm")

        norm = None
        match self.cscale:
            case 'linear':
                norm = colors.Normalize(vmin=self.clim[0], vmax=self.clim[1])
            case 'log':
                norm = colors.LogNorm(vmin=self.clim[0], vmax=self.clim[1])
            case 'discrete':
                if N is None:
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
        if self.debug:
            self.logger.print("get_colormap")

        if hasattr(self.ui,'canvas_tab') and hasattr(self.ui,'canvasWindow'):
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
        if self.debug:
            self.logger.print("create_custom_colormap")

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
            self.logger.print("cbar_direction_callback")

        if self.cbar_dir == self.ui.comboBoxCbarDirection.currentText():
            return
        self.cbar_dir = self.ui.comboBoxCbarDirection.currentText()

        self.schedule_update()

    def cbar_label_callback(self):
        """Sets color label

        Sets the color label in ``MainWindow.styles`` for the current plot type.
        """
        if self.debug:
            self.logger.print("cbar_label_callback")

        if self.clabel == self.ui.lineEditCbarLabel.text():
            return
        self.clabel = self.ui.lineEditCbarLabel.text()

        if self.ui.comboBoxCbarLabel.isEnabled():
            self.schedule_update()

    # cluster styles
    # -------------------------------------

    def set_default_cluster_colors(self, mask=False):
        """Sets cluster group to default colormap

        Sets the colors in ``MainWindow.tableWidgetViewGroups`` to the default colormap in
        ``MainWindow.styles['cluster']['Colormap'].  Change the default colormap
        by changing ``MainWindow.comboBoxColormap``, when ``MainWindow.comboBoxFieldTypeC.currentText()`` is ``Cluster``.

        Returns
        -------
            str : hexcolor
        """
        if self.debug:
            self.logger.print("set_default_cluster_colors")

        #print('set_default_cluster_colors')
        cluster_tab = self.parent.mask_dock.cluster_tab

        # cluster colormap
        cmap = self.get_colormap(N=self.parent.tableWidgetViewGroups.rowCount())

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(cluster_tab.tableWidgetViewGroups.rowCount()):
            hexcolor.append(get_hex_color(colors[i]))
            cluster_tab.tableWidgetViewGroups.blockSignals(True)
            cluster_tab.tableWidgetViewGroups.setItem(i,2,QTableWidgetItem(hexcolor[i]))
            cluster_tab.tableWidgetViewGroups.blockSignals(False)

        if mask:
            hexcolor.append(self.style_dict['cluster']['OverlayColor'])

        cluster_tab.toolButtonClusterColor.setStyleSheet("background-color: %s;" % cluster_tab.tableWidgetViewGroups.item(cluster_tab.spinBoxClusterGroup.value()-1,2).text())

        return hexcolor

    def ternary_colormap_changed(self):
        """Changes toolButton backgrounds associated with ternary colormap

        Updates ternary colormap when swatch colors are changed in the Scatter and Heatmaps >
        Map from Ternary groupbox.  The ternary colored chemical map is updated.
        """
        if self.debug:
            self.logger.print("ternary_colormap_changed")

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
        if self.debug:
            self.logger.print("button_color_select")

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