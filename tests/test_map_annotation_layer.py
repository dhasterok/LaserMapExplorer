"""Annotations are a layer of the sample, shown on every map of it.

Every map of a sample is drawn in the same stage coordinates, so a label or
a distance measurement is as true of one element map as of the next -- the
annotations behave like the sample's other layers (masks, polygons, ROIs)
rather than belonging to whichever plot was on screen when they were made.
An individual entry is switched off in the Info dock's annotations table
when a particular figure should not carry it, and switched back on for the
next.

Before this, nothing persisted at all. ``MplCanvas`` accepted ``plot_id``
and ``sample_obj``, and both ``_store_annotation_in_registry`` and
``_load_annotations_from_registry`` opened with
``if not self.sample_obj or not self.plot_id: return`` -- but no caller
ever passed either, and nothing assigned them afterwards. So the registry
conversion code, ``SampleObj.plot_annotations`` and its four annotation
signals never ran once: an annotation lived on the canvas object and died
with it. Even had it been wired, ``plot_annotations`` was keyed by
``plot_id``, which ``_generate_plot_id`` builds from the *field* among
other things, so Sr88 and Ca43 would have been separate buckets; and
nothing in ``src/project/`` saved it.
"""
import json

import numpy as np
import pandas as pd
import pytest
from matplotlib.backend_bases import MouseEvent
from PyQt6.QtCore import Qt

from src.project.ProjectModel import (
    _processing_state_from_dict,
    _processing_state_to_dict,
)


# ---------------------------------------------------------------------------
# the layer on SampleObj
# ---------------------------------------------------------------------------
@pytest.fixture
def sample(sample_factory, qapp):
    from src.data.DataHandling import LaserSampleObj
    return LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore negatives',
        ref_chem=pd.Series(dtype=float),
    )


def a_text_record(text='note', x=10.0, y=20.0):
    return {'type': 'text', 'text': text, 'position': [[x, y]],
            'style': {'color': '#ff0000', 'font_size': 11.0}}


def test_a_new_sample_has_an_empty_layer(sample):
    assert sample.get_map_annotations() == []


def test_adding_assigns_an_id_and_defaults(sample):
    stored = sample.add_map_annotation(a_text_record())

    assert stored['id']
    assert stored['visible'] is True
    assert stored['created_at'] and stored['modified_at']
    assert sample.get_map_annotations() == [stored]


def test_ids_are_distinct(sample):
    first = sample.add_map_annotation(a_text_record('one'))
    second = sample.add_map_annotation(a_text_record('two'))
    assert first['id'] != second['id']


def test_get_by_id(sample):
    stored = sample.add_map_annotation(a_text_record())
    assert sample.get_map_annotation(stored['id']) is stored
    assert sample.get_map_annotation('nope') is None


def test_update_changes_the_record(sample):
    stored = sample.add_map_annotation(a_text_record())

    assert sample.update_map_annotation(stored['id'], {'visible': False}) is True

    assert sample.get_map_annotation(stored['id'])['visible'] is False
    assert sample.update_map_annotation('nope', {'visible': False}) is False


def test_remove_and_clear(sample):
    first = sample.add_map_annotation(a_text_record('one'))
    sample.add_map_annotation(a_text_record('two'))

    assert sample.remove_map_annotation(first['id']) is True
    assert len(sample.get_map_annotations()) == 1
    assert sample.remove_map_annotation(first['id']) is False

    sample.clear_map_annotations()
    assert sample.get_map_annotations() == []


@pytest.mark.parametrize("change", ['add', 'update', 'remove', 'clear'])
def test_every_change_announces_itself(sample, change):
    """One signal for the whole layer: each listener rebuilds from it."""
    stored = sample.add_map_annotation(a_text_record())
    seen = []
    sample.mapAnnotationsChanged.connect(lambda: seen.append(1))

    {
        'add': lambda: sample.add_map_annotation(a_text_record('another')),
        'update': lambda: sample.update_map_annotation(stored['id'], {'text': 'x'}),
        'remove': lambda: sample.remove_map_annotation(stored['id']),
        'clear': sample.clear_map_annotations,
    }[change]()

    assert len(seen) == 1


