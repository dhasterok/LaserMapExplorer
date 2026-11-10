"""Cropping the area of analysis.

Crop restricts a sample to a rectangle of the map; everything downstream --
filters, clustering, stoichiometry, plots -- then works on that region only, and
"Full Map" is the way back.

The tool had stopped working entirely. It was written for pyqtgraph and left
behind when maps moved to matplotlib, so every part of it referred to something
that no longer existed: ``parent.plot.addItem`` (a pyqtgraph PlotItem), PyQt5's
short enum spellings (``Qt.DashLine``), ``parent.actionCrop`` and
``parent.toolbar_action``, and an assignment to the now read-only ``xlim``. It
was also never connected -- the toolbar's Crop action only wrote a log line. On
the data side ``crop_mask``'s setter took two arguments, which a property setter
can never supply, and ``confirm_reset`` called ``.exec()`` on the button that
the *static* ``QMessageBox.warning`` returns, so Full Map raised AttributeError.

These tests pin the behaviour rather than the wreckage: the data-layer crop, the
round trip back to the full map, and that Crop is offered only where there is a
map to crop.
"""
import pathlib

import numpy as np
import pytest
from PyQt6.QtWidgets import QMessageBox

from src.data.DataHandling import LaserSampleObj


SAMPLE = "projects/test_project/RM01/RM01.lame.csv"


@pytest.fixture
def sample(qapp):
    return LaserSampleObj(sample_id="RM01", file_path=SAMPLE,
                          outlier_method='none', negative_method='ignore')


def middle_half(sample):
    """A rectangle covering the central quarter of the map, in data coords."""
    x0, x1 = (float(v) for v in sample.xlim)
    y0, y1 = (float(v) for v in sample.ylim)
    return ((x0 + (x1 - x0) * 0.25, x0 + (x1 - x0) * 0.75),
            (y0 + (y1 - y0) * 0.25, y0 + (y1 - y0) * 0.75))


# --- the data layer ---------------------------------------------------------

def test_crop_reduces_the_sample_to_the_rectangle(sample):
    before = len(sample.processed)
    xlim, ylim = middle_half(sample)

    assert sample.apply_crop(xlim, ylim) is True

    assert len(sample.processed) < before
    assert sample.crop is True
    assert sample.xlim[0] >= xlim[0] and sample.xlim[1] <= xlim[1]
    assert sample.ylim[0] >= ylim[0] and sample.ylim[1] <= ylim[1]


def test_crop_leaves_raw_whole(sample):
    """raw is what reset_crop restores from, so it must not be cropped."""
    before = len(sample.raw)

    sample.apply_crop(*middle_half(sample))

    assert len(sample.raw) == before


def test_cropped_map_is_still_rectangular(sample):
    """A field map is reshaped to (ny, nx); a ragged result raises instead."""
    sample.apply_crop(*middle_half(sample))

    ny, nx = sample.array_size
    assert ny * nx == len(sample.processed)


def test_crop_survives_a_later_prep_data(sample):
    """The crop lives in crop_mask and is reapplied whenever processed is
    rebuilt. Without that, any change of negative handling or autoscaling
    quietly restored the whole map."""
    sample.apply_crop(*middle_half(sample))
    cropped = len(sample.processed)

    sample.prep_data()

    assert len(sample.processed) == cropped


def test_column_attributes_survive_the_crop(sample):
    """Plain pandas indexing drops the AttributeDataFrame subclass, and with it
    every column's data_type, units and bounds."""
    sample.apply_crop(*middle_half(sample))

    assert sample.processed.get_attribute('Xc', 'data_type') == 'coordinate'
    analytes = sample.processed.match_attribute('data_type', 'Analyte')
    assert analytes, "analyte typing was lost"


def test_a_region_with_no_pixels_is_refused(sample):
    """Rather than leaving a sample with nothing in it."""
    before = len(sample.processed)
    x1 = float(sample.xlim[1])
    y1 = float(sample.ylim[1])

    assert sample.apply_crop((x1 + 100, x1 + 200), (y1 + 100, y1 + 200)) is False
    assert len(sample.processed) == before
    assert sample.crop is False


def test_bounds_may_be_given_in_either_order(sample):
    """The rubber band reports whatever corner the drag started from."""
    (x0, x1), (y0, y1) = middle_half(sample)

    sample.apply_crop((x1, x0), (y1, y0))

    assert sample.crop is True
    assert len(sample.processed) < len(sample.raw)


