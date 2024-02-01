#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 12:43:45 2023

@author: a1904121
"""

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
# from scipy.spatial import Delaunay
import matplotlib.tri as mtri
from matplotlib.path import Path
import ternary
import itertools

class ternary:
    def __init__(self, labels, n=3, dg =0.1, dt=0.1):
        """Initialize the Ternary plotting class."""
        self.labels = labels
        self.n = n
        
        self.fig, self.ax = self.ternary_axes(labels)
        if dg:
            self.ternary_grid(spacing=dg)
        if dt:
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

                
        if self.ax is None:
            self.ax = plt.gca()
        dt = spacing

        # Generate tick mark locations
        xp = np.arange(-0.5 + dt, 0.5, dt)
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

        if self.n == 4:
            self.ax.plot(xa, -ya, 'k-', linewidth=1)
            self.ax.plot(xb, -yb, 'k-', linewidth=1)
            self.ax.plot(xc, -yc, 'k-', linewidth=1)

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
        

            
        fig = Figure()
        ax = fig.add_subplot(111)
        
        if ax is None:
            ax = plt.gca()
            
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
        ax.text(-w, 0, Labels[1], ha='right', va='center', fontsize=12)
        ax.text(w, 0, Labels[2], ha='left', va='center', fontsize=12)
        if self.n == 4:
            ax.text(0, -h, Labels[3], ha='center', va='top', fontsize=12)
    
        return fig, ax
    
            
            
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
    
        if self.ax is None:
            self.ax = plt.gca()
    
        dg = spacing
    
        xa = np.arange(-0.5 + dg, 0.5, dg)
        ya = np.zeros_like(xa)
    
        a, b, c = self.xy2tern(xa, ya)
        xb, yb = self.tern2xy(b, a, c)
        xc, yc = self.tern2xy(c, b, a)
    
        self.ax.plot([xa, xb], [ya, yb], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
        self.ax.plot([xb, np.flip(xc)], [yb, np.flip(yc)], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
        self.ax.plot([xc, xa], [yc, ya], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
    
        if self.n == 4:
            self.ax.plot([xa, xb], [-ya, -yb], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
            self.ax.plot([xb, np.flip(xc)], [-yb, -np.flip(yc)], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
            self.ax.plot([xc, xa], [-yc, -ya], '-', linewidth=0.25, color=[0.8, 0.8, 0.8])
    
    
    def ternscatter(self, a, b, c, d=None, size=36, color=None, categories=None, 
                    alpha=1, symbol='o', ax=None):
        """
        Scatter plot data on ternary axes.
        
        Args:
        ...
        
        Returns:
        t: scatter plot object
        leg: legend (if applicable)
        """
    
        # if color is None:
            # color = plt.cm.get_cmap('tab10', 1)
            
        if self.ax is None:
            self.ax = plt.gca()
        
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
            t = self.ax.scatter(x, y, s=size, c=color, marker=symbol, alpha=alpha)
            return t
        else:
            # Get unique categories and assign a color to each
            unique_categories = np.unique(categories)
            colors = plt.cm.jet(np.linspace(0, 1, len(unique_categories)))
    
            # Scatter plot for each category
            for i, category in enumerate(unique_categories):
                # Select data for the current category
                indices = np.where(categories == category)
                t = self.ax.scatter(x[indices], y[indices], c=colors[i], label=category, s=size, marker=symbol, alpha=alpha)
            return t


    def ternheatmap(self, a, b, c, values, scale=10, cmap='viridis'):
        """
        Create a heatmap on the ternary plot.
        
        Args:
        - a, b, c: arrays of ternary coordinates.
        - values: array of values corresponding to each point in a, b, c.
        - scale: the resolution of the heatmap.
        - cmap: colormap for the heatmap.
        """
        if self.ax is None:
            self.ax = plt.gca()

        # Convert to Cartesian coordinates for ease of processing
        x, y = self.tern2xy(a, b, c)

        d = mean_scatter_points_in_simplex(10, zip(x,y))



        # Create a triangular grid
        triang = tri.Triangulation(x, y)

        # Calculate the value for each triangle as the average of its vertices
        zvals = np.array([values[triangle].mean() for triangle in triang.triangles])

        # Create the heatmap
        t = self.ax.tricontourf(triang, values, scale, cmap=cmap)
        # self.ax.triplot(triang, 'ko-', markersize=0.5, alpha=0.5)  # Optionally, plot the grid

        return t
    
def point_in_triangle(p, a, b, c):
    """Check if point p is inside the triangle defined by points a, b, c."""
    # Barycentric coordinates
    det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    alpha = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / det
    beta = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / det
    gamma = 1.0 - alpha - beta

    return 0 <= alpha <= 1 and 0 <= beta <= 1 and 0 <= gamma <= 1

def simplex_iterator(scale, boundary=True):
    start = 0
    if not boundary:
        start = 1
    for i in range(start, scale + (1 - start)):
        for j in range(start, scale + (1 - start) - i):
            k = scale - i - j
            yield (i, j, k)

def mean_scatter_points_in_simplex(scale, scatter_points):
    # Convert simplex 3D points to 2D coordinates (for instance, using barycentric coordinates)
    # Here, a simple linear transformation is used for demonstration purposes.
    # This needs to be adapted based on your specific requirements.
    def simplex_to_2d(x, y, z, scale):
        """
        Transforms simplex coordinates (x, y, z) to 2D coordinates.
    
        Parameters:
        x, y, z (float): Coordinates in the simplex space.
        scale (int): The normalized scale of the simplex.
    
        Returns:
        tuple: A tuple representing the 2D coordinates (x', y').
        """
        # Normalize the coordinates
        total = x + y + z
        a = x / total
        b = y / total
        c = z / total
    
        # Constants based on the ternary plot geometry
        w = 0.5
        h = 0.5 / np.tan(np.pi / 6)
    
        # Transform to 2D
        y_2d = a * h
        x_2d = (1 - b) * h / np.cos(np.pi / 6) - y_2d * np.tan(np.pi / 6) - w
    
        # Scale adjustment
        return (x_2d , y_2d )

     # simplexes = list(simplex_iterator(scale))
    counts = []
    d = dict()
    for (i,j,k) in simplex_iterator(scale):
        count = 0
        a, b, c = [(simplex_to_2d(*point, scale)) for point in triangle_coordinates(i,j,k)]
        print(a,b,c)
        for point in scatter_points:
            if point_in_triangle(point, a, b, c):
                count += 1
        
        d[(i,j)] = count
    return d
    
def triangle_coordinates(i, j, k):
    """
    Computes coordinates of the constituent triangles of a triangulation for the
    simplex. These triangles are parallel to the lower axis on the lower side.

    Parameters
    ----------
    i,j,k: enumeration of the desired triangle

    Returns
    -------
    A numpy array of coordinates of the hexagon (unprojected)
    """

    return [(i, j, k), (i + 1, j, k - 1), (i, j + 1, k - 1)]


    # def heron(self,a, b, c):
    #     """Calculate area of a triangle using Heron's formula."""
    #     s = (a + b + c) / 2
    #     return np.sqrt(s * (s - a) * (s - b) * (s - c))
    
    # def ternsurf(self, a, b, c, val, dt, extend=0):
    #     g = np.arange(0, 1 + dt, dt)
    #     n = len(g)
    #     Tv = []

    #     for i in g:
    #         for j in g:
    #             for k in g:
    #                 if abs(i + j + k - 1) <= 0.001 * dt:
    #                     Tv.append([i, j, k])

    #     Tv = np.flipud(np.array(Tv))

    #     # Convert to Cartesian coordinates
    #     xv, yv = self.tern2xy(Tv[:, 0], Tv[:, 1], Tv[:, 2])

    #     # Delaunay triangulation
    #     tri = Delaunay(np.column_stack([xv, yv]))

    #     # Filter triangles based on area
    #     tri_areas = self.heron(
    #         np.linalg.norm(np.column_stack([xv[tri.simplices[:, 0]], yv[tri.simplices[:, 0]]]) -
    #                        np.column_stack([xv[tri.simplices[:, 1]], yv[tri.simplices[:, 1]]]), axis=1),
    #         np.linalg.norm(np.column_stack([xv[tri.simplices[:, 1]], yv[tri.simplices[:, 1]]]) -
    #                        np.column_stack([xv[tri.simplices[:, 2]], yv[tri.simplices[:, 2]]]), axis=1),
    #         np.linalg.norm(np.column_stack([xv[tri.simplices[:, 2]], yv[tri.simplices[:, 2]]]) -
    #                        np.column_stack([xv[tri.simplices[:, 0]], yv[tri.simplices[:, 0]]]), axis=1)
    #     )
    #     area_tolerance = (1e-3 * dt) ** 3
    #     valid_triangles = tri_areas > area_tolerance
    #     tri = tri.simplices[valid_triangles]

    #     # Convert ternary points to Cartesian ignoring NaN values
    #     mask = ~np.isnan(a) & ~np.isnan(b) & ~np.isnan(c) & ~np.isnan(val)
    #     xp, yp = self.tern2xy(a[mask], b[mask], c[mask])
    #     val = val[mask]

    #     # Compute statistics for each triangle
    #     # For simplicity, we compute the mean value in each triangle
    #     tri_means = []
    #     for t in tri:
    #         # Creating a path for each triangle
    #         triangle_path = Path([(xv[t[0]], yv[t[0]]), (xv[t[1]], yv[t[1]]), (xv[t[2]], yv[t[2]]), (xv[t[0]], yv[t[0]])])
    #         # Checking which points are inside the triangle
    #         t_mask = triangle_path.contains_points(np.column_stack((xp, yp)))
    #         tri_means.append(np.mean(val[t_mask]))

    #     # Interpolation
    #     xc = xv[tri].mean(axis=1)
    #     yc = yv[tri].mean(axis=1)
    #     interp = mtri.LinearTriInterpolator(mtri.Triangulation(xc, yc, tri), tri_means)

    #     # Visualization
    #     fig, ax = plt.subplots()
    #     # Creating a uniform grid
    #     xi, yi = np.meshgrid(np.linspace(xv.min(), xv.max(), 100), np.linspace(yv.min(), yv.max(), 100))
    #     zi = interp(xi, yi)

    #     # Plotting
    #     ax.tricontourf(mtri.Triangulation(xv, yv, tri), zi(xi, yi).data, levels=14, cmap='RdYlBu')
    #     ax.set_aspect('equal')
    #     plt.show()



# import ternary
# scale = 40
#     figure, tax = ternary.figure(scale=scale)

#     tax.set_title("Ternary Heatmap")
#     tax.boundary(linewidth=2.0)
#     tax.gridlines(multiple=5, color="blue")

#     # Define the heatmap style
#     if style == 'triangle':
#         d = tax.heatmapf(sample_function, boundary=True, style="triangular")

# Example usage
labels = ["A", "B", "C"]
ternary_plot = ternary(labels)
a, b, c = np.random.rand(3, 100) # Generate some random data
values = np.random.rand(100)  # Corresponding values
ternary_plot.ternheatmap(a, b, c, values, scale=10, cmap='viridis')
# ternary_plot.ternscatter(a, b, c, size=100)
plt.show()



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
