"""Polygons saved with a project come back when it is reopened.

The Mask dock is created lazily, the first time the user opens it -- usually
*after* a project's samples have loaded. Polygons used to be read only if the
dock already existed at sample-load time, so in a fresh session they never
loaded at all; the next polygon drawn then reused id 1 and a save overwrote
and deleted the originals.
"""
from src.data.Polygon import SerializablePolygon

SQUARE = [(2.0, 2.0), (12.0, 2.0), (12.0, 12.0), (2.0, 12.0)]
TRIANGLE = [(20.0, 5.0), (30.0, 5.0), (25.0, 15.0)]


def _manager(window):
    return window.mask_dock.polygon_tab.polygon_manager


def _add_polygon(window, verts, sample_id='RM01'):
    manager = _manager(window)
    p_id = manager.increment_pid()
    manager.polygons.setdefault(sample_id, {})[p_id] = SerializablePolygon(p_id, list(verts))
    return p_id


def _saved_project(window, tmp_path):
    """Draw two linked polygons, save, and return the manifest path."""
    window.open_mask_dock()
    _add_polygon(window, SQUARE)
    _add_polygon(window, TRIANGLE)
    _manager(window).link_polygons([1, 2], 'RM01')
    manifest = tmp_path / 'proj' / 'P.lame_project.json'
    window.project_manager.save_project(manifest)
    return manifest


def _reopen_fresh(lame_app, manifest):
    """Open `manifest` in a new window that has never created a Mask dock."""
    from main import MainWindow
    window = MainWindow(lame_app)
    assert not hasattr(window, 'mask_dock')
    window.project_manager.open_project(manifest)
    assert 'RM01' in window.data
    return window


def test_polygons_load_when_mask_dock_opens_after_project(loaded_window, lame_app, tmp_path):
    window, _ = loaded_window
    manifest = _saved_project(window, tmp_path)

    reopened = _reopen_fresh(lame_app, manifest)
    try:
        reopened.open_mask_dock()
        polygons = _manager(reopened).polygons['RM01']

        assert list(polygons) == [1, 2]  # id order, not directory order
        assert polygons[1].verts == SQUARE
        assert polygons[2].verts == TRIANGLE
        assert polygons[1].group == polygons[2].group is not None
        # the mask is rebuilt from them, not left all-True
        assert not reopened.data['RM01'].polygon_mask.all()
    finally:
        reopened.close()


def test_new_polygon_after_reopen_does_not_overwrite_saved_ones(loaded_window, lame_app, tmp_path):
    window, _ = loaded_window
    manifest = _saved_project(window, tmp_path)

    reopened = _reopen_fresh(lame_app, manifest)
    try:
        reopened.open_mask_dock()
        new_id = _add_polygon(reopened, [(40.0, 5.0), (50.0, 5.0), (45.0, 15.0)])
        assert new_id == 3

        reopened.project_manager.save_project()
        poly_dir = manifest.parent / 'P' / 'RM01'
        assert sorted(p.name for p in poly_dir.glob('*.poly')) == [
            'polygon_1.poly', 'polygon_2.poly', 'polygon_3.poly',
        ]
    finally:
        reopened.close()


def test_save_refuses_to_clobber_unread_polygons(loaded_window, tmp_path):
    """Defence in depth: a sample whose saved polygons were never read is not
    written, even if something bypasses loading."""
    window, _ = loaded_window
    manifest = _saved_project(window, tmp_path)
    project_dir = manifest.parent / 'P'

    manager = _manager(window)
    manager.clear_all()  # forget what was loaded, keep the files
    manager.polygons['RM01'] = {1: SerializablePolygon(1, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)])}
    manager.save_polygons(project_dir, 'RM01')

    files = sorted(p.name for p in (project_dir / 'RM01').glob('*.poly'))
    assert files == ['polygon_1.poly', 'polygon_2.poly']
    assert manager.polygons['RM01'][1].verts != SQUARE  # memory untouched...
    import pickle
    with open(project_dir / 'RM01' / 'polygon_1.poly', 'rb') as f:
        assert pickle.load(f).verts == SQUARE  # ...and the file too