def test_records_are_json_ready(sample):
    """They are persisted verbatim, so nothing may be a datetime or tuple."""
    sample.add_map_annotation(a_text_record())
    assert json.loads(json.dumps(sample.get_map_annotations()))


# ---------------------------------------------------------------------------
# making annotations on a map
# ---------------------------------------------------------------------------
@pytest.fixture
def map_window(loaded_window):
    """``(window, data, canvas)`` showing RM01's first field map."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.style_data.plot_type = 'field map'
    window.update_SV()
    return window, window.data['RM01'], window.canvas_widget.current_canvas


def measure(canvas, p1, p2):
    """Draw one distance measurement between two data points."""
    canvas.toggle_tool('distance', True)
    for x, y in (p1, p2):
        event = MouseEvent('button_press_event', canvas, 0, 0, button=1)
        event.inaxes = canvas.axes
        event.xdata, event.ydata = x, y
        canvas.distanceOnClick(event)
    canvas.toggle_tool('distance', False)


def show_field(window, data, index):
    """Switch the field map to another analyte and return the new canvas."""
    window.app_data.c_field = data.processed.match_attribute('data_type', 'Analyte')[index]
    window.update_SV()
    return window.canvas_widget.current_canvas


def test_a_map_canvas_is_given_its_sample(map_window):
    _window, data, canvas = map_window
    assert canvas.sample_obj is data
    assert canvas.is_annotatable() is True


def test_a_distance_joins_the_sample_layer(map_window):
    _window, data, canvas = map_window

    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    records = data.get_map_annotations()
    assert len(records) == 1
    assert records[0]['type'] == 'line'
    assert records[0]['position'] == [[10.0, 10.0], [50.0, 50.0]]
    assert records[0]['text'].strip(), 'the measured distance should be the label'
    assert canvas.annotations[0]['annotation_id'] == records[0]['id']


def test_an_annotation_appears_on_the_next_map(map_window):
    """The reported gap: it used to vanish with the canvas."""
    window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    other = show_field(window, data, 1)

    assert other is not canvas
    assert len(other.annotations) == 1
    assert other.annotations[0]['annotation_id'] == data.get_map_annotations()[0]['id']


def test_it_is_actually_drawn_on_the_next_map(map_window):
    """Not just listed -- the line and its label are real artists on the
    new axes, which is what makes it show up in an export."""
    window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    other = show_field(window, data, 1)

    drawn = other.annotations[0]
    assert drawn['object'] in other.axes.lines
    assert drawn['text_object'] in other.axes.texts


def test_several_annotations_all_travel(map_window):
    window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))
    measure(canvas, (20.0, 60.0), (80.0, 15.0))

    other = show_field(window, data, 1)

    assert len(other.annotations) == 2
    assert [a['annotation_id'] for a in other.annotations] == \
           [r['id'] for r in data.get_map_annotations()]


def test_a_plot_with_its_own_axes_is_not_annotatable(lame_window):
    """A note placed at a concentration pair means nothing on a map, so a
    canvas built without a sample -- scatter, histogram, ternary -- keeps
    its annotations to itself rather than pushing them into the layer."""
    from src.plotting.CustomMplCanvas import MplCanvas

    canvas = MplCanvas(parent=lame_window)

    assert canvas.sample_obj is None
    assert canvas.is_annotatable() is False
    assert canvas._store_map_annotation(
        {'Type': 'text', 'Text': 'note', 'X1': 1.0, 'Y1': 2.0, 'Color': '#000'}
    ) is False


def test_every_stage_coordinate_plot_passes_its_sample():
    """Field, score, cluster and ROI maps all draw the same axes, so each
    one hands the canvas its sample. Guards against a new map plot being
    added without it."""
    import inspect
    import src.plotting.LamePlot as lame_plot

    source = inspect.getsource(lame_plot)
    for function in ('plot_map_mpl', 'plot_score_map', 'plot_cluster_map', 'plot_roi_map'):
        start = source.index(f"def {function}(")
        body = source[start:source.index("\ndef ", start + 1)]
        assert 'sample_obj=data' in body, f"{function} does not pass its sample"


# ---------------------------------------------------------------------------
# hiding one for a single figure
# ---------------------------------------------------------------------------
@pytest.fixture
def annotated(map_window):
    """``(window, data, canvas, dock)`` with one measurement and the dock up."""
    window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))
    window.open_annotation_dock()
    dock = window.annotation_dock
    dock.update_annotation_table()
    return window, data, canvas, dock


def test_the_table_lists_the_annotation(annotated):
    _window, _data, _canvas, dock = annotated
    table = dock.annotations_table

    assert table.rowCount() == 1
    assert table.item(0, 0).text() == 'line'
    assert table.item(0, dock.COL_TEXT).text().strip()


def test_the_table_follows_the_plot(annotated):
    """Its only caller used to be PlotInfoTab.__init__, so it stayed empty."""
    window, data, _canvas, dock = annotated
    show_field(window, data, 1)
    assert dock.annotations_table.rowCount() == 1


def test_the_dock_says_which_annotations_these_are(annotated):
    """Remove reaches every map, so the table says so before it is used."""
    _window, _data, _canvas, dock = annotated
    from src.plotting.AnnotationDock import AnnotationDock
    assert dock.scope_label.text() == AnnotationDock._MAP_SCOPE


def test_hiding_keeps_the_record(annotated):
    """Hiding is for leaving one annotation out of one figure -- the entry
    has to survive it, or it could not be switched back on for the next."""
    _window, data, canvas, dock = annotated

    dock.toggle_annotation(0, 0)

    assert data.get_map_annotations()[0]['visible'] is False
    assert len(data.get_map_annotations()) == 1
    assert canvas.annotations[0]['object'].get_visible() is False


def test_hiding_then_showing_again_restores_it(annotated):
    _window, data, canvas, dock = annotated
    dock.toggle_annotation(0, 0)

    dock.toggle_annotation(2, 0)

    assert data.get_map_annotations()[0]['visible'] is True
    assert canvas.annotations[0]['object'].get_visible() is True


def test_a_hidden_annotation_stays_hidden_on_the_next_map(annotated):
    _window, data, _canvas, dock = annotated
    dock.toggle_annotation(0, 0)

    other = show_field(_window, data, 1)

    assert other.annotations[0]['object'].get_visible() is False


def test_editing_the_label_writes_the_record(annotated):
    from PyQt6.QtWidgets import QTableWidgetItem
    _window, data, _canvas, dock = annotated

    item = dock.annotations_table.item(0, dock.COL_TEXT)
    item.setText('grain width')

    assert data.get_map_annotations()[0]['text'] == 'grain width'


def test_editing_the_line_width_writes_the_record(annotated):
    _window, data, _canvas, dock = annotated

    dock.annotations_table.item(0, dock.COL_WIDTH).setText('4.0')

    assert data.get_map_annotations()[0]['style']['line_width'] == 4.0


def test_changing_the_color_writes_the_record(annotated):
    _window, data, _canvas, dock = annotated

    dock.change_annotation_color('#00ff00', 0)

    assert data.get_map_annotations()[0]['style']['color'] == '#00ff00'


def test_a_bad_number_is_ignored_rather_than_raising(annotated):
    _window, data, _canvas, dock = annotated
    before = data.get_map_annotations()[0]['style']['line_width']

    dock.annotations_table.item(0, dock.COL_WIDTH).setText('wide')

    assert data.get_map_annotations()[0]['style']['line_width'] == before


# ---------------------------------------------------------------------------
# the toolbar actions, which were built and connected to nothing
# ---------------------------------------------------------------------------
def test_select_all_selects_every_row(annotated):
    window, data, canvas, dock = annotated
    measure(canvas, (20.0, 60.0), (80.0, 15.0))
    dock.update_annotation_table()

    dock.action_select_all.trigger()

    assert dock._selected_rows() == [0, 1]


def test_show_hide_toggles_the_selection(annotated):
    _window, data, _canvas, dock = annotated
    dock.annotations_table.selectRow(0)

    dock.action_show_hide.trigger()
    assert data.get_map_annotations()[0]['visible'] is False

    dock.annotations_table.selectRow(0)
    dock.action_show_hide.trigger()
    assert data.get_map_annotations()[0]['visible'] is True


def test_remove_deletes_from_the_layer(annotated):
    """Removing is not hiding: it takes the annotation off every map."""
    window, data, _canvas, dock = annotated
    dock.annotations_table.selectRow(0)

    dock.action_remove.trigger()

    assert data.get_map_annotations() == []
    assert dock.annotations_table.rowCount() == 0
    assert show_field(window, data, 1).annotations == []


def test_remove_handles_several_rows_at_once(annotated):
    """The rows underneath shift as each one goes, so they are resolved to
    annotations before anything is deleted."""
    _window, data, canvas, dock = annotated
    measure(canvas, (20.0, 60.0), (80.0, 15.0))
    measure(canvas, (30.0, 30.0), (70.0, 70.0))
    dock.update_annotation_table()
    dock.action_select_all.trigger()

    dock.action_remove.trigger()

    assert data.get_map_annotations() == []


# ---------------------------------------------------------------------------
# saved with the project
# ---------------------------------------------------------------------------
def test_the_layer_round_trips_through_a_project(map_window):
    window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))
    original = data.get_map_annotations()[0]

    state = data.export_processing_state()
    restored = _processing_state_from_dict(
        json.loads(json.dumps(_processing_state_to_dict(state)))
    )

    assert len(restored.annotations) == 1
    assert restored.annotations[0] == original


def test_applying_a_saved_state_restores_the_layer(sample, map_window):
    """A sample loaded fresh from disk gets its annotations back."""
    _window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))
    state = data.export_processing_state()
    assert sample.get_map_annotations() == []

    sample.apply_processing_state(state)

    assert len(sample.get_map_annotations()) == 1
    assert sample.get_map_annotations()[0]['position'] == [[10.0, 10.0], [50.0, 50.0]]


def test_the_restored_layer_is_independent_of_the_original(sample, map_window):
    """Exported verbatim, but as a copy -- two samples must not share one
    list of records."""
    _window, data, canvas = map_window
    measure(canvas, (10.0, 10.0), (50.0, 50.0))
    sample.apply_processing_state(data.export_processing_state())

    sample.update_map_annotation(sample.get_map_annotations()[0]['id'], {'text': 'changed'})

    assert data.get_map_annotations()[0]['text'] != 'changed'


def test_a_project_without_annotations_loads(sample):
    from src.project.ProjectModel import SampleProcessingState
    sample.apply_processing_state(SampleProcessingState())
    assert sample.get_map_annotations() == []


# ---------------------------------------------------------------------------
# moving an annotation
# ---------------------------------------------------------------------------
# The table had six columns -- Type, Text, Size, Width, Color, Visible --
# and `update_annotation_from_table` handled only text, font size and line
# width, so there was no way to move an annotation once it was placed.
# Position is edited through the record rather than the artist: moving a
# line has to move its label too, and the label's offset is recomputed per
# figure from that figure's own limits.

def test_editing_x1_moves_the_annotation(annotated):
    _window, data, canvas, dock = annotated

    dock.annotations_table.item(0, dock.COL_X1).setText('100')

    assert data.get_map_annotations()[0]['position'] == [[100.0, 10.0], [50.0, 50.0]]
    assert list(canvas.annotations[0]['object'].get_xdata()) == [100.0, 50.0]


def test_editing_y2_moves_only_the_second_endpoint(annotated):
    _window, data, canvas, dock = annotated

    dock.annotations_table.item(0, dock.COL_Y2).setText('75')

    assert data.get_map_annotations()[0]['position'] == [[10.0, 10.0], [50.0, 75.0]]
    assert list(canvas.annotations[0]['object'].get_ydata()) == [10.0, 75.0]


def test_a_moved_annotation_moves_on_every_map(annotated):
    window, data, _canvas, dock = annotated
    dock.annotations_table.item(0, dock.COL_X1).setText('100')

    other = show_field(window, data, 1)

    assert list(other.annotations[0]['object'].get_xdata()) == [100.0, 50.0]


def test_a_non_numeric_position_is_ignored(annotated):
    _window, data, _canvas, dock = annotated
    before = list(data.get_map_annotations()[0]['position'])

    dock.annotations_table.item(0, dock.COL_X1).setText('over there')

    assert data.get_map_annotations()[0]['position'] == before
    # and the cell is put back rather than left holding the rejected text
    assert dock.annotations_table.item(0, dock.COL_X1).text() == '10'


def test_a_text_annotation_has_no_second_endpoint_to_edit(map_window):
    """X2/Y2 and Width mean nothing for a label, so those cells are blank
    and cannot be typed into."""
    window, data, canvas = map_window
    data.add_map_annotation(a_text_record('note', 15.0, 25.0))
    window.open_annotation_dock()
    dock = window.annotation_dock
    dock.update_annotation_table()

    for column in (dock.COL_X2, dock.COL_Y2, dock.COL_WIDTH):
        item = dock.annotations_table.item(0, column)
        assert item.text() == ''
        assert not item.flags() & Qt.ItemFlag.ItemIsEditable

    dock.annotations_table.item(0, dock.COL_X1).setText('33')
    assert data.get_map_annotations()[0]['position'] == [[33.0, 25.0]]


# ---------------------------------------------------------------------------
# plots with their own axes keep their own annotations
# ---------------------------------------------------------------------------
@pytest.fixture
def histogram_window(loaded_window):
    """``(window, data, canvas)`` showing a histogram -- not a map."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    analytes = window.data['RM01'].processed.match_attribute('data_type', 'Analyte')
    window.app_data.x_field_type = 'Analyte'
    window.app_data.x_field = analytes[0]
    window.style_data.plot_type = 'histogram'
    window.update_SV()
    canvas = window.plot_info['figure']
    return window, window.data['RM01'], canvas


