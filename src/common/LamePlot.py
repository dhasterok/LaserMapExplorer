import numpy as np
import pandas as pd

import matplotlib
import matplotlib.gridspec as gs
#import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Patch
import matplotlib.colors as colors
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

import src.common.CustomMplCanvas as mplc
import src.common.format as fmt
from src.common.colorfunc import get_hex_color, get_rgb_color
from src.common.plot_spider import plot_spider_norm
from src.common.radar import Radar
from src.common.scalebar import scalebar
from src.common.ternary_plot import ternary

def plot_map_mpl(parent, data, app_data, plot_style, field_type, field, add_histogram=False):
    """Create a matplotlib canvas for plotting a map

    Create a map using ``mplc.MplCanvas``.

    Parameters
    ----------
    sample_id : str
        Sample identifier
    field_type : str
        Type of field for plotting
    field : str
        Field for plotting
    """        
    # create plot canvas
    canvas = mplc.MplCanvas(parent=parent)

    # set color limits
    if field not in data.axis_dict:
        plot_style.initialize_axis_values(field_type,field)
        plot_style.set_style_widgets()

    # get data for current map
    #scale = data.processed_data.get_attribute(field, 'norm')
    scale = plot_style.cscale
    map_df = data.get_map_data(field, field_type)

    array_size = data.array_size
    aspect_ratio = data.aspect_ratio

    # store map_df to save_data if data needs to be exported
    parent.save_data = map_df.copy()

    # equalized color bins to CDF function
    if app_data.equalize_color_scale:
        sorted_data = map_df['array'].sort_values()
        cum_sum = sorted_data.cumsum()
        cdf = cum_sum / cum_sum.iloc[-1]
        map_df.loc[sorted_data.index, 'array'] = cdf.values

    # plot map
    reshaped_array = np.reshape(map_df['array'].values, array_size, order=data.order)
        
    norm = plot_style.color_norm()

    cax = canvas.axes.imshow(reshaped_array,
                            cmap=plot_style.get_colormap(),
                            aspect=aspect_ratio, interpolation='none',
                            norm=norm)

    add_colorbar(plot_style, canvas, cax)
    match plot_style.cscale:
        case 'linear':
            clim = plot_style.clim
        case 'log':
            clim = plot_style.clim
            #clim = np.log10(plot_style.clim)
        case 'logit':
            print('Color limits for logit are not currently implemented')

    cax.set_clim(clim[0], clim[1])

    # use mask to create an alpha layer
    mask = data.mask.astype(float)
    reshaped_mask = np.reshape(mask, array_size, order=data.order)

    alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
    alphas = np.clip(alphas, .4, 1)

    alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
    canvas.axes.imshow(np.ones_like(alpha_mask), aspect=aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)
    canvas.array = reshaped_array

    canvas.axes.tick_params(direction=None,
        labelbottom=False, labeltop=False, labelright=False, labelleft=False,
        bottom=False, top=False, left=False, right=False)

    canvas.set_initial_extent()
    
    # axes
    #xmin, xmax, xscale, xlbl = plot_style.get_axis_values(None,field= 'X')
    #ymin, ymax, yscale, ylbl = plot_style.get_axis_values(None,field= 'Y')


    # axes limits
    #canvas.axes.set_xlim(xmin,xmax)
    #canvas.axes.set_ylim(ymin,ymax)

    # add scalebar
    add_scalebar(app_data, plot_style, canvas.axes)

    canvas.fig.tight_layout()

    # add small histogram
    if add_histogram:
        plot_small_histogram(parent, data, app_data, plot_style, map_df)

    plot_info = {
        'tree': field_type,
        'sample_id': app_data.sample_id,
        'plot_name': field,
        'plot_type': 'analyte map',
        'field_type': field_type,
        'field': field,
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': None,
        'view': [True,False],
        'position': None
        }
    
    return canvas, plot_info

def plot_small_histogram(parent, data, app_data, plot_style, current_plot_df):
    """Creates a small histogram on the Samples and Fields tab associated with the selected map

    Parameters
    ----------
    current_plot_df : dict
        Current data for plotting
    field : str
        Name of field to plot
    """
    #print('plot_small_histogram')
    # create Mpl canvas
    canvas = mplc.SimpleMplCanvas()

    # Histogram
    #remove by mask and drop rows with na
    mask = data.mask
    if plot_style.cscale == 'log' or 'logit':
        mask = mask & current_plot_df['array'].notna() & (current_plot_df['array'] > 0)
    else:
        mask = mask & current_plot_df['array'].notna()

    array = current_plot_df['array'][mask].values

    logflag = False
    # check the analyte map cscale, the histogram needs to be the same
    if plot_style.cscale == 'log':
        print('log scale')
        logflag = True
        if any(array <= 0):
            print(f"Warning issues with values <= 0, (-): {sum(array < 0)}, (0): {sum(array == 0)}")
            return

    bin_width = (np.nanmax(array) - np.nanmin(array)) / app_data.default_hist_num_bins
    edges = np.arange(np.nanmin(array), np.nanmax(array) + bin_width, bin_width)

    if sum(mask) != len(mask):
        canvas.axes.hist( 
            current_plot_df['array'], 
            bins=edges, 
            density=True, 
            color='#b3b3b3', 
            edgecolor=None, 
            linewidth=plot_style.line_width, 
            log=logflag, 
            alpha=0.6, 
            label='unmasked' )

    _, _, patches = canvas.axes.hist(array,
            bins=edges,
            density=True,
            color=plot_style.marker_color,
            edgecolor=None,
            linewidth=plot_style.line_width,
            log=logflag,
            alpha=0.6 )

    # color histogram bins by analyte colormap?
    if parent.checkBoxShowHistCmap.isChecked():
        cmap = plot_style.get_colormap()
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
    canvas.axes.set_xlabel(plot_style.clabel, fontdict={'size':8})

    # Size the histogram in the widget
    canvas.axes.margins(x=0)
    pos = canvas.axes.get_position()
    canvas.axes.set_position((pos.x0/2, 3*pos.y0, pos.width+pos.x0, pos.height-1.5*pos.y0))

    parent.clear_layout(parent.widgetHistView.layout())
    parent.widgetHistView.layout().addWidget(canvas)

