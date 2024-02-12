#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  2 20:43:59 2023

@author: a1904121
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
    def __init__(self, labels,plot_type= 'scatter',  n=3, dg =0.1, dt=0.1, mul_axis = False):
        """Initialize the Ternary plotting class."""
        self.labels = labels
        self.n = n
        self.plot_type = plot_type
        self.mul_axis = mul_axis
        self.fig, self.axs = self.ternary_axes(labels)
        
        if dg and plot_type == 'scatter':
            self.ternary_grid(spacing=dg)
        if dt and plot_type == 'scatter':
            self.ternary_ticks(spacing=dt)
        

    

    def ternary_ticks(self, spacing=0.1):
        """
        Adds ternary tick marks to ternary axes.
        
        Args:
        - spacing: Distance between tick marks.
        - nvertices: Number of vertices, either 3 for ternary or 4 for quaternary.
        """

        if self.n not in [3, 4]:
            raise ValueError('NVertices can be 3 or 4.')

                
        if self.axs is None:
            self.axs = plt.gca()
        dt = spacing

        # Generate tick mark locations
        xp = np.arange(-0.5 + dt, 0.5, dt)
        ya = np.zeros((3, len(xp)))
        ya[[0, 2], :] = 0.015
        xa = np.zeros_like(ya)
        xa[1, :] = xp
        xa[0, :] = xa[1, :] + ya[0, :] / np.tan(np.pi / 3)
        xa[2, :] = xa[1, :] - ya[0, :] / np.tan(np.pi / 3)
        
        for ax in self.axs:   
            # Add tick marks to the axes
            ax.plot(xa, ya, 'k-', linewidth=1)
            a, b, c = self.xy2tern(xa, ya)
            xb, yb = self.tern2xy(b, a, c)
            xc, yc = self.tern2xy(c, b, a)
            ax.plot(xb, yb, 'k-', linewidth=1)
            ax.plot(xc, yc, 'k-', linewidth=1)
    
            if self.n == 4:
                ax.plot(xa, -ya, 'k-', linewidth=1)
                ax.plot(xb, -yb, 'k-', linewidth=1)
                ax.plot(xc, -yc, 'k-', linewidth=1)

    def ternary_axes(self,Labels):
        """
        Set up ternary plot axes with optional labeling for a quaternary plot.
        
        Args:
        - labels: List of strings for the labels of the axes.
        
        Returns:
        - fig: The matplotlib figure object.
        - ax: The matplotlib axes object.
        """
        
        
        if self.n not in [3, 4]:
            raise ValueError('nvertices can be 3 or 4.')
        

            
        fig = Figure(figsize=(6, 4))
        
        if self.plot_type == 'scatter' or (self.mul_axis is False):
            axs = [fig.add_subplot(111)]
        else: #create 3 sets of axis for heatmaps
            axs = [fig.add_subplot(131), fig.add_subplot(132), fig.add_subplot(133)]
        # if ax is None:
        #     ax = plt.gca()
        
        for ax in axs:    
            ax.axis("off")
            ax.set_aspect("equal")
            w = 0.5
            h = 0.5 / np.tan(np.pi / 6)
        
            # create axes
            ax.plot([-w, 0, w, -w], [0, h, 0, 0], '-k', linewidth=1)
            if self.n == 4:
                ax.plot([-w, 0, w, -w], [0, -h, 0, 0], '-k', linewidth=1)
        
            # Set labels
            ax.text(0, h, Labels[0], ha='center', va='bottom', fontsize=12)
            ax.text(-w*0.85, -h*0.03, Labels[1], ha='right', va='center', fontsize=12)
            ax.text(w*0.85, -h*0.03, Labels[2], ha='left', va='center', fontsize=12)
            if self.n == 4:
                ax.text(0, -h, Labels[3], ha='center', va='top', fontsize=12)
    
        return fig, axs
    
            
            
    def tern2xy(self,a, b, c):
            w = 0.5
            h = 0.5 / np.tan(np.pi/6)
            s = a + b + c
            a = a / s
            b = b / s
            c = c / s
            y = a * h
            x = (1 - b) * h / np.cos(np.pi/6) - y * np.tan(np.pi/6) - w
            return x, y
        
    def xy2tern(self,x, y):
        """
        Converts cartesian (x,y) points to ternary (a,b,c) coordinates. 
        The cartesian origin is defined as the midpoint on the B-C edge.
    
        The order of the axes are as follows:
                         A
                        / \
                       /   \
                      B --- C
        where the cartesian origin is defined at the midpoint between B and C.
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
    
    
    
    def ternary_grid(self, ax=None,spacing=0.1):
        """
        Adds ternary grid lines to ternary axes.
    
        Parameters:
            spacing (float): Grid spacing. Default is 0.1 units.
            nvertices (int): Number of vertices, either 3 or 4.
            ax (matplotlib.axes): Axes object for plotting. If None, the current axes is used.
    
        """
        if self.n not in [3, 4]:
            raise ValueError('nvertices can be 3 or 4.')
    
        if self.axs is None:
            self.axs = plt.gca()
    
        dg = spacing
    
        xa = np.arange(-0.5 + dg, 0.5, dg)
        ya = np.zeros_like(xa)
    
        a, b, c = self.xy2tern(xa, ya)
        xb, yb = self.tern2xy(b, a, c)
        xc, yc = self.tern2xy(c, b, a)
    
        for ax in self.axs:   
            ax.plot([xa, xb], [ya, yb], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
            ax.plot([xb, np.flip(xc)], [yb, np.flip(yc)], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
            ax.plot([xc, xa], [yc, ya], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
        
            if self.n == 4:
                ax.plot([xa, xb], [-ya, -yb], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
                ax.plot([xb, np.flip(xc)], [-yb, -np.flip(yc)], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
                ax.plot([xc, xa], [-yc, -ya], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
    
    
    def ternscatter(self, a, b, c, d=None, size=36, cmap=None, categories=None,labels = False, 
                    alpha=1, symbol='o', ax=None, orientation ='horizontal', ):
        """
        Scatter plot data on ternary axes.
        
        Args:
        ...
        
        Returns:
        t: scatter plot object
        leg: legend (if applicable)
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
            t = self.axs[0].scatter(x, y, s=size, color=cmap(0.5), marker=symbol, alpha=alpha)
            return t
        elif not labels:
            # Handle continuous categories
            norm = plt.Normalize(vmin=np.min(categories), vmax=np.max(categories))
            scalarMappable = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            scalarMappable.set_array(categories)
            cbar = self.fig.colorbar(scalarMappable, ax=self.axs[0], pad=0.1, orientation = orientation)
            self.axs[0].scatter(x, y, c=scalarMappable.to_rgba(categories), s=size, marker=symbol, alpha=alpha)
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
            self.axs[0].scatter(x, y, c=color_values, cmap=cmap_discrete, norm=norm, s=size, marker=symbol, alpha=alpha)
            
            # Create a colorbar with discrete colors
            cbar = self.fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap_discrete), ax=self.axs[0], ticks=(bounds[:-1] + bounds[1:]) / 2, pad=0.1, orientation=orientation)
            cbar.ax.set_xticklabels(unique_categories)  #
            

        return self.axs, cbar
            # # Scatter plot for each category
            # for i, category in enumerate(unique_categories):
            #     # Select data for the current category
            #     indices = np.where(categories == category)
            #     t = self.axs[0].scatter(x[indices], y[indices], c=colors[i], label=category, s=size, marker=symbol, alpha=alpha)
            # return t
    
    def hexagon(self, n):
        # Check if 'n' is a positive integer. If not, raise an error.
        if n <= 0 or int(n) != n:
            raise ValueError('n must be a positive integer.')
        
        # Define rotation angles for the vertices of a hexagon.
        rot = np.linspace(0, 360, 7) * np.pi / 180
        
        # Calculate the coordinates for the first vertex of the hexagon.
        y = 0.5 / (3 * n * np.tan(np.pi / 6))
        x = y * np.tan(np.pi / 6)
        
        # Create hexagon vertices based on the calculated coordinates.
        xv = x * np.cos(rot) - y * np.sin(rot)
        yv = x * np.sin(rot) + y * np.cos(rot)
        
        # Initialize an empty list to store the hexagons.
        hexbin = []
        # Loop over rows of hexagons (j) and individual hexagons within a row (i).
        for j in range(n, 0, -1): #rows
            for i in range(1, j + 2): #columns
                # Calculate the center coordinates for each hexagon.
                hex_center_x = (i - (j + 2) / 2) * 6 * x
                hex_center_y = 3 * (n - j) * y
        
                # Adjust the vertices of the hexagon to its position in the grid.
                hex_xv = xv + hex_center_x
                hex_yv = yv + hex_center_y
        
                # Handle edge cases for hexagons at the bottom edge and corners.
                if j == n:
                    if i == 1:  # Bottom left cell
                        hex_xv = [hex_xv[0], hex_center_x, hex_xv[5], hex_xv[0]]
                        hex_yv = [hex_yv[0], 0, hex_yv[5], hex_yv[0]]
                    elif i == n + 1:  # Bottom right cell
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
                hex_center_y = (3 * (n - j)+1) * y
        
                # Adjust the vertices of the hexagon to its position in the grid.
                hex_xv = xv + hex_center_x
                hex_yv = yv + hex_center_y
                
                # Add the hexagon to the hexbin list.
                hexbin.append({'xv': np.array(hex_xv), 'yv': np.array(hex_yv),'xc': hex_center_x,'yc': hex_center_y})
                

                
            for i in range(2, j+1): #columns
                # Calculate the center coordinates for each hexagon.
                hex_center_x = (i - (j + 2) / 2) * 6 * x
                hex_center_y = (3 * (n - j)+2) * y
        
                # Adjust the vertices of the hexagon to its position in the grid.
                hex_xv = xv + hex_center_x
                hex_yv = yv + hex_center_y
                
                
                # Add the hexagon to the hexbin list.
                hexbin.append({'xv': np.array(hex_xv), 'yv': np.array(hex_yv),'xc': hex_center_x,'yc': hex_center_y})
            
            
        # Add the topmost hexagon (at the top of the ternary plot).
        top_hex_xv = xv
        top_hex_yv = yv + 3 * n * y
        top_hex_xv = [top_hex_xv[3], top_hex_xv[4], 0, top_hex_xv[3]]
        top_hex_yv = [top_hex_yv[3], top_hex_yv[4], 3 * n * y, top_hex_yv[3]]
        
        # Add the top hexagon to the hexbin list.
        hexbin.append({'xv': np.array(top_hex_xv), 'yv': np.array(top_hex_yv),'xc': hex_center_x,'yc': hex_center_y})

        return hexbin
    
    def ternhex(self, a, b, c, val=None, n=10, color_map=None, orientation = 'horizontal'):
        #hexagonal heatmaps
        hexbin = self.hexagon(n)
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
            
            hb['mean'] = np.mean(val[in_bin])
            hb['median'] = np.median(val[in_bin])
            hb['std'] = np.std(val[in_bin])
            plots = ['n','mean', 'median']
        
        hexbin_df = pd.DataFrame(hexbin)
        hexbin_df=hexbin_df.fillna(0)
        # Prepare the colormap
        if color_map is None:
            color_map = cm.get_cmap('virdis')
        
        if (self.mul_axis is False):
            plots = ['n']
        
        
        for ax, k in zip(self.axs[0:len(plots)],plots):
            norm = colors.Normalize(vmin=hexbin_df[k].min(), vmax=hexbin_df[k].max())
            # for hb in hexbin:
            #     ax.fill(hb['xv'], hb['yv'], hb[data_key], edgecolor='none')
            
            for index, hb in hexbin_df.iterrows():
                color = color_map(norm(hb[k]))
                ax.fill(hb['xv'], hb['yv'], color=color, edgecolor='none')
    
            ax.set_aspect('equal', 'box')
            ax.set_title(k)
            plt.colorbar(cm.ScalarMappable(norm=norm, cmap=color_map), ax=ax, fraction=0.046, pad=0.04, orientation=orientation)

    def terncolor(self, a, b, c, ca = [0, 0, 0], cb = [0, 1, 0], cc = [1, 1 ,0], p = [1/3, 1/3, 1/3], cp = []):
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


#    def [ca,cb,cc] = getcmap(cmapname)
#
#    switch cmapname
#        case "kgy"
#            ca = [0 0 0];
#            cb = [0 1 0];
#            cc = [1 1 0];
#        case "ybg"
#            ca = [1 1 0];
#            cb = [0 0 0.5];
#            cc = [0 0.7 0.3];
#        case "ycm"
#            ca = [1 1 0];
#            cb = [0 1 1];
#            cc = [1 0 1];
#        case "grb"
#            ca = [0 1 0];
#            cb = [1 0 0];
#            cc = [0 0 1];
#        otherwise
#            error('Unknown colormap name.');
#    end


    def cplane(self,a,b,c,ca,cb,cc,p,cp):

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

        cval = np.zeros([len(xd),3])
        for i in range(0,3):
            v1 = [xp - x1, yp - y1, cp[i] - cv1[i]]
            v2 = [xp - x2, yp - y2, cp[i] - cv2[i]]

            n = np.cross(v1,v2)

            cval[:,i] = cp[i] + (-n[0]*(xd - xp) - n[1]*(yd - yp))/n[2]
        
        return cval


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
#     # ternscatter(a, b, c,  size=36, color=None, categories=None,alpha=0.2, symbol='o', ax=ax)
#     # ternscatter(a, b, c,  size=36, color=None,alpha=0.2, symbol='o', ax=ax)
#     # plt.show()

# main()
