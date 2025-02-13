import numpy as np

import matplotlib
import matplotlib.gridspec as gs
#import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Patch
import matplotlib.colors as colors
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar

import src.common.CustomMplCanvas as mplc
import src.common.format as fmt

def plot_histogram(parent, app_data, plot_style):
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
        x = get_scatter_data(app_data, plot_style, processed=False)['x']
    else:
        print('processed_data for histogram')
        x = get_scatter_data(app_data, plot_style, processed=True)['x']

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
        method = app_data.cluster_dict['active method']

        # Get the cluster labels for the data
        cluster_color, cluster_label, _ = plot_style.get_cluster_colormap(app_data.cluster_dict[method],alpha=plot_style.marker_alpha)
        cluster_group = app_data.data[app_data.sample_id].processed_data.loc[:,method]
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

    # set y-limits as p-axis min and max in app_data.data[app_data.sample_id].axis_dict
    if app_data.hist_plot_style != 'log-scaling' :
        pflag = False
        if 'pstatus' not in app_data.data[app_data.sample_id].axis_dict[x['field']]:
            pflag = True
        elif app_data.data[app_data.sample_id].axis_dict[x['field']]['pstatus'] == 'auto':
            pflag = True

        if pflag:
            ymin, ymax = canvas.axes.get_ylim()
            d = {'pstatus':'auto', 'pmin':fmt.oround(ymin,order=2,toward=0), 'pmax':fmt.oround(ymax,order=2,toward=1)}
            app_data.data[app_data.sample_id].axis_dict[x['field']].update(d)
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

def add_colorbar(plot_style, canvas, cax, cbartype='continuous', grouplabels=None, groupcolors=None):
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
                    alpha=1
                )
        elif plot_style.cbar_dir == 'horizontal':
            cbar = canvas.fig.colorbar( cax,
                    ax=canvas.axes,
                    orientation=plot_style.cbar_dir,
                    location='bottom',
                    shrink=0.62,
                    fraction=0.1,
                    alpha=1
                )
        else:
            # should never reach this point
            assert plot_style.cbar_dir == 'none', "Colorbar direction is set to none, but is trying to generate anyway."
            return

        cbar.set_label(plot_style.clabel, size=plot_style.font_size)
        cbar.ax.tick_params(labelsize=plot_style.font_size)
        cbar.set_alpha(1)

    # adjust tick marks if labels are given
    if cbartype == 'continuous' or grouplabels is None:
        ticks = None
    # elif cbartype == 'discrete':
    #     ticks = np.arange(0, len(grouplabels))
    #     cbar.set_ticks(ticks=ticks, labels=grouplabels, minor=False)
    #else:
    #    print('(add_colorbar) Unknown type: '+cbartype)

def plot_correlation(parent, app_data, plot_style):
    """Creates an image of the correlation matrix"""
    #print('plot_correlation')

    canvas = mplc.MplCanvas(parent=parent)
    canvas.axes.clear()

    # get the data for computing correlations
    df_filtered, analytes = app_data.data[app_data.sample_id].get_processed_data()

    # Calculate the correlation matrix
    method = app_data.corr_method.lower()
    if app_data.cluster_method not in app_data.data[app_data.sample_id].processed_data.columns:
        correlation_matrix = df_filtered.corr(method=method)
    else:
        algorithm = app_data.cluster_method
        cluster_group = app_data.data[app_data.sample_id].processed_data.loc[:,algorithm]
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

def get_scatter_data(app_data, plot_style, processed=True):

    scatter_dict = {'x': {'type': None, 'field': None, 'label': None, 'array': None},
            'y': {'type': None, 'field': None, 'label': None, 'array': None},
            'z': {'type': None, 'field': None, 'label': None, 'array': None},
            'c': {'type': None, 'field': None, 'label': None, 'array': None}}

    match plot_style.plot_type:
        case 'histogram':
            if processed or app_data.hist_field_type != 'Analyte':
                scatter_dict['x'] = app_data.data[app_data.sample_id].get_vector(app_data.hist_field_type, app_data.hist_field, norm=plot_style.xscale)
            else:
                scatter_dict['x'] = app_data.data[app_data.sample_id].get_vector(app_data.hist_field_type, app_data.hist_field, norm=plot_style.xscale, processed=False)
        # case 'PCA scatter' | 'PCA heatmap':
        #     scatter_dict['x'] = app_data.data[app_data.sample_id].get_vector('PCA score', f'PC{self.spinBoxPCX.value()}', norm=plot_style.xscale)
        #     scatter_dict['y'] = app_data.data[app_data.sample_id].get_vector('PCA score', f'PC{self.spinBoxPCY.value()}', norm=plot_style.yscale)
        #     if (self.field_type is None) or (self.comboBoxColorByField.currentText != ''):
        #         scatter_dict['c'] = app_data.data[app_data.sample_id].get_vector(self.field_type, self.field)
        # case _:
        #     scatter_dict['x'] = app_data.data[app_data.sample_id].get_vector(self.comboBoxFieldTypeX.currentText(), self.comboBoxFieldX.currentText(), norm=plot_style.xscale)
        #     scatter_dict['y'] = app_data.data[app_data.sample_id].get_vector(self.comboBoxFieldTypeY.currentText(), self.comboBoxFieldY.currentText(), norm=plot_style.yscale)
        #     if (self.field_type is not None) and (self.field_type != ''):
        #         scatter_dict['z'] = app_data.data[app_data.sample_id].get_vector(self.comboBoxFieldTypeZ.currentText(), self.comboBoxFieldZ.currentText(), norm=plot_style.zscale)
        #     elif (self.comboBoxFieldZ.currentText() is not None) and (self.comboBoxFieldZ.currentText() != ''):
        #         scatter_dict['c'] = app_data.data[app_data.sample_id].get_vector(self.field_type, self.field, norm=plot_style.cscale)

    # set axes widgets
    if (scatter_dict['x']['field'] is not None) and (scatter_dict['y']['field'] != ''):
        if scatter_dict['x']['field'] not in app_data.data[app_data.sample_id].axis_dict.keys():
            plot_style.initialize_axis_values(scatter_dict['x']['type'], scatter_dict['x']['field'])
            plot_style.set_axis_widgets('x', scatter_dict['x']['field'])

    if (scatter_dict['y']['field'] is not None) and (scatter_dict['y']['field'] != ''):
        if scatter_dict['y']['field'] not in app_data.data[app_data.sample_id].axis_dict.keys():
            plot_style.initialize_axis_values(scatter_dict['y']['type'], scatter_dict['y']['field'])
            plot_style.set_axis_widgets('y', scatter_dict['y']['field'])

    if (scatter_dict['z']['field'] is not None) and (scatter_dict['z']['field'] != ''):
        if scatter_dict['z']['field'] not in app_data.data[app_data.sample_id].axis_dict.keys():
            plot_style.initialize_axis_values(scatter_dict['z']['type'], scatter_dict['z']['field'])
            plot_style.set_axis_widgets('z', scatter_dict['z']['field'])

    if (scatter_dict['c']['field'] is not None) and (scatter_dict['c']['field'] != ''):
        if scatter_dict['c']['field'] not in app_data.data[app_data.sample_id].axis_dict.keys():
            plot_style.set_color_axis_widgets()
            plot_style.set_axis_widgets('c', scatter_dict['c']['field'])

    return scatter_dict