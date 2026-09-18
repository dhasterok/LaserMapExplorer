"""Tests for polygon vertex editing.

Three layers, bottom up:

* the Qt-free hit-testing helpers in ``src/data/polygon_edit.py``;
* the vertex operations on ``SerializablePolygon``;
* ``PolygonManager``'s Move / Add / Remove Point modes, driven headlessly by
  synthetic matplotlib mouse events on an Agg canvas (no Qt), which is how
  the toolbar buttons reach the geometry.
"""
import pickle
from types import SimpleNamespace

import matplotlib
matplotlib.use('Agg')
import numpy as np
import pytest
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from src.data.polygon_edit import nearest_segment, nearest_vertex, point_segment_distance
from src.data.Polygon import PolygonManager, SerializablePolygon, detached_copy

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


# ---------------------------------------------------------------------------
# polygon_edit helpers
# ---------------------------------------------------------------------------
def test_nearest_vertex_picks_the_closest_one():
    assert nearest_vertex(SQUARE, (9.0, 9.5)) == 2
    assert nearest_vertex(SQUARE, (0.4, 0.1)) == 0


def test_nearest_vertex_respects_the_threshold():
    assert nearest_vertex(SQUARE, (5.0, 5.0), max_dist=1.0) is None
    assert nearest_vertex(SQUARE, (9.5, 9.5), max_dist=1.0) == 2
    assert nearest_vertex([], (0.0, 0.0)) is None


def test_point_segment_distance_projects_onto_the_interior():
    # perpendicular foot lands inside the segment
    assert point_segment_distance((5.0, 3.0), (0.0, 0.0), (10.0, 0.0)) == pytest.approx(3.0)


def test_point_segment_distance_falls_back_to_the_nearer_endpoint():
    # beyond the far end: the endpoint-only approximation the old code used
    # would have been right here, but see the interior case above
    assert point_segment_distance((13.0, 4.0), (0.0, 0.0), (10.0, 0.0)) == pytest.approx(5.0)
    # degenerate segment
    assert point_segment_distance((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)) == pytest.approx(5.0)


def test_nearest_segment_finds_the_edge_not_the_nearest_vertex():
    # mid-way along the bottom edge, but nearer to the top-left corner than
    # to either bottom corner would be if we only compared endpoints
    assert nearest_segment(SQUARE, (5.0, 0.5)) == 0    # (0,0)->(10,0)
    assert nearest_segment(SQUARE, (9.5, 5.0)) == 1    # (10,0)->(10,10)
    assert nearest_segment(SQUARE, (5.0, 9.5)) == 2    # (10,10)->(0,10)


def test_nearest_segment_includes_the_closing_edge():
    # the left edge is the last vertex back to the first
    assert nearest_segment(SQUARE, (0.5, 5.0)) == 3
    assert nearest_segment([(0.0, 0.0)], (1.0, 1.0)) is None


# ---------------------------------------------------------------------------
# SerializablePolygon vertex operations
# ---------------------------------------------------------------------------
def test_add_vertex_inserts_after_the_given_index():
    polygon = SerializablePolygon(1, list(SQUARE))

    new_idx = polygon.add_vertex(0, (5, 0))

    assert new_idx == 1
    assert polygon.verts[1] == (5.0, 0.0)
    assert len(polygon.verts) == 5


def test_add_vertex_on_the_closing_edge_appends():
    polygon = SerializablePolygon(1, list(SQUARE))

    assert polygon.add_vertex(3, (0, 5)) == 4
    assert polygon.verts[-1] == (0.0, 5.0)


