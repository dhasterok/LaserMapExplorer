import numpy as np
import pandas as pd
import traceback
from scipy.stats import gaussian_kde

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QVBoxLayout

import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget, ImageItem, colormap, TargetItem

import matplotlib
import matplotlib.gridspec as gs
#import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Patch
import matplotlib.colors as colors
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from src.plotting.CustomMplCanvas import MplCanvas, SimpleMplCanvas
import lame_core.format as fmt
# Removed deprecated imports: get_hex_color, get_rgb_color - now using ColorManager
from lame_core.ColorManager import convert_color
from global_geochemistry.geochem.plotting.spider import plot_spider_norm
from global_geochemistry.plotting.radar import radar_prep, radarplot
from src.plotting.scalebar import scalebar
from global_geochemistry.plotting.ternary import ternary
from src.control.Logger import LoggerConfig, log_call, log

def create_plot(parent, data, app_data, style_data):
    """Creates a plot without UI dependencies.
    
    This function handles the core plotting logic without requiring UI components.
    It can be used by both UI (MainWindow.update_SV) and non-UI (Blockly) contexts.
    
    Parameters
    ----------
    parent : object
        Parent object for MplCanvas initialization (required for annotation/tracking tools)
    data : object
        Data object containing processed data
    app_data : object
        Application data object containing settings
    style_data : object
        Plot style object providing styling information
    
    Returns
    -------
    tuple
        (canvas, plot_info) - The matplotlib canvas and plot information dict
    """
    # Basic validation - only data-related checks
    if app_data.sample_id == '' or style_data.plot_type in [None, '', 'none', 'None']:
        return None, None

    canvas = None
    plot_info = None
    
    try:
        match style_data.plot_type:
            case 'field map':
                field_type = app_data.c_field_type
                field = app_data.c_field
                canvas, plot_info, _ = plot_map_mpl(parent, data, app_data, style_data, field_type, field, add_histogram=False)
                
            case 'gradient map':
                # Note: gradient map logic would go here
                # For now, skip as it requires noise reduction preprocessing
                pass
                
            case 'correlation':
                if app_data.corr_method == 'none':
                    return None, None
                canvas, plot_info = plot_correlation(parent, data, app_data, style_data)

            case 'TEC' | 'radar':
                canvas, plot_info = plot_ndim(parent, data, app_data, style_data)

            case 'histogram':
                canvas, plot_info = plot_histogram(parent, data, app_data, style_data)

            case 'scatter' | 'heatmap':
                # Check if fields are the same
                if hasattr(app_data, 'x_field') and hasattr(app_data, 'y_field'):
                    if app_data.x_field == app_data.y_field:
                        return None, None
                canvas, plot_info = plot_scatter(parent, data, app_data, style_data)

            case 'ternary map':
                # Check if any fields are the same
                if (hasattr(app_data, 'x_field') and hasattr(app_data, 'y_field') and hasattr(app_data, 'z_field')):
                    if (app_data.x_field == app_data.y_field or 
                        app_data.x_field == app_data.z_field or 
                        app_data.y_field == app_data.z_field):
                        return None, None
                canvas, plot_info = plot_ternary_map(parent, data, app_data, style_data)

            case 'variance' | 'basis vectors' | 'dimension scatter' | 'dimension heatmap' | 'dimension score map':
                # Check if PCA needs to be computed - this is data-related, not UI-related
                if app_data.update_pca_flag or not data.processed.match_attribute('data_type','PCA score'):
                    # Note: PCA computation should be done by caller before calling create_plot
                    return None, None
                canvas, plot_info = plot_pca(parent, data, app_data, style_data)

            case 'cluster map' | 'cluster score map':
                # Note: clustering computation should be done by caller before calling create_plot
                canvas, plot_info = plot_clusters(parent, data, app_data, style_data)

            case 'cluster performance':
                # Note: cluster performance computation should be done by caller before calling create_plot
                canvas, plot_info = cluster_performance_plot(parent, data, app_data, style_data)

            case 'roi map':
                canvas, plot_info = plot_roi(parent, data, app_data, style_data)

            case 'isochron':
                canvas, plot_info = plot_isochron(parent, data, app_data, style_data)

    except Exception as e:
        print(f"Error in create_plot: {e}")
        traceback.print_exc()
        return None, None
        
    return canvas, plot_info

@log_call(logger_key='Plot')
def plot_map_mpl(parent, data, app_data, style_data, field_type, field, add_histogram=False):
    """
    Plots a 2D field map using Matplotlib, with optional histogram, color scaling, and style customization.

    Parameters
    ----------
    parent : QWidget or similar
        The parent widget for the plot canvas.
    data : object
        Data object containing processed data, mask, and methods for retrieving map data.
    app_data : object
        Application data object containing settings such as color scale equalization and sample ID.
    style_data : object
        Plot style object providing colormap, normalization, and style dictionary.
    field_type : str
        The type of field to plot (e.g., 'element', 'phase').
    field : str
        The specific field or attribute to plot.
    add_histogram : bool, optional
        If True, adds a small histogram of the field data to the plot (default is False).

    Returns
    -------
    canvas : MplCanvas
        The Matplotlib canvas containing the plotted map.
    plot_info : dict
        Dictionary containing metadata about the plot (e.g., field, style, sample ID).
    hist_canvas : MplCanvas, optional
        The Matplotlib canvas containing the histogram, only returned if add_histogram is True.

    Notes
    -----
    - Applies color normalization and optional color scale equalization.
    - Handles different color scale types (linear, log, logit, symlog).
    - Applies a mask as an alpha layer to the plot.
    - Adds a scalebar and adjusts layout.
    - Stores the plotted data in the parent for potential export.
    """
    # create plot canvas
    canvas = MplCanvas(parent=parent, map_flag=True)

    # get data for current map
    #scale = data.processed.get_attribute(field, 'norm')
    map_df = data.get_map_data(field, field_type)

    # A categorical/discrete field (e.g. the stoichiometry dock's
    # '{abbrev}_dominant' end-member field -- see src/stoichiometry/dock.py)
    # is a code with no meaningful magnitude ordering, so it renders with a
    # swatch-per-category legend (mirrors plot_cluster_map/plot_roi_map)
    # instead of the usual continuous colormap/colorbar.
    is_discrete = bool(data.processed.get_attribute(field, 'discrete'))

    array_size = data.array_size
    # style_data.aspect_ratio is None until first synced (see
    # StylingUI.set_style_widgets) or once a user has overridden it via the
    # Axes page; data.aspect_ratio (the map's true pixel aspect ratio) is
    # only a fallback for callers that bypass that sync (e.g. Blockly).
    aspect_ratio = style_data.aspect_ratio if style_data.aspect_ratio is not None else data.aspect_ratio

    # store map_df to save_data if data needs to be exported
    canvas.data = map_df.copy()

    # equalized color bins to CDF function -- not meaningful for a
    # categorical code, so skipped for discrete fields.
    if app_data.equalize_color_scale and not is_discrete:
        sorted_data = map_df['array'].sort_values()
        cum_sum = sorted_data.cumsum()
        cdf = cum_sum / cum_sum.iloc[-1]
        map_df.loc[sorted_data.index, 'array'] = cdf.values

    # plot map
    reshaped_array = np.reshape(map_df['array'].values, array_size, order=data.order)

    if is_discrete:
        # Codes are 1-indexed (see dock.py's _write_results_to_sample);
        # shift to 0-indexed to match Cluster/ROI maps' own convention.
        reshaped_array = reshaped_array - 1.0
        labels = data.processed.get_attribute(field, 'category_labels') or []
        hexcolors = data.processed.get_attribute(field, 'category_colors') or []
        group_color, group_label, cmap = style_data.get_discrete_colormap(labels, hexcolors, alpha=style_data.marker_alpha)
        n = max(len(labels), 1)
        norm = colors.BoundaryNorm(np.arange(-0.5, n, 1), n, clip=True)

        cax = canvas.axes.imshow(reshaped_array, cmap=cmap, norm=norm, aspect=aspect_ratio, interpolation='none')
        canvas.array = reshaped_array
        canvas.dx = app_data.current_data.dx
        canvas.dy = app_data.current_data.dy
        canvas.color_units = None
        canvas.distance_units = data.processed.column_attributes['Xc']['units']

        add_colorbar(style_data, canvas, cax, cbartype='discrete', grouplabels=group_label, groupcolors=group_color)
    else:
        norm = style_data.color_norm()

        cax = canvas.axes.imshow(reshaped_array,
                                cmap=style_data.get_colormap(),
                                aspect=aspect_ratio, interpolation='none',
                                norm=norm)
        canvas.array = reshaped_array
        canvas.dx = app_data.current_data.dx
        canvas.dy = app_data.current_data.dy
        canvas.color_units = data.processed.column_attributes[field]['units']
        canvas.distance_units = data.processed.column_attributes['Xc']['units']

        add_colorbar(style_data, canvas, cax)
        # Default to style_data.clim so any cscale this match doesn't
        # explicitly handle (e.g. 'discrete' reaching this generic/
        # continuous branch, which shouldn't normally happen but crashed
        # here with an UnboundLocalError when it did -- see color_norm's
        # own 'discrete'-with-no-N warning path) still has a value to call
        # set_clim with, rather than crashing.
        clim = style_data.clim
        match style_data.cscale:
            case 'linear':
                clim = style_data.clim
            case 'log':
                clim = style_data.clim
                #clim = np.log10(style_data.clim)
            case 'logit':
                print('Color limits for logit are not currently implemented')
            case 'symlog':
                print('Color limits for symlog are not currently implemented')

        cax.set_clim(clim[0], clim[1])

    # use mask to create an alpha layer — grey RGBA overlay on masked pixels
    mask = data.mask.astype(float)
    reshaped_mask = np.reshape(mask, array_size, order=data.order)
    masked_count = int((reshaped_mask == 0).sum())
    log(f"plot_map_mpl: masking {masked_count}/{mask.size} pixels ({100*masked_count/mask.size:.2f}%)", prefix='Mask')

    overlay = np.zeros((*reshaped_mask.shape, 4), dtype=float)
    overlay[..., :3] = 0.5  # grey
    overlay[..., 3] = np.where(reshaped_mask == 0, 0.5, 0)  # 50% alpha where masked, transparent elsewhere
    canvas.axes.imshow(overlay, aspect=aspect_ratio, interpolation='none')

    canvas.axes.tick_params(direction=None,
        labelbottom=False, labeltop=False, labelright=False, labelleft=False,
        bottom=False, top=False, left=False, right=False)

    canvas.set_initial_extent()

    # axes limits -- style_data.xlim/ylim are in physical Xc/Yc units, but imshow's
    # default axes are in pixel-index space (0..nx, 0..ny), so convert by subtracting
    # the sample's own minimum before dividing by pixel spacing. Anchoring on the
    # sample's actual minimum (rather than assuming it's 0) keeps this correct
    # regardless of indexing convention -- matrix-form imports store Xc/Yc as
    # 1-indexed multiples of dx/dy (first pixel's Xc == dx, not 0), while raw
    # per-line imports store them 0-indexed. Preserve whichever direction
    # (ascending/descending) imshow already established as correct for this
    # array, rather than assuming one.
    def _apply_map_lim(get_lim, set_lim, style_lim, spacing, origin):
        if not style_lim or None in style_lim or not spacing:
            return
        lo, hi = sorted([(style_lim[0] - origin) / spacing, (style_lim[1] - origin) / spacing])
        cur_lo, cur_hi = get_lim()
        set_lim(lo, hi) if cur_lo <= cur_hi else set_lim(hi, lo)

    _apply_map_lim(canvas.axes.get_xlim, canvas.axes.set_xlim, style_data.xlim, data.dx, data.xlim[0])
    _apply_map_lim(canvas.axes.get_ylim, canvas.axes.set_ylim, style_data.ylim, data.dy, data.ylim[0])

    # add scalebar
    add_scalebar(data, app_data, style_data, canvas.axes)

    canvas.fig.tight_layout()

    # add small histogram
    if add_histogram:
        hist_canvas = plot_small_histogram(parent, data, app_data, style_data, map_df)
    plot_name = field
    canvas.plot_name = plot_name
    # set title to set default name when saving figure
    
    plot_info = {
        'tree': field_type,
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'field map',
        'field_type': field_type,
        'field': field,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': None,
        'view': [True,False],
        'position': None,
        'data': canvas.data
        }
    
    if add_histogram:
        return canvas, plot_info, hist_canvas
    else:
        return canvas, plot_info, None

