"""Polygons are drawn and edited on the field map only.

Leaving the field map turns polygon mode off, and the polygon tab's own draw
paths (table click, delete, link) do nothing while another plot type is up.
The polygons and their mask survive untouched.
"""
import pytest

from src.data.Polygon import SerializablePolygon


@pytest.fixture
def polygon_window(loaded_window):
    """``(window, tab)`` on a field map, in polygon mode, with one polygon."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.open_mask_dock('polygon')
    tab = window.mask_dock.polygon_tab

    window.control_dock.update_plot_type('field map', force=True)
    window.update_SV()

    tab.polygon_toggle.setChecked(True)
    assert tab.polygon_toggle.isChecked()

    mgr = tab.polygon_manager
    mgr.polygons.setdefault('RM01', {})[1] = SerializablePolygon(
        1, [(1.0, 1.0), (4.0, 1.0), (4.0, 4.0), (1.0, 4.0)])
    tab.refresh_polygons()
    window.update_SV()   # field-map branch draws the polygons
    assert mgr.polygons['RM01'][1].patch is not None
    assert mgr.cid_click is not None
    return window, tab


def test_leaving_the_field_map_turns_polygon_mode_off(polygon_window):
    window, tab = polygon_window
    mgr = tab.polygon_manager
    tab.actionPolyMovePoint.trigger()
    assert mgr.edit_mode == 'move'

    window.control_dock.update_plot_type('histogram', force=True)

    assert not tab.polygon_toggle.isChecked()
    assert mgr.edit_mode is None
    assert not tab.actionPolyMovePoint.isChecked()
    assert mgr.cid_click is None
    # the model and the mask are not what changed
    assert 1 in mgr.polygons['RM01']
    assert not window.data['RM01'].polygon_mask.all()


def test_table_click_does_not_draw_on_a_non_field_map(polygon_window):
    window, tab = polygon_window
    mgr = tab.polygon_manager

    window.control_dock.update_plot_type('histogram', force=True)
    window.update_SV()
    canvas = window.mpl_canvas
    patches_before = list(canvas.axes.patches)

    tab.tableWidgetPolyPoints.selectRow(0)   # -> view_selected_polygon
    tab._redraw_polygons()

    assert list(canvas.axes.patches) == patches_before
    assert mgr.polygons['RM01'][1].patch is None or mgr.polygons['RM01'][1].patch.axes is not canvas.axes


def test_returning_to_the_field_map_draws_the_polygons_again(polygon_window):
    window, tab = polygon_window
    mgr = tab.polygon_manager

    window.control_dock.update_plot_type('histogram', force=True)
    window.update_SV()
    window.control_dock.update_plot_type('field map', force=True)
    tab.polygon_toggle.setChecked(True)
    window.update_SV()

    patch = mgr.polygons['RM01'][1].patch
    assert patch is not None and patch.axes is window.mpl_canvas.axes
    assert mgr.cid_click is not None