def inside(canvas):
    """A point near the middle of `canvas`'s axes.

    A histogram's x-axis is in concentration units -- tens of thousands of
    ppm here -- so an annotation at (1, 2) sits thousands of axis units off
    the left edge. Matplotlib still tries to draw it, at a pixel offset
    large enough to overflow FreeType's fixed-point coordinates
    ("FT_Render_Glyph ... raster overflow"). A click can never land there;
    only a hand-written test can.
    """
    (x0, x1), (y0, y1) = canvas.axes.get_xlim(), canvas.axes.get_ylim()
    return (x0 + x1) / 2, (y0 + y1) / 2


def test_a_plot_with_its_own_axes_gets_its_own_key(histogram_window):
    _window, data, canvas = histogram_window

    assert canvas.annotation_scope() == 'plot'
    assert canvas.plot_key.startswith('RM01:histogram:')
    assert canvas.sample_obj is data


def test_its_annotations_go_to_its_own_list(histogram_window):
    _window, data, canvas = histogram_window

    x, y = inside(canvas)
    canvas._store_map_annotation(
        {'Type': 'text', 'Text': 'spike', 'X1': x, 'Y1': y, 'Color': '#000'})

    assert data.get_map_annotations() == []
    assert len(data.get_plot_annotations(canvas.plot_key)) == 1


def test_a_plot_annotation_does_not_appear_on_a_map(histogram_window):
    window, data, canvas = histogram_window
    x, y = inside(canvas)
    canvas._store_map_annotation(
        {'Type': 'text', 'Text': 'spike', 'X1': x, 'Y1': y, 'Color': '#000'})

    window.style_data.plot_type = 'field map'
    window.update_SV()

    assert window.canvas_widget.current_canvas.annotations == []


def test_the_plot_key_is_the_same_next_time(histogram_window):
    """`_generate_plot_id` appends _1/_2 on collision, so it cannot be the
    key -- the same plot has to resolve to the same string every time."""
    window, data, canvas = histogram_window
    key = canvas.plot_key
    x, y = inside(canvas)
    canvas._store_map_annotation(
        {'Type': 'text', 'Text': 'spike', 'X1': x, 'Y1': y, 'Color': '#000'})

    window.style_data.plot_type = 'field map'
    window.update_SV()
    window.style_data.plot_type = 'histogram'
    window.update_SV()

    returned = window.plot_info['figure']
    assert returned.plot_key == key
    assert len(returned.annotations) == 1
    assert returned.annotations[0]['Text'] == 'spike'


def test_plot_annotations_round_trip_through_a_project(histogram_window):
    _window, data, canvas = histogram_window
    x, y = inside(canvas)
    canvas._store_map_annotation(
        {'Type': 'text', 'Text': 'spike', 'X1': x, 'Y1': y, 'Color': '#000'})

    state = data.export_processing_state()
    restored = _processing_state_from_dict(
        json.loads(json.dumps(_processing_state_to_dict(state)))
    )

    assert list(restored.plot_annotations) == [canvas.plot_key]
    assert restored.plot_annotations[canvas.plot_key][0]['text'] == 'spike'