def test_reset_restores_the_full_map(sample, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'warning',
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    full = len(sample.processed)
    size = sample.array_size
    sample.apply_crop(*middle_half(sample))
    assert len(sample.processed) < full

    sample.reset_crop()

    assert len(sample.processed) == full
    assert sample.array_size == size
    assert sample.crop is False
    assert len(sample.crop_mask) == len(sample.raw)
    assert bool(np.asarray(sample.crop_mask).all())


def test_reset_can_be_declined(sample, monkeypatch):
    """confirm_reset used to raise AttributeError whatever the user clicked."""
    monkeypatch.setattr(QMessageBox, 'warning',
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))
    sample.apply_crop(*middle_half(sample))
    cropped = len(sample.processed)

    sample.reset_crop()

    assert len(sample.processed) == cropped, "declining must change nothing"
    assert sample.crop is True


# --- the tool, on a live window --------------------------------------------

@pytest.fixture
def mapped_window(qtbot, app, monkeypatch, dialogs):
    """A window showing RM01 as a field map.

    ``dialogs`` answers Discard to the unsaved-changes prompt: adding a sample
    dirties the project and qtbot's teardown closes the window, so without it
    closeEvent blocks on a modal nothing can click and the run hangs.
    """
    monkeypatch.setattr(QMessageBox, 'warning',
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    from tests.conftest import MainWindow

    window = MainWindow(app)
    qtbot.addWidget(window)
    window.project_manager.add_samples([pathlib.Path(SAMPLE)])
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.style_data.plot_type = 'field map'
    window.update_SV()
    return window


def test_crop_is_offered_on_a_map(mapped_window):
    assert mapped_window.lame_action.Crop.isEnabled()
    assert mapped_window.crop_tool.is_available()


@pytest.mark.parametrize("plot_type", ['histogram', 'correlation', 'scatter', 'heatmap'])
def test_crop_is_not_offered_off_a_map(mapped_window, plot_type):
    """A crop is a region of the sample, which a scatter or histogram has no
    notion of -- the same distinction that governs the scalebar."""
    mapped_window.style_data.plot_type = plot_type
    mapped_window.update_crop_availability()

    assert not mapped_window.lame_action.Crop.isEnabled()
    assert not mapped_window.crop_tool.is_available()


def test_leaving_a_map_abandons_a_live_crop(mapped_window):
    """The rubber band must not outlive the plot it referred to."""
    mapped_window.lame_action.Crop.setChecked(True)
    assert mapped_window.crop_tool.selector is not None

    mapped_window.style_data.plot_type = 'histogram'
    mapped_window.update_crop_availability()

    assert mapped_window.crop_tool.selector is None
    assert not mapped_window.lame_action.Crop.isChecked()


def test_the_toolbar_action_arms_the_rubber_band(mapped_window):
    mapped_window.lame_action.Crop.setChecked(True)

    assert mapped_window.crop_tool.selector is not None
    assert mapped_window.crop_tool.bounds() is not None, "starts on a usable region"


def test_applying_crops_the_sample_and_releases_the_button(mapped_window):
    data = mapped_window.app_data.current_data
    before = len(data.processed)
    mapped_window.lame_action.Crop.setChecked(True)
    x0, _x1 = (float(v) for v in data.xlim)
    y0, _y1 = (float(v) for v in data.ylim)
    mapped_window.crop_tool.selector.extents = (x0 + 100, x0 + 300, y0 + 40, y0 + 140)

    assert mapped_window.crop_tool.apply() is True

    assert len(data.processed) < before
    assert not mapped_window.lame_action.Crop.isChecked()
    assert mapped_window.crop_tool.selector is None
    assert mapped_window.lame_action.FullMap.isEnabled()


def test_releasing_the_mouse_does_not_commit(mapped_window):
    """Cropping discards computed fields, so it waits for Enter rather than
    happening the instant a drag ends."""
    data = mapped_window.app_data.current_data
    before = len(data.processed)
    mapped_window.lame_action.Crop.setChecked(True)
    x0 = float(data.xlim[0])
    y0 = float(data.ylim[0])
    mapped_window.crop_tool.selector.extents = (x0 + 100, x0 + 300, y0 + 40, y0 + 140)

    mapped_window.crop_tool._on_select(None, None)      # what the selector calls

    assert len(data.processed) == before
    assert mapped_window.crop_tool.selector is not None


def _press(dblclick, x, y):
    import types
    return types.SimpleNamespace(dblclick=dblclick, xdata=x, ydata=y)


def _inside(data):
    x0 = float(data.xlim[0])
    y0 = float(data.ylim[0])
    return x0 + 200, y0 + 90


def armed(window):
    """Arms the tool over a known region and returns (data, row count)."""
    data = window.app_data.current_data
    before = len(data.processed)
    window.lame_action.Crop.setChecked(True)
    x0 = float(data.xlim[0])
    y0 = float(data.ylim[0])
    window.crop_tool.selector.extents = (x0 + 100, x0 + 300, y0 + 40, y0 + 140)
    return data, before


def test_double_click_inside_applies(mapped_window):
    """The mouse route matters because Enter only arrives while the canvas holds
    keyboard focus, and clicking the toolbar button leaves focus on the button.
    Mouse events are delivered by position, so this works regardless."""
    data, before = armed(mapped_window)
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(True, x, y))

    assert len(data.processed) < before
    assert not mapped_window.lame_action.Crop.isChecked()