def test_remove_vertex_keeps_at_least_three():
    polygon = SerializablePolygon(1, list(SQUARE))

    assert polygon.remove_vertex(1) is True
    assert polygon.verts == [(0.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert polygon.remove_vertex(0) is False
    assert len(polygon.verts) == 3


def test_translate_shifts_every_vertex():
    polygon = SerializablePolygon(1, list(SQUARE))

    polygon.translate(1.5, -2.0)

    assert polygon.verts == [(1.5, -2.0), (11.5, -2.0), (11.5, 8.0), (1.5, 8.0)]


def test_edited_polygon_is_still_picklable():
    polygon = SerializablePolygon(1, list(SQUARE))
    polygon.add_vertex(0, (5, 0))
    polygon.translate(1, 1)

    restored = pickle.loads(pickle.dumps(detached_copy(polygon)))

    assert restored.verts == polygon.verts


# ---------------------------------------------------------------------------
# PolygonManager edit modes, driven by synthetic canvas events
# ---------------------------------------------------------------------------
class _Canvas(FigureCanvasAgg):
    """The bits of `MplCanvas` the manager touches, on a Qt-free backend."""

    def __init__(self):
        super().__init__(Figure(figsize=(4, 4), dpi=100))
        self.axes = self.figure.add_subplot(111)
        self.axes.set_xlim(-5, 15)
        self.axes.set_ylim(-5, 15)

    def disable_distance_mode(self):
        pass


class _Tab:
    """Records what the manager reports back to its owning tab."""

    def __init__(self):
        self.model_changes = 0
        self.selected_rows = []
        self.exits = 0

    def refresh_polygons(self):
        self.model_changes += 1

    def select_polygon_row(self, p_id):
        self.selected_rows.append(p_id)

    def exit_edit_mode(self):
        self.exits += 1
        self.manager.set_edit_mode(None)


@pytest.fixture
def manager():
    canvas = _Canvas()
    tab = _Tab()
    main_window = SimpleNamespace(app_data=SimpleNamespace(sample_id='S1', sample_list=['S1']))
    mgr = PolygonManager(parent=tab, main_window=main_window)
    tab.manager = mgr
    mgr.polygons['S1'] = {
        1: SerializablePolygon(1, list(SQUARE)),
        2: SerializablePolygon(2, [(12.0, 12.0), (14.0, 12.0), (14.0, 14.0), (12.0, 14.0)]),
    }
    mgr.draw_polygons(canvas, p_id=1)
    canvas.draw()  # transforms need a laid-out figure
    return mgr


def _press(mgr, x, y, button=1):
    px, py = mgr.ax.transData.transform((x, y))
    mgr.onclick(MouseEvent('button_press_event', mgr.canvas, px, py, button=button))


def _move(mgr, x, y):
    px, py = mgr.ax.transData.transform((x, y))
    mgr.onmove(MouseEvent('motion_notify_event', mgr.canvas, px, py, button=1))


def _release(mgr, x, y):
    px, py = mgr.ax.transData.transform((x, y))
    mgr.onrelease(MouseEvent('button_release_event', mgr.canvas, px, py, button=1))


def _key(mgr, key):
    mgr.onkey(KeyEvent('key_press_event', mgr.canvas, key))


def test_move_mode_drags_a_vertex_and_commits_on_release(manager):
    manager.set_edit_mode('move', manager.canvas)
    polygon = manager.polygons['S1'][1]

    _press(manager, 10, 10)          # on vertex 2
    assert manager.dragging_vertex and manager.dragged_idx == 2
    _move(manager, 12, 11)
    assert polygon.verts[2] == (12.0, 11.0)
    # the red handle follows the vertex while dragging
    assert polygon.vertex_markers[2].get_offsets()[0].tolist() == [12.0, 11.0]
    assert manager.parent.model_changes == 0
    _release(manager, 12, 11)

    assert not manager.dragging_vertex
    assert manager.parent.model_changes == 1
    assert polygon.patch.get_xy()[2].tolist() == [12.0, 11.0]


def test_move_mode_drags_the_whole_polygon_from_its_interior(manager):
    manager.set_edit_mode('move', manager.canvas)
    polygon = manager.polygons['S1'][1]

    _press(manager, 5, 5)
    assert manager.dragging_poly
    _move(manager, 6, 7)
    _release(manager, 6, 7)

    assert polygon.verts[0] == pytest.approx((1.0, 2.0))
    assert polygon.verts[2] == pytest.approx((11.0, 12.0))
    assert manager.parent.model_changes == 1


def test_a_click_without_movement_changes_nothing(manager):
    manager.set_edit_mode('move', manager.canvas)
    before = list(manager.polygons['S1'][1].verts)

    _press(manager, 10, 10)
    _release(manager, 10, 10)

    assert manager.polygons['S1'][1].verts == before
    assert manager.parent.model_changes == 0


def test_add_mode_inserts_on_the_nearest_edge(manager):
    manager.set_edit_mode('add', manager.canvas)
    polygon = manager.polygons['S1'][1]

    _press(manager, 5, 0.1)          # on the bottom edge

    assert len(polygon.verts) == 5
    assert polygon.verts[1] == pytest.approx((5.0, 0.1))
    assert len(polygon.vertex_markers) == 5
    assert manager.parent.model_changes == 1


def test_add_mode_far_from_every_edge_selects_instead(manager):
    manager.set_edit_mode('add', manager.canvas)

    _press(manager, 13, 13)          # inside polygon 2, nowhere near polygon 1's edges

    assert len(manager.polygons['S1'][1].verts) == 4
    assert manager.selected_poly is manager.polygons['S1'][2]
    assert manager.parent.selected_rows == [2]
    assert manager.parent.model_changes == 0


def test_remove_mode_drops_the_clicked_vertex_but_keeps_three(manager):
    manager.set_edit_mode('remove', manager.canvas)
    polygon = manager.polygons['S1'][1]

    _press(manager, 10, 0)
    assert polygon.verts == [(0.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert len(polygon.vertex_markers) == 3
    assert manager.parent.model_changes == 1

    _press(manager, 0, 0)            # would leave two vertices
    assert len(polygon.verts) == 3
    assert manager.parent.model_changes == 1


def test_vertex_hit_test_is_in_screen_pixels(manager):
    manager.set_edit_mode('remove', manager.canvas)
    polygon = manager.polygons['S1'][1]
    px, py = manager.ax.transData.transform((10.0, 0.0))

    # just inside the tolerance
    manager.onclick(MouseEvent('button_press_event', manager.canvas,
                               px + PolygonManager.VERTEX_PICK_PX - 1, py, button=1))
    assert len(polygon.verts) == 3
    # well outside it, and outside every polygon: deselects rather than edits
    manager.onclick(MouseEvent('button_press_event', manager.canvas,
                               px + 4 * PolygonManager.VERTEX_PICK_PX, py - 60, button=1))
    assert len(polygon.verts) == 3


def test_clicking_a_polygon_with_no_mode_selects_it_and_syncs_the_table(manager):
    _press(manager, 13, 13)

    selected = manager.polygons['S1'][2]
    assert manager.selected_poly is selected
    assert selected.is_selected and len(selected.vertex_markers) == 4
    assert not manager.polygons['S1'][1].is_selected
    assert manager.polygons['S1'][1].vertex_markers == []
    assert manager.parent.selected_rows == [2]

    _press(manager, -4, -4)          # empty map
    assert manager.selected_poly is None
    assert not selected.is_selected


def test_deselecting_restores_the_group_colour(manager):
    from matplotlib.colors import to_rgba

    polygon = manager.polygons['S1'][1]
    polygon.group = 1
    manager.draw_polygons(manager.canvas, p_id=1)
    assert to_rgba(polygon.patch.get_edgecolor()) == to_rgba('orange')

    _press(manager, -4, -4)

    assert to_rgba(polygon.patch.get_edgecolor()) == to_rgba(PolygonManager.GROUP_COLORS[0])


def test_escape_and_right_click_leave_the_edit_mode(manager):
    manager.set_edit_mode('move', manager.canvas)
    _key(manager, 'escape')
    assert manager.edit_mode is None
    assert manager.parent.exits == 1

    manager.set_edit_mode('add', manager.canvas)
    _press(manager, 5, 5, button=3)
    assert manager.edit_mode is None
    assert manager.parent.exits == 2


def test_edit_mode_survives_a_replot_onto_a_new_canvas(manager):
    manager.set_edit_mode('remove', manager.canvas)

    new_canvas = _Canvas()
    manager.draw_polygons(new_canvas)   # what MainWindow.update_SV does
    new_canvas.draw()

    assert manager.edit_mode == 'remove'
    assert manager.canvas is new_canvas
    assert manager.cid_click is not None
    _press(manager, 10, 0)
    assert len(manager.polygons['S1'][1].verts) == 3


def test_handlers_stay_connected_after_a_polygon_is_finished(manager):
    manager.start_polygon(manager.canvas)
    manager.p_id = 3
    for x, y in [(1, 1), (3, 1), (2, 3)]:
        _press(manager, x, y)
    _press(manager, 2, 2, button=3)

    assert 3 in manager.polygons['S1']
    assert manager.cid_click is not None
    assert manager.selected_poly is manager.polygons['S1'][3]
