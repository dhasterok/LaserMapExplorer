"""Tests for the polygon model's storage contract (``src/data/Polygon.py``).

Covers the two things a ``.poly`` file depends on: polygons pickled before
``in_out``/``enabled`` existed still load, and live matplotlib artists never
reach the file.
"""
import pickle

from matplotlib.patches import Polygon as MplPolygon

from src.data.Polygon import SerializablePolygon, detached_copy

VERTS = [(1.0, 1.0), (4.0, 1.0), (4.0, 4.0), (1.0, 4.0)]


def test_new_polygon_defaults_to_an_included_enabled_region():
    polygon = SerializablePolygon(1, VERTS)

    assert polygon.in_out == 'in'
    assert polygon.enabled is True
    assert polygon.is_out is False
    assert polygon.display_name == 'Polygon 1'


def test_out_polygon_reports_is_out():
    assert SerializablePolygon(2, VERTS, in_out='out').is_out
    # the table stores 'Out' with a capital
    assert SerializablePolygon(3, VERTS, in_out='Out').is_out


def test_named_polygon_uses_its_name():
    assert SerializablePolygon(4, VERTS, name='Garnet core').display_name == 'Garnet core'


def test_polygon_pickled_before_in_out_existed_still_loads():
    """Old .poly files have no in_out/enabled/name in their instance dict.

    They must fall back to the class-level defaults rather than raising
    AttributeError, which is why those defaults exist.
    """
    legacy = SerializablePolygon(7, VERTS)
    for field in ('in_out', 'enabled', 'name'):
        del legacy.__dict__[field]

    restored = pickle.loads(pickle.dumps(legacy))

    assert 'in_out' not in restored.__dict__  # genuinely an old-shaped object
    assert restored.in_out == 'in'
    assert restored.enabled is True
    assert restored.display_name == 'Polygon 7'


def test_detached_copy_strips_artists_and_leaves_the_original_alone():
    polygon = SerializablePolygon(1, VERTS)
    polygon.patch = MplPolygon(VERTS, closed=True)
    polygon.vertex_markers = ['marker']
    polygon.is_selected = True

    clone = detached_copy(polygon)

    assert clone.patch is None
    assert clone.vertex_markers == []
    assert clone.is_selected is False
    assert clone.verts == polygon.verts
    # the displayed polygon keeps its artists
    assert polygon.patch is not None


def test_detached_copy_is_picklable_without_dragging_in_a_figure():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    try:
        polygon = SerializablePolygon(1, VERTS)
        polygon.patch = MplPolygon(VERTS, closed=True)
        ax.add_patch(polygon.patch)

        blob = pickle.dumps(detached_copy(polygon))
    finally:
        plt.close(fig)

    # A pickled figure runs to hundreds of kilobytes; bare geometry is tiny.
    assert len(blob) < 2000
    assert pickle.loads(blob).verts == VERTS