def test_a_single_click_does_not_apply(mapped_window):
    data, before = armed(mapped_window)
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(False, x, y))

    assert len(data.processed) == before
    assert mapped_window.crop_tool.selector is not None


def test_double_click_outside_the_rectangle_does_not_apply(mapped_window):
    """Otherwise a stray double-click anywhere on the map would commit a crop."""
    data, before = armed(mapped_window)
    x0 = float(data.xlim[0])
    y0 = float(data.ylim[0])

    mapped_window.crop_tool._on_press(_press(True, x0 + 400, y0 + 190))

    assert len(data.processed) == before


def test_clicking_the_canvas_claims_keyboard_focus(mapped_window, monkeypatch):
    """Which is what makes the Enter shortcut live.

    Asserted as "focus was asked for" rather than "focus was granted": Qt only
    gives focus inside an active top-level window, and these tests run offscreen
    on a window that is never activated, so hasFocus() is False either way. That
    is precisely why double-click, not Enter, is the primary way to apply.
    """
    data, _before = armed(mapped_window)
    canvas = mapped_window.crop_tool.canvas
    asked = []
    monkeypatch.setattr(canvas, 'setFocus', lambda *a: asked.append(True))
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(False, x, y))

    assert asked, "a press on the map must claim keyboard focus"


def test_the_instruction_is_drawn_on_the_map(mapped_window):
    """The status bar is easy to miss and quickly overwritten, and without being
    told, there is no way to discover how to commit a crop."""
    mapped_window.lame_action.Crop.setChecked(True)
    hint = mapped_window.crop_tool._hint_artist

    assert hint is not None
    text = hint.get_text().lower()
    assert 'double-click' in text and 'enter' in text and 'esc' in text


def test_the_instruction_is_removed_afterwards(mapped_window):
    data, _before = armed(mapped_window)
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(True, x, y))

    assert mapped_window.crop_tool._hint_artist is None


def test_escape_cancels_without_touching_the_data(mapped_window):
    data = mapped_window.app_data.current_data
    before = len(data.processed)
    mapped_window.lame_action.Crop.setChecked(True)

    mapped_window.crop_tool._on_key(type('E', (), {'key': 'escape'})())

    assert len(data.processed) == before
    assert mapped_window.crop_tool.selector is None
    assert not mapped_window.lame_action.Crop.isChecked()


def test_enter_applies(mapped_window):
    data = mapped_window.app_data.current_data
    before = len(data.processed)
    mapped_window.lame_action.Crop.setChecked(True)
    x0 = float(data.xlim[0])
    y0 = float(data.ylim[0])
    mapped_window.crop_tool.selector.extents = (x0 + 100, x0 + 300, y0 + 40, y0 + 140)

    mapped_window.crop_tool._on_key(type('E', (), {'key': 'enter'})())

    assert len(data.processed) < before


def test_unchecking_the_action_cancels(mapped_window):
    data = mapped_window.app_data.current_data
    before = len(data.processed)
    mapped_window.lame_action.Crop.setChecked(True)

    mapped_window.lame_action.Crop.setChecked(False)

    assert mapped_window.crop_tool.selector is None
    assert len(data.processed) == before


def test_the_mask_is_resized_with_the_crop(mapped_window):
    """The combined mask is one entry per *displayed* pixel, and the field map
    reshapes it into array_size. It used to be left at the uncropped length, so
    the first redraw after a crop died with
    ``cannot reshape array of size 29666 into shape (36,4)`` -- the crop
    appeared to do nothing because the plot never completed.
    """
    data, _before = armed(mapped_window)
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(True, x, y))

    ny, nx = data.array_size
    assert len(data.mask) == ny * nx == len(data.processed)
    np.reshape(data.mask, data.array_size, order=data.order)   # must not raise


def test_redraw_after_cropping_succeeds(mapped_window):
    """The end of the reported failure: the map has to come back."""
    data, _before = armed(mapped_window)
    x, y = _inside(data)
    mapped_window.crop_tool._on_press(_press(True, x, y))

    mapped_window.update_SV()

    assert mapped_window.mpl_canvas.axes.get_images(), "the cropped map must draw"


def test_the_mask_survives_a_further_prep_data(mapped_window):
    data, _before = armed(mapped_window)
    x, y = _inside(data)
    mapped_window.crop_tool._on_press(_press(True, x, y))

    data.prep_data()

    ny, nx = data.array_size
    assert len(data.mask) == ny * nx == len(data.processed)


def test_rectangle_is_read_as_pixel_indices_not_microns(mapped_window):
    """A field map is drawn with imshow, so its axes are pixel indices
    (0..nx, 0..ny) -- see LamePlot.plot_map_mpl. Passing those straight to
    apply_crop, which wants Xc/Yc, selected the wrong region (or none at all)
    on any sample whose pixel spacing isn't 1.
    """
    data = mapped_window.app_data.current_data
    mapped_window.lame_action.Crop.setChecked(True)
    xs = np.sort(np.unique(np.asarray(data.processed['Xc'], dtype=float)))
    ys = np.sort(np.unique(np.asarray(data.processed['Yc'], dtype=float)))
    mapped_window.crop_tool.selector.extents = (3, 11, 5, 17)

    (x0, x1), (y0, y1) = mapped_window.crop_tool.data_bounds()

    assert (x0, x1) == (xs[3], xs[11])
    assert (y0, y1) == (ys[5], ys[17])


def test_indices_outside_the_map_are_clamped(mapped_window):
    """A drag can run off the edge of the axes."""
    data = mapped_window.app_data.current_data
    mapped_window.lame_action.Crop.setChecked(True)
    xs = np.sort(np.unique(np.asarray(data.processed['Xc'], dtype=float)))
    mapped_window.crop_tool.selector.extents = (-50, len(xs) + 50, 0, 10)

    (x0, x1), _ylim = mapped_window.crop_tool.data_bounds()

    assert (x0, x1) == (xs[0], xs[-1])


def _axes_fit_the_image(window):
    """True when the axis limits match the drawn image's extent.

    plot_map_mpl sets the axes from style_data.xlim/ylim rather than from the
    data, so a stale value leaves the map floating in empty space instead of
    filling the plot.
    """
    axes = window.mpl_canvas.axes
    x0, x1, y0, y1 = axes.get_images()[0].get_extent()
    ax_x = sorted(axes.get_xlim())
    ax_y = sorted(axes.get_ylim())
    img_x = sorted((x0, x1))
    img_y = sorted((y0, y1))
    return (abs(ax_x[0] - img_x[0]) <= 1 and abs(ax_x[1] - img_x[1]) <= 1
            and abs(ax_y[0] - img_y[0]) <= 1 and abs(ax_y[1] - img_y[1]) <= 1)


def test_the_view_closes_in_on_the_cropped_region(mapped_window):
    """Otherwise the cropped-away area just reads as 'no data': the map keeps
    its old extent and the remaining pixels sit in a corner of it."""
    data, _before = armed(mapped_window)
    assert _axes_fit_the_image(mapped_window)
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(True, x, y))
    mapped_window.update_SV()

    assert _axes_fit_the_image(mapped_window)
    assert mapped_window.style_data.xlim == [float(data.xlim[0]), float(data.xlim[1])]


def test_full_map_opens_the_view_back_out(mapped_window):
    data, _before = armed(mapped_window)
    x, y = _inside(data)
    mapped_window.crop_tool._on_press(_press(True, x, y))
    mapped_window.update_SV()
    cropped_lim = list(mapped_window.style_data.xlim)

    mapped_window.lame_action.FullMap.trigger()
    mapped_window.update_SV()

    data = mapped_window.app_data.current_data
    assert mapped_window.style_data.xlim != cropped_lim
    assert mapped_window.style_data.xlim == [float(data.xlim[0]), float(data.xlim[1])]
    assert _axes_fit_the_image(mapped_window)


def test_limits_are_refreshed_for_every_map_type(mapped_window):
    """A crop changes the sample for all of them, not just the one on screen,
    so switching to a cluster map afterwards must not show the old extent."""
    data, _before = armed(mapped_window)
    x, y = _inside(data)

    mapped_window.crop_tool._on_press(_press(True, x, y))

    expected = [float(data.xlim[0]), float(data.xlim[1])]
    for plot_type in mapped_window.style_data.map_plot_types:
        entry = mapped_window.style_data.style_dict.get(plot_type)
        if entry is not None:
            assert entry['XLim'] == expected, plot_type


def test_full_map_restores_and_disables_itself(mapped_window):
    data = mapped_window.app_data.current_data
    full = len(data.processed)
    mapped_window.lame_action.Crop.setChecked(True)
    x0 = float(data.xlim[0])
    y0 = float(data.ylim[0])
    mapped_window.crop_tool.selector.extents = (x0 + 100, x0 + 300, y0 + 40, y0 + 140)
    mapped_window.crop_tool.apply()

    mapped_window.lame_action.FullMap.trigger()

    data = mapped_window.app_data.current_data
    assert len(data.processed) == full
    assert data.crop is False
    assert not mapped_window.lame_action.FullMap.isEnabled()
