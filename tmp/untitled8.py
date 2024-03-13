#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 15:43:20 2023

@author: a1904121
"""
import random
import ternary
import matplotlib
def generate_random_heatmap_data(scale=5):
    from ternary.helpers import simplex_iterator
    d = dict()
    for (i,j,k) in simplex_iterator(scale):
        d[(i,j)] = random.random()
    return d

scale = 20
d = generate_random_heatmap_data(scale)
figure, tax = ternary.figure(scale=scale)
figure.set_size_inches(10, 8)
tax.heatmap(d, style="t")
tax.boundary()
tax.clear_matplotlib_ticks()
tax.get_axes().axis('off')
tax.set_title("Heatmap Test: Hexagonal")
tax.show()

def simplex_iterator(scale, boundary=True):
    """
    Systematically iterates through a lattice of points on the 2-simplex.

    Parameters
    ----------
    scale: Int
        The normalized scale of the simplex, i.e. N such that points (x,y,z)
        satisify x + y + z == N

    boundary: bool, True
        Include the boundary points (tuples where at least one
        coordinate is zero)

    Yields
    ------
    3-tuples, There are binom(n+2, 2) points (the triangular
    number for scale + 1, less 3*(scale+1) if boundary=False
    """

    start = 0
    if not boundary:
        start = 1
    for i in range(start, scale + (1 - start)):
        for j in range(start, scale + (1 - start) - i):
            k = scale - i - j
            yield (i, j, k)
            
            


import itertools
import numpy as np

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
        return (x + 0.5 * y, np.sqrt(3) / 2 * y)

    simplexes = list(simplex_iterator(scale))
    counts = []

    for simplex in simplexes:
        count = 0
        a, b, c = [simplex_to_2d(*point, scale) for point in itertools.combinations(simplex, 2)]
        for point in scatter_points:
            if point_in_triangle(point, a, b, c):
                count += 1
        counts.append(count)

    return np.mean(counts) if counts else 0


# Example usage
scatter_points = [(0.5, 0.8), (1.2, 0.3), ...]  # Define your scatter points here
mean_count = mean_scatter_points_in_simplex(10, scatter_points)
print("Mean number of scatter points per simplex:", mean_count)