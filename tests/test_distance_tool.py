"""The distance tool measures a new pair of points each time.

Only the first measurement worked. Every click after it was read as the
*second* click of the first measurement, so every distance was drawn from
the point the user had clicked first, once, at the beginning.

``distanceOnClick`` did reset ``first_point`` on the second click -- but
last, after building the annotation record, and two lines of that record
raised:

* ``self.ui.style.font_size`` -- ``MainWindow`` has no ``style``, so this
  resolved to ``QWidget.style``, the *method*, giving
  ``AttributeError: 'builtin_function_or_method' object has no attribute
  'font_size'``. It is ``style_data`` everywhere else in the file.
* ``self.notify_observers(...)`` -- ``MplCanvas`` extends ``FigureCanvas``,
  not ``Observable``, and nothing registers for ``"annotations"``. The
  sibling text-annotation path emits the ``annotationsUpdated`` signal
  declared for exactly this.

Matplotlib runs click handlers inside the Qt event loop, which prints the
traceback to stderr and carries on, so nothing reached the user: the line
and its label were already drawn, and only the reset was skipped.

Switching the tool off was no escape either -- ``disable_distance_mode``
dropped the event connections and left ``first_point`` where it was.
"""
import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent


@pytest.fixture
def map_canvas(loaded_window):
    """``(window, canvas)`` showing RM01's field map with the tool armed."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.style_data.plot_type = 'field map'
    window.update_SV()

    canvas = window.canvas_widget.current_canvas
    assert canvas.map_flag, 'the distance tool only arms on map plots'
    canvas.toggle_tool('distance', True)
    assert canvas.active_tool == 'distance'
    return window, canvas


def click(canvas, x, y):
    """One left-click on the axes at data coordinates ``(x, y)``."""
    event = MouseEvent('button_press_event', canvas, 0, 0, button=1)
    event.inaxes = canvas.axes
    event.xdata, event.ydata = x, y
    canvas.distanceOnClick(event)


def measure(canvas, p1, p2):
    click(canvas, *p1)
    click(canvas, *p2)


def test_one_measurement_records_its_own_endpoints(map_canvas):
    _window, canvas = map_canvas

    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    assert canvas.first_point is None, 'the next click must start a new line'
    assert len(canvas.annotations) == 1
    recorded = canvas.annotations[0]
    assert (recorded['X1'], recorded['Y1']) == (10.0, 10.0)
    assert (recorded['X2'], recorded['Y2']) == (50.0, 50.0)


def test_the_second_measurement_is_independent_of_the_first(map_canvas):
    """The reported bug: the second distance was drawn from (10, 10)."""
    _window, canvas = map_canvas
    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    measure(canvas, (100.0, 100.0), (150.0, 20.0))

    assert len(canvas.annotations) == 2
    second = canvas.annotations[1]
    assert (second['X1'], second['Y1']) == (100.0, 100.0)
    assert (second['X2'], second['Y2']) == (150.0, 20.0)
    # saved_line/saved_dtext are not used on a map: the sample's annotation
    # layer owns those artists (see tests/test_map_annotation_layer.py).
    assert canvas.saved_line == canvas.saved_dtext == []


def test_many_measurements_each_start_fresh(map_canvas):
    _window, canvas = map_canvas
    points = [((i * 10.0, 5.0), (i * 10.0 + 4.0, 25.0)) for i in range(1, 6)]

    for p1, p2 in points:
        measure(canvas, p1, p2)

    assert len(canvas.annotations) == 5
    for (p1, p2), recorded in zip(points, canvas.annotations):
        assert (recorded['X1'], recorded['Y1']) == p1
        assert (recorded['X2'], recorded['Y2']) == p2


def test_the_annotation_record_is_complete(map_canvas):
    """Both failing lines wrote into this dict, so it is what proves they
    are fixed rather than merely moved out of the way."""
    window, canvas = map_canvas

    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    recorded = canvas.annotations[0]
    assert recorded['Type'] == 'line'
    assert recorded['Size'] == window.style_data.font_size
    assert recorded['Color'] == window.style_data.line_color
    assert recorded['Width'] == window.style_data.line_width
    assert recorded['Text'] == recorded['text_object'].get_text()
    assert recorded['Text'].strip(), 'the on-map label should carry the distance'
    assert recorded['Visible'] is True


def test_completing_a_measurement_emits_annotations_updated(map_canvas):
    """What `notify_observers` was reaching for."""
    _window, canvas = map_canvas
    seen = []
    canvas.annotationsUpdated.connect(seen.append)

    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    assert len(seen) == 1
    assert len(seen[0]) == 1


# ---------------------------------------------------------------------------
# switching the tool off
# ---------------------------------------------------------------------------
def test_switching_off_mid_measurement_abandons_it(map_canvas):
    """One click, then the user changes their mind."""
    _window, canvas = map_canvas
    click(canvas, 10.0, 10.0)
    assert canvas.first_point is not None

    canvas.toggle_tool('distance', False)

    assert canvas.first_point is None
    assert canvas.active_tool is None


def test_switching_off_and_on_starts_a_new_measurement(map_canvas):
    """The user's workaround that did not work: the abandoned start point
    used to survive, so the first click after switching back on completed
    the old measurement instead of beginning a new one."""
    _window, canvas = map_canvas
    click(canvas, 10.0, 10.0)

    canvas.toggle_tool('distance', False)
    canvas.toggle_tool('distance', True)
    measure(canvas, (100.0, 100.0), (150.0, 20.0))

    assert len(canvas.annotations) == 1
    recorded = canvas.annotations[0]
    assert (recorded['X1'], recorded['Y1']) == (100.0, 100.0)


def test_switching_off_keeps_finished_measurements(map_canvas):
    """Only the measurement in progress is abandoned."""
    _window, canvas = map_canvas
    measure(canvas, (10.0, 10.0), (50.0, 50.0))

    canvas.toggle_tool('distance', False)

    assert len(canvas.annotations) == 1


def test_switching_off_clears_the_rubber_band(map_canvas):
    """The dashed line and its label follow the cursor between the two
    clicks; they must not be left on the canvas."""
    _window, canvas = map_canvas
    click(canvas, 10.0, 10.0)
    move = MouseEvent('motion_notify_event', canvas, 0, 0)
    move.inaxes = canvas.axes
    move.xdata, move.ydata = 40.0, 40.0
    canvas.distanceOnMove(move)
    assert canvas.line is not None

    canvas.toggle_tool('distance', False)

    assert canvas.line is None and canvas.dtext is None


def test_distance_reset_also_clears_a_pending_measurement(map_canvas):
    """``distance_reset`` is the path the pop-out plot viewer uses."""
    _window, canvas = map_canvas
    click(canvas, 10.0, 10.0)

    canvas.distance_reset()

    assert canvas.first_point is None


# ---------------------------------------------------------------------------
# the measurement itself
# ---------------------------------------------------------------------------
def test_the_distance_is_scaled_by_the_pixel_dimensions(map_canvas):
    """Guards the arithmetic the label reports, not just the bookkeeping."""
    _window, canvas = map_canvas
    canvas.dx, canvas.dy = 2.0, 3.0

    assert canvas.calculate_distance((0.0, 0.0), (3.0, 4.0)) == pytest.approx(
        np.hypot(3.0 * 2.0, 4.0 * 3.0))


def test_a_click_outside_the_axes_is_ignored(map_canvas):
    _window, canvas = map_canvas
    event = MouseEvent('button_press_event', canvas, 0, 0, button=1)
    event.inaxes = None
    event.xdata, event.ydata = None, None

    canvas.distanceOnClick(event)

    assert canvas.first_point is None
    assert canvas.annotations == []