@log_call(logger_key='Plot')
def plot_map_pg(parent, sample_id, field_type, field, add_histogram=False):
    """Create a graphic widget for plotting a map

    Create a map using pyqtgraph.

    Parameters
    ----------
    sample_id : str
        Sample identifier
    field_type : str
        Type of field for plotting
    field : str
        Field for plotting
    """        
    # ----start debugging----
    # print('[plot_map_pg] sample_id: '+sample_id+'   field_type: '+'   field: '+field)
    # ----end debugging----

    # get data for current map
    scale = parent.style_data.cscale
    map_df = parent.data[parent.app_data.sample_id].get_map_data(field, field_type, norm=scale)

    # store map_df to save_data if data needs to be exported
    parent.save_data = map_df
    
    #Change transparency of values outside mask
    parent.array, rgba_array = parent.array_to_image(map_df)

    # plotWidget = QWidget()
    # layout = QVBoxLayout()
    # layout.setSpacing(0)
    # plotWidget.setLayout(layout)

    title = ''

    view = parent.canvasWindow.currentIndex()
    if view == parent.tab_dict['sv']:
        title = field
    elif view == parent.tab_dict['mv']:
        title = sample_id + '_' + field
    else:
        view = parent.tab_dict['sv']
        parent.canvasWindow.setCurrentIndex(view)
        title = field

    graphicWidget = GraphicsLayoutWidget(show=True)
    graphicWidget.setObjectName('LaserMap')
    graphicWidget.setBackground('w')

    # layout.addWidget(graphicWidget)

    # Create the ImageItem
    img_item = ImageItem(image=parent.array, antialias=False)

    #set aspect ratio of rectangle
    img_item.setRect(parent.data[parent.app_data.sample_id].x.min(),
            parent.data[parent.app_data.sample_id].y.min(),
            parent.data[parent.app_data.sample_id].x_range,
            parent.data[parent.app_data.sample_id].y_range)

    #--- add non-interactive image with integrated color ------------------
    plotWindow = graphicWidget.addPlot(0,0,title=title.replace('_',' '))

    plotWindow.addItem(img_item)

    # turn off axes and
    plotWindow.showAxes(False, showValues=(True,False,False,True) )
    plotWindow.invertY(True)
    plotWindow.setAspectLocked()

    # Prevent zooming/panning outside the default view
    ## These cut off parts of the map when plotting.
    #plotWindow.setRange(yRange=[parent.y.min(), parent.y.max()])
    #plotWindow.setLimits(xMin=parent.x.min(), xMax=parent.x.max(), yMin=parent.y.min(), yMax = parent.y.max())
    #plotWindow.setLimits(maxXRange=parent.data[parent.app_data.sample_id].x_range, maxYRange=parent.data[parent.app_data.sample_id].y_range)

    #supress right click menu
    plotWindow.setMenuEnabled(False)

    # colorbar
    cmap = colormap.get(parent.style_data.cmap, source = 'matplotlib')
    #clb,cub,cscale,clabel = parent.style_data.get_axis_values(field_type,field)
    # cbar = ColorBarItem(values=(clb,cub), width=25, colorMap=cmap, label=clabel, interactive=False, limits=(clb,cub), orientation=parent.style_data.cbar_dir, pen='black')
    img_item.setLookupTable(cmap.getLookupTable())
    # graphicWidget.addItem(cbar)
    pg.setConfigOption('leftButtonPan', False)

    # ... Inside your plotting function
    target = TargetItem(symbol = '+', )
    target.setZValue(1e9)
    plotWindow.addItem(target)

    # store plots in parent.lasermap to be used in profiling. parent.lasermaps is a multi index dictionary with index: (field, view)
    parent.lasermaps[field,view] = (target, plotWindow, parent.array)

    #hide pointer
    target.hide()

    plotWindow.scene().sigMouseClicked.connect(lambda event,array=parent.array, k=field, plot=plotWindow: parent.plot_clicked(event,array, k, plotWindow))

    #remove previous plot in single view
    if view == 1:
        #create label with analyte name
        #create another label for value of the corresponding plot
        labelMVInfoField = QLabel()
        # labelMVInfoValueLabel.setMaximumSize(QSize(20, 16777215))
        labelMVInfoField.setObjectName("labelMVInfoField"+field)
        labelMVInfoField.setText(field)
        font = QFont()
        font.setPointSize(9)
        labelMVInfoField.setFont(font)
        verticalLayout = QVBoxLayout()
        # Naming the verticalLayout
        verticalLayout.setObjectName(field + str(view))
        verticalLayout.addWidget(labelMVInfoField)

        labelMVInfoValue = QLabel()
        labelMVInfoValue.setObjectName("labelMVInfoValue"+field)
        labelMVInfoValue.setFont(font)
        verticalLayout.addWidget(labelMVInfoValue)
        parent.gridLayoutMVInfo.addLayout(verticalLayout, 0, parent.gridLayoutMVInfo.count()+1, 1, 1)
        # Store the reference to verticalLayout in a dictionary
        parent.multiview_info_label[field] = (labelMVInfoField, labelMVInfoValue)
    else:
        #print(parent.lasermaps)
        #print(parent.prev_plot)
        if parent.prev_plot and (parent.prev_plot,0) in parent.lasermaps:
            parent.plot_info['view'][0] = False
            del parent.lasermaps[(parent.prev_plot,0)]
        # update variables which stores current plot in SV
        parent.plot = plotWindow
        parent.prev_plot = field
        parent.init_zoom_view()
        # uncheck edge detection
        parent.mask_dock.polygon_tab.action_edge_detect.setChecked(False)


    # Create a SignalProxy to handle mouse movement events
    # Create a SignalProxy for this plot and connect it to mouseMoved

    plotWindow.scene().sigMouseMoved.connect(lambda event,plot=plotWindow: parent.mouse_moved_pg(event,plot))

    #add zoom window
    plotWindow.getViewBox().autoRange()

    # add edge detection
    if parent.mask_dock.polygon_tab.action_edge_detect.isChecked():
        parent.noise_reduction.add_edge_detection()

    if view == 0 and parent.plot_info:
        parent.plot_info['view'][0] = False
        tmp = [True,False]
    else:
        tmp = [False,True]


    parent.plot_info = {
        'tree': 'Analyte',
        'sample_id': sample_id,
        'plot_name': field,
        'plot_type': 'field map',
        'field_type': field_type,
        'field': field,
        'figure': graphicWidget,
        'style': parent.style_data.style_dict[parent.style_data.plot_type],
        'cluster_groups': None,
        'view': tmp,
        'position': None
        }

    #parent.plot_widget_dict[parent.plot_info['tree']][parent.plot_info['sample_id']][parent.plot_info['plot_name']] = {'info':parent.plot_info, 'view':view, 'position':None}
    parent.parent.canvas_widget.add_canvas_to_window(parent.plot_info)

    #parent.update_tree(plot_info=parent.plot_info)
    parent.plot_tree.add_tree_item(parent.plot_info)

    # add small histogram
    if add_histogram and (parent.toolBox.currentIndex() == parent.ui.control_dock.tab_dict['sample']) and (view == parent.ui.canvas_widget.tab_dict['sv']):
        plot_small_histogram(parent, parent.data[parent.app_data.sample_id], parent.app_data, parent.style_data, map_df)

@log_call(logger_key='Plot')
def plot_small_histogram(parent, data, app_data, style_data, current_plot_df):
    """Creates a small histogram on the Samples and Fields tab associated with the selected map

    Parameters
    ----------
    parent : QWidget
        The parent widget for the plot canvas.
    data : object
        Data object containing processed data, mask, and methods for retrieving map data.
    app_data : object
        Application data object containing settings such as color scale equalization and sample ID.
    style_data : object
        Plot style object providing colormap, normalization, and style dictionary.
    current_plot_df : pd.DataFrame
        DataFrame containing the current plot data, typically the map data for the selected field.

    Returns
    -------
    canvas : MplCanvas
        The Matplotlib canvas containing the plotted histogram.
    """
    #print('plot_small_histogram')
    # create Mpl canvas
    canvas = SimpleMplCanvas()

    # Histogram
    #remove by mask and drop rows with na
    mask = data.mask
    if style_data.cscale in ['log', 'logit', 'symlog']:
        mask = mask & current_plot_df['array'].notna() & (current_plot_df['array'] > 0)
    else:
        mask = mask & current_plot_df['array'].notna()

    array = current_plot_df['array'][mask].values

    logflag = False
    # check the analyte map cscale, the histogram needs to be the same
    if style_data.cscale == 'log':
        print('log scale')
        logflag = True
        if any(array <= 0):
            print(f"Warning issues with values <= 0, (-): {sum(array < 0)}, (0): {sum(array == 0)}")
            return

    bin_width = (np.nanmax(array) - np.nanmin(array)) / app_data._default_hist_num_bins
    edges = np.arange(np.nanmin(array), np.nanmax(array) + bin_width, bin_width)

    if sum(mask) != len(mask):
        canvas.axes.hist( 
            current_plot_df['array'], 
            bins=edges, 
            density=True, 
            color='#b3b3b3', 
            edgecolor=None, 
            linewidth=style_data.line_width, 
            log=logflag, 
            alpha=0.6, 
            label='unmasked' )

    _, _, patches = canvas.axes.hist(array,
            bins=edges,
            density=True,
            color=style_data.marker_color,
            edgecolor=None,
            linewidth=style_data.line_width,
            log=logflag,
            alpha=0.6 )

    # color histogram bins by analyte colormap?
    if parent.control_dock.preprocess.checkBoxShowHistCmap.isChecked():
        cmap = style_data.get_colormap()
        for j, p in enumerate(patches):
            p.set_facecolor(cmap(j / len(patches)))

    # Turn off axis box
    canvas.axes.spines['top'].set_visible(False)
    canvas.axes.spines['bottom'].set_visible(True)
    canvas.axes.spines['left'].set_visible(False)
    canvas.axes.spines['right'].set_visible(False)

    # Set ticks and labels labels
    canvas.axes.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)
    canvas.axes.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True, labelsize=8)
    canvas.axes.set_xlabel(style_data.clabel, fontdict={'size':8})

    # Size the histogram in the widget
    canvas.axes.margins(x=0)
    pos = canvas.axes.get_position()
    canvas.axes.set_position((pos.x0/2, 3*pos.y0, pos.width+pos.x0, pos.height-1.5*pos.y0))

    return canvas

