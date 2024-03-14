#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 2 20:43:59 2023

@author: Shavin Kaluthantri and Derrick Hasterok
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.tri as tri
from scipy.spatial import Delaunay
import matplotlib.tri as mtri
from matplotlib.path import Path
import pandas as pd
import matplotlib.cm as cm
import matplotlib.colors as colors
from matplotlib.colors import BoundaryNorm, ListedColormap
# import ternary
class ternary:
    """Initialize the ternary plotting class.

    :param ax: Axes object for displaying ternary diagram
    :type ax: matplotlib.axes
    :param labels: vertex labels
    :type labels: list of str
    :param plot_type: Defaults to 'scatter'
    :type plot_type: str, optional
    :param style: ternary plot style, ternary (triangle) or quaternary (diamond)
    :type style: str, optional
    :param dg: grid spacing (0,1), Defaults to None
    :type dg: double, optional
    :param dt: tick spacing (0,1), Defaults to None
    :type dt: double, optional
    """
    def __init__(self, ax, labels, plot_type='scatter', style='ternary', grid_spacing=None, tick_spacing=None):
       
        self.labels = labels
        self.style = style 
        self.plot_type = plot_type
        self.ax = ax

        self.ternaxes(labels)
        
        if (grid_spacing is not None) and (plot_type == 'scatter'):
            self.terngrid(spacing=grid_spacing)
        if (tick_spacing is not None) and (plot_type == 'scatter'):
            self.ternticks(spacing=tick_spacing)


    def ternticks(self, spacing=0.1):
        """Adds ternary tick marks to ternary axes.
        
        Updates current ternary axes with tick marks.

        :param spacing: Distance between tick marks.
        :type spacing: double
        """

        if self.style not in [3, 4]:
            raise ValueError('NVertices can be 3 or 4.')

        if self.ax is None:
            self.ax = plt.gca()

        if spacing < 0 or spacing > 1:
            raise ValueError('Tick spacing must be between 0 and 1')

        # Generate tick mark locations
        xp = np.arange(-0.5 + spacing, 0.5, spacing)
        ya = np.zeros((3, len(xp)))
        ya[[0, 2], :] = 0.015
        xa = np.zeros_like(ya)
        xa[1, :] = xp
        xa[0, :] = xa[1, :] + ya[0, :] / np.tan(np.pi / 3)
        xa[2, :] = xa[1, :] - ya[0, :] / np.tan(np.pi / 3)
        
        # Add tick marks to the axes
        self.ax.plot(xa, ya, 'k-', linewidth=1)
        a, b, c = self.xy2tern(xa, ya)
        xb, yb = self.tern2xy(b, a, c)
        xc, yc = self.tern2xy(c, b, a)
        self.ax.plot(xb, yb, 'k-', linewidth=1)
        self.ax.plot(xc, yc, 'k-', linewidth=1)

        if self.style == 'quaternary':
            self.ax.plot(xa, -ya, 'k-', linewidth=1)
            self.ax.plot(xb, -yb, 'k-', linewidth=1)
            self.ax.plot(xc, -yc, 'k-', linewidth=1)


    def ternaxes(self,labels):
        """Set up ternary plot axes with optional labeling for a quaternary plot.
        
        :param labels: List of strings for the labels of the axes.
        :type labels: list(str)
        """
        if self.style not in ['ternary', 'quaternary']:
            raise ValueError("style must be 'ternary' or 'quaternary'.")
            
        #fig = Figure(figsize=(6, 4))
        
        #if self.plot_type == 'scatter':
        #    axs = [fig.add_subplot(111)]
        #else: #create 3 sets of axis for heatmaps
        #    axs = [fig.add_subplot(131), fig.add_subplot(132), fig.add_subplot(133)]
        # if ax is None:
        #     ax = plt.gca()

        #ax = fig.add_subplot()

        self.ax.axis("off")
        self.ax.set_aspect("equal")

        w = 0.5
        h = 0.5 / np.tan(np.pi / 6)
    
        # create axes
        self.ax.plot([-w, 0, w, -w], [0, h, 0, 0], '-k', linewidth=1)
        if self.style == 'quaternary':
            self.ax.plot([-w, 0, w, -w], [0, -h, 0, 0], '-k', linewidth=1)
    
        # Set labels
        self.ax.text(0, h, labels[0], ha='center', va='bottom', fontsize=11)
        self.ax.text(-w*0.85, -h*0.05, labels[1], ha='right', va='center', fontsize=11)
        self.ax.text(w*0.85, -h*0.05, labels[2], ha='left', va='center', fontsize=11)
        if self.style == 'quaternary':
            self.ax.text(0, -h, labels[3], ha='center', va='top', fontsize=11)
        