def plot_histogram(parent, data, app_data, plot_style):
    """Plots a histogramn in the canvas window"""
    
    plot_data = None
    #print('plot histogram')
    # create Mpl canvas
    canvas = mplc.MplCanvas(parent=parent)

    nbins = int(app_data.hist_num_bins)

    #if analysis == 'Ratio':
    #    analyte_1 = field.split(' / ')[0]
    #    analyte_2 = field.split(' / ')[1]

    if app_data.hist_plot_style == 'log-scaling' and app_data.hist_field_type == 'Analyte':
        print('raw_data for log-scaling')
        x = get_scatter_data(data, app_data, plot_style, processed=False)['x']
    else:
        print('processed_data for histogram')
        x = get_scatter_data(data, app_data, plot_style, processed=True)['x']

    # determine edges
    xmin,xmax,xscale,xlbl = plot_style.get_axis_values(x['type'],x['field'])
    plot_style.xlim = [xmin, xmax]
    plot_style.xscale = xscale
    #if xscale == 'log':
    #    x['array'] = np.log10(x['array'])
    #    xmin = np.log10(xmin)
    #    xmax = np.log10(xmax)

    #bin_width = (xmax - xmin) / nbins
    #print(nbins)
    #print(bin_width)
    
    if (xscale == 'linear') or (xscale == 'scientific'):
        edges = np.linspace(xmin, xmax, nbins)
    else:
        edges = np.linspace(10**xmin, 10**xmax, nbins)

    #print(edges)

    # histogram style
    lw = plot_style.line_width
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
    if app_data.hist_field_type == 'cluster' and app_data.hist_field != '':
        method = app_data.hist_field

        # Get the cluster labels for the data
        cluster_color, cluster_label, _ = plot_style.get_cluster_colormap(app_data.cluster_dict[method],alpha=plot_style.marker_alpha)
        cluster_group = data.processed_data.loc[:,method]
        clusters = app_data.cluster_dict[method]['selected_clusters']

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
                        alpha=plot_style.marker_alpha/100,
                        density=True
                    )
            else:
                # Filter out NaN and zero values
                filtered_data = cluster_data[~np.isnan(cluster_data) & (cluster_data > 0)]

                # Sort the data in ascending order
                sorted_data = np.sort(filtered_data)

                # Calculate log(number of values > x)
                log_values = np.log10(sorted_data)
                log_counts = np.log10(len(sorted_data) - np.arange(len(sorted_data)))

                # Plot the data
                canvas.axes.plot(log_values, log_counts, label=cluster_label[int(i)], color=bar_color, lw=lw)

        # Add a legend
        add_colorbar(plot_style, canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color, alpha=plot_style.marker_alpha/100)
        #canvas.axes.legend()
    else:
        clusters = None
        # Regular histogram
        bar_color = plot_style.marker_color
        if htype == 'step':
            ecolor = plot_style.line_color
        else:
            ecolor = None

        if app_data.hist_plot_style != 'log-scaling' :
            plot_data = canvas.axes.hist( x['array'],
                    cumulative=cumflag,
                    histtype=htype,
                    bins=edges,
                    color=bar_color, edgecolor=ecolor,
                    linewidth=lw,
                    alpha=plot_style.marker_alpha/100,
                    density=True
                )
        else:
            # Filter out NaN and zero values
            filtered_data = x['array'][~np.isnan(x['array']) & (x['array'] > 0)]

            # Sort the data in ascending order
            sorted_data = np.sort(filtered_data)

            # Calculate log(number of values > x)
            #log_values = np.log10(sorted_data)
            counts = len(sorted_data) - np.arange(len(sorted_data))

            # Plot the data
            #canvas.axes.plot(log_values, log_counts, label=cluster_label[int(i)], color=bar_color, lw=lw)
            canvas.axes.plot(sorted_data, counts, color=bar_color, lw=lw, alpha=plot_style.marker_alpha/100)

    # axes
    # label font
    if 'font' == '':
        font = {'size':plot_style.font}
    else:
        font = {'font':plot_style.font, 'size':plot_style.font_size}

    # set y-limits as p-axis min and max in data.axis_dict
    if app_data.hist_plot_style != 'log-scaling' :
        pflag = False
        if 'pstatus' not in data.axis_dict[x['field']]:
            pflag = True
        elif data.axis_dict[x['field']]['pstatus'] == 'auto':
            pflag = True

        if pflag:
            ymin, ymax = canvas.axes.get_ylim()
            d = {'pstatus':'auto', 'pmin':fmt.oround(ymin,order=2,toward=0), 'pmax':fmt.oround(ymax,order=2,toward=1)}
            data.axis_dict[x['field']].update(d)
            plot_style.set_axis_widgets('y', x['field'])

        # grab probablility axes limits
        _, _, _, _, ymin, ymax = plot_style.get_axis_values(x['type'],x['field'],ax='p')

        # x-axis
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        if xscale == 'log':
        #    self.logax(canvas.axes, [xmin,xmax], axis='x', label=xlbl)
            canvas.axes.set_xscale(xscale,base=10)
        # if plot_style.xscale == 'linear':
        # else:
        #     canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_xlim(xmin,xmax)

        if xscale == 'scientific':
            canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))

        # y-axis
        canvas.axes.set_ylabel(app_data.hist_plot_style, fontdict=font)
        canvas.axes.set_ylim(ymin,ymax)
    else:
        canvas.axes.set_xscale('log',base=10)
        canvas.axes.set_yscale('log',base=10)

        canvas.axes.set_xlabel(r"$\log_{10}($" + f"{app_data.hist_field}" + r"$)$", fontdict=font)
        canvas.axes.set_ylabel(r"$\log_{10}(N > \log_{10}$" + f"{app_data.hist_field}" + r"$)$", fontdict=font)

    canvas.axes.tick_params(labelsize=plot_style.font_size,direction=plot_style.tick_dir)
    canvas.axes.set_box_aspect(plot_style.aspect_ratio)

    plot_style.update_figure_font(canvas, plot_style.font)

    canvas.fig.tight_layout()

    plot_info = {
        'tree': 'Histogram',
        'sample_id': app_data.sample_id,
        'plot_name': app_data.hist_field_type+'_'+app_data.hist_field,
        'field_type': app_data.hist_field_type,
        'field': app_data.hist_field,
        'plot_type': plot_style.plot_type,
        'type': app_data.hist_plot_style,
        'nbins': nbins,
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': clusters,
        'view': [True,False],
        'position': [],
        'data': plot_data
    }

    return canvas, plot_info

def logax(ax, lim, axis='y', label='', tick_label_rotation=0):
    """
    Produces log-axes limits and labels.

    Parameters:
    ax (matplotlib.axes.Axes): The axes to modify.
    lim (list): The log10 values of the axes limits.
    axis (str): 'x' or 'y' to add ticks to x- or y-axis, default is 'y'.
    label (str): Label for the axis.
    tick_label_rotation (float): Angle of text rotation, default is 0.
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

def add_colorbar(plot_style, canvas, cax, cbartype='continuous', grouplabels=None, groupcolors=None, alpha=1):
    """Adds a colorbar to a MPL figure

    Parameters
    ----------
    canvas : mplc.MplCanvas
        canvas object
    cax : axes
        color axes object
    cbartype : str
        Type of colorbar, ``dicrete`` or ``continuous``, Defaults to continuous
    grouplabels : list of str, optional
        category/group labels for tick marks
    """
    #print("add_colorbar")
    # Add a colorbar
    cbar = None
    if plot_style.cbar_dir == 'none':
        return

    # discrete colormap - plot as a legend
    if cbartype == 'discrete':

        if grouplabels is None or groupcolors is None:
            return

        # create patches for legend items
        p = [None]*len(grouplabels)
        for i, label in enumerate(grouplabels):
            p[i] = Patch(facecolor=groupcolors[i], edgecolor='#111111', linewidth=0.5, label=label)

        if plot_style.cbar_dir == 'vertical':
            canvas.axes.legend(
                    handles=p,
                    handlelength=1,
                    loc='upper left',
                    bbox_to_anchor=(1.025,1),
                    fontsize=plot_style.font_size,
                    frameon=False,
                    ncol=1
                )
        elif plot_style.cbar_dir == 'horizontal':
            canvas.axes.legend(
                    handles=p,
                    handlelength=1,
                    loc='upper center',
                    bbox_to_anchor=(0.5,-0.1),
                    fontsize=plot_style.font_size,
                    frameon=False,
                    ncol=3
                )
    # continuous colormap - plot with colorbar
    else:
        if plot_style.cbar_dir == 'vertical':
            if plot_style.plot_type == 'correlation':
                loc = 'left'
            else:
                loc = 'right'
            cbar = canvas.fig.colorbar( cax,
                    ax=canvas.axes,
                    orientation=plot_style.cbar_dir,
                    location=loc,
                    shrink=0.62,
                    fraction=0.1,
                    alpha=alpha
                )
        elif plot_style.cbar_dir == 'horizontal':
            cbar = canvas.fig.colorbar( cax,
                    ax=canvas.axes,
                    orientation=plot_style.cbar_dir,
                    location='bottom',
                    shrink=0.62,
                    fraction=0.1,
                    alpha=alpha
                )
        else:
            # should never reach this point
            assert plot_style.cbar_dir == 'none', "Colorbar direction is set to none, but is trying to generate anyway."
            return

        cbar.set_label(plot_style.clabel, size=plot_style.font_size)
        cbar.ax.tick_params(labelsize=plot_style.font_size)
        cbar.set_alpha(alpha)

    # adjust tick marks if labels are given
    if cbartype == 'continuous' or grouplabels is None:
        ticks = None
    # elif cbartype == 'discrete':
    #     ticks = np.arange(0, len(grouplabels))
    #     cbar.set_ticks(ticks=ticks, labels=grouplabels, minor=False)
    #else:
    #    print('(add_colorbar) Unknown type: '+cbartype)


def add_scalebar(app_data, plot_style, ax):
    """Add a scalebar to a map

    Parameters
    ----------
    ax : 
        Axes to place scalebar on.
    """        
    # add scalebar
    direction = plot_style.scale_dir
    length = plot_style.scale_length
    if (length is not None) and (direction != 'none'):
        if direction == 'horizontal':
            dd = data.dx
        else:
            dd = data.dy
        sb = scalebar( width=length,
                pixel_width=dd,
                units=app_data.preferences['Units']['Distance'],
                location=plot_style.scale_location,
                orientation=direction,
                color=plot_style.overlay_color,
                ax=ax )

        sb.create()
    else:
        return

def plot_correlation(parent, data, app_data, plot_style):
    """Creates an image of the correlation matrix"""
    #print('plot_correlation')

    canvas = mplc.MplCanvas(parent=parent)
    canvas.axes.clear()

    # get the data for computing correlations
    df_filtered, analytes = data.get_processed_data()

    # Calculate the correlation matrix
    method = app_data.corr_method.lower()
    if app_data.cluster_method not in data.processed_data.columns:
        correlation_matrix = df_filtered.corr(method=method)
    else:
        algorithm = app_data.cluster_method
        cluster_group = data.processed_data.loc[:,algorithm]
        selected_clusters = app_data.cluster_dict[algorithm]['selected_clusters']

        ind = np.isin(cluster_group, selected_clusters)

        correlation_matrix = df_filtered[ind].corr(method=method)
    
    columns = correlation_matrix.columns

    font = {'size':plot_style.font_size}

    # mask lower triangular matrix to show only upper triangle
    mask = np.zeros_like(correlation_matrix, dtype=bool)
    mask[np.tril_indices_from(mask)] = True
    correlation_matrix = np.ma.masked_where(mask, correlation_matrix)

    norm = plot_style.color_norm()

    # plot correlation or correlation^2
    square_flag = app_data.corr_squared
    if square_flag:
        cax = canvas.axes.imshow(correlation_matrix**2, cmap=plot_style.get_colormap(), norm=norm)
        canvas.array = correlation_matrix**2
    else:
        cax = canvas.axes.imshow(correlation_matrix, cmap=plot_style.get_colormap(), norm=norm)
        canvas.array = correlation_matrix
        
    # store correlation_matrix to save_data if data needs to be exported
    parent.save_data = canvas.array

    canvas.axes.spines['top'].set_visible(False)
    canvas.axes.spines['bottom'].set_visible(False)
    canvas.axes.spines['left'].set_visible(False)
    canvas.axes.spines['right'].set_visible(False)

    # Add colorbar to the plot
    add_colorbar(plot_style, canvas, cax)

    # set color limits
    cax.set_clim(plot_style.clim[0], plot_style.clim[1])

    # Set tick labels
    ticks = np.arange(len(columns))
    canvas.axes.tick_params(length=0, labelsize=8,
                    labelbottom=False, labeltop=True, labelleft=False, labelright=True,
                    bottom=False, top=True, left=False, right=True)

    canvas.axes.set_yticks(ticks, minor=False)
    canvas.axes.set_xticks(ticks, minor=False)

    labels = plot_style.toggle_mass(columns)

    canvas.axes.set_xticklabels(labels, rotation=90, ha='center', va='bottom', fontproperties=font)
    canvas.axes.set_yticklabels(labels, ha='left', va='center', fontproperties=font)

    canvas.axes.set_title('')

    plot_style.update_figure_font(canvas, plot_style.font)

    if square_flag:
        plot_name = method+'_squared'
    else:
        plot_name = method

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
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': correlation_matrix,
    }

    return canvas, plot_info

 

def get_scatter_data(data, app_data, plot_style, processed=True):

    scatter_dict = {'x': {'type': None, 'field': None, 'label': None, 'array': None},
            'y': {'type': None, 'field': None, 'label': None, 'array': None},
            'z': {'type': None, 'field': None, 'label': None, 'array': None},
            'c': {'type': None, 'field': None, 'label': None, 'array': None}}

    match plot_style.plot_type:
        case 'histogram':
            if processed or app_data.hist_field_type != 'Analyte':
                scatter_dict['x'] = data.get_vector(app_data.hist_field_type, app_data.hist_field, norm=plot_style.xscale)
            else:
                scatter_dict['x'] = data.get_vector(app_data.hist_field_type, app_data.hist_field, norm=plot_style.xscale, processed=False)
        case 'PCA scatter' | 'PCA heatmap':
            scatter_dict['x'] = data.get_vector('PCA score', f'PC{app_data.dim_red_x}', norm=plot_style.xscale)
            scatter_dict['y'] = data.get_vector('PCA score', f'PC{app_data.dim_red_y}', norm=plot_style.yscale)
            if (plot_style.color_field_type is None) or (plot_style.color_field != ''):
                scatter_dict['c'] = data.get_vector(plot_style.color_field_type, plot_style.color_field)
        case _:
            scatter_dict['x'] = data.get_vector(app_data.x_field_type, app_data.x_field, norm=plot_style.xscale)
            scatter_dict['y'] = data.get_vector(app_data.y_field_type, app_data.y_field, norm=plot_style.yscale)
            if (plot_style.color_field_type is not None) and (plot_style.color_field != ''):
                scatter_dict['z'] = data.get_vector(app_data.z_field_type, app_data.z_field, norm=plot_style.zscale)
            elif (app_data.z_field_type is not None) and (app_data.z_field != ''):
                scatter_dict['c'] = data.get_vector(plot_style.color_field_type, plot_style.color_field, norm=plot_style.cscale)

    # set axes widgets
    if (scatter_dict['x']['field'] is not None) and (scatter_dict['y']['field'] != ''):
        if scatter_dict['x']['field'] not in data.axis_dict.keys():
            plot_style.initialize_axis_values(scatter_dict['x']['type'], scatter_dict['x']['field'])
            plot_style.set_axis_widgets('x', scatter_dict['x']['field'])

    if (scatter_dict['y']['field'] is not None) and (scatter_dict['y']['field'] != ''):
        if scatter_dict['y']['field'] not in data.axis_dict.keys():
            plot_style.initialize_axis_values(scatter_dict['y']['type'], scatter_dict['y']['field'])
            plot_style.set_axis_widgets('y', scatter_dict['y']['field'])

    if (scatter_dict['z']['field'] is not None) and (scatter_dict['z']['field'] != ''):
        if scatter_dict['z']['field'] not in data.axis_dict.keys():
            plot_style.initialize_axis_values(scatter_dict['z']['type'], scatter_dict['z']['field'])
            plot_style.set_axis_widgets('z', scatter_dict['z']['field'])

    if (scatter_dict['c']['field'] is not None) and (scatter_dict['c']['field'] != ''):
        if scatter_dict['c']['field'] not in data.axis_dict.keys():
            plot_style.set_color_axis_widgets()
            plot_style.set_axis_widgets('c', scatter_dict['c']['field'])

    return scatter_dict

# -------------------------------------
# Scatter/Heatmap functions
# -------------------------------------
def plot_scatter(parent, data, app_data, plot_style, canvas=None):
    """Creates a plots from self.toolBox Scatter page.

    Creates both scatter and heatmaps (spatial histograms) for bi- and ternary plots.

    Parameters
    ----------
    canvas : MplCanvas
        canvas within gui for plotting, by default ``None``
    """
    #print('plot_scatter')
    plot_type = plot_style.plot_type 

    # get data for plotting
    scatter_dict = get_scatter_data(data, app_data, plot_style)
    if (scatter_dict['x']['field'] == '') or (scatter_dict['y']['field'] == ''):
        return

    if canvas is None:
        plot_flag = True
        canvas = mplc.MplCanvas(parent=parent)
    else:
        plot_flag = False

    match plot_type.split()[-1]:
        # scatter
        case 'scatter':
            if (scatter_dict['z']['field'] is None) or (scatter_dict['z']['field'] == ''):
                # biplot
                plot_info = biplot(canvas, data, app_data, plot_style, scatter_dict['x'],scatter_dict['y'],scatter_dict['c'])
            else:
                # ternary
                plot_info = ternary_scatter(canvas, data, app_data, plot_style, scatter_dict['x'],scatter_dict['y'],scatter_dict['z'],scatter_dict['c'])

        # heatmap
        case 'heatmap':
            # biplot
            if (scatter_dict['z']['field'] is None) or (scatter_dict['z']['field'] == ''):
                plot_info = hist2dbiplot(canvas, data, app_data, plot_style, scatter_dict['x'],scatter_dict['y'])
            # ternary
            else:
                plot_info = hist2dternplot(canvas, data, app_data, plot_style, scatter_dict['x'],scatter_dict['y'],scatter_dict['z'],scatter_dict['c'])

    canvas.axes.margins(x=0)

    if plot_flag:
        plot_style.update_figure_font(canvas, plot_style.font)

        return canvas, plot_info

def biplot(canvas, data, app_data, plot_style, x, y, c):
    """Creates scatter bi-plots

    A general function for creating scatter plots of 2-dimensions.

    Parameters
    ----------
    canvas : MplCanvas
        Canvas to be added to main window
    x : dict
        Data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as x coordinate
    y : dict
        Data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as y coordinate
    c : dict
        Data associated with field ``MainWindow.comboBoxColorField.currentText()`` as marker colors
    style : dict
        Style parameters
    """
    if (c['field'] is None) or (c['field'] == ''):
        # single color
        canvas.axes.scatter(x['array'], y['array'], c=plot_style.marker_color,
            s=plot_style.marker_size,
            marker=plot_style.marker_dict[plot_style.marker],
            edgecolors='none',
            alpha=plot_style.marker_alpha/100)
        cb = None
        
        plot_data = pd.DataFrame(np.vstack((x['array'], y['array'])).T, columns = ['x','y'])
        
    elif plot_style.color_field_type == 'cluster':
        # color by cluster
        method = plot_style.color_field
        if method not in list(app_data.cluster_dict.keys()):
            return
        else:
            if 0 not in list(app_data.cluster_dict[method].keys()):
                return

        cluster_color, cluster_label, cmap = plot_style.get_cluster_colormap(app_data.cluster_dict[method],alpha=plot_style.marker_alpha)
        cluster_group = data.processed_data.loc[:,method]
        selected_clusters = app_data.cluster_dict[method]['selected_clusters']

        ind = np.isin(cluster_group, selected_clusters)

        norm = plot_style.color_norm(app_data.cluster_dict[method]['n_clusters'])

        cb = canvas.axes.scatter(x['array'][ind], y['array'][ind], c=c['array'][ind],
            s=plot_style.marker_size,
            marker=plot_style.marker_dict[plot_style.marker],
            edgecolors='none',
            cmap=cmap,
            alpha=plot_style.marker_alpha/100,
            norm=norm)

        add_colorbar(plot_style, canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
        plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], c['array'][ind], cluster_group[ind])).T, columns = ['x','y','c','cluster_group'])
    else:
        # color by field
        norm = plot_style.color_norm()
        cb = canvas.axes.scatter(x['array'], y['array'], c=c['array'],
            s=plot_style.marker_size,
            marker=plot_style.marker_dict[plot_style.marker],
            edgecolors='none',
            cmap=plot_style.get_colormap(),
            alpha=plot_style.marker_alpha/100,
            norm=norm)

        self.add_colorbar(canvas, cb)
        plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])
        

    # axes
    xmin, xmax, xscale, xlbl = plot_style.get_axis_values(x['type'],x['field'])
    ymin, ymax, yscale, ylbl = plot_style.get_axis_values(y['type'],y['field'])

    # labels
    font = {'size':plot_style.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)
    canvas.axes.set_ylabel(ylbl, fontdict=font)

    # axes limits
    canvas.axes.set_xlim(xmin,xmax)
    canvas.axes.set_ylim(ymin,ymax)

    # tick marks
    canvas.axes.tick_params(direction=plot_style.tick_dir,
        labelsize=plot_style.font_size,
        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
        bottom=True, top=True, left=True, right=True)

    # aspect ratio
    canvas.axes.set_box_aspect(plot_style.aspect_ratio)
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

    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'scatter',
        'field_type': [x['type'], y['type'], '', c['type']],
        'field': [x['field'], y['field'], '', c['field']],
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data':  plot_data
    }

    return plot_info

def ternary_scatter(canvas, data, app_data, plot_style, x, y, z, c):
    """Creates ternary scatter plots

    A general function for creating ternary scatter plots.

    Parameters
    ----------
    canvas : MplCanvas
        Canvas that contains axes and figure
    x : dict
        coordinate associated with top vertex
    y : dict
        coordinate associated with left vertex
    z : dict
        coordinate associated with right vertex
    c : dict
        color dimension
    """
    labels = [x['field'], y['field'], z['field']]
    tp = ternary(canvas.axes, labels, 'scatter')

    if (c['field'] is None) or (c['field'] == ''):
        tp.ternscatter( x['array'], y['array'], z['array'],
                marker=plot_style.marker_dict[plot_style.marker],
                size=plot_style.marker_size,
                color=plot_style.marker_color,
                alpha=plot_style.marker_alpha/100,
            )
        cb = None
        plot_data = pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
        
    elif plot_style.color_field_type == 'cluster':
        # color by cluster
        method = plot_style.color_field
        if method not in list(app_data.cluster_dict.keys()):
            return
        else:
            if 0 not in list(app_data.cluster_dict[method].keys()):
                return

        cluster_color, cluster_label, cmap = plot_style.get_cluster_colormap(app_data.cluster_dict[method],alpha=plot_style.marker_alpha)
        cluster_group = data.processed_data.loc[:,method]
        selected_clusters = app_data.cluster_dict[method]['selected_clusters']

        ind = np.isin(cluster_group, selected_clusters)

        norm = plot_style.color_norm(app_data.cluster_dict[method]['n_clusters'])

        _, cb = tp.ternscatter( x['array'][ind], y['array'][ind], z['array'][ind],
                categories=c['array'][ind],
                marker=plot_style.marker_dict[plot_style.marker],
                size=plot_style.marker_size,
                cmap=cmap,
                norm=norm,
                labels=True,
                alpha=plot_style.marker_alpha/100,
                orientation='None' )

        add_colorbar(plot_style, canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
        plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], z['array'][ind], cluster_group[ind])).T, columns = ['x','y','z','cluster_group'])
    else:
        # color field
        norm = plot_style.color_norm()
        _, cb = tp.ternscatter(x['array'], y['array'], z['array'],
                categories=c['array'],
                marker=plot_style.marker_dict[plot_style.marker],
                size=plot_style.marker_size,
                cmap=plot_style.cmap,
                norm=norm,
                alpha=plot_style.marker_alpha/100,
                orientation=plot_style.cbar_dir )
        
        if cb:
            cb.set_label(c['label'])
            plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])

    # axes limits
    canvas.axes.set_xlim(-1.01,1.01)
    canvas.axes.set_ylim(-0.01,1)

    plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'ternscatter'}"
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'scatter',
        'field_type': [x['type'], y['type'], z['type'], c['type']],
        'field': [x['field'], y['field'], z['field'], c['field']],
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': plot_data
    }

    return plot_info

def hist2dbiplot(canvas, data, app_data, plot_style, x, y):
    """Creates 2D histogram figure

    A general function for creating 2D histograms (heatmaps).

    Parameters
    ----------
    canvas : MplCanvas
        plotting canvas
    x : dict
        X-axis dictionary
    y : dict
        Y-axis dictionary
    """
    # color by field
    norm = plot_style.color_norm()
    h = canvas.axes.hist2d(x['array'], y['array'], bins=plot_style.resolution, norm=norm, cmap=plot_style.get_colormap())
    add_colorbar(plot_style, canvas, h[3])

    # axes
    xmin, xmax, xscale, xlbl = plot_style.get_axis_values(x['type'],x['field'])
    ymin, ymax, yscale, ylbl = plot_style.get_axis_values(y['type'],y['field'])

    # labels
    font = {'size':plot_style.font_size}
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
    canvas.axes.tick_params(direction=plot_style.tick_dir,
                    labelsize=plot_style.font_size,
                    labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                    bottom=True, top=True, left=True, right=True)

    # aspect ratio
    canvas.axes.set_box_aspect(plot_style.aspect_ratio)

    if xscale == 'log':
        canvas.axes.set_xscale(xscale,base=10)
    if yscale == 'log':
        canvas.axes.set_yscale(yscale,base=10)

    if xscale == 'scientific':
        canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
    if yscale == 'scientific':
        canvas.axes.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

    plot_name = f"{x['field']}_{y['field']}_{'heatmap'}"
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'heatmap',
        'field_type': [x['type'], y['type'], '', ''],
        'field': [x['field'], y['field'], '', ''],
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': pd.DataFrame(np.vstack((x['array'],y['array'])).T, columns = ['x','y'])
    }

    return plot_info

def hist2dternplot(canvas, data, app_data, plot_style, x, y, z, c):
    """Creates a ternary histogram figure

    A general function for creating scatter plots of 2-dimensions.

    Parameters
    ----------
    fig : matplotlib.figure
        Figure object
    x, y, z : dict
        Coordinates associated with top, left and right vertices, respectively
    style:  dict
        Style parameters
    save : bool
        Saves figure widget to plot tree
    c : str
        Display, mean, median, standard deviation plots for a fourth dimension in
        addition to histogram map. Default is None, which produces a histogram.
    """
    labels = [x['field'], y['field'], z['field']]

    if (c['field'] is None) or (c['field'] == ''):
        tp = ternary(canvas.axes, labels, 'heatmap')

        norm = plot_style.color_norm()
        hexbin_df, cb = tp.ternhex(a=x['array'], b=y['array'], c=z['array'],
            bins=plot_style.resolution,
            plotfield='n',
            cmap=plot_style.cmap,
            orientation=plot_style.cbar_dir,
            norm=norm)

        if cb is not None:
            cb.set_label('log(N)')
    else:
        pass
        # axs = fig.subplot_mosaic([['left','upper right'],['left','lower right']], layout='constrained', width_ratios=[1.5, 1])

        # for idx, ax in enumerate(axs):
        #     tps[idx] = ternary(ax, labels, 'heatmap')

        # hexbin_df = ternary.ternhex(a=x['array'], b=y['array'], c=z['array'], val=c['array'], bins=plot_style.resolution)

        # cb.set_label(c['label'])

        # #tp.ternhex(hexbin_df=hexbin_df, plotfield='n', cmap=plot_style.cmap, orientation='vertical')

    plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'heatmap'}"
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'heatmap',
        'field_type': [x['type'], y['type'], z['type'], ''],
        'field': [x['field'], y['field'], z['field'], ''],
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data' : pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
    }

    return plot_info

def plot_ternary_map(parent, data, app_data, plot_style):
    """Creates map colored by ternary coordinate positions"""
    if plot_style.plot_type != 'ternary map':
        app_data.plot_type = 'ternary map'
        plot_style.set_style_widgets('ternary map')

    canvas = mplc.MplCanvas(sub=121,parent=parent)

    afield = app_data.x_field
    bfield = app_data.y_field
    cfield = app_data.z_field

    a = data.processed_data.loc[:,afield].values
    b = data.processed_data.loc[:,bfield].values
    c = data.processed_data.loc[:,cfield].values

    ca = get_rgb_color(get_hex_color(app_data.ternary_color_x))
    cb = get_rgb_color(get_hex_color(app_data.ternary_color_y))
    cc = get_rgb_color(get_hex_color(app_data.ternary_color_z))
    cm = get_rgb_color(get_hex_color(app_data.ternary_color_m))

    t = ternary(canvas.axes)

    cval = t.terncolor(a, b, c, ca, cb, cc, cp=cm)

    M, N = data.array_size

    # Reshape the array into MxNx3
    map_data = np.zeros((M, N, 3), dtype=np.uint8)
    map_data[:len(cval), :, :] = cval.reshape(M, N, 3, order=data.order)

    canvas.axes.imshow(map_data, aspect=data.aspect_ratio)
    canvas.array = map_data

    # add scalebar
    add_scalebar(app_data, plot_style, canvas.axes)

    grid = None
    if plot_style.cbar_dir == 'vertical':
        grid = gs.GridSpec(5,1)
    elif plot_style.cbar_dir == 'horizontal':
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
    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': 'ternary map',
        'field_type': [app_data.x_field, app_data.y_field, app_data.z_field, ''],
        'field': [afield, bfield, cfield, ''],
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': map_data
    }

    return canvas, plot_info

# -------------------------------------
# TEC and Radar plots
# -------------------------------------

def plot_ndim(parent, data, app_data, plot_style):
    """Produces trace element compatibility (TEC) and Radar plots
    
    Geochemical TEC diagrams are a staple of geochemical analysis, often referred to as spider diagrams, which display a set of elements
    arranged by compatibility.  Radar plots show data displayed on a set of radial spokes (axes), giving the appearance of a radar screen
    or spider web.
    
    The function updates ``MainWindow.plot_info`` with the displayed plot metadata and figure ``mplc.MplCanvas`` for display in the centralWidget views.
    """
    if not app_data.ndim_list:
        return

    df_filtered, _  = data[app_data.sample_id].get_processed_data()

    # match self.comboBoxNorm.currentText():
    #     case 'log':
    #         df_filtered.loc[:,:] = 10**df_filtered.values
    #     case 'mixed':
    #         pass
    #     case 'linear':
    #         # do nothing
    #         pass
    df_filtered = df_filtered[data.mask]

    ref_i = app_data.ref_index

    plot_type = plot_style.plot_type
    plot_data = None

    # Get quantile for plotting TEC & radar plots
    quantiles = app_data.ndim_quantiles(app_data.ndim_quantile_index)
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
    if plot_style.show_mass:
        angle = 45
    else:
        angle = 0
    labels = plot_style.toggle_mass(app_data.ndim_list)
        
    clusters = []
    cluster_color = []
    cluster_label = []
    if plot_style.color_field_type == 'cluster' and plot_style.color_field != '':
        method = plot_style.color_field
        cluster_dict = app_data.cluster_dict[method]
        cluster_color, cluster_label, cmap = plot_style.get_cluster_colormap(cluster_dict, alpha=plot_style.marker_alpha)

        clusters = cluster_dict['selected_clusters']
        if 0 in list(cluster_dict.keys()):
            cluster_flag = True
        else:
            cluster_dict = None
            cluster_flag = False
            print(f'No cluster data found for {method}, recompute?')
    else:
        cluster_dict = None
        cluster_flag = False

    
    canvas = mplc.MplCanvas(parent=parent, proj='radar')

    match plot_type:
        case 'Radar':
            axes_interval = 5
            if cluster_flag and method in data.processed_data.columns:
                # Get the cluster labels for the data
                cluster_group = data.processed_data[method][data.mask]

                df_filtered['clusters'] = cluster_group
                df_filtered = df_filtered[df_filtered['clusters'].isin(clusters)]
                radar = Radar( 
                    canvas.axes,
                    df_filtered,
                    fields=app_data.ndim_list,
                    fieldlabels=labels,
                    quantiles=quantiles,
                    axes_interval=axes_interval,
                    group_field='clusters',
                    groups=clusters)

                canvas.fig, canvas.axes = radar.plot(cmap = cmap)
                canvas.axes.legend(loc='upper right', frameon='False')
            else:
                radar = Radar(canvas.axes, df_filtered, fields=app_data.ndim_list, fieldlabels=labels, quantiles=quantiles, axes_interval=axes_interval, group_field='', groups=None)
                    
                radar.plot()
                
                plot_data = radar.vals
                
        case 'TEC':
            yl = [np.inf, -np.inf]
            if cluster_flag and method in data.processed_data.columns:
                # Get the cluster labels for the data
                cluster_group = data.processed_data[method][data.mask]

                df_filtered['clusters'] = cluster_group

                # Plot tec for all clusters
                for i in clusters:
                    # Create RGBA color
                    #print(f'Cluster {i}')
                    canvas.axes, yl_tmp, _ = plot_spider_norm(
                            data=df_filtered.loc[df_filtered['clusters']==i,:],
                            ref_data=app_data.ref_data, norm_ref_data=app_data.ref_data['model'][ref_i],
                            layer=app_data.ref_data['layer'][ref_i], el_list=app_data.ndim_list ,
                            style='Quanta', quantiles=quantiles, ax=canvas.axes, c=cluster_color[i], label=cluster_label[i]
                        )
                    #store max y limit to convert the set y limit of axis
                    yl = [np.floor(np.nanmin([yl[0] , yl_tmp[0]])), np.ceil(np.nanmax([yl[1] , yl_tmp[1]]))]

                # Put a legend below current axis
                box = canvas.axes.get_position()
                canvas.axes.set_position((box.x0, box.y0 - box.height * 0.1, box.width, box.height * 0.9))

                add_colorbar(plot_style, canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
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

    plot_style.update_figure_font(canvas, plot_style.font)

    plot_info = {
        'tree': 'Geochemistry',
        'sample_id': app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': plot_type,
        'field_type': 'analyte',
        'field': app_data.ndim_list,
        'figure': canvas,
        'style': plot_style.style_dict[plot_style.plot_type],
        'cluster_groups': cluster_dict,
        'view': [True,False],
        'position': [],
        'data': plot_data
    }

    return canvas, plot_info

# -------------------------------------
# PCA functions and plotting
# -------------------------------------
def plot_score_map(self):
    """Plots score maps

    Creates a score map for PCA and clusters.  Maps are displayed on an ``mplc.MplCanvas``.
    """
    canvas = mplc.MplCanvas(parent=self)

    plot_type = self.plot_style.plot_type

    # data frame for plotting
    match plot_type:
        case 'PCA score':
            idx = int(self.comboBoxColorField.currentIndex()) + 1
            field = f'PC{idx}'
        case 'cluster score':
            #idx = int(self.comboBoxColorField.currentIndex())
            #field = f'{idx}'
            field = self.field
        case _:
            print('(MainWindow.plot_score_map) Unknown score type'+plot_type)
            return canvas

    reshaped_array = np.reshape(self.data[self.app_data.sample_id].processed_data[field].values, self.data[self.app_data.sample_id].array_size, order=self.data[self.app_data.sample_id].order)

    cax = canvas.axes.imshow(reshaped_array, cmap=self.plot_style.cmap, aspect=self.data[self.app_data.sample_id].aspect_ratio, interpolation='none')
    canvas.array = reshaped_array

        # Add a colorbar
    self.add_colorbar(canvas, cax, field)

    canvas.axes.set_title(f'{plot_type}')
    canvas.axes.tick_params(direction=None,
        labelbottom=False, labeltop=False, labelright=False, labelleft=False,
        bottom=False, top=False, left=False, right=False)
    #canvas.axes.set_axis_off()

    # add scalebar
    self.add_scalebar(canvas.axes)

    return canvas, self.data[self.app_data.sample_id].processed_data[field]


def plot_pca(self):
    """Plot principal component analysis (PCA)
    
    Wrapper for one of four types of PCA plots:
    * ``plot_pca_variance()`` a plot of explained variances
    * ``plot_pca_vectors()`` a plot of PCA vector components as a heatmap
    * uses ``plot_scatter()`` and ``plot_pca_components`` to produce both scatter and heatmaps of PCA scores with vector components.
    * ``plot_score_map()`` produces a plot of PCA scores for a single component as a map

    .. seealso::
        ``MainWindow.plot_scatter``
    """
    #'plot_pca')
    if self.app_data.sample_id == '':
        return

    if self.update_pca_flag or not self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','pca score'):
        self.compute_pca()

    # Determine which PCA plot to create based on the combobox selection
    plot_type = self.plot_style.plot_type

    match plot_type.lower():
        # make a plot of explained variance
        case 'variance':
            canvas, plot_data = self.plot_pca_variance()
            plot_name = plot_type

        # make an image of the PC vectors and their components
        case 'vectors':
            canvas, plot_data = self.plot_pca_vectors()
            plot_name = plot_type

        # make a scatter plot or heatmap of the data... add PC component vectors
        case 'pca scatter'| 'pca heatmap':
            pc_x = int(self.spinBoxPCX.value())
            pc_y = int(self.spinBoxPCY.value())

            if pc_x == pc_y:
                return

            plot_name = plot_type+f'_PC{pc_x}_PC{pc_y}'
            # Assuming pca_df contains scores for the principal components
            # uncomment to use plot scatter instead of ax.scatter
            canvas = mplc.MplCanvas(parent=self)
            plot_scatter(self, self.data, self.app_data, self.plot_style, canvas=canvas)

            plot_data= self.plot_pca_components(canvas)

        # make a map of a principal component score
        case 'pca score':
            if self.field_type.lower() == 'none' or self.field == '':
                return

            # Assuming pca_df contains scores for the principal components
            canvas, plot_data = self.plot_score_map()
            plot_name = plot_type+f'_{self.field}'
        case _:
            print(f'Unknown PCA plot type: {plot_type}')
            return

    self.plot_style.update_figure_font(canvas, self.plot_style.font)

    self.plot_info = {
        'tree': 'Multidimensional Analysis',
        'sample_id': self.app_data.sample_id,
        'plot_name': plot_name,
        'plot_type': self.plot_style.plot_type,
        'field_type':self.field_type,
        'field':  self.field,
        'figure': canvas,
        'style': self.plot_style.style_dict[self.plot_style.plot_type],
        'cluster_groups': [],
        'view': [True,False],
        'position': [],
        'data': plot_data
    }

    self.update_canvas(canvas)
    #self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)

def plot_pca_variance(self):
    """Creates a plot of explained variance, individual and cumulative, for PCA

    Returns
    -------
    mplc.MplCanvas
        
    """        
    canvas = mplc.MplCanvas(parent=self)

    # pca_dict contains variance ratios for the principal components
    variances = self.pca_results.explained_variance_ratio_
    n_components = range(1, len(variances)+1)
    cumulative_variances = variances.cumsum()  # Calculate cumulative explained variance

    # Plotting the explained variance
    canvas.axes.plot(n_components, variances, linestyle='-', linewidth=self.plot_style.line_width,
        marker=self.plot_style.marker_dict[self.plot_style.marker], markeredgecolor=self.plot_style.marker_color, markerfacecolor='none', markersize=self.plot_style.marker_size,
        color=self.plot_style.marker_color, label='Explained Variance')

    # Plotting the cumulative explained variance
    canvas.axes.plot(n_components, cumulative_variances, linestyle='-', linewidth=self.plot_style.line_width,
        marker=self.plot_style.marker_dict[self.plot_style.marker], markersize=self.plot_style.marker_size,
        color=self.plot_style.marker_color, label='Cumulative Variance')

    # Adding labels, title, and legend
    xlbl = 'Principal Component'
    ylbl = 'Variance Ratio'

    canvas.axes.legend(fontsize=self.plot_style.font_size)

    # Adjust the y-axis limit to make sure the plot includes all markers and lines
    canvas.axes.set_ylim([0, 1.0])  # Assuming variance ratios are between 0 and 1

    # labels
    font = {'size':self.plot_style.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)
    canvas.axes.set_ylabel(ylbl, fontdict=font)

    # tick marks
    canvas.axes.tick_params(direction=self.plot_style.tick_dir,
        labelsize=self.plot_style.font_size,
        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
        bottom=True, top=True, left=True, right=True)

    canvas.axes.set_xticks(range(1, len(n_components) + 1, 5))
    canvas.axes.set_xticks(n_components, minor=True)

    # aspect ratio
    canvas.axes.set_box_aspect(self.plot_style.aspect_ratio)
    
    plot_data = pd.DataFrame(np.vstack((n_components, variances, cumulative_variances)).T, columns = ['Components','Variance','Cumulative Variance'])
    return canvas, plot_data

def plot_pca_vectors(self):
    """Displays a heat map of PCA vector components

    Returns
    -------
    mplc.MplCanvas
        Creates figure on mplc.MplCanvas
    """        
    canvas = mplc.MplCanvas(parent=self)

    # pca_dict contains 'components_' from PCA analysis with columns for each variable
    # No need to transpose for heatmap representation
    analytes = self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','analyte')

    components = self.pca_results.components_
    # Number of components and variables
    n_components = components.shape[0]
    n_variables = components.shape[1]

    norm = self.plot_style.color_norm()
    cax = canvas.axes.imshow(components, cmap=self.plot_style.get_colormap(), aspect=1.0, norm=norm)
    canvas.array = components

    # Add a colorbar
    self.add_colorbar(canvas, cax)
    # if self.plot_style.cbar_dir == 'vertical':
    #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=self.plot_style.cbar_dir, location='right', shrink=0.62, fraction=0.1)
    #     cbar.set_label('PCA score', size=self.plot_style.font_size)
    #     cbar.ax.tick_params(labelsize=self.plot_style.font_size)
    # elif self.plot_style.cbar_dir == 'horizontal':
    #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=self.plot_style.cbar_dir, location='bottom', shrink=0.62, fraction=0.1)
    #     cbar.set_label('PCA score', size=self.plot_style.font_size)
    #     cbar.ax.tick_params(labelsize=self.plot_style.font_size)
    # else:
    #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=self.plot_style.cbar_dir, location='bottom', shrink=0.62, fraction=0.1)


    xlbl = 'Principal Components'

    # Optional: Rotate x-axis labels for better readability
    # plt.xticks(rotation=45)

    # labels
    font = {'size':self.plot_style.font_size}
    canvas.axes.set_xlabel(xlbl, fontdict=font)

    # tickmarks and labels
    canvas.axes.tick_params(labelsize=self.plot_style.font_size)
    canvas.axes.tick_params(axis='x', direction=self.plot_style.tick_dir,
                    labelsize=self.plot_style.font_size,
                    labelbottom=False, labeltop=True,
                    bottom=True, top=True)

    canvas.axes.tick_params(axis='y', length=0, direction=self.plot_style.tick_dir,
                    labelsize=self.plot_style.font_size,
                    labelleft=True, labelright=False,
                    left=True, right=True)

    canvas.axes.set_xticks(range(0, n_components, 5))
    canvas.axes.set_xticks(range(0, n_components, 1), minor=True)
    canvas.axes.set_xticklabels(np.arange(1, n_components+1, 5))

    #ax.set_yticks(n_components, labels=[f'Var{i+1}' for i in range(len(n_components))])
    canvas.axes.set_yticks(range(0, n_variables,1), minor=False)
    canvas.axes.set_yticklabels(self.plot_style.toggle_mass(analytes), ha='right', va='center')

    canvas.fig.tight_layout()
    plot_data = pd.DataFrame(components, columns = list(map(str, range(n_variables))))
    return canvas, plot_data

def plot_pca_components(self, canvas):
    """Adds vector components to PCA scatter and heatmaps

    Parameters
    ----------
    canvas : mplc.MplCanvas
        Canvas object for plotting

    .. seealso::
        ``MainWindow.plot_pca_vectors``
    """
    #print('plot_pca_components')
    if self.plot_style.line_width == 0:
        return

    # field labels
    analytes = self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','analyte')
    nfields = len(analytes)

    # components
    pc_x = int(self.spinBoxPCX.value())-1
    pc_y = int(self.spinBoxPCY.value())-1

    x = self.pca_results.components_[:,pc_x]
    y = self.pca_results.components_[:,pc_y]

    # mulitiplier for scale
    m = self.plot_style.line_multiplier #np.min(np.abs(np.sqrt(x**2 + y**2)))

    # arrows
    canvas.axes.quiver(np.zeros(nfields), np.zeros(nfields), m*x, m*y, color=self.plot_style.line_color,
        angles='xy', scale_units='xy', scale=1, # arrow angle and scale set relative to the data
        linewidth=self.plot_style.line_width, headlength=2, headaxislength=2) # arrow properties

    # labels
    for i, analyte in enumerate(analytes):
        if x[i] > 0 and y[i] > 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='bottom', color=self.plot_style.line_color)
        elif x[i] < 0 and y[i] > 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='top', color=self.plot_style.line_color)
        elif x[i] > 0 and y[i] < 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='bottom', color=self.plot_style.line_color)
        elif x[i] < 0 and y[i] < 0:
            canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='top', color=self.plot_style.line_color)

    plot_data = pd.DataFrame(np.vstack((x,y)).T, columns = ['PC x', 'PC Y'])
    return plot_data