"""Geometry helpers for editing a polygon's vertices.

Pure functions on plain coordinate lists, with no Qt or matplotlib involved,
so the hit-testing that ``PolygonManager`` does on mouse clicks can be tested
headlessly. Callers pass whatever coordinates suit the tolerance they want:
the manager passes *display pixels* (vertices run through
``ax.transData.transform`` and the event's ``x``/``y``), so a threshold is a
screen distance and does not depend on the axes' units or zoom.
"""
from __future__ import annotations

import numpy as np


def nearest_vertex(verts, xy, max_dist=None):
    """Index of the vertex closest to `xy`.

    Parameters
    ----------
    verts : sequence of (x, y)
        Polygon vertices, in the same coordinate system as `xy`.
    xy : (x, y)
        Query point.
    max_dist : float, optional
        Ignore vertices farther than this. With the default, the nearest
        vertex is returned however far away it is.

    Returns
    -------
    int or None
        Index into `verts`, or None if `verts` is empty or nothing lies
        within `max_dist`.
    """
    pts = np.asarray(verts, dtype=float).reshape(-1, 2)
    if pts.shape[0] == 0:
        return None

    d2 = (pts[:, 0] - xy[0]) ** 2 + (pts[:, 1] - xy[1]) ** 2
    idx = int(np.argmin(d2))
    if max_dist is not None and d2[idx] > float(max_dist) ** 2:
        return None
    return idx


def point_segment_distance(p, a, b):
    """Distance from point `p` to the segment `a`--`b`.

    The true perpendicular distance when the projection of `p` falls inside
    the segment, else the distance to the nearer endpoint. (The pre-refactor
    code approximated this with the endpoint distance alone, which picks the
    wrong edge whenever the click lands mid-way along a long side.)
    """
    px, py = float(p[0]), float(p[1])
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])

    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0.0:
        return float(np.hypot(px - ax, py - ay))

    t = ((px - ax) * dx + (py - ay) * dy) / length2
    t = min(1.0, max(0.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return float(np.hypot(px - cx, py - cy))


def nearest_segment(verts, xy):
    """Index `i` of the closed polygon's edge ``verts[i] -> verts[(i+1) % n]``
    that lies closest to `xy`.

    A new vertex on that edge is inserted at ``i + 1`` (which, for the closing
    edge, appends after the last vertex).

    Returns
    -------
    int or None
        None when there are fewer than two vertices, so there is no edge.
    """
    n = len(verts)
    if n < 2:
        return None

    best_idx, best_dist = None, float('inf')
    for i in range(n):
        d = point_segment_distance(xy, verts[i], verts[(i + 1) % n])
        if d < best_dist:
            best_idx, best_dist = i, d
    return best_idx