#        for ax in axs:    
#            ax.axis("off")
#            ax.set_aspect("equal")
#            w = 0.5
#            h = 0.5 / np.tan(np.pi / 6)
#        
#            # create axes
#            ax.plot([-w, 0, w, -w], [0, h, 0, 0], '-k', linewidth=1)
#            if self.style == 'quaternary':
#                ax.plot([-w, 0, w, -w], [0, -h, 0, 0], '-k', linewidth=1)
#        
#            # Set labels
#            ax.text(0, h, labels[0], ha='center', va='bottom', fontsize=11)
#            ax.text(-w*0.85, -h*0.05, labels[1], ha='right', va='center', fontsize=11)
#            ax.text(w*0.85, -h*0.05, labels[2], ha='left', va='center', fontsize=11)
#            if self.style == 'quaternary':
#                ax.text(0, -h, labels[3], ha='center', va='top', fontsize=11)
    
        return self.ax
            
            
    def tern2xy(self,a, b, c):
        """Converts ternary (a,b,c) points to cartesian (x,y) coordinates. 

        The order of the axes are a (top), b (left), and c (right), where
        the Cartesian origin is defined at the midpoint between b and c.
        
        :param a: top vertex coordinates
        :type a: np.array
        :param b: left vertex coordinates
        :type b: np.array
        :param c: right vertex coordinates
        :type c: np.array
        """
        w = 0.5
        h = 0.5 / np.tan(np.pi/6)

        # total
        s = a + b + c

        # normalize coordinates on [0,1]
        a = a / s
        b = b / s
        c = c / s

        # convert to cartesian
        y = a * h
        x = (1 - b) * h / np.cos(np.pi/6) - y * np.tan(np.pi/6) - w

        return x, y
        
    def xy2tern(self,x, y):
        """Converts cartesian (x,y) points to ternary (a,b,c) coordinates. 

        The order of the axes are a (top), b (left), and c (right), where
        the Cartesian origin is defined at the midpoint between b and c.

        :param x: x coordinates
        :type x: np.array
        :param y: y coordinates
        :type y: np.array
        """
        # half-width
        w = 0.5
    
        # vertical scale
        h = 0.5 / np.tan(np.pi / 6)
    
        # convert cartesian coordinates to ternary coordinates
        a = y / h
        b = 1 - (w + x + y * np.tan(np.pi / 6)) * np.cos(np.pi / 6) / h
        c = 1 - a - b
    
        return a, b, c
    
    
    def terngrid(self, spacing=0.1):
        """Adds ternary grid lines to ternary axes.

        Updates current ternary axes with tick marks.
    
        :param spacing: Grid spacing. Default is 0.1 units.
        :type spacing: double
        :param nvertices: Number of vertices, either 3 or 4.
        :type nvertices: int
        """
        if self.style not in ['ternary', 'quaternary']:
            raise ValueError('nvertices can be 3 or 4.')
    
        if self.ax is None:
            self.ax = plt.gca()

        if spacing < 0 or spacing > 1:
            raise ValueError('Grid spacing must be a value between 0 and 1')
    
        xa = np.arange(-0.5 + spacing, 0.5, spacing)
        ya = np.zeros_like(xa)
    
        a, b, c = self.xy2tern(xa, ya)
        xb, yb = self.tern2xy(b, a, c)
        xc, yc = self.tern2xy(c, b, a)
    
        self.ax.plot([xa, xb], [ya, yb], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
        self.ax.plot([xb, np.flip(xc)], [yb, np.flip(yc)], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
        self.ax.plot([xc, xa], [yc, ya], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
    
        if self.style == 'quaternary':
            self.ax.plot([xa, xb], [-ya, -yb], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
            self.ax.plot([xb, np.flip(xc)], [-yb, -np.flip(yc)], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
            self.ax.plot([xc, xa], [-yc, -ya], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
    
    
    def ternscatter(self, a, b, c, d=None, size=36, cmap=None, color=None, categories=None, labels = False,
            alpha=1, marker='o', edgecolors='none', ax=None, orientation ='horizontal'):
        """Scatter plot data on ternary axes.

        Ternary scatter plot, ternscatter() uses many of the same parameters as
        matplotlib scatter.
        
        :param a: coordinate associated with top vertex
        :type a: np.array
        :param b: coordinate associated with left vertex
        :type b: np.array
        :param c: coordinate associated with right vertex
        :type c: np.array
        :param d: coordinate associated with bottom vertex (diamond plot)
        :type d: np.array, optional
        :param size: Marker size (in points), Defaults to 36
        :type size: double, optional
        :param cmap: Colormap, Defaults to None
        :type cmap: matplotlib.Colormap
        :param color: Defaults to None
        :type color: optional
        :param edgecolors: Defaults to None
        :type edgecolors: optional
        :param marker: Symbol used for plotting, Defaults to 'o'
        :type marker: str, optional
        :param categories: Defaults to None
        :type categories: optional
        :param labels:
        :type labels: bool, optional
        
        :return: t, scatter plot object, legend (if applicable)
        """
        if cmap is None:
            cmap = plt.cm.get_cmap('plasma')
            # cmap = cm.get_cmap(cmap)
            
        # if self.ax is None:
        #     self.ax = plt.gca()
        
        if d is None:
            x, y = self.tern2xy(a, b, c)
        else:
            x = np.zeros_like(a)
            y = np.zeros_like(a)
            
            ind = d > 0
            x[~ind], y[~ind] = self.tern2xy(a[~ind], b[~ind], c[~ind])
            x[ind], y[ind] = self.tern2xy(d[ind], b[ind], c[ind])
            y[ind] = -y[ind]
        
        if categories is None:
            if color is None:
                t = self.ax.scatter(x, y, s=size, color=cmap(0.5), marker=marker, edgecolors=edgecolors, alpha=alpha)
            else:
                t = self.ax.scatter(x, y, s=size, color=color, marker=marker, edgecolors=edgecolors, alpha=alpha)
            return t
        elif not labels:
            # Handle continuous categories
            norm = plt.Normalize(vmin=np.min(categories), vmax=np.max(categories))
            scalarMappable = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            scalarMappable.set_array(categories)
            fig = plt.gcf()
            cbar = fig.colorbar(scalarMappable, ax=self.ax, pad=0, shrink=0.50, orientation = orientation)
            self.ax.scatter(x, y, c=scalarMappable.to_rgba(categories), s=size, marker=marker, edgecolors=edgecolors, alpha=alpha)
        else:
            group_cmap = cmap
            # Assuming clusters and categories are the same
            unique_categories = np.unique(categories)
            
            color_mapping = {cluster: i for i, cluster in enumerate(unique_categories)}

            # Apply the mapping to get colors/numbers
            color_values = categories.map(color_mapping)
            
            # Create a list of colors for each category from self.group_cmap
            category_colors = [group_cmap[category] for category in unique_categories]
            
            # Create a discrete colormap
            cmap_discrete = ListedColormap(category_colors)
            
            # Create a normalization object
            bounds = np.arange(len(unique_categories) + 1)
            norm = BoundaryNorm(bounds, cmap_discrete.N)
            
            # Scatter plot using the discrete colormap and normalization
            self.ax.scatter(x, y, c=color_values, cmap=cmap_discrete, norm=norm, s=size, marker=marker, edgecolors=edgecolors, alpha=alpha)
            
            fig = plt.gcf()
            # Create a colorbar with discrete colors
            cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap_discrete), ax=self.ax, ticks=(bounds[:-1] + bounds[1:]) / 2, pad=0.1, orientation=orientation)
            cbar.ax.set_xticklabels(unique_categories)  #
            

        return self.ax, cbar
            # # Scatter plot for each category
            # for i, category in enumerate(unique_categories):
            #     # Select data for the current category
            #     indices = np.where(categories == category)
            #     t = self.ax.scatter(x[indices], y[indices], c=colors[i], label=category, s=size, marker=marker, alpha=alpha)
            # return t
    
    def hexagon(self, bins):
        """Creates hexagonal bins within a ternary
        
        :param n: Hexagonal cell resolution, equivalent to n+1 cells across the bottom
            ternary axis            
        :type n: int

        :return: hexbin, Dictionary of hexagonal bins, including verticies, in Cartesian
            coordinates and the center of each cell
        :rtype: dict
        """
        # Check if 'n' is a positive integer. If not, raise an error.
        if bins <= 0 or int(bins) != bins:
            raise ValueError('bins must be a positive integer.')
        
        # Define rotation angles for the vertices of a hexagon.
        rot = np.linspace(0, 360, 7) * np.pi / 180
        
        # Calculate the coordinates for the first vertex of the hexagon.
        y = 0.5 / (3 * bins * np.tan(np.pi / 6))
        x = y * np.tan(np.pi / 6)
        
        # Create hexagon vertices based on the calculated coordinates.
        xv = x * np.cos(rot) - y * np.sin(rot)
        yv = x * np.sin(rot) + y * np.cos(rot)
        
        # Initialize an empty list to store the hexagons.
        hexbin = []
        # Loop over rows of hexagons (j) and individual hexagons within a row (i).
        for j in range(bins, 0, -1): #rows
            for i in range(1, j + 2): #columns
                # Calculate the center coordinates for each hexagon.
                hex_center_x = (i - (j + 2) / 2) * 6 * x
                hex_center_y = 3 * (bins - j) * y
        
                # Adjust the vertices of the hexagon to its position in the grid.
                hex_xv = xv + hex_center_x
                hex_yv = yv + hex_center_y
        
                # Handle edge cases for hexagons at the bottom edge and corners.
                if j == bins:
                    if i == 1:  # Bottom left cell
                        hex_xv = [hex_xv[0], hex_center_x, hex_xv[5], hex_xv[0]]
                        hex_yv = [hex_yv[0], 0, hex_yv[5], hex_yv[0]]
                    elif i == bins + 1:  # Bottom right cell
                        hex_xv = [hex_xv[2], hex_xv[1], hex_center_x, hex_xv[2]]
                        hex_yv = [hex_yv[2], hex_yv[1], 0, hex_yv[2]]
                    else:  # Bottom cells
                        hex_xv = [hex_xv[5], hex_xv[0], hex_xv[1], hex_xv[2], hex_xv[5]]
                        hex_yv = [hex_yv[5], hex_yv[0], hex_yv[1], hex_yv[2], hex_yv[5]]
                else:
                    if i ==1:  # Left cells
                        hex_xv = [hex_xv[3], hex_xv[4], hex_xv[5], hex_xv[0], hex_xv[3]]
                        hex_yv = [hex_yv[3], hex_yv[4], hex_yv[5], hex_yv[0], hex_yv[3]]
                        
                    if i ==j+1:  # Left cells
                        hex_xv = [hex_xv[4], hex_xv[1], hex_xv[2], hex_xv[3], hex_xv[4]]
                        hex_yv = [hex_yv[4], hex_yv[1], hex_yv[2], hex_yv[3], hex_yv[4]]
        
                # Add the hexagon to the hexbin list.
                hexbin.append({'xv': np.array(hex_xv), 'yv': np.array(hex_yv),'xc': hex_center_x,'yc': hex_center_y})
                
            for i in range(1, j + 1): #columns
                # Calculate the center coordinates for each hexagon.
                hex_center_x = (i - (j + 1) / 2) * 6 * x
                hex_center_y = (3 * (bins - j)+1) * y
        
                # Adjust the vertices of the hexagon to its position in the grid.
                hex_xv = xv + hex_center_x
                hex_yv = yv + hex_center_y
                
                # Add the hexagon to the hexbin list.
                hexbin.append({'xv': np.array(hex_xv), 'yv': np.array(hex_yv),'xc': hex_center_x,'yc': hex_center_y})
                

                
            for i in range(2, j+1): #columns
                # Calculate the center coordinates for each hexagon.
                hex_center_x = (i - (j + 2) / 2) * 6 * x
                hex_center_y = (3 * (bins - j)+2) * y
        
                # Adjust the vertices of the hexagon to its position in the grid.
                hex_xv = xv + hex_center_x
                hex_yv = yv + hex_center_y
                
                
                # Add the hexagon to the hexbin list.
                hexbin.append({'xv': np.array(hex_xv), 'yv': np.array(hex_yv),'xc': hex_center_x,'yc': hex_center_y})
            
            
        # Add the topmost hexagon (at the top of the ternary plot).
        top_hex_xv = xv
        top_hex_yv = yv + 3 * bins * y
        top_hex_xv = [top_hex_xv[3], top_hex_xv[4], 0, top_hex_xv[3]]
        top_hex_yv = [top_hex_yv[3], top_hex_yv[4], 3 * bins * y, top_hex_yv[3]]
        
        # Add the top hexagon to the hexbin list.
        hexbin.append({'xv': np.array(top_hex_xv), 'yv': np.array(top_hex_yv),'xc': hex_center_x,'yc': hex_center_y})

        return hexbin
    
    def ternhex(self, a=None, b=None, c=None, val=None, hexbin_df=None, plotfield=None, bins=10, cmap=None, orientation='horizontal'):
        """Creates a heatmap from a set of hexgonal bins
        
        :param a: locations of points within a ternary system, not needed if hexbin_df is provided,
            Defaults to None
        :type a: np.array
        :param b: locations of points within a ternary system, not needed if hexbin_df is provided,
            Defaults to None
        :type b: np.array
        :param c: locations of points within a ternary system, not needed if hexbin_df is provided,
            Defaults to None
        :type c: np.array
        :param val: a fourth-dimension, compute statistics of val within each hexbin,
            not supplied if hexbin_df is provided, Defaults to None
        :type val: np.array
        :param hexbin_df: a data frame containing statistics from a previously call to ternhex, in this case,
            do not supply a, b, c, or val, Defaults to None
        :type hexbin_df: pandas.DataFrame
        :param plotfield: field in hexbin_df to plot, values may include ['n', 'mean', 'median', 'std']
            if None, no plot is produced, but hexbin_df is returned, Defaults to None
        :type plotfield: str
        :param bins: resolution factor (bins+1 hexagons across bottom axis)
        :type bins: int
        :param cmap: colormap, Defaults to None
        :type cmap: 
        :param orientation: orientation of colormap, 'horizontal' (default) or vertical
        :type orientation: str
        """

        if hexbin_df is None:
            #hexagonal heatmaps
            hexbin = self.hexagon(bins)
            if val is None:
                val = np.column_stack((a,b,c))
            
            x, y = self.tern2xy(a, b, c)

            for i, hb in enumerate(hexbin):
                # Assuming hb['xv'] and hb['yv'] are lists of x and y coordinates
                vertices = np.column_stack((hb['xv'], hb['yv']))  # Combine into Nx2 array
                
                # Create the Path object
                hex_path = Path(vertices)
                
                # Check if points are inside the hexagon
                in_bin = hex_path.contains_points(np.column_stack([x, y]))
                hb['n'] = np.sum(in_bin)
                
                # if a fourth-dimension is provided, compute statists within each bin
                if val is not None:
                    hb['mean'] = np.mean(val[in_bin])
                    hb['median'] = np.median(val[in_bin])
                    hb['std'] = np.std(val[in_bin])
            
            hexbin_df = pd.DataFrame(hexbin)
            hexbin_df = hexbin_df.fillna(0)
        
        # if plots is not provided, return hexbin_df
        if plotfield is None:
            return hexbin_df

        # Prepare the colormap
        if cmap is None:
            cmap = cm.get_cmap('virdis')
        else:
            cmap = cm.get_cmap(cmap)
        
        norm = colors.Normalize(vmin=hexbin_df[plotfield].min(), vmax=hexbin_df[plotfield].max())

        # for hb in hexbin:
        #     ax.fill(hb['xv'], hb['yv'], hb[data_key], edgecolor='none')
        
        for _, row in hexbin_df.iterrows():
            color = cmap(norm(row['n']))
            self.ax.fill(row['xv'], row['yv'], color=color, edgecolor='none')

        self.ax.set_aspect('equal', 'box')
        self.ax.set_title(plotfield)
        cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=self.ax, fraction=0.046, pad=0.04, orientation=orientation)

        return hexbin_df, cbar

    def terncolor(self, a, b, c, ca=[1,1,0], cb=[0.3,0.73,0.1], cc=[0,0,0.15], p=[1/3,1/3,1/3], cp = []):
        """Computes colors using a ternary colormap

        Given four colors, one for each vertex of a ternary and a fourth at an arbitrary
        location within the triangle, the function computes a gradient for any set of points
        within the triangle.  Default color scheme is yellow-green-navy.
        
        :param a: a coordinate of data points where color is computed
        :type a: np.array
        :param b: b coordinate of data points where color is computed
        :type b: np.array
        :param c: c coordinate of data points where color is computed
        :type c: np.array
        :param ca: color at top vertex, Defaults to [0.3,0.73,0.1]
        :type ca: np.array, optional
        :param cb: color at left vertex, Defaults to [0,0,0.15]
        :type cb: np.array, optional
        :param cc: color at right vertex, Defaults to [1/3,1/3,1/3]
        :type cc: np.array, optional
        :param p: location of point within ternary associated with cp
        :type p: np.array, optional
        :param cp: color at p, default is [], which will use average of colors
        :type cp: np.array, optional

        :return: cval, colors at (a,b,c)
        :rtype: np.array
        """
        # normalize ternary coordinates
    
        T = np.array(a) + np.array( b) + np.array(c)
        a = a/T
        b = b/T
        c = c/T
        p = np.array(p)

        ca = np.array(ca)
        cb = np.array(cb)
        cc = np.array(cc)
        cp = np.array(cp)


        if len(cp) == 0:
            cp = (ca + cb + cc)/3
        
        cval = self.cplane(a,b,c,ca,cb,cc,p,cp)
        
        return cval


    def cplane(self,a,b,c,ca,cb,cc,p,cp):
        """Determines colors for a set of points (a,b,c) within a ternary
        
        Given four colors, one for each vertex of a ternary and a fourth at an arbitrary
        location within the triangle, the function computes a gradient for any set of points
        within the triangle.
        
        :param a: a coordinate of data points where color is computed
        :type a: np.array
        :param b: b coordinate of data points where color is computed
        :type b: np.array
        :param c: c coordinate of data points where color is computed
        :type c: np.array
        :param ca: color at each vertex a
        :type ca: np.array
        :param cb: color at each vertex b
        :type cb: np.array
        :param cc: color at each vertex c
        :type cc: np.array
        :param p: location of point within ternary
        :type p: np.array
        :param cp: color at p
        :type cp: np.array

        :return: cval, colors at (a,b,c)
        :rtype: np.array
        """
        [xp,yp] = self.tern2xy(p[0],p[1],p[2])

        [xa,ya] = self.tern2xy(1,0,0)
        ya += 1e-8
        [xb,yb] = self.tern2xy(0,1,0)
        xb -= 1e-8
        yb -= 1e-12
        [xc,yc] = self.tern2xy(0,0,1)
        xc += 1e-8
        yc -= 1e-12

        [xd,yd] = self.tern2xy(a,b,c)

        cval = np.zeros([len(a),3])
        points = np.column_stack((xd,yd))
        # points = [Point(xd[i],yd[i]) for i in range(len(xd))]
        p = Path([ [xa, ya],[xb, yb],[xp, yp] ])
        inpoly = p.contains_points(points)
        # poly = Polygon([ [xa, ya],[xb, yb],[xp, yp] ])
        # inpoly = [(poly.contains(point) or poly.intersects(point)) for point in points] 
        cval[inpoly,:] = self.cplanexy(xd[inpoly],yd[inpoly],xp,yp,cp,xa,ya,ca,xb,yb,cb)

        p = Path([[xa, ya],[xc, yc],[xp, yp]])
        inpoly = p.contains_points(points)
        # poly = Polygon([ [xa, ya],[xc, yc],[xp, yp] ])
        # inpoly = [(poly.contains(point) or poly.intersects(point)) for point in points] 
        cval[inpoly,:] = self.cplanexy(xd[inpoly],yd[inpoly],xp,yp,cp,xa,ya,ca,xc,yc,cc)
        
        p = Path([[xc, yc],[xb, yb],[xp, yp]])
        inpoly = p.contains_points(points)
        # poly = Polygon([ [xc, yc],[xb, yb],[xp, yp] ])
        # inpoly = [(poly.contains(point) or poly.intersects(point)) for point in points] 
        cval[inpoly,:] = self.cplanexy(xd[inpoly],yd[inpoly],xp,yp,cp, xc,yc,cc, xb,yb,cb)
        
        cval[cval<0] = 0
        cval[cval>1] = 1
        return cval


    def cplanexy(self, xd,yd, xp,yp,cp, x1,y1,cv1, x2,y2,cv2):
        """Fits a plane to (x,y,color) data
        
        Fits a plane using three points in (x,y,color) space and then interpolates the
        color of know points.

        :param xd: x Cartesian coordinates for data within ternary
        :type xd: np.array
        :param yd: y Cartesian coordinates for data within ternary
        :type yd: np.array
        :param xp: x coordinate of point within ternary
        :type xp: double
        :param yp: y coordinate of point within ternary
        :type yp: double
        :param cp: color at point within ternary
        :type cp: np.array
        :param x1: x coordinate at ternary vertex 1
        :type x1: double
        :param y1: y coordinate at ternary vertex 1
        :type y1: double
        :param cv1: color at vertex 1
        :type cv1: np.array
        :param x2: x coordinate at ternary vertex 2
        :type x2: double
        :param y2: y coordinate at ternary vertex 2
        :type y2: double
        :param cv2: color at vertex 2
        :type cv2: np.array

        :return: cval, colors at (a,b,c)
        :rtype: np.array
        """
        cval = np.zeros([len(xd),3])
        for i in range(0,3):
            v1 = [xp - x1, yp - y1, cp[i] - cv1[i]]
            v2 = [xp - x2, yp - y2, cp[i] - cv2[i]]

            n = np.cross(v1,v2)

            cval[:,i] = cp[i] + (-n[0]*(xd - xp) - n[1]*(yd - yp))/n[2]
        
        return cval

    def ternmap(self, x,y, a,b,c, ca=[1,1,0], cb=[0.3,0.73,0.1], cc=[0,0,0.15], p=[1/3,1/3,1/3], cp = []):
        """Generates a raster map colored by position within a ternary plot.
        
        """

        return cb


# # # Example usage
# # t_plot = ternary(['A', 'B', 'C'], 'heatmap')
# # a, b, c = np.random.rand(3, 100)  # Example data
# # values = np.random.rand(100)      # Example values for heatmap
# t_plot.ternhex(a, b, c, n=10)



# Example Usage
# ternary = ternary(["A", "B", "C"])

# Test data
# a = np.random.rand(100)
# b = np.random.rand(100)
# c = 1 - a - b
# val = np.random.rand(100)

# # Plot
# # ternary.ternsurf(a, b, c, val, 0.05)  # Using dt=0.05

# # import ternary
# scale = 40
# figure, tax = ternary.figure(scale=scale)

# tax.set_title("Ternary Heatmap")
# tax.boundary(linewidth=2.0)
# tax.gridlines(multiple=5, color="blue")

# # Define the heatmap style
# if style == 'triangle':
#     d = tax.heatmapf(sample_function, boundary=True, style="triangular")

# Example usage
# labels = ["A", "B", "C"]
# ternary_plot = ternary(labels)
# a, b, c = np.random.rand(3, 100) # Generate some random data
# values = np.random.rand(100)  # Corresponding values
# ternary_plot.ternheatmap(a, b, c, values, scale=10, cmap='viridis')
# # ternary_plot.ternscatter(a, b, c, size=100)
# plt.show()



# def main():
#     Labels = ["A", "B", "C", "D"]
    
#     # Example usage:
    # labels = ["A", "B", "C"]
    # ternary_plot = ternary(labels)
    
    # a, b, c = np.random.rand(3, 100) # Generate some random data
    # ternary_plot.ternscatter(a, b, c, size=100)
    # plt.show(ternary_plot.fig)
#     # d = sample_data[:,3]
#     # ternscatter(a, b, c,  size=36, color=None, categories=None,alpha=0.2, marker='o', ax=ax)
#     # ternscatter(a, b, c,  size=36, color=None,alpha=0.2, marker='o', ax=ax)
#     # plt.show()

# main()
