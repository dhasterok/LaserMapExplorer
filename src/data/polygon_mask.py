"""Polygon mask computation.

Qt-free so it can be tested headlessly -- the GUI side lives in
``src/data/Polygon.py`` (geometry/interaction) and ``PolygonTab``
(``src/data/Masking.py``), which calls :func:`polygon_mask` and stores the
result in ``SampleObj.polygon_mask``.

Polygons combine as a *union* of the ``'in'`` polygons, minus the ``'out'``
ones -- so two separate regions both stay selected, and an ``'out'`` polygon
carves a hole. An earlier version intersected them, which emptied the mask as
soon as two polygons did not overlap.
"""
from __future__ import annotations

import numpy as np
from matplotlib.path import Path


def pixel_coordinates(array_size, order, n):
    """Pixel-centre coordinates of each data point, in imshow's index space.

    Polygon vertices are recorded in the coordinates of the displayed map,
    which ``imshow`` indexes as ``(col, row)`` with pixel centres on integers.
    The image itself is produced by ``np.reshape(values, array_size,
    order=data.order)``, so the data index ``k`` maps to a pixel as:

    - ``order='F'``: ``data[k]`` -> ``matrix[k % nrows, k // nrows]``,
      i.e. ``col = k // nrows``, ``row = k % nrows``
    - ``order='C'``: ``data[k]`` -> ``matrix[k // ncols, k % ncols]``,
      i.e. ``col = k % ncols``, ``row = k // ncols``

    Using this mapping makes containment match what the user drew.

    Parameters
    ----------
    array_size : tuple of int
        ``(nrows, ncols)`` of the map, i.e. ``SampleObj.array_size``.
    order : str
        ``'F'`` or ``'C'``, i.e. ``SampleObj.order``.
    n : int
        Number of data points.

    Returns
    -------
    numpy.ndarray
        ``(n, 2)`` array of ``(col, row)`` pixel centres.
    """
    nrows, ncols = array_size
    k = np.arange(n, dtype=float)
    if order == 'F':
        image_col = k // nrows
        image_row = k % nrows
    else:
        image_col = k % ncols
        image_row = k // ncols

    return np.column_stack([image_col, image_row])


def polygon_mask(polygons, array_size, order, n):
    """Combine polygons into a boolean mask over the map's data points.

    Parameters
    ----------
    polygons : list of tuple
        ``(verts, in_out)`` pairs for the *enabled* polygons only, where
        ``verts`` is a sequence of ``(x, y)`` vertices in pixel-index space and
        ``in_out`` is ``'in'`` or ``'out'`` (case-insensitive). Polygons with
        fewer than three vertices are ignored.
    array_size : tuple of int
        ``(nrows, ncols)`` of the map.
    order : str
        ``'F'`` or ``'C'``.
    n : int
        Number of data points.

    Returns
    -------
    numpy.ndarray
        Boolean array of length ``n``, True where a point is kept.

    Notes
    -----
    With no ``'in'`` polygon the mask starts all-True, so a lone ``'out'``
    polygon excludes just its own area rather than everything.
    """
    points = pixel_coordinates(array_size, order, n)

    inside_in = np.zeros(n, dtype=bool)
    inside_out = np.zeros(n, dtype=bool)
    any_in = False

    for verts, in_out in polygons:
        if verts is None or len(verts) < 3:
            continue

        contained = Path([(x, y) for x, y in verts]).contains_points(points)

        if str(in_out).lower() == 'out':
            inside_out |= contained
        else:
            inside_in |= contained
            any_in = True

    mask = inside_in if any_in else np.ones(n, dtype=bool)

    return mask & ~inside_out
