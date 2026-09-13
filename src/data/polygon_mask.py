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


def _contains(verts, points):
    """Which `points` fall inside the polygon `verts`, or None if degenerate."""
    if verts is None or len(verts) < 3:
        return None

    return Path([(x, y) for x, y in verts]).contains_points(points)


def polygon_mask(polygons, array_size, order, n):
    """Combine polygons into a boolean mask over the map's data points.

    Parameters
    ----------
    polygons : list of tuple
        One entry per *enabled* polygon: ``(verts, in_out)`` or
        ``(verts, in_out, group)``. ``verts`` is a sequence of ``(x, y)``
        vertices in pixel-index space, ``in_out`` is ``'in'`` or ``'out'``
        (case-insensitive), and ``group`` is a group id or None for an
        ungrouped polygon. Polygons with fewer than three vertices are ignored.
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
    Linked polygons (those sharing a ``group``) are resolved *within* their
    group first, so an ``'out'`` polygon linked into a group cuts a hole in
    that group's region only::

        include  = U { union(in_g) & ~union(out_g)  for each group g with an 'in' }
                 U { each ungrouped 'in' polygon }
        subtract = U { ungrouped 'out' } U { 'out' of groups with no 'in' }
        mask     = (include, or all-True when nothing is 'in') & ~subtract

    With no groups this reduces to a plain union of the ``'in'`` polygons
    minus the ``'out'`` ones. With no ``'in'`` polygon at all the mask starts
    all-True, so a lone ``'out'`` excludes just its own area rather than
    everything.
    """
    points = pixel_coordinates(array_size, order, n)

    # group id -> {'in': mask, 'out': mask, 'any_in': bool}; ungrouped
    # polygons are collected under the sentinel None.
    groups = {}
    for entry in polygons:
        verts, in_out = entry[0], entry[1]
        group = entry[2] if len(entry) > 2 else None

        contained = _contains(verts, points)
        if contained is None:
            continue

        bucket = groups.setdefault(
            group, {'in': np.zeros(n, dtype=bool), 'out': np.zeros(n, dtype=bool), 'any_in': False}
        )
        if str(in_out).lower() == 'out':
            bucket['out'] |= contained
        else:
            bucket['in'] |= contained
            bucket['any_in'] = True

    include = np.zeros(n, dtype=bool)
    subtract = np.zeros(n, dtype=bool)
    any_in = False

    for group, bucket in groups.items():
        if not bucket['any_in']:
            # Nothing to include here, so these only take away -- whether that
            # is an ungrouped 'out' or a group that holds nothing but 'out's.
            subtract |= bucket['out']
            continue

        any_in = True
        if group is None:
            # Ungrouped polygons don't shield each other: their 'out's apply
            # to the whole map, as they did before linking existed.
            include |= bucket['in']
            subtract |= bucket['out']
        else:
            include |= bucket['in'] & ~bucket['out']

    mask = include if any_in else np.ones(n, dtype=bool)

    return mask & ~subtract