def test_removing_the_last_one_drops_the_key(histogram_window):
    """An empty list should not be saved for a plot with nothing on it."""
    _window, data, canvas = histogram_window
    x, y = inside(canvas)
    canvas._store_map_annotation(
        {'Type': 'text', 'Text': 'spike', 'X1': x, 'Y1': y, 'Color': '#000'})
    annotation_id = canvas.annotations[0]['annotation_id']

    assert canvas.remove_stored_annotation(annotation_id) is True

    assert data.plot_annotations == {}


def test_the_dock_says_these_are_this_plot_only(histogram_window):
    from src.plotting.AnnotationDock import AnnotationDock
    window, _data, _canvas = histogram_window
    window.open_annotation_dock()

    window.annotation_dock.update_annotation_table()

    assert window.annotation_dock.scope_label.text() == AnnotationDock._PLOT_SCOPE


# ---------------------------------------------------------------------------
# where the annotations actually have to end up
# ---------------------------------------------------------------------------
def test_a_visible_annotation_reaches_the_exported_figure(annotated, tmp_path):
    """`LameIO.save_figure` calls `fig.savefig`, so whatever is on the axes
    is in the file -- and hiding, which only clears an artist's visible
    flag, is what keeps one out of a particular export."""
    window, data, canvas, dock = annotated

    shown = tmp_path / 'shown.png'
    canvas.figure.savefig(shown)

    dock.toggle_annotation(0, 0)
    hidden = tmp_path / 'hidden.png'
    canvas.figure.savefig(hidden)

    data.clear_map_annotations()
    bare = tmp_path / 'bare.png'
    canvas.figure.savefig(bare)

    assert shown.read_bytes() != bare.read_bytes(), 'annotation missing from the export'
    assert hidden.read_bytes() == bare.read_bytes(), 'hidden annotation was exported'


def test_the_pop_out_window_carries_the_annotations(annotated):
    """`PlotWindow` reparents the same canvas, and `redraw_annotations`
    runs first -- it used to add a second set of artists on top.

    The canvas is read fresh rather than taken from the fixture: opening
    a dock resizes the main window, which schedules a replot, so the
    fixture's reference can already be stale by the time this runs.
    """
    from src.plotting.CustomMplCanvas import MplCanvas

    window, _data, _stale, _dock = annotated
    toolbar = window.canvas_widget.toolbar
    canvas = window.canvas_widget.current_canvas
    assert len(canvas.annotations) == 1, 'the measurement should be on this map too'
    lines_before = len(canvas.axes.lines)

    toolbar.move_canvas_to_window()

    popped = toolbar.pop_figure
    try:
        assert popped.findChild(MplCanvas) is canvas
        assert len(canvas.axes.lines) == lines_before, 'annotations were drawn twice'
        assert canvas.annotations[0]['object'] in canvas.axes.lines
    finally:
        popped.close()