def _plot_kde_overlay(ax, values, color, peak_label=True):
    """Overlays a Gaussian KDE curve on a density-normalized histogram axes.

    Matches MATLAB's ``grouphistogram.m`` KDE-plus-peak-marker behavior
    (``ksdensity`` there, ``scipy.stats.gaussian_kde`` here).
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2 or np.std(values) == 0:
        return
    try:
        kde = gaussian_kde(values)
    except Exception:
        return

    xs = np.linspace(values.min(), values.max(), 500)
    density = kde(xs)
    ax.plot(xs, density, color=color, linewidth=1.5, zorder=5)

    if peak_label:
        peak_idx = np.argmax(density)
        ax.scatter([xs[peak_idx]], [density[peak_idx]], color=color, zorder=6, s=20)
        ax.annotate(f'{xs[peak_idx]:.3g}', (xs[peak_idx], density[peak_idx]),
                     textcoords='offset points', xytext=(0, 6), fontsize=7,
                     color=color, ha='center')

@log_call(logger_key='Plot')
def plot_histogram(parent, data, app_data, style_data):
    """Plots a histogramn in the canvas window.

    Parameters
    ----------
    parent : QWidget
        The parent widget for the plot canvas.
    data : object
        Data object containing processed data, mask, and methods for retrieving map data.
    app_data : object
        Application data object containing settings such as color scale equalization and sample ID.
    style_data : object
        Plot style object providing colormap, normalization, and style dictionary.

    Returns
    -------
    canvas : MplCanvas
        The Matplotlib canvas containing the plotted histogram.
    """

    plot_data = None
    #print('plot histogram')
    # create Mpl canvas
    canvas = MplCanvas(parent=parent)

    nbins = int(app_data.hist_num_bins)

    #if analysis == 'Ratio':
    #    analyte_1 = field.split(' / ')[0]
    #    analyte_2 = field.split(' / ')[1]

    x = dict()
    if app_data.hist_plot_style == 'log-scaling' and app_data.c_field_type == 'Analyte':
        print('raw_data for log-scaling')
        scatter_data = get_scatter_data(data, app_data, style_data, processed=False)
        x = scatter_data['x'] if scatter_data and 'x' in scatter_data else None
    else:
        print('processed_data for histogram')
        scatter_data = get_scatter_data(data, app_data, style_data, processed=True)
        x = scatter_data['x'] if scatter_data and 'x' in scatter_data else None
    
    # Check if x data was successfully retrieved
    if x is None or 'array' not in x or x['array'] is None:
        print(f"Error: Unable to retrieve data for histogram. Field: {app_data.c_field}, Field Type: {app_data.c_field_type}")
        # Create empty canvas and return
        canvas = MplCanvas(parent=parent)
        canvas.plot_name = "error"
        return canvas, {}

    # determine edges
    xmin,xmax,xscale,xlbl = style_data.get_axis_values(data, x['field'])
    style_data.xlim = [xmin, xmax]
    style_data.xscale = xscale
    #if xscale == 'log':
    #    x['array'] = np.log10(x['array'])
    #    xmin = np.log10(xmin)
    #    xmax = np.log10(xmax)

    #bin_width = (xmax - xmin) / nbins
    #print(nbins)
    #print(bin_width)
    
    if (xscale == 'linear') or (xscale == 'scientific'):
        edges = np.linspace(xmin, xmax, nbins + 1)
    else:
        edges = np.linspace(10**xmin, 10**xmax, nbins + 1)

    #print(edges)

    # histogram style
    lw = style_data.line_width
    if lw > 0:
        htype = 'step'
    else:
        htype = 'bar'

    # CDF or PDF
    match app_data.hist_plot_style:
        case 'CDF':
            cumflag = True
        case _:
            cumflag = False

    # Check if the algorithm is in the current group and if results are available
    if app_data.c_field_type.lower() in ('cluster', 'roi') and app_data.c_field != '':
        if app_data.c_field_type.lower() == 'roi':
            # ROI groups are per-sample (see SampleObj.roi_stack), not a
            # global algorithm setting like cluster_dict -- populate the same
            # cluster_color/cluster_label/cluster_group/clusters names the
            # shared per-group loop below consumes either way. Ids aren't
            # guaranteed 0-based/contiguous (regions can be removed), so
            # remap to a dense 0..n-1 index matching get_roi_colormap's
            # stack-order color/label lists.
            cluster_color, cluster_label, _ = style_data.get_roi_colormap(data.roi_stack, alpha=style_data.marker_alpha)
            id_to_index = {r['id']: i for i, r in enumerate(data.roi_stack)}
            cluster_group = data.processed.loc[data.mask, 'ROI'].map(id_to_index)
            clusters = list(range(len(data.roi_stack)))
        else:
            method = app_data.c_field

            # Get the cluster labels for the data
            cluster_color, cluster_label, _ = style_data.get_cluster_colormap(app_data.cluster_dict[method],alpha=style_data.marker_alpha)
            # x['array']/etc. are already reduced to data.mask (see DataHandling.get_vector),
            # so cluster_group must be masked the same way or np.isin(...) below will size-mismatch.
            cluster_group = data.processed.loc[data.mask, method]
            clusters = app_data.cluster_dict[method]['selected_clusters']

            # fall back to all clusters when none are explicitly selected
            if not clusters:
                clusters = sorted(cluster_group.dropna().unique().astype(int).tolist())

        hist_dfs = []
        # Plot histogram for all clusters
        for i in clusters:
            cluster_data = x['array'][cluster_group == i]

            bar_color = cluster_color[int(i)]
            if htype == 'step':
                ecolor = bar_color
            else:
                ecolor = None

            if app_data.hist_plot_style != 'log-scaling' :
                plot_data = canvas.axes.hist( cluster_data,
                        cumulative=cumflag,
                        histtype=htype,
                        bins=edges,
                        color=bar_color, edgecolor=ecolor,
                        linewidth=lw,
                        label=cluster_label[int(i)],
                        alpha=style_data.marker_alpha/100,
                        density=True
                    )
                # plot_data: (n, bins, patches)
                counts, bin_edges, _ = plot_data
                if app_data.hist_show_kde and not cumflag:
                    _plot_kde_overlay(canvas.axes, cluster_data, bar_color)
                # Store histogram data for each cluster
                df = pd.DataFrame({
                    'bin_left': bin_edges[:-1],
                    'bin_right': bin_edges[1:],
                    'bin_center': 0.5 * (bin_edges[:-1] + bin_edges[1:]),
                    f'prob_{cluster_label[int(i)]}': counts
                })
                df['cluster'] = cluster_label[int(i)]
                hist_dfs.append(df)
            else:
                # Filter out NaN and zero values
                filtered_data = cluster_data[~np.isnan(cluster_data) & (cluster_data > 0)]

                # Sort the data in ascending order
                sorted_data = np.sort(filtered_data)

                # Calculate log(number of values > x)
                log_values = np.log10(sorted_data)
                log_counts = np.log10(len(sorted_data) - np.arange(len(sorted_data)))

                # Plot the data
                if lw == 0:
                    lw = 1
                canvas.axes.plot(
                    log_values,
                    log_counts,
                    label=cluster_label[int(i)],
                    color=bar_color,
                    lw=lw
                )
                
                # Store data
                df = pd.DataFrame({
                    'log_value': log_values,
                    'log_count': log_counts,
                    'cluster': cluster_label[int(i)]
                })
                hist_dfs.append(df)

        # Combine all clusters to one DataFrame
        if hist_dfs:
            canvas.data = pd.concat(hist_dfs, ignore_index=True)
        else:
            canvas.data = None
        # Add a legend
        add_colorbar(style_data, canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color, alpha=style_data.marker_alpha/100)
        #canvas.axes.legend()
    else:
        clusters = None
        # Regular histogram
        bar_color = style_data.marker_color
        if htype == 'step':
            ecolor = style_data.line_color
        else:
            ecolor = None

        if app_data.hist_plot_style != 'log-scaling' :
            plot_data = canvas.axes.hist( x['array'],
                    cumulative=cumflag,
                    histtype=htype,
                    bins=edges,
                    color=bar_color, edgecolor=ecolor,
                    linewidth=lw,
                    alpha=style_data.marker_alpha/100,
                    density=True
                )
            counts, bin_edges, _ = plot_data
            if app_data.hist_show_kde and not cumflag:
                _plot_kde_overlay(canvas.axes, x['array'], style_data.line_color or bar_color)
            canvas.data = pd.DataFrame({
                'bin_left': bin_edges[:-1],
                'bin_right': bin_edges[1:],
                'bin_center': 0.5 * (bin_edges[:-1] + bin_edges[1:]),
                'probability': counts
            })
        else:
            # Filter out NaN and zero values
            filtered_data = x['array'][~np.isnan(x['array']) & (x['array'] > 0)]

            # Sort the data in ascending order
            sorted_data = np.sort(filtered_data)

            # Calculate log(number of values > x)
            counts = len(sorted_data) - np.arange(len(sorted_data))

            # Plot the data
            if lw == 0:
                lw = 1
            canvas.axes.plot(
                sorted_data,
                counts,
                color=bar_color,
                lw=lw,
                alpha=style_data.marker_alpha/100)
            canvas.data = pd.DataFrame({
                'value': sorted_data,
                'count': counts
            })
    # axes
    # label font
    if 'font' == '':
        font = {'size':style_data.font}
    else:
        font = {'font':style_data.font, 'size':style_data.font_size}

    # set y-limits as p-axis min and max in data.processed.column_attributes
    if app_data.hist_plot_style != 'log-scaling' :
        pmin = data.processed.get_attribute(x['field'], 'p_min')
        pmax = data.processed.get_attribute(x['field'], 'p_max')
        if pmin is None or pmax is None:
            ymin, ymax = canvas.axes.get_ylim()
            data.processed.set_attribute(x['field'], 'p_min', fmt.oround(ymin,order=2,toward=0))
            data.processed.set_attribute(x['field'], 'p_max', fmt.oround(ymax,order=2,toward=1))
            style_data.set_axis_attributes('y', x['field'])

        # grab probablility axes limits
        _, _, _, _, ymin, ymax = style_data.get_axis_values(data, x['field'],ax='p')

        # x-axis
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        if xscale == 'log':
        #    parent.logax(canvas.axes, [xmin,xmax], axis='x', label=xlbl)
            canvas.axes.set_xscale(xscale,base=10)
        # if style_data.xscale == 'linear':
        # else:
        #     canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_xlim(xmin,xmax)

        if xscale == 'scientific':
            canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))

        # y-axis
        canvas.axes.set_ylabel(app_data.hist_plot_style, fontdict=font)
        # For CDF histograms, y-axis should be [0, 1]
        if app_data.hist_plot_style == 'CDF':
            canvas.axes.set_ylim(0, 1)
        else:
            canvas.axes.set_ylim(ymin,ymax)
    else:
        canvas.axes.set_xscale('log',base=10)
        canvas.axes.set_yscale('log',base=10)

        canvas.axes.set_xlabel(r"$\log_{10}($" + f"{app_data.x_field}" + r"$)$", fontdict=font)
        canvas.axes.set_ylabel(r"$\log_{10}(N > \log_{10}$" + f"{app_data.x_field}" + r"$)$", fontdict=font)

    canvas.axes.tick_params(labelsize=style_data.font_size,direction=style_data.tick_dir)
    canvas.axes.set_box_aspect(style_data.aspect_ratio)

    update_figure_font(canvas, style_data.font)

    canvas.fig.tight_layout()

    # Use x-axis fields for histogram (the actual data axis), changed from c-axis
    hist_field_type = app_data.x_field_type
    hist_field = app_data.x_field
    plot_name = hist_field_type + '_' + hist_field
    canvas.plot_name = plot_name

    plot_info = {
        'tree': 'Histogram',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'field_type': hist_field_type,
        'field': hist_field,
        'plot_type': style_data.plot_type,
        'type': app_data.hist_plot_style,
        'nbins': nbins,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': clusters,
        'view': [True, False],
        'position': [],
        'data': canvas.data
    }

    return canvas, plot_info

@log_call(logger_key='Plot')
def logax(ax, lim, axis='y', label='', tick_label_rotation=0):
    """
    Creates a logarithmic axis with tick marks and labels for a given axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes object to modify.
    lim : list or tuple
        The limits for the logarithmic axis, e.g., [1, 3] for 10^1 to 10^3.
    axis : str, optional
        The axis to apply the logarithmic scale to, either 'x' or 'y'.
        Defaults to 'y'.
    label : str, optional
        The label for the axis. If provided, it will be set as the axis label.
        Defaults to an empty string.
    tick_label_rotation : int, optional
        The rotation angle for the tick labels. Defaults to 0 (no rotation).
    """
    # Create tick marks and labels
    mt = np.log10(np.arange(1, 10))
    ticks = []
    tick_labels = []
    for i in range(int(lim[0]), int(lim[1]) + 1):
        ticks.extend([i + m for m in mt])
        tick_labels.extend([f'$10^{{{i}}}$'] + [''] * (len(mt) - 1))

    # Apply settings based on the axis
    if axis.lower() == 'x':
        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, rotation=tick_label_rotation)
        ax.set_xlim([10**lim[0], 10**lim[1]])
        if label:
            ax.set_xlabel(label)
    elif axis.lower() == 'y':
        ax.set_yticks(ticks)
        ax.set_yticklabels(tick_labels, rotation=tick_label_rotation)
        ax.set_ylim([10**lim[0], 10**lim[1]])
        if label:
            ax.set_ylabel(label)
    else:
        print('Incorrect axis argument. Please use "x" or "y".')

def add_colorbar(style_data, canvas, cax, cbartype='continuous', grouplabels=None, groupcolors=None, alpha=1):
    """Adds a colorbar to a MPL figure

    Parameters
    ----------
    style_data : StyleData
        StyleData object containing style settings for the plot.
    canvas : MplCanvas
        canvas object
    cax : axes
        color axes object
    cbartype : str
        Type of colorbar, ``dicrete`` or ``continuous``, Defaults to continuous
    grouplabels : list of str, optional
        category/group labels for tick marks
    groupcolors : list of str, optional
        List of colors for each group/category, used for discrete colorbars.
    alpha : float, optional
        Transparency of the colorbar, defaults to 1 (opaque).
    """
    #print("add_colorbar")
    # Add a colorbar
    cbar = None
    if style_data.cbar_dir == 'none':
        return

    # discrete colormap - plot as a legend
    if cbartype == 'discrete':

        if grouplabels is None or groupcolors is None:
            return

        # create patches for legend items
        p = [None]*len(grouplabels)
        for i, label in enumerate(grouplabels):
            p[i] = Patch(facecolor=groupcolors[i], edgecolor='#111111', linewidth=0.5, label=label)

        if style_data.cbar_dir == 'vertical':
            canvas.axes.legend(
                    handles=p,
                    handlelength=1,
                    loc='upper left',
                    bbox_to_anchor=(1.025,1),
                    fontsize=style_data.font_size,
                    frameon=False,
                    ncol=1
                )
        elif style_data.cbar_dir == 'horizontal':
            canvas.axes.legend(
                    handles=p,
                    handlelength=1,
                    loc='upper center',
                    bbox_to_anchor=(0.5,-0.1),
                    fontsize=style_data.font_size,
                    frameon=False,
                    ncol=3
                )
    # continuous colormap - plot with colorbar
    else:
        if style_data.cbar_dir == 'vertical':
            if style_data.plot_type == 'correlation':
                loc = 'left'
            else:
                loc = 'right'
            cbar = canvas.fig.colorbar( cax,
                    ax=canvas.axes,
                    orientation=style_data.cbar_dir,
                    location=loc,
                    shrink=0.62,
                    fraction=0.1,
                    alpha=alpha
                )
        elif style_data.cbar_dir == 'horizontal':
            cbar = canvas.fig.colorbar( cax,
                    ax=canvas.axes,
                    orientation=style_data.cbar_dir,
                    location='bottom',
                    shrink=0.62,
                    fraction=0.1,
                    alpha=alpha
                )
        else:
            # should never reach this point
            assert style_data.cbar_dir == 'none', "Colorbar direction is set to none, but is trying to generate anyway."
            return

        cbar.set_label(style_data.clabel, size=style_data.font_size)
        cbar.ax.tick_params(labelsize=style_data.font_size)
        cbar.set_alpha(alpha)

    # adjust tick marks if labels are given
    if cbartype == 'continuous' or grouplabels is None:
        ticks = None
    # elif cbartype == 'discrete':
    #     ticks = np.arange(0, len(grouplabels))
    #     cbar.set_ticks(ticks=ticks, labels=grouplabels, minor=False)
    #else:
    #    print('(add_colorbar) Unknown type: '+cbartype)

@log_call(logger_key='Plot')
def add_scalebar(data, app_data, style_data, ax):
    """Add a scalebar to a map

    Parameters
    ----------
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    ax : 
        Axes to place scalebar on.
    """        
    # add scalebar
    direction = style_data.scale_dir
    length = style_data.scale_length
    if (length is not None) and (direction != 'none'):
        if direction == 'horizontal':
            dd = data.dx
        else:
            dd = data.dy
        sb = scalebar( width=length,
                pixel_width=dd,
                units=app_data.preferences['Units']['Distance'],
                location=style_data.scale_location,
                orientation=direction,
                color=style_data.overlay_color,
                ax=ax )

        sb.create()
    else:
        return

@log_call(logger_key='Plot')
def plot_correlation(parent, data, app_data, style_data):
    """
    Creates an image of the correlation matrix.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the correlation plot.
    plot_info : dict
        Dictionary containing information about the plot, including the correlation matrix.
    """
    #print('plot_correlation')

    canvas = MplCanvas(parent=parent)
    canvas.axes.clear()

    # get the data for computing correlations
    df_filtered, analytes = data.get_processed_data()

    # Calculate the correlation matrix
    method = app_data.corr_method.lower()
    if app_data.cluster_method not in data.processed.columns:
        correlation_matrix = df_filtered.corr(method=method)
    else:
        algorithm = app_data.cluster_method
        cluster_group = data.processed.loc[:,algorithm]
        selected_clusters = app_data.cluster_dict[algorithm]['selected_clusters']

        ind = np.isin(cluster_group, selected_clusters)

        correlation_matrix = df_filtered[ind].corr(method=method)
    
    columns = correlation_matrix.columns

    font = {'size':style_data.font_size}

    # mask lower triangular matrix to show only upper triangle
    mask = np.zeros_like(correlation_matrix, dtype=bool)
    mask[np.tril_indices_from(mask)] = True
    correlation_matrix = np.ma.masked_where(mask, correlation_matrix)

    norm = style_data.color_norm()

    # plot correlation or correlation^2
    square_flag = app_data.corr_squared
    if square_flag:
        cax = canvas.axes.imshow(correlation_matrix**2, cmap=style_data.get_colormap(), norm=norm)
        canvas_array = correlation_matrix**2
    else:
        cax = canvas.axes.imshow(correlation_matrix, cmap=style_data.get_colormap(), norm=norm)
        canvas_array = correlation_matrix
        
    # store correlation_matrix to save_data if data needs to be exported
    canvas.data = pd.DataFrame(canvas_array, columns = columns, index = columns)

    canvas.axes.spines['top'].set_visible(False)
    canvas.axes.spines['bottom'].set_visible(False)
    canvas.axes.spines['left'].set_visible(False)
    canvas.axes.spines['right'].set_visible(False)

    # Add colorbar to the plot
    add_colorbar(style_data, canvas, cax)

    # set color limits
    cax.set_clim(style_data.clim[0], style_data.clim[1])

    # Set tick labels
    ticks = np.arange(len(columns))
    canvas.axes.tick_params(length=0, labelsize=8,
                    labelbottom=False, labeltop=True, labelleft=False, labelright=True,
                    bottom=False, top=True, left=False, right=True)

    canvas.axes.set_yticks(ticks, minor=False)
    canvas.axes.set_xticks(ticks, minor=False)

    labels = style_data.toggle_mineral_prefix(style_data.toggle_mass(columns))

    canvas.axes.set_xticklabels(labels, rotation=90, ha='center', va='bottom', fontproperties=font)
    canvas.axes.set_yticklabels(labels, ha='left', va='center', fontproperties=font)

    canvas.axes.set_title('')

    update_figure_font(canvas, style_data.font)

    if square_flag:
        plot_name = method+'_squared'
    else:
        plot_name = method

    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Correlation',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'correlation',
        'method': method,
        'square_flag': square_flag,
        'field_type': None,
        'field': None,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': canvas.data
    }

    return canvas, plot_info

 
@log_call(logger_key='Plot')
def get_scatter_data(data, app_data, style_data, processed=True):
    """
    Get data for scatter plots.

    This function retrieves the necessary data vectors for scatter plots based on the
    specified plot style and application settings. It constructs a dictionary containing
    vectors for the x, y, z, and c axes, which can be used for plotting scatter or heatmap
    visualizations.

    Parameters
    ----------
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    processed : bool, optional
        If True, use processed data; if False, use raw data. Defaults to True.

    Returns
    -------
    scatter_dict : dict
        Dictionary containing vectors for x, y, z, and c axes.
    """

    scatter_dict = {'x': {'type': None, 'field': None, 'label': None, 'array': None},
            'y': {'type': None, 'field': None, 'label': None, 'array': None},
            'z': {'type': None, 'field': None, 'label': None, 'array': None},
            'c': {'type': None, 'field': None, 'label': None, 'array': None}}

    match style_data.plot_type:
        case 'histogram':
            if processed or app_data.x_field_type != 'Analyte':
                scatter_dict['x'] = data.get_vector(app_data.x_field_type, app_data.x_field, norm=style_data.xscale)
            else:
                scatter_dict['x'] = data.get_vector(app_data.x_field_type, app_data.x_field, norm=style_data.xscale, processed=False)
        case 'dimension scatter' | 'dimension heatmap':
            scatter_dict['x'] = data.get_vector(app_data.x_field_type, app_data.x_field, norm=style_data.xscale)
            scatter_dict['y'] = data.get_vector(app_data.y_field_type, app_data.y_field, norm=style_data.yscale)
            if app_data.z_field_type and app_data.z_field and app_data.z_field.lower() not in ['', 'none']:
                scatter_dict['z'] = data.get_vector(app_data.z_field_type, app_data.z_field, norm=style_data.zscale)
            if app_data.c_field_type and app_data.c_field and app_data.c_field.lower() not in ['', 'none']:
                scatter_dict['c'] = data.get_vector(app_data.c_field_type, app_data.c_field, norm=style_data.cscale)
        case _:
            scatter_dict['x'] = data.get_vector(app_data.x_field_type, app_data.x_field, norm=style_data.xscale)
            scatter_dict['y'] = data.get_vector(app_data.y_field_type, app_data.y_field, norm=style_data.yscale)
            if app_data.z_field_type and app_data.z_field and app_data.z_field.lower() not in ['', 'none']:
                scatter_dict['z'] = data.get_vector(app_data.z_field_type, app_data.z_field, norm=style_data.zscale)
            if app_data.c_field_type and app_data.c_field and app_data.c_field.lower() not in ['', 'none']:
                scatter_dict['c'] = data.get_vector(app_data.c_field_type, app_data.c_field, norm=style_data.cscale)

    # set axes widgets
    if (scatter_dict['x']['field'] is not None) and (scatter_dict['y']['field'] != ''):
        if scatter_dict['x']['field'] not in data.processed.column_attributes:
            style_data.initialize_axis_values(data,scatter_dict['x']['type'], scatter_dict['x']['field'])
            style_data.set_axis_attributes(data,'x', scatter_dict['x']['field'])

    if (scatter_dict['y']['field'] is not None) and (scatter_dict['y']['field'] != ''):
        if scatter_dict['y']['field'] not in data.processed.column_attributes:
            style_data.initialize_axis_values(data,scatter_dict['y']['type'], scatter_dict['y']['field'])
            style_data.set_axis_attributes('y', scatter_dict['y']['field'])

    if (scatter_dict['z']['field'] is not None) and (scatter_dict['z']['field'] != ''):
        if scatter_dict['z']['field'] not in data.processed.column_attributes:
            style_data.initialize_axis_values(data,scatter_dict['z']['type'], scatter_dict['z']['field'])
            style_data.set_axis_attributes('z', scatter_dict['z']['field'])

    if (scatter_dict['c']['field'] is not None) and (scatter_dict['c']['field'] != ''):
        if scatter_dict['c']['field'] not in data.processed.column_attributes:
            style_data.set_color_axis_widgets()
            style_data.set_axis_attributes('c', scatter_dict['c']['field'])

    return scatter_dict

# -------------------------------------
# Scatter/Heatmap functions
# -------------------------------------
@log_call(logger_key='Plot')
def plot_scatter(parent, data, app_data, style_data, canvas=None):
    """Creates a plots from self.toolBox Scatter page.

    Creates both scatter and heatmaps (spatial histograms) for bi- and ternary plots.
    This function retrieves the necessary data vectors for scatter plots based on the
    specified plot style and application settings. It constructs a dictionary containing
    vectors for the x, y, z, and c axes, which can be used for plotting scatter or heatmap
    visualizations.

    Parameters
    ----------
    parent : QWidget
        The parent widget for the plot canvas.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    canvas : MplCanvas
        canvas within gui for plotting, by default ``None``

    Returns
    -------
    canvas : MplCanvas
        The Matplotlib canvas containing the plotted scatter or heatmap.
    plot_info : dict
        Dictionary containing information about the plot, including the x, y, z, and c data
        and the plot type.
    """
    #print('plot_scatter')
    plot_type = style_data.plot_type 

    # get data for plotting
    scatter_dict = get_scatter_data(data, app_data, style_data)
    if (scatter_dict['x']['field'] == '') or (scatter_dict['y']['field'] == '') \
        or scatter_dict['x']['field'] == scatter_dict['y']['field']:
        return

    plot_flag = False
    if canvas is None:
        plot_flag = True
        canvas = MplCanvas(parent=parent)

    match plot_type.split()[-1]:
        # scatter
        case 'scatter':
            if (scatter_dict['z']['field'] is None) or (scatter_dict['z']['field'] == '') \
                or scatter_dict['z']['field'] == scatter_dict['x']['field'] \
                or scatter_dict['z']['field'] == scatter_dict['y']['field']:
                # biplot
                plot_info = biplot(
                    canvas, data, app_data, style_data,
                    scatter_dict['x'],
                    scatter_dict['y'],
                    scatter_dict['c']
                )
            else:
                # ternary
                plot_info = ternary_scatter(
                    canvas, data, app_data, style_data,
                    scatter_dict['x'],
                    scatter_dict['y'],
                    scatter_dict['z'],
                    scatter_dict['c']
                )

        # heatmap
        case 'heatmap':
            # biplot
            if (scatter_dict['z']['field'] is None) or (scatter_dict['z']['field'] == ''):
                plot_info = hist2dbiplot(
                    canvas, data, app_data, style_data,
                    scatter_dict['x'],
                    scatter_dict['y']
                )
            # ternary
            else:
                plot_info = hist2dternplot(
                    canvas, data, app_data, style_data,
                    scatter_dict['x'],
                    scatter_dict['y'],
                    scatter_dict['z'],
                    scatter_dict['c']
                )

    canvas.axes.margins(x=0)

    if plot_flag:
        update_figure_font(canvas, style_data.font)

        return canvas, plot_info

@log_call(logger_key='Plot')
def biplot(canvas, data, app_data, style_data, x, y, c):
    """Creates scatter bi-plots

    A general function for creating scatter plots of 2-dimensions.

    Parameters
    ----------
    canvas : MplCanvas
        Canvas to be added to main window
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    x : dict
        Data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as x coordinate
    y : dict
        Data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as y coordinate
    c : dict
        Data associated with field ``MainWindow.comboBoxColorField.currentText()`` as marker colors

    Returns
    -------
    plot_info : dict
        Dictionary containing information about the plot, including the x, y, and c data
        and the plot type.
    """
    if (c['field'] is None) or (c['field'] == ''):
        # single color
        canvas.axes.scatter(x['array'], y['array'], c=style_data.marker_color,
            s=style_data.marker_size,
            marker=style_data.marker_dict[style_data.marker],
            edgecolors='none',
            alpha=style_data.marker_alpha/100)
        cb = None
        
        plot_data = pd.DataFrame(np.vstack((x['array'], y['array'])).T, columns = ['x','y'])

    elif app_data.c_field_type.lower() == 'cluster':
        # color by cluster
        method = app_data.c_field
        if method not in app_data.cluster_dict:
            return
        else:
            if 0 not in app_data.cluster_dict[method]:
                return

        cluster_color, cluster_label, cmap = style_data.get_cluster_colormap(app_data.cluster_dict[method],alpha=style_data.marker_alpha)
        # x['array']/etc. are already reduced to data.mask (see DataHandling.get_vector),
        # so cluster_group must be masked the same way or np.isin(...) below will size-mismatch.
        cluster_group = data.processed.loc[data.mask, method]
        selected_clusters = app_data.cluster_dict[method]['selected_clusters']

        ind = np.isin(cluster_group, selected_clusters)

        # actual non-mask cluster count, not cluster_dict[method]['n_clusters']
        # (k-means/fuzzy c-means' requested-k setting -- HDBSCAN has no such key
        # at all; see StyleToolbox.get_cluster_colormap's identical fix for why)
        n_clusters_actual = len([k for k in app_data.cluster_dict[method].keys() if isinstance(k, int) and k != 99])
        norm = style_data.color_norm(n_clusters_actual)

        cb = canvas.axes.scatter(x['array'][ind], y['array'][ind], c=c['array'][ind],
            s=style_data.marker_size,
            marker=style_data.marker_dict[style_data.marker],
            edgecolors='none',
            cmap=cmap,
            alpha=style_data.marker_alpha/100,
            norm=norm)

        add_colorbar(style_data, canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
        plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], c['array'][ind], cluster_group[ind])).T, columns = ['x','y','c','cluster_group'])
    elif app_data.c_field_type.lower() == 'roi':
        # color by ROI (see SampleObj.roi_stack). Ids aren't guaranteed
        # 0-based/contiguous (regions can be removed), so remap to a dense
        # 0..n-1 index matching get_roi_colormap's stack-order color/label
        # lists, and use that remapped series as the color value directly
        # (rather than c['array'], which would still hold raw, possibly
        # sparse ids).
        if not data.roi_stack:
            return

        cluster_color, cluster_label, cmap = style_data.get_roi_colormap(data.roi_stack, alpha=style_data.marker_alpha)
        id_to_index = {r['id']: i for i, r in enumerate(data.roi_stack)}
        roi_group = data.processed.loc[data.mask, 'ROI'].map(id_to_index)
        selected = [id_to_index[i] for i in data.selected_rois if i in id_to_index] or list(range(len(data.roi_stack)))

        ind = np.isin(roi_group, selected)

        norm = style_data.color_norm(len(data.roi_stack))

        cb = canvas.axes.scatter(x['array'][ind], y['array'][ind], c=roi_group[ind],
            s=style_data.marker_size,
            marker=style_data.marker_dict[style_data.marker],
            edgecolors='none',
            cmap=cmap,
            alpha=style_data.marker_alpha/100,
            norm=norm)

        add_colorbar(style_data, canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
        plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], roi_group[ind], roi_group[ind])).T, columns = ['x','y','c','roi_group'])
    else:
        # color by field
        norm = style_data.color_norm()
        cb = canvas.axes.scatter(x['array'], y['array'], c=c['array'],
            s=style_data.marker_size,
            marker=style_data.marker_dict[style_data.marker],
            edgecolors='none',
            cmap=style_data.get_colormap(),
            alpha=style_data.marker_alpha/100,
            norm=norm)

        add_colorbar(style_data,canvas, cb)
        plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])
        

    # axes
    xmin, xmax, xscale, xlbl = style_data.get_axis_values(data, x['field'])
    ymin, ymax, yscale, ylbl = style_data.get_axis_values(data, y['field'])

    # labels
    font = {'size':style_data.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)
    canvas.axes.set_ylabel(ylbl, fontdict=font)

    # axes limits
    canvas.axes.set_xlim(xmin,xmax)
    canvas.axes.set_ylim(ymin,ymax)

    # tick marks
    canvas.axes.tick_params(direction=style_data.tick_dir,
        labelsize=style_data.font_size,
        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
        bottom=True, top=True, left=True, right=True)

    # aspect ratio
    canvas.axes.set_box_aspect(style_data.aspect_ratio)
    canvas.fig.tight_layout()

    if xscale == 'log':
        canvas.axes.set_xscale(xscale,base=10)
    if yscale == 'log':
        canvas.axes.set_yscale(yscale,base=10)

    if xscale == 'scientific':
        canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
    if yscale == 'scientific':
        canvas.axes.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

    plot_name = f"{x['field']}_{y['field']}_{'scatter'}"
    canvas.data = plot_data
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'scatter',
        'field_type': [x['type'], y['type'], '', c['type']],
        'field': [x['field'], y['field'], '', c['field']],
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data':  plot_data
    }

    return plot_info

@log_call(logger_key='Plot')
def plot_isochron(parent, data, app_data, style_data):
    """Plots multi-cluster Lu-Hf isochrons: a normal-space panel and an
    inverse-space panel, each showing cluster-colored pixel data, isochron
    reference lines (``geochronology.plot_isochron_lines``), and per-cluster
    Monte Carlo isochron fits.

    Reads fit results cached by
    ``Geochronology.compute_multipixel_isochron()`` (the Geochronology dock)
    rather than recomputing the Monte Carlo simulation on every redraw --
    click "Multi-pixel isochron" there first.

    Parameters
    ----------
    parent : MainWindow
        Needed (unlike most plot functions) to reach the Geochronology dock's
        cached fit results via ``parent.geochron_dock``.
    """
    # local import: avoids a module-load cycle with geochronology.py, which
    # imports FieldLogic.py (GeochronDock mixes in FieldLogicUI), which in
    # turn imports this module
    from src.common.geochronology import LU_HF, plot_isochron_lines

    geochron_dock = getattr(parent, 'geochron_dock', None)
    geochron = getattr(geochron_dock, 'geochron', None) if geochron_dock else None
    results = getattr(geochron, '_last_results', None) if geochron else None

    canvas = MplCanvas(parent=parent, sub=121, width=9, height=4.5)

    if not results or not results.get('clusters'):
        canvas.axes.text(0.5, 0.5,
            "Use the Geochronology dock's 'Multi-pixel isochron'\nbutton to compute a fit first.",
            ha='center', va='center', transform=canvas.axes.transAxes)
        canvas.axes.set_axis_off()
        canvas.plot_name = 'isochron'
        canvas.data = None
        plot_info = {
            'tree': 'Geochemistry', 'sample_id': app_data.sample_id, 'plot_name': 'isochron',
            'plot_type': 'isochron', 'field_type': ['', '', '', ''], 'field': ['', '', '', ''],
            'figure': canvas, 'style': style_data.style_dict.get('isochron', {}),
            'cluster_groups': [], 'view': [True, False], 'position': [], 'data': None,
        }
        return canvas, plot_info

    ax_normal = canvas.axes
    ax_inv = canvas.fig.add_subplot(122)

    cluster_method = results['cluster_method']
    cluster_color, cluster_label, _ = style_data.get_cluster_colormap(
        app_data.cluster_dict[cluster_method], alpha=style_data.marker_alpha)

    def _plot_cluster(ax, res, color, label, xs_all, ys_all):
        if 'error' in res or len(res.get('x', [])) == 0:
            return
        ax.scatter(res['x'], res['y'], s=style_data.marker_size, color=color,
                   alpha=style_data.marker_alpha / 100, edgecolors='none', label=label)
        xs_all.extend(res['x'])
        ys_all.extend(res['y'])
        if np.isfinite(res.get('age_mean', np.nan)):
            xs = np.array([np.min(res['x']), np.max(res['x'])])
            ys = res['intercept'] + xs * res['slope']
            ax.plot(xs, ys, color=color, linewidth=1.8)
            ax.annotate(f"{label}: {res['age_mean']:.0f}±{res['age_std']:.0f} Ma",
                        (xs[-1], ys[-1]), textcoords='offset points', xytext=(-4, 4),
                        fontsize=7, color=color, ha='right')

    all_x_normal, all_y_normal, all_x_inv, all_y_inv = [], [], [], []
    for c, r in results['clusters'].items():
        color = cluster_color[int(c)] if int(c) < len(cluster_color) else style_data.marker_color
        label = cluster_label[int(c)] if int(c) < len(cluster_label) else str(c)
        _plot_cluster(ax_normal, r['normal'], color, label, all_x_normal, all_y_normal)
        _plot_cluster(ax_inv, r['inverse'], color, label, all_x_inv, all_y_inv)

    decay_const = None
    dt = geochron_dock
    if dt is not None:
        try:
            decay_const = dt.lineEditDecayConstant.value
        except Exception:
            decay_const = None

    if all_x_normal:
        ax_normal.set_xlim(0, np.quantile(all_x_normal, 0.995))
        ax_normal.set_ylim(0, np.quantile(all_y_normal, 0.995))
    plot_isochron_lines(ax_normal, 'normal', intercept=LU_HF['Hf176_Hf177_i'], decay_const=decay_const)
    ax_normal.set_xlabel('$^{176}$Lu/$^{177}$Hf')
    ax_normal.set_ylabel('$^{176}$Hf/$^{177}$Hf')
    ax_normal.set_title('Normal isochron', fontsize=style_data.font_size)
    ax_normal.tick_params(direction=style_data.tick_dir)

    if all_x_inv:
        ax_inv.set_xlim(0, np.quantile(all_x_inv, 0.995))
        ax_inv.set_ylim(0, 4)
    plot_isochron_lines(ax_inv, 'inverse', intercept=1.0 / LU_HF['Hf176_Hf177_i'], decay_const=decay_const)
    ax_inv.set_xlabel('$^{176}$Lu/$^{176}$Hf')
    ax_inv.set_ylabel('$^{177}$Hf/$^{176}$Hf')
    ax_inv.set_title('Inverse isochron', fontsize=style_data.font_size)
    ax_inv.tick_params(direction=style_data.tick_dir)

    canvas.fig.tight_layout()

    plot_name = f"isochron_{cluster_method}"
    plot_data = pd.DataFrame({'x_normal': all_x_normal, 'y_normal': all_y_normal}) if all_x_normal else None
    canvas.data = plot_data
    canvas.plot_name = plot_name

    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'isochron',
        'field_type': ['Ratio', 'Ratio', '', 'Cluster'],
        'field': ['isochron', 'isochron', '', cluster_method],
        'figure': canvas,
        'style': style_data.style_dict.get('isochron', {}),
        'cluster_groups': list(results['clusters'].keys()),
        'view': [True, False],
        'position': [],
        'data': plot_data,
    }
    return canvas, plot_info

@log_call(logger_key='Plot')
def ternary_scatter(canvas, data, app_data, style_data, x, y, z, c):
    """Creates ternary scatter plots

    A general function for creating ternary scatter plots.

    Parameters
    ----------
    canvas : MplCanvas
        Canvas that contains axes and figure
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    x : dict
        coordinate associated with top vertex
    y : dict
        coordinate associated with left vertex
    z : dict
        coordinate associated with right vertex
    c : dict
        color dimension

    Returns
    -------
    plot_info : dict
        Dictionary containing information about the plot, including the x, y, z, and c data
        and the plot type.
    """
    labels = [x['field'], y['field'], z['field']]
    tp = ternary(canvas.axes, labels, 'scatter')

    plot_data = pd.DataFrame()
    if (c['field'] is None) or (c['field'] == ''):
        tp.ternscatter( x['array'], y['array'], z['array'],
                marker=style_data.marker_dict[style_data.marker],
                size=style_data.marker_size,
                color=style_data.marker_color,
                alpha=style_data.marker_alpha/100,
            )
        cb = None
        plot_data = pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])

    elif app_data.c_field_type.lower() == 'cluster':
        # color by cluster
        method = app_data.c_field
        if method not in app_data.cluster_dict:
            return
        else:
            if 0 not in app_data.cluster_dict[method]:
                return

        cluster_color, cluster_label, cmap = style_data.get_cluster_colormap(app_data.cluster_dict[method],alpha=style_data.marker_alpha)
        # x['array']/etc. are already reduced to data.mask (see DataHandling.get_vector),
        # so cluster_group must be masked the same way or np.isin(...) below will size-mismatch.
        cluster_group = data.processed.loc[data.mask, method]
        selected_clusters = app_data.cluster_dict[method]['selected_clusters']

        ind = np.isin(cluster_group, selected_clusters)

        # actual non-mask cluster count, not cluster_dict[method]['n_clusters']
        # (k-means/fuzzy c-means' requested-k setting -- HDBSCAN has no such key
        # at all; see StyleToolbox.get_cluster_colormap's identical fix for why)
        n_clusters_actual = len([k for k in app_data.cluster_dict[method].keys() if isinstance(k, int) and k != 99])
        norm = style_data.color_norm(n_clusters_actual)

        _, cb = tp.ternscatter(
            x['array'][ind], y['array'][ind], z['array'][ind],
            categories=c['array'][ind],
            marker=style_data.marker_dict[style_data.marker],
            size=style_data.marker_size,
            cmap=cmap,
            norm=norm,
            labels=True,
            alpha=style_data.marker_alpha/100,
            orientation='None'
        )

        add_colorbar(style_data, canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
        plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], z['array'][ind], cluster_group[ind])).T, columns = ['x','y','z','cluster_group'])
    elif app_data.c_field_type.lower() == 'roi':
        # color by ROI -- see the scatter-plot ROI branch above for why ids
        # are remapped to a dense 0..n-1 index before use as color values.
        if not data.roi_stack:
            return

        cluster_color, cluster_label, cmap = style_data.get_roi_colormap(data.roi_stack, alpha=style_data.marker_alpha)
        id_to_index = {r['id']: i for i, r in enumerate(data.roi_stack)}
        roi_group = data.processed.loc[data.mask, 'ROI'].map(id_to_index)
        selected = [id_to_index[i] for i in data.selected_rois if i in id_to_index] or list(range(len(data.roi_stack)))

        ind = np.isin(roi_group, selected)

        norm = style_data.color_norm(len(data.roi_stack))

        _, cb = tp.ternscatter(
            x['array'][ind], y['array'][ind], z['array'][ind],
            categories=roi_group[ind],
            marker=style_data.marker_dict[style_data.marker],
            size=style_data.marker_size,
            cmap=cmap,
            norm=norm,
            labels=True,
            alpha=style_data.marker_alpha/100,
            orientation='None'
        )

        add_colorbar(style_data, canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
        plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], z['array'][ind], roi_group[ind])).T, columns = ['x','y','z','roi_group'])
    else:
        # color field
        norm = style_data.color_norm()
        _, cb = tp.ternscatter(x['array'], y['array'], z['array'],
                categories=c['array'],
                marker=style_data.marker_dict[style_data.marker],
                size=style_data.marker_size,
                cmap=style_data.cmap,
                norm=norm,
                alpha=style_data.marker_alpha/100,
                orientation=style_data.cbar_dir )
        
        if cb:
            cb.set_label(c['label'])
            plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])

    # axes limits
    canvas.axes.set_xlim(-1.01,1.01)
    canvas.axes.set_ylim(-0.01,1)
    canvas.data = plot_data
    plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'ternscatter'}"
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'scatter',
        'field_type': [x['type'], y['type'], z['type'], c['type']],
        'field': [x['field'], y['field'], z['field'], c['field']],
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': plot_data
    }

    return plot_info

@log_call(logger_key='Plot')
def hist2dbiplot(canvas, data, app_data, style_data, x, y):
    """Creates 2D histogram figure

    A general function for creating 2D histograms (heatmaps).

    Parameters
    ----------
    canvas : MplCanvas
        plotting canvas
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    x : dict
        X-axis dictionary
    y : dict
        Y-axis dictionary

    Returns
    -------
    plot_info : dict
        Dictionary containing information about the plot, including the x and y data
        and the plot type.
    """
    # color by field
    norm = style_data.color_norm()
    h = canvas.axes.hist2d(x['array'], y['array'], bins=style_data.resolution, norm=norm, cmap=style_data.get_colormap())
    add_colorbar(style_data, canvas, h[3])

    # axes
    xmin, xmax, xscale, xlbl = style_data.get_axis_values(data, x['field'])
    ymin, ymax, yscale, ylbl = style_data.get_axis_values(data, y['field'])

    # labels
    font = {'size':style_data.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)
    canvas.axes.set_ylabel(ylbl, fontdict=font)

    # axes limits
    canvas.axes.set_xlim(xmin,xmax)
    canvas.axes.set_ylim(ymin,ymax)

    if yscale == 'scientific':
        canvas.axes.ticklabel_format(axis='y', style=yscale)
    if yscale == 'scientific':
        canvas.axes.ticklabel_format(axis='y', style=yscale)

    # tick marks
    canvas.axes.tick_params(direction=style_data.tick_dir,
                    labelsize=style_data.font_size,
                    labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                    bottom=True, top=True, left=True, right=True)

    # aspect ratio
    canvas.axes.set_box_aspect(style_data.aspect_ratio)

    if xscale == 'log':
        canvas.axes.set_xscale(xscale,base=10)
    if yscale == 'log':
        canvas.axes.set_yscale(yscale,base=10)

    if xscale == 'scientific':
        canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
    if yscale == 'scientific':
        canvas.axes.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

    plot_name = f"{x['field']}_{y['field']}_{'heatmap'}"
    canvas.data = pd.DataFrame(np.vstack((x['array'],y['array'])).T, columns = ['x','y'])
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'heatmap',
        'field_type': [x['type'], y['type'], '', ''],
        'field': [x['field'], y['field'], '', ''],
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': canvas.data
    }

    return plot_info

@log_call(logger_key='Plot')
def hist2dternplot(canvas, data, app_data, style_data, x, y, z, c):
    """Creates a ternary histogram figure

    A general function for creating scatter plots of 2-dimensions.

    Parameters
    ----------
    canvas : MplCanvas
        Canvas that contains axes and figure
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    x, y, z : dict
        Coordinates associated with top, left and right vertices, respectively
    c : str
        Display, mean, median, standard deviation plots for a fourth dimension in
        addition to histogram map. Default is None, which produces a histogram.
    """
    labels = [x['field'], y['field'], z['field']]

    if (c['field'] is None) or (c['field'] == ''):
        tp = ternary(canvas.axes, labels, 'heatmap')

        norm = style_data.color_norm()
        hexbin_df, cb = tp.ternhex(a=x['array'], b=y['array'], c=z['array'],
            bins=style_data.resolution,
            plotfield='n',
            cmap=style_data.cmap,
            orientation=style_data.cbar_dir,
            norm=norm)

        if cb is not None:
            cb.set_label('log(N)')
    else:
        pass
        # axs = fig.subplot_mosaic([['left','upper right'],['left','lower right']], layout='constrained', width_ratios=[1.5, 1])

        # for idx, ax in enumerate(axs):
        #     tps[idx] = ternary(ax, labels, 'heatmap')

        # hexbin_df = ternary.ternhex(a=x['array'], b=y['array'], c=z['array'], val=c['array'], bins=style_data.resolution)

        # cb.set_label(c['label'])

        # #tp.ternhex(hexbin_df=hexbin_df, plotfield='n', cmap=plot_style.cmap, orientation='vertical')
    canvas.data = pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
    plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'heatmap'}"
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'heatmap',
        'field_type': [x['type'], y['type'], z['type'], ''],
        'field': [x['field'], y['field'], z['field'], ''],
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data' : canvas.data
    }

    return plot_info

@log_call(logger_key='Plot')
def plot_ternary_map(parent, data, app_data, style_data):
    """
    Creates map colored by ternary coordinate positions.

    This function generates a ternary map plot using the specified x, y, and z fields from the
    processed data. It uses the ternary library to create a ternary plot and displays it
    on a Matplotlib canvas. The plot is styled according to the provided StyleData object.
    
    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the ternary map plot.
    plot_info : dict
        Dictionary containing information about the plot, including the x, y, z fields and the plot type.
    """
    if style_data.plot_type != 'ternary map':
        app_data.plot_type = 'ternary map'
        style_data.set_style_widgets('ternary map')

    canvas = MplCanvas(sub=121, parent=parent)

    afield = app_data.x_field
    bfield = app_data.y_field
    cfield = app_data.z_field

    a = data.processed.loc[:,afield].values
    b = data.processed.loc[:,bfield].values
    c = data.processed.loc[:,cfield].values

    # Convert hex colors to RGB for ternary plotting
    ca = convert_color(style_data.ternary_color_x, 'hex', 'rgb', norm_out=False) or [255, 0, 0]  # Red fallback
    cb = convert_color(style_data.ternary_color_y, 'hex', 'rgb', norm_out=False) or [0, 255, 0]  # Green fallback
    cc = convert_color(style_data.ternary_color_z, 'hex', 'rgb', norm_out=False) or [0, 0, 255]  # Blue fallback
    
    # Handle center color - if 'none', use empty list as required by terncolor
    if style_data.ternary_color_m == 'none':
        cm = []  # Empty list for no center color
    else:
        cm = convert_color(style_data.ternary_color_m, 'hex', 'rgb', norm_out=False) or [128, 128, 128]  # Gray fallback

    t = ternary(canvas.axes)

    cval = t.terncolor(a, b, c, ca, cb, cc, cp=cm)

    M, N = data.array_size

    # Reshape the array into MxNx3
    map_data = np.zeros((M, N, 3), dtype=np.uint8)
    map_data[:len(cval), :, :] = cval.reshape(M, N, 3, order=data.order)

    aspect_ratio = style_data.aspect_ratio if style_data.aspect_ratio is not None else data.aspect_ratio
    canvas.axes.imshow(map_data, aspect=aspect_ratio)
    canvas.data = pd.DataFrame(map_data.reshape(M*N,3), columns = ['x','y','z'])

    # add scalebar
    add_scalebar(data, app_data, style_data, canvas.axes)

    grid = None
    if style_data.cbar_dir == 'vertical':
        grid = gs.GridSpec(5,1)
    elif style_data.cbar_dir == 'horizontal':
        grid = gs.GridSpec(1,5)
    else:
        return canvas, None

    canvas.axes.set_position(grid[0:4].get_position(canvas.fig))
    canvas.axes.set_subplotspec(grid[0:4])              # only necessary if using tight_layout()

    canvas.axes2 = canvas.fig.add_subplot(grid[4])

    canvas.fig.tight_layout()

    t2 = ternary(canvas.axes2, labels=[afield,bfield,cfield])

    hbin = t2.hexagon(10)
    xc = np.array([v['xc'] for v in hbin])
    yc = np.array([v['yc'] for v in hbin])
    at,bt,ct = t2.xy2tern(xc,yc)
    cv = t2.terncolor(at,bt,ct, ca=ca, cb=cb, cc=cc, cp=cm)
    for i, hb in enumerate(hbin):
        t2.ax.fill(hb['xv'], hb['yv'], color=cv[i]/255, edgecolor='none')

    plot_name = f'{afield}_{bfield}_{cfield}_ternarymap'
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'ternary map',
        'field_type': [app_data.x_field, app_data.y_field, app_data.z_field, ''],
        'field': [afield, bfield, cfield, ''],
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': canvas.data
    }

    return canvas, plot_info

# -------------------------------------
# TEC and Radar plots
# -------------------------------------
@log_call(logger_key='Plot')
def plot_ndim(parent, data, app_data, style_data):
    """Produces trace element compatibility (TEC) and Radar plots
    
    Geochemical TEC diagrams are a staple of geochemical analysis, often referred to as spider
    diagrams, which display a set of elements arranged by compatibility.  Radar plots show
    data displayed on a set of radial spokes (axes), giving the appearance of a radar screen
    or spider web.
    
    The function updates ``MainWindow.plot_info`` with the displayed plot metadata and figure
    ``MplCanvas`` for display in the centralWidget views.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the TEC or Radar plot.
    plot_info : dict
        Dictionary containing information about the plot, including the fields and plot type.
    """
    if not app_data.ndim_list:
        return None, None

    # Deliberately not data.get_processed_data(): that pulls each field's own
    # display-scale setting ('norm', e.g. 'log' for a field the user set to log
    # scale on the Field Map view), so a sample with mixed per-field scales would
    # come back with some elements already log10-transformed and others not.
    # TEC/radar need physically consistent raw concentrations across every
    # element -- plot_spider_norm applies its own log10 transform uniformly as
    # part of the reference normalization -- so fetch every ndim_list field at a
    # fixed, explicit linear scale here instead.
    df_filtered = pd.DataFrame(
        {field: data.get_map_data(field, field_type='Analyte', norm='linear')['array'].values
         for field in app_data.ndim_list},
        index=data.processed.index,
    )
    df_filtered = df_filtered[data.mask]

    ref_i = app_data.ref_index

    plot_type = style_data.plot_type
    plot_data = None

    # Get quantile for plotting TEC & radar plots
    quantiles = app_data.ndim_quantiles[app_data.ndim_quantile_index]
    # match app_data.ndim_quantile_index:
    #     case 0:
    #         quantiles = [0.5]
    #     case 1:
    #         quantiles = [0.25, 0.75]
    #     case 2:
    #         quantiles = [0.25, 0.5, 0.75]
    #     case 3:
    #         quantiles = [0.05, 0.25, 0.5, 0.75, 0.95]

    # remove mass from labels
    if style_data.show_mass:
        angle = 45
    else:
        angle = 0
    labels = style_data.toggle_mass(app_data.ndim_list)
        
    clusters = []
    cluster_color = []
    cluster_label = []
    id_to_index = {}  # ROI-only: remap raw (possibly sparse) ids to a dense 0..n-1 index
    if app_data.c_field_type.lower() == 'cluster' and app_data.c_field != '':
        method = app_data.c_field
        cluster_dict = app_data.cluster_dict[method]
        cluster_color, cluster_label, cmap = style_data.get_cluster_colormap(cluster_dict, alpha=style_data.marker_alpha)

        clusters = cluster_dict['selected_clusters']
        if 0 in cluster_dict:
            cluster_flag = True
        else:
            cluster_dict = None
            cluster_flag = False
            print(f'No cluster data found for {method}, recompute?')
    elif app_data.c_field_type.lower() == 'roi' and app_data.c_field != '' and data.roi_stack:
        # ROI groups are per-sample (see SampleObj.roi_stack), not a global
        # algorithm setting like cluster_dict. `method` stays 'ROI' (the
        # actual column name in data.processed), but the group values used
        # below are remapped via id_to_index since raw ROI ids aren't
        # guaranteed 0-based/contiguous the way cluster labels are.
        method = 'ROI'
        cluster_dict = None
        cluster_color, cluster_label, cmap = style_data.get_roi_colormap(data.roi_stack, alpha=style_data.marker_alpha)
        id_to_index = {r['id']: i for i, r in enumerate(data.roi_stack)}
        clusters = [id_to_index[i] for i in data.selected_rois if i in id_to_index] or list(range(len(data.roi_stack)))
        cluster_flag = True
    else:
        cluster_dict = None
        cluster_flag = False

    
    canvas = MplCanvas(parent=parent)

    match plot_type:
        case 'radar':
            n_ticks = 5

            if cluster_flag and method in data.processed.columns:
                # Get the cluster labels for the data
                cluster_group = data.processed[method][data.mask]
                if id_to_index:
                    cluster_group = cluster_group.map(id_to_index)

                df_filtered['clusters'] = cluster_group
                df_filtered = df_filtered[df_filtered['clusters'].isin(clusters)]

                prep = radar_prep(df_filtered, fields=app_data.ndim_list,
                                   group_field='clusters', groups=clusters,
                                   quantiles=quantiles)

                # cluster_color/cluster_label are indexed by cluster id
                # (0..n_clusters-1, plus a trailing entry for id 99, the
                # "mask"/other cluster) -- not by position in `clusters`,
                # which may be a non-contiguous subset of selected ids.
                def _cluster_style(g):
                    idx = int(g)
                    if idx == 99 or idx >= len(cluster_color):
                        return cluster_color[-1], cluster_label[-1]
                    return cluster_color[idx], cluster_label[idx]

                styles = [_cluster_style(g) for g in clusters]
                # Swap in display names for the legend; radar_prep's `groups`
                # (raw cluster ids) already did their job selecting rows above.
                prep['groups'] = [lbl for _, lbl in styles]

                radarplot(**prep, ax=canvas.axes, axis_labels=labels,
                          n_ticks=n_ticks, colors=[c for c, _ in styles])
            else:
                prep = radar_prep(df_filtered, fields=app_data.ndim_list,
                                   group_field=None, quantiles=quantiles)
                radarplot(**prep, ax=canvas.axes, axis_labels=labels, n_ticks=n_ticks)

            canvas.fig.tight_layout()

            # Long-form table (group/field/quantile/value) -- robust to any
            # group/quantile count and always 2-D, unlike the raw (n_groups,
            # n_fields[, n_quantiles]) array in prep['vals'].
            p_vals, p_fields, p_groups, p_quantiles = (
                prep['vals'], prep['fields'], prep['groups'], prep['quantiles']
            )
            if p_vals.ndim == 2:
                p_vals = p_vals[:, :, np.newaxis]
                p_quantiles = [None]
            plot_data = pd.DataFrame([
                {'group': g, 'field': f, 'quantile': q, 'value': p_vals[gi, fi, qi]}
                for gi, g in enumerate(p_groups)
                for fi, f in enumerate(p_fields)
                for qi, q in enumerate(p_quantiles)
            ])

        case 'TEC':
            yl = [np.inf, -np.inf]
            if cluster_flag and method in data.processed.columns:
                # Get the cluster labels for the data
                cluster_group = data.processed[method][data.mask]
                if id_to_index:
                    cluster_group = cluster_group.map(id_to_index)

                df_filtered['clusters'] = cluster_group

                # Plot tec for all clusters
                for i in clusters:
                    # Create RGBA color
                    #print(f'Cluster {i}')
                    canvas.axes, yl_tmp, _ = plot_spider_norm(
                            data=df_filtered.loc[df_filtered['clusters']==i,:],
                            ref_data=app_data.ref_data, norm_ref_data=app_data.ref_data['model'][ref_i],
                            layer=app_data.ref_data['layer'][ref_i], el_list=app_data.ndim_list ,
                            style='Quanta', quantiles=quantiles, ax=canvas.axes, c=cluster_color[int(i)], label=cluster_label[int(i)]
                        )
                    #store max y limit to convert the set y limit of axis
                    yl = [np.floor(np.nanmin([yl[0] , yl_tmp[0]])), np.ceil(np.nanmax([yl[1] , yl_tmp[1]]))]

                # Put a legend below current axis
                box = canvas.axes.get_position()
                canvas.axes.set_position((box.x0, box.y0 - box.height * 0.1, box.width, box.height * 0.9))

                add_colorbar(style_data, canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
                #canvas.axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, handlelength=1)

                logax(canvas.axes, yl, 'y')
                canvas.axes.set_ylim(yl)

                canvas.axes.set_xticklabels(labels, rotation=angle)
            else:
                canvas.axes, yl, plot_data = plot_spider_norm(data=df_filtered, ref_data=app_data.ref_data, norm_ref_data=app_data.ref_data['model'][ref_i], layer=app_data.ref_data['layer'][ref_i], el_list=app_data.ndim_list, style='Quanta', quantiles=quantiles, ax=canvas.axes)

                canvas.axes.set_xticklabels(labels, rotation=angle)
            canvas.axes.set_ylabel(f"Abundance / [{app_data.ref_data['model'][ref_i]}, {app_data.ref_data['layer'][ref_i]}]")
            canvas.fig.tight_layout()

    if cluster_flag:
        plot_name = f"{plot_type}_"
    else:
        plot_name = f"{plot_type}_all"

    update_figure_font(canvas, style_data.font)
    canvas.data = pd.DataFrame(plot_data)
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': plot_type,
        'field_type': 'Analyte',
        'field': app_data.ndim_list,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': cluster_dict,
        'view': [True,False],
        'position': [],
        'data': canvas.data
    }

    return canvas, plot_info

# -------------------------------------
# PCA functions and plotting
# -------------------------------------
@log_call(logger_key='Plot')
def plot_score_map(parent,data, app_data, style_data):
    """Plots score maps for dimensionality reduction methods such as PCA or clustering.

    Creates a score map for PCA and clusters.  Maps are displayed on an ``MplCanvas``.
    The function uses the processed data from the DataHandler and the selected field from AppData
    to generate the score map. The plot is styled according to the provided StyleData object.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the score map plot.
    field_data : pd.Series
        The data series corresponding to the selected field for the score map.
    """
    canvas = MplCanvas(parent=parent)
    plot_type = style_data.plot_type
    field_type = app_data.c_field_type
    #field = app_data.c_field
    # data frame for plotting
    match field_type:
        case 'PCA score':
            #idx = int(self.comboBoxColorField.currentIndex()) + 1
            #field = f'PC{idx}'
            field = app_data.c_field
        case 'Cluster score':
            #idx = int(self.comboBoxColorField.currentIndex())
            #field = f'{idx}'
            field = app_data.c_field
        case _:
            print('(MainWindow.plot_score_map) Unknown score type'+plot_type)
            return canvas, None

    reshaped_array = np.reshape(data.processed[field].values, data.array_size, order=data.order)

    aspect_ratio = style_data.aspect_ratio if style_data.aspect_ratio is not None else data.aspect_ratio
    cax = canvas.axes.imshow(reshaped_array, cmap=style_data.cmap, aspect=aspect_ratio, interpolation='none')
    canvas.array = reshaped_array

        # Add a colorbar
    add_colorbar(style_data, canvas, cax, field)

    canvas.axes.set_title(f'{plot_type}_{field}', fontsize=style_data.font_size+2)
    canvas.axes.tick_params(direction=None,
        labelbottom=False, labeltop=False, labelright=False, labelleft=False,
        bottom=False, top=False, left=False, right=False)
    #canvas.axes.set_axis_off()

    # add scalebar
    add_scalebar(data, app_data, style_data, canvas.axes)

    return canvas, data.processed[field]

@log_call(logger_key='Plot')
def plot_pca(parent, data, app_data, style_data):
    """Plot principal component analysis (PCA)
    
    Wrapper for one of four types of PCA plots:
    * ``plot_pca_variance()`` a plot of explained variances
    * ``plot_pca_vectors()`` a plot of PCA vector components as a heatmap
    * uses ``plot_scatter()`` and ``plot_pca_components`` to produce both scatter and heatmaps of PCA scores with vector components.
    * ``plot_score_map()`` produces a plot of PCA scores for a single component as a map

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the PCA plot.
    plot_info : dict
        Dictionary containing information about the plot, including the fields and plot type.

    .. seealso::
        ``MainWindow.plot_scatter``
    """
    #'plot_pca')
    if app_data == '':
        return
    canvas = MplCanvas(parent=parent)
    pca_results = data.dim_red_results[app_data.dim_red_method]
    # Determine which PCA plot to create based on the combobox selection
    plot_type = style_data.plot_type
    #set clims 
    # style_data.clim = [np.amin(pca_results.components_), np.amax(pca_results.components_)]
    match plot_type.lower():
        # make a plot of explained variance
        case 'variance':
            canvas, plot_data = plot_pca_variance(parent,pca_results, style_data)
            plot_name = plot_type

        # make an image of the PC vectors and their components
        case 'basis vectors':
            canvas, plot_data = plot_pca_vectors(parent,pca_results, data, app_data, style_data)
            plot_name = plot_type

        # make a scatter plot or heatmap of the data... add PC component vectors
        case 'dimension scatter'| 'dimension heatmap':
            pc_x = int(app_data.dim_red_x)
            pc_y = int(app_data.dim_red_y)

            if pc_x == pc_y:
                return

            plot_name = plot_type+f'_PC{pc_x}_PC{pc_y}'
            # Assuming pca_df contains scores for the principal components
            # uncomment to use plot scatter instead of ax.scatter
            
            plot_scatter(parent, data, app_data, style_data, canvas=canvas)

            plot_data = plot_pca_components(pca_results, data, app_data, style_data, canvas)

        # make a map of a principal component score
        case 'dimension score map':
            if app_data.c_field_type.lower() == 'none' or app_data.c_field == '':
                return

            # Assuming pca_df contains scores for the principal components
            canvas, plot_data = plot_score_map(parent, data, app_data, style_data)
            plot_name = plot_type+f'_{app_data.c_field}'
        case _:
            print(f'Unknown PCA plot type: {plot_type}')
            return

    update_figure_font(canvas, style_data.font)
    canvas.data = pd.DataFrame(plot_data)
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Multidimensional Analysis',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': style_data.plot_type,
        'field_type':app_data.c_field_type,
        'field':  app_data.c_field,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': canvas.data
    }
    return canvas, plot_info
    #update_canvas(canvas)
    #self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)

@log_call(logger_key='Plot')
def plot_pca_variance(parent,pca_results, style_data):
    """Creates a plot of explained variance, individual and cumulative, for PCA

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    pca_results : PCA
        PCA results object containing explained variance ratios.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the PCA variance plot.
    plot_data : pd.DataFrame
        DataFrame containing the principal components, variance ratios, and cumulative variance ratios.
    """        
    canvas = MplCanvas(parent=parent)

    # pca_dict contains variance ratios for the principal components
    variances = pca_results.explained_variance_ratio_
    n_components = range(1, len(variances)+1)
    cumulative_variances = variances.cumsum()  # Calculate cumulative explained variance

    # Plotting the explained variance
    canvas.axes.plot(n_components, variances, linestyle='-', linewidth=style_data.line_width,
        marker=style_data.marker_dict[style_data.marker], markeredgecolor=style_data.marker_color, markerfacecolor='none', markersize=style_data.marker_size,
        color=style_data.marker_color, label='Explained Variance')

    # Plotting the cumulative explained variance
    canvas.axes.plot(n_components, cumulative_variances, linestyle='-', linewidth=style_data.line_width,
        marker=style_data.marker_dict[style_data.marker], markersize=style_data.marker_size,
        color=style_data.marker_color, label='Cumulative Variance')

    # Adding labels, title, and legend
    xlbl = 'Principal Component'
    ylbl = 'Variance Ratio'

    canvas.axes.legend(fontsize=style_data.font_size)

    # Adjust the y-axis limit to make sure the plot includes all markers and lines
    canvas.axes.set_ylim([0, 1.0])  # Assuming variance ratios are between 0 and 1

    # labels
    font = {'size':style_data.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)
    canvas.axes.set_ylabel(ylbl, fontdict=font)

    # tick marks
    canvas.axes.tick_params(direction=style_data.tick_dir,
        labelsize=style_data.font_size,
        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
        bottom=True, top=True, left=True, right=True)

    canvas.axes.set_xticks(range(1, len(n_components) + 1, 5))
    canvas.axes.set_xticks(n_components, minor=True)

    # aspect ratio
    canvas.axes.set_box_aspect(style_data.aspect_ratio)
    
    plot_data = pd.DataFrame(np.vstack((n_components, variances, cumulative_variances)).T, columns = ['Components','Variance','Cumulative Variance'])
    return canvas, plot_data

@log_call(logger_key='Plot')
def plot_pca_vectors(parent,pca_results, data, app_data, style_data):
    """Displays a heat map of PCA vector components

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    pca_results : PCA
        PCA results object containing the components.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the PCA vector components heatmap.
    plot_data : pd.DataFrame
        DataFrame containing the PCA components, with columns for each variable.
    """        
    canvas = MplCanvas(parent=parent)

    # pca_dict contains 'components_' from PCA analysis with columns for each variable
    # No need to transpose for heatmap representation
    analytes = data.processed.match_attribute('data_type','Analyte')

    components = pca_results.components_
    # Number of components and variables
    n_components = components.shape[0]
    n_variables = components.shape[1]

    norm = style_data.color_norm()
    cax = canvas.axes.imshow(components, cmap=style_data.get_colormap(), aspect=1.0, norm=norm)
    canvas.array = components

    # Add a colorbar
    add_colorbar(style_data,canvas, cax)
        # if style_data.cbar_dir == 'vertical':
    #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=style_data.cbar_dir, location='right', shrink=0.62, fraction=0.1)
    #     cbar.set_label('PCA score', size=style_data.font_size)
    #     cbar.ax.tick_params(labelsize=style_data.font_size)
    # elif style_data.cbar_dir == 'horizontal':
    #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=style_data.cbar_dir, location='bottom', shrink=0.62, fraction=0.1)
    #     cbar.set_label('PCA score', size=style_data.font_size)
    #     cbar.ax.tick_params(labelsize=style_data.font_size)
    # else:
    #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=style_data.cbar_dir, location='bottom', shrink=0.62, fraction=0.1)


    xlbl = 'Principal Components'

    # Optional: Rotate x-axis labels for better readability
    # plt.xticks(rotation=45)

    # labels
    font = {'size':style_data.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)

    # tickmarks and labels
    canvas.axes.tick_params(labelsize=style_data.font_size)
    canvas.axes.tick_params(axis='x', direction=style_data.tick_dir,
                    labelsize=style_data.font_size,
                    labelbottom=False, labeltop=True,
                    bottom=True, top=True)

    canvas.axes.tick_params(axis='y', length=0, direction=style_data.tick_dir,
                    labelsize=style_data.font_size,
                    labelleft=True, labelright=False,
                    left=True, right=True)

    canvas.axes.set_xticks(range(0, n_components, 5))
    canvas.axes.set_xticks(range(0, n_components, 1), minor=True)
    canvas.axes.set_xticklabels(np.arange(1, n_components+1, 5))

    #ax.set_yticks(n_components, labels=[f'Var{i+1}' for i in range(len(n_components))])
    canvas.axes.set_yticks(range(0, n_variables,1), minor=False)
    canvas.axes.set_yticklabels(style_data.toggle_mass(analytes), ha='right', va='center')

    canvas.fig.tight_layout()
    plot_data = pd.DataFrame(components, columns = list(map(str, range(n_variables))))
    return canvas, plot_data

@log_call(logger_key='Plot')
def plot_pca_components(pca_results,data, app_data, style_data,canvas):
    """Adds vector components to PCA scatter and heatmaps

    Parameters
    ----------
    pca_results : PCA
        PCA results object containing the components.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    canvas : MplCanvas
        The canvas containing the PCA scatter or heatmap plot.

    Returns
    -------
    plot_data : pd.DataFrame
        DataFrame containing the PCA components, with columns for each variable.

    .. seealso::
        plot_pca_vectors
    """
    #print('plot_pca_components')
    if style_data.line_width == 0:
        return

    # field labels
    analytes = data.processed.match_attribute('data_type','Analyte')
    nfields = len(analytes)

    # components
    pc_x = int(app_data.dim_red_x)
    pc_y = int(app_data.dim_red_y)

    x = pca_results.components_[:,pc_x]
    y = pca_results.components_[:,pc_y]

    # mulitiplier for scale
    m = style_data.length_multiplier #np.min(np.abs(np.sqrt(x**2 + y**2)))

    # arrows
    canvas.axes.quiver(np.zeros(nfields), np.zeros(nfields), m*x, m*y, color=style_data.line_color,
        angles='xy', scale_units='xy', scale=1, # arrow angle and scale set relative to the data
        linewidth=style_data.line_width, headlength=2, headaxislength=2) # arrow properties

    # labels
    for i, analyte in enumerate(analytes):
        if x[i] > 0 and y[i] > 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='bottom', color=style_data.line_color)
        elif x[i] < 0 and y[i] > 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='top', color=style_data.line_color)
        elif x[i] > 0 and y[i] < 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='bottom', color=style_data.line_color)
        elif x[i] < 0 and y[i] < 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='top', color=style_data.line_color)

    plot_data = pd.DataFrame(np.vstack((x,y)).T, columns = ['PC x', 'PC Y'])
    return plot_data

@log_call(logger_key='Plot')
def plot_clusters(parent, data, app_data, style_data):
    """Plot maps associated with clustering

    Will produce plots of Clusters or Cluster Scores and computes clusters if necesseary.
    The function updates ``MainWindow.plot_info`` with the displayed plot metadata and figure
    ``MplCanvas`` for display in the centralWidget views.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the clustering plot.
    plot_info : dict
        Dictionary containing information about the plot, including the fields and plot type.
    """        
    if app_data.sample_id == '':
        return

    plot_type = style_data.plot_type
    method = app_data.cluster_method
    match plot_type:
        case 'cluster map':
            plot_name = f"{plot_type}_{method}_map"
            canvas, plot_data = plot_cluster_map(parent, data, app_data, style_data)
        case 'cluster score map':
            plot_name = f"{plot_type}_{method}_{app_data.c_field}_score_map"
            canvas, plot_data = plot_score_map(parent, data, app_data, style_data)
        case _:
            return

    update_figure_font(canvas, style_data.font)
    canvas.data = canvas.data = pd.DataFrame(plot_data)
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Multidimensional Analysis',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': style_data.plot_type,
        'field_type':app_data.c_field_type,
        'field':  app_data.c_field,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': app_data.cluster_dict[method]['selected_clusters'],
        'view': [True,False],
        'position': [],
        'data': plot_data
        }

    return canvas, plot_info

@log_call(logger_key='Plot')
def cluster_performance_plot(parent, data, app_data, style_data):
    """Plots used to estimate the optimal number of clusters

    1. Elbow Method
    The elbow method looks at the variance (or inertia) within clusters as the number
    of clusters increases. The idea is to plot the sum of squared distances between
    each point and its assigned cluster's centroid, known as the within-cluster sum
    of squares (WCSS) or inertia, for different values of k (number of clusters).

    Process:
    * Run KMeans for a range of cluster numbers (k).
    * Plot the inertia (WCSS) vs. the number of clusters.
    * Look for the "elbow" point, where the rate of decrease sharply slows down,
    indicating that adding more clusters does not significantly reduce the inertia.


    2. Silhouette Score
    The silhouette score measures how similar an object is to its own cluster compared
    to other clusters. The score ranges from -1 to 1, where:

    * A score close to 1 means the sample is well clustered.
    * A score close to 0 means the sample lies on the boundary between clusters.
    * A score close to -1 means the sample is assigned to the wrong cluster.

    In cases where clusters have widely varying sizes or densities, Silhouette Score may provide the best result.

    Process:
    * Run KMeans for a range of cluster numbers (k).
    * Calculate the silhouette score for each k.
    * Choose the k with the highest silhouette score.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.
    
    Returns
    -------
    canvas : MplCanvas
        The canvas containing the cluster performance plot.
    plot_info : dict
        Dictionary containing information about the plot, including the fields and plot type.
    """        
    if app_data.sample_id == '':
        return

    method = app_data.cluster_method
    # maximum clusters for producing an cluster performance
    max_clusters =app_data.max_clusters

    # compute cluster results
    inertia = data.cluster_results[method]
    silhouette_scores =  data.silhouette_scores[method]

    second_derivative = np.diff(np.diff(inertia))

    #optimal_k = np.argmax(second_derivative) + 2  # Example heuristic

    # Plot inertia
    canvas = MplCanvas(parent=parent)

    canvas.axes.plot(range(1, max_clusters+1), inertia, linestyle='-', linewidth=style_data.line_width,
        marker=style_data.marker_dict[style_data.marker], markeredgecolor=style_data.marker_color, markerfacecolor='none', markersize=style_data.marker_size,
        color=style_data.marker_color, label='Inertia')

    # Plotting the cumulative explained variance

    canvas.axes.set_xlabel('Number of clusters')
    canvas.axes.set_ylabel('Inertia', color=style_data.marker_color)
    canvas.axes.tick_params(axis='y', labelcolor=style_data.marker_color)
    canvas.axes.set_title(f'Cluster performance: {method}')
    #canvas.axes.axvline(x=optimal_k, linestyle='--', color='m', label=f'Elbow at k={optimal_k}')

    # aspect ratio
    canvas.axes.set_box_aspect(style_data.aspect_ratio)

    # Create a secondary y-axis to plot the second derivative
    canvas.axes2 = canvas.axes.twinx()
    canvas.axes2.plot(range(2, max_clusters), second_derivative, linestyle='-', linewidth=style_data.line_width,
        marker=style_data.marker_dict[style_data.marker], markersize=style_data.marker_size,
        color='r', label='3nd Derivative')

    canvas.axes2.set_ylabel('2nd Derivative', color='r')
    canvas.axes2.tick_params(axis='y', labelcolor='r')

    # aspect ratio
    canvas.axes2.set_box_aspect(style_data.aspect_ratio)

    canvas.axes3 = canvas.axes.twinx()
    canvas.axes3.plot(range(1, max_clusters+1), silhouette_scores, linestyle='-', linewidth=style_data.line_width,
        marker=style_data.marker_dict[style_data.marker], markeredgecolor='orange', markerfacecolor='none', markersize=style_data.marker_size,
        color='orange', label='Silhouette Scores')

    canvas.axes3.spines['right'].set_position(('outward', 60))  # Move it outward by 60 points
    canvas.axes3.set_ylabel('Silhouette score', color='orange')
    canvas.axes3.tick_params(axis='y', labelcolor='orange')

    canvas.axes3.set_box_aspect(style_data.aspect_ratio)


    #print(f"Second derivative of inertia: {second_derivative}")
    #print(f"Optimal number of clusters: {optimal_k}")

    plot_type = style_data.plot_type
    plot_name = f"{plot_type}_{method}"
    
    # store data in dataframe
    K = len(inertia)
    k = np.arange(1, K + 1, dtype=int)

    # Pad 2nd derivative to length K with NaNs at the ends (center-aligned)
    second_full = np.full(K, np.nan, dtype=float)
    if K >= 3:
        second_full[1:-1] = np.diff(np.diff(inertia))

    # Build DataFrame
    perf_df = pd.DataFrame({
        'k': k,
        'inertia': np.asarray(inertia, dtype=float),
        'silhouette': np.asarray(silhouette_scores, dtype=float),
        'second_derivative': second_full
    })
    canvas.data = pd.DataFrame(perf_df)
    canvas.plot_name = plot_name
    
    plot_info = {
        'tree': 'Multidimensional Analysis',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': style_data.plot_type,
        'field_type':app_data.c_field_type,
        'field':  app_data.c_field,
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'cluster_groups': app_data.cluster_dict[method],
        'view': [True,False],
        'position': [],
        'data': perf_df
        }

    return canvas, plot_info


# -------------------------------------
# Cluster functions
# -------------------------------------
@log_call(logger_key='Plot')
def plot_cluster_map(parent, data, app_data, style_data):
    """Produces a map of cluster categories
    
    Creates the map on an ``MplCanvas``.  Each cluster category is assigned a unique color.
    The function updates ``MainWindow.plot_info`` with the displayed plot metadata and figure
    ``MplCanvas`` for display in the centralWidget views.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the cluster map plot.
    plot_data : pd.Series
        Series containing the cluster labels for each data point.
    """
    canvas = MplCanvas(parent=parent)

    plot_type = style_data.plot_type
    method = app_data.cluster_method

    # data frame for plotting
    groups = data.processed[method].values.astype(float)
    # mask-out points that are excluded by the combined mask (cluster, polygon, filter, crop)
    groups[~data.mask] = np.nan

    reshaped_array = np.reshape(groups, data.array_size, order=data.order)

    # The norm has to span *every* cluster the colormap defines, so a raw
    # label k always lands on cmap(k). Counting only the labels still
    # visible (np.unique of the non-NaN pixels) collapses BoundaryNorm's
    # range whenever the cluster table has a subset selected -- with one
    # cluster shown that leaves a single [-0.5, 0.5] bin and every pixel
    # clips to the first colour. Use the full cluster count instead, the
    # same one get_cluster_colormap builds the colormap from (and that the
    # cluster scatter path and plot_roi_map already use).
    n_clusters = len([k for k in app_data.cluster_dict[method].keys() if isinstance(k, int) and k != 99])

    cluster_color, cluster_label, cmap = style_data.get_cluster_colormap(app_data.cluster_dict[method], alpha=style_data.marker_alpha)

    overlay = style_data.style_dict.get('cluster map', {}).get('OverlayColor', '#888888')
    cmap = cmap.copy()
    cmap.set_bad(overlay)

    norm = style_data.color_norm(n_clusters)

    aspect_ratio = style_data.aspect_ratio if style_data.aspect_ratio is not None else data.aspect_ratio
    cax = canvas.axes.imshow(reshaped_array, cmap=cmap, norm=norm, aspect=aspect_ratio)
    #cax.cmap.set_under(style['Scale']['OverlayColor'])

    add_colorbar(style_data, canvas, cax, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)

    canvas.fig.subplots_adjust(left=0.05, right=1)  # Adjust these values as needed
    canvas.fig.tight_layout()

    canvas.axes.set_title(f'Clustering ({method})')
    canvas.axes.tick_params(direction=None,
        labelbottom=False, labeltop=False, labelright=False, labelleft=False,
        bottom=False, top=False, left=False, right=False)
    #canvas.axes.set_axis_off()

    # add scalebar
    add_scalebar(data, app_data, style_data, canvas.axes)

    return canvas, data.processed[method]

@log_call(logger_key='Plot')
def plot_roi(parent, data, app_data, style_data):
    """Wraps `plot_roi_map`, building the plot_info metadata dict.

    Mirrors `plot_clusters`, but ROI has only one map variant (no "score" or
    "performance" counterpart -- ROIs are user-drawn, not fit by an
    algorithm), so there's no inner `match` needed.

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the ROI map plot.
    plot_info : dict
        Dictionary containing information about the plot.
    """
    if app_data.sample_id == '' or not data.roi_stack:
        return None, None

    canvas, plot_data = plot_roi_map(parent, data, app_data, style_data)

    plot_name = "roi_map"
    update_figure_font(canvas, style_data.font)
    canvas.data = pd.DataFrame(plot_data)
    canvas.plot_name = plot_name

    plot_info = {
        'tree': 'Masking',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': style_data.plot_type,
        'field_type': 'ROI',
        'field': 'ROI',
        'figure': canvas,
        'style': style_data.style_dict[style_data.plot_type],
        'roi_groups': data.selected_rois,
        'view': [True, False],
        'position': [],
        'data': plot_data
    }

    return canvas, plot_info

@log_call(logger_key='Plot')
def plot_roi_map(parent, data, app_data, style_data):
    """Produces a map of ROI categories.

    Mirrors `plot_cluster_map`, but reads the single fixed `'ROI'` column and
    remaps ids to a dense 0..n-1 index -- ROI ids aren't guaranteed
    contiguous the way algorithm-assigned cluster labels are, since
    individual regions can be removed (see `SampleObj.remove_roi`).

    Parameters
    ----------
    parent : QWidget
        Parent widget for the plot.
    data : DataHandler
        DataHandler object containing the processed data.
    app_data : AppData
        AppData object containing application settings and user preferences.
    style_data : StyleData
        StyleData object containing style settings for the plot.

    Returns
    -------
    canvas : MplCanvas
        The canvas containing the ROI map plot.
    plot_data : pd.Series
        Series containing the raw ROI labels for each data point.
    """
    canvas = MplCanvas(parent=parent)

    id_to_index = {r['id']: i for i, r in enumerate(data.roi_stack)}
    groups = data.processed['ROI'].map(id_to_index).values.astype(float)
    # mask-out points that are excluded by the combined mask (roi, cluster, polygon, filter, crop)
    groups[~data.mask] = np.nan

    reshaped_array = np.reshape(groups, data.array_size, order=data.order)

    n_rois = len(data.roi_stack)
    roi_color, roi_label, cmap = style_data.get_roi_colormap(data.roi_stack, alpha=style_data.marker_alpha)

    overlay = style_data.style_dict.get('roi map', {}).get('OverlayColor', '#888888')
    cmap = cmap.copy()
    cmap.set_bad(overlay)

    norm = style_data.color_norm(n_rois)

    aspect_ratio = style_data.aspect_ratio if style_data.aspect_ratio is not None else data.aspect_ratio
    cax = canvas.axes.imshow(reshaped_array, cmap=cmap, norm=norm, aspect=aspect_ratio)

    add_colorbar(style_data, canvas, cax, cbartype='discrete', grouplabels=roi_label, groupcolors=roi_color)

    canvas.fig.subplots_adjust(left=0.05, right=1)
    canvas.fig.tight_layout()

    canvas.axes.set_title('Regions of Interest')
    canvas.axes.tick_params(direction=None,
        labelbottom=False, labeltop=False, labelright=False, labelleft=False,
        bottom=False, top=False, left=False, right=False)

    # add scalebar
    add_scalebar(data, app_data, style_data, canvas.axes)

    return canvas, data.processed['ROI']

def update_figure_font(canvas, font_name):
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
    except Exception as e:
        print(f'Unable to update figure font: {e}')

# def plot_colormap_annulus(cmap_name, r_inner=0.5, r_outer=1.0, n_points=512):
#     """
#     Preview a colormap as an annulus (good for circular colormaps).
    
#     Parameters
#     ----------
#     cmap_name : str
#         The name of the matplotlib colormap.
#     r_inner : float
#         Inner radius of the annulus.
#     r_outer : float
#         Outer radius of the annulus.
#     n_points : int
#         Angular resolution (higher = smoother).
#     """
#     theta = np.linspace(0, 2*np.pi, n_points)
#     r = np.linspace(r_inner, r_outer, 2)
#     T, R = np.meshgrid(theta, r)
    
#     # Normalize theta to [0,1] for colormap lookup
#     norm = mcolors.Normalize(vmin=0, vmax=2*np.pi)
#     cmap = get_cmap(cmap_name)
#     Z = T  # angle determines color
    
#     fig, ax = plt.subplots(subplot_kw={'projection':'polar'})
#     c = ax.pcolormesh(T, R, Z, cmap=cmap, norm=norm, shading='auto')
    
#     ax.set_yticklabels([])   # hide radius labels
#     ax.set_xticklabels([])   # hide angle labels
#     ax.set_ylim(r_inner, r_outer)
#     ax.set_aspect(1)
    
#     plt.show()