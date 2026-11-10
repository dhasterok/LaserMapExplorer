"""Interactive crop of a map's area of analysis.

Cropping restricts the sample to a rectangle of the map, and everything
downstream -- filters, clustering, stoichiometry, plots -- then works on that
region only. ``SampleObj.apply_crop`` does the data side; this module is the
rubber band the user drags over the map, and "Full Map" (``reset_crop``) is the
way back.

Only map-type plots can be cropped (see ``StyleToolbox.map_plot_types``): the
rectangle is a region of the sample, which a scatter or a histogram has no
notion of.

This replaces a pyqtgraph implementation that was left behind when maps moved to
matplotlib. It drew ``QGraphicsRectItem`` overlays into ``parent.plot`` -- a
pyqtgraph ``PlotItem`` that no longer exists -- and hand-rolled corner-drag
resizing. ``matplotlib.widgets.RectangleSelector`` is the same interaction,
maintained upstream, in data coordinates, so there is no pixel arithmetic here
at all.
"""
import numpy as np
from matplotlib.widgets import RectangleSelector

from src.control.Logger import log


class CropTool:
    """Drags a rectangle over the current map and crops the sample to it.

    The crop is deliberately a two-step action. Releasing the mouse only sets
    the rectangle; *Enter* commits it and *Escape* (or unchecking the toolbar
    button) abandons it. Committing throws away computed fields and filters --
    the same reset "Full Map" warns about -- so it should take a deliberate
    keystroke rather than happening the moment a drag ends.

    Attributes
    ----------
    selector : matplotlib.widgets.RectangleSelector or None
        Live rubber band, or None when the tool isn't running.
    canvas : MplCanvas or None
        Canvas the selector is attached to.
    """

    #: Shown while the tool is live -- the keys are not otherwise discoverable.
    HINT = ("Crop: drag a rectangle over the area to analyse, then double-click "
            "inside it (or press Enter) to apply. Esc cancels.")

    #: Drawn on the map itself, because the status bar is easy to miss.
    CANVAS_HINT = "double-click inside or Enter to apply · Esc to cancel"

    def __init__(self, ui):
        self.ui = ui
        self.selector = None
        self.canvas = None
        self._key_cid = None
        self._press_cid = None
        self._hint_artist = None

    # --- availability ------------------------------------------------------

    def is_available(self):
        """True when the current plot is a map of a loaded sample.

        Drives whether the Crop action is enabled, so the button can't be
        pressed on a plot that has no spatial extent to crop.
        """
        app_data = getattr(self.ui, 'app_data', None)
        style_data = getattr(self.ui, 'style_data', None)
        if app_data is None or style_data is None:
            return False
        if not getattr(app_data, 'sample_id', ''):
            return False
        return style_data.plot_type in style_data.map_plot_types

    # --- lifecycle ---------------------------------------------------------

    def start(self, canvas=None):
        """Puts a rubber band over the map, sized to the current extent."""
        canvas = canvas if canvas is not None else getattr(self.ui, 'mpl_canvas', None)
        axes = getattr(canvas, 'axes', None)
        if axes is None:
            log("crop: no map canvas to crop", prefix="Warning")
            self._uncheck()
            return False

        if not self.is_available():
            log(f"crop: {getattr(self.ui.style_data, 'plot_type', '?')} is not a map",
                prefix="Warning")
            self._uncheck()
            return False

        self.stop()
        self.canvas = canvas

        # The distance tool owns button_press on this canvas; two rubber bands
        # fighting over the same drag is how the old tool used to lock up.
        if hasattr(canvas, 'disable_distance_mode'):
            canvas.disable_distance_mode()

        x0, x1 = axes.get_xlim()
        y0, y1 = axes.get_ylim()
        self.selector = RectangleSelector(
            axes,
            self._on_select,
            useblit=False,          # blitting fights the mask overlay's redraws
            button=[1],             # left button only; right is the context menu
            interactive=True,       # draggable edges and corner handles
            spancoords='data',
            props=dict(facecolor='none', edgecolor='white', linewidth=2,
                       linestyle='--', alpha=0.9, fill=False),
        )
        # Start on the middle half, so there is something to grab straight away.
        self.selector.extents = (
            x0 + (x1 - x0) * 0.25, x0 + (x1 - x0) * 0.75,
            min(y0, y1) + abs(y1 - y0) * 0.25, min(y0, y1) + abs(y1 - y0) * 0.75,
        )

        self._key_cid = canvas.mpl_connect('key_press_event', self._on_key)
        # Enter only reaches us while the canvas holds keyboard focus, and clicking
        # the toolbar button leaves focus on the button. A double-click inside the
        # rectangle is therefore the primary way to apply -- mouse events are
        # delivered by position, not by focus -- and any press also claims focus so
        # the keyboard route starts working too.
        self._press_cid = canvas.mpl_connect('button_press_event', self._on_press)

        # Say it on the map. The status bar is both easy to miss and quick to be
        # overwritten by whatever else reports progress. Placed just inside the
        # top edge rather than above it, because map plots set a title there
        # (see LamePlot.plot_map_mpl) and the two would overlap.
        self._hint_artist = axes.text(
            0.5, 0.985, self.CANVAS_HINT,
            transform=axes.transAxes, ha='center', va='top',
            fontsize=8, color='black',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffe9a8',
                      edgecolor='#b08900', alpha=0.9),
            zorder=1e6,
        )

        canvas.setFocus()
        canvas.draw_idle()

        # matplotlib selectors respect the navigation toolbar's widgetlock, so
        # with pan or zoom armed the rubber band simply won't answer the mouse.
        # Say so -- silently inert is indistinguishable from broken.
        toolbar = getattr(canvas, 'toolbar', None)
        mode = getattr(toolbar, 'mode', None)
        if mode:
            self._status(f"Crop: turn off {str(mode).strip() or 'pan/zoom'} first — "
                         "the map tools take the mouse while they are active.")
        else:
            self._status(self.HINT)
        return True

    def stop(self):
        """Removes the rubber band, leaving the data untouched."""
        if self.selector is not None:
            try:
                self.selector.set_active(False)
                self.selector.set_visible(False)
                # Drop the selector's own mpl callbacks too. Deactivating alone
                # leaves them bound to a canvas we are walking away from, and a
                # replot builds a new one -- so without this they accumulate and
                # keep firing (and scheduling draws) on detached figures.
                self.selector.disconnect_events()
            except Exception as e:                      # pragma: no cover
                log(f"crop: could not retire selector: {e}", prefix="Warning")
            self.selector = None

        if self._hint_artist is not None:
            try:
                self._hint_artist.remove()
            except Exception:                           # pragma: no cover
                pass
            self._hint_artist = None

        if self.canvas is not None:
            for cid in (self._key_cid, self._press_cid):
                if cid is not None:
                    try:
                        self.canvas.mpl_disconnect(cid)
                    except Exception:                   # pragma: no cover
                        pass
            # Only redraw a canvas that is still the live one. update_SV replaces
            # the canvas on every replot and then (in its finally) refreshes the
            # crop buttons, which can retire the tool -- so by here self.canvas is
            # sometimes the detached predecessor. draw_idle() defers the draw into
            # the Qt event loop, where matplotlib catches and prints the failure
            # itself ("'NoneType' object has no attribute 'set_cursor'", from a
            # NavigationToolbar2 whose canvas is gone), so a try/except here could
            # never have suppressed it.
            if self.canvas is getattr(self.ui, 'mpl_canvas', None):
                try:
                    self.canvas.draw_idle()
                except Exception:                       # pragma: no cover
                    pass
            else:
                # Detached: cancel whatever is still queued on it instead. A draw
                # requested while it was live (by start(), or by the selector as
                # the rectangle moved) would otherwise fire after CanvasWidget's
                # cleanup has nulled the old toolbar's canvas. See apply() for why
                # _draw_pending is the right lever.
                try:
                    self.canvas._draw_pending = False
                except Exception:                       # pragma: no cover
                    pass

        self._key_cid = None
        self._press_cid = None
        self.canvas = None

    def cancel(self):
        """Abandons the crop and releases the toolbar button."""
        self.stop()
        self._uncheck()
        self._status("Crop cancelled.")

    # --- applying ----------------------------------------------------------

    def bounds(self):
        """``(xlim, ylim)`` of the rectangle in **axes** coordinates, or None.

        A field map is drawn with ``imshow``, whose axes are pixel indices
        (0..nx, 0..ny) rather than microns -- see ``LamePlot.plot_map_mpl``. These
        are therefore indices, which is the right space for hit-testing a click
        but not for ``SampleObj.apply_crop``; `data_bounds` does that conversion.
        """
        if self.selector is None:
            return None
        xmin, xmax, ymin, ymax = self.selector.extents
        if xmin == xmax or ymin == ymax:
            return None
        return (xmin, xmax), (ymin, ymax)

    def data_bounds(self):
        """The rectangle in Xc/Yc units, or None.

        Converted through the sample's own sorted coordinate values rather than
        ``index * dx + origin``. ``dx`` is ``x_range / nunique()`` -- a pixel too
        few -- so on a 91-line, 1800 micron map it reads 19.78 instead of 20 and
        the far edge of the crop would land ~1% short.
        """
        bounds = self.bounds()
        data = self.ui.app_data.current_data
        if bounds is None or data is None:
            return None

        (xi0, xi1), (yi0, yi1) = bounds

        def to_values(column, lo, hi):
            values = np.unique(np.asarray(data.processed[column], dtype=float))
            last = len(values) - 1
            i0 = int(np.clip(round(min(lo, hi)), 0, last))
            i1 = int(np.clip(round(max(lo, hi)), 0, last))
            return float(values[i0]), float(values[i1])

        return to_values('Xc', xi0, xi1), to_values('Yc', yi0, yi1)

    def apply(self):
        """Crops the sample to the rectangle and replots."""
        bounds = self.data_bounds()
        if bounds is None:
            self._status("Crop: drag out a region first.")
            return False

        data = self.ui.app_data.current_data
        if data is None:
            return False

        xlim, ylim = bounds
        if not data.apply_crop(xlim, ylim):
            # Can happen on a sparse map: a rectangle drawn over a gap in the
            # data selects no pixels at all.
            self._status("Crop: that region contains no data — nothing changed.")
            return False

        leaving = self.canvas
        self.stop()
        self._uncheck()

        # Cancel any draw still queued on the canvas we just left. The replot
        # below replaces it, and CanvasWidget's cleanup deliberately sets the old
        # toolbar's canvas to None (to stop a dying widget being drawn). A
        # deferred draw landing after that reaches matplotlib's
        # _wait_cursor_for_draw_cm and prints an AttributeError. _draw_pending is
        # matplotlib's own cancel flag -- FigureCanvasQT._draw_idle returns early
        # when it is False.
        if leaving is not None:
            try:
                leaving._draw_pending = False
            except Exception:                           # pragma: no cover
                pass

        # The axes come from style_data.xlim/ylim, not from the data, so without
        # this the map keeps its old extent and the cropped-away area just shows
        # as empty space instead of the view closing in on what is left.
        if hasattr(self.ui, 'reset_map_limits'):
            self.ui.reset_map_limits()

        full_map = getattr(getattr(self.ui, 'lame_action', None), 'FullMap', None)
        if full_map is not None:
            full_map.setEnabled(True)

        if hasattr(self.ui, 'schedule_update'):
            self.ui.schedule_update()
        self._status(f"Cropped to {data.nx} × {data.ny} pixels. "
                     "Use Full Map to restore the whole sample.")
        return True

    # --- events ------------------------------------------------------------

    def _on_select(self, eclick, erelease):
        """Mouse release. Only reports the region; applying is a separate step."""
        bounds = self.data_bounds()
        if bounds is None:
            return
        (xmin, xmax), (ymin, ymax) = bounds
        self._status(f"Crop: x {xmin:.1f}–{xmax:.1f}, y {ymin:.1f}–{ymax:.1f}. "
                     "Double-click inside or press Enter to apply, Esc to cancel.")

    def _on_press(self, event):
        """Double-click inside the rectangle applies; any press claims focus."""
        canvas = self.canvas
        if canvas is None:
            return

        # Clicking the canvas is what makes the keyboard shortcuts live.
        if not canvas.hasFocus():
            canvas.setFocus()

        if not getattr(event, 'dblclick', False):
            return

        bounds = self.bounds()
        if bounds is None or event.xdata is None or event.ydata is None:
            return
        (xmin, xmax), (ymin, ymax) = bounds
        if xmin <= event.xdata <= xmax and ymin <= event.ydata <= ymax:
            self.apply()

    def _on_key(self, event):
        if event.key in ('enter', 'return'):
            self.apply()
        elif event.key == 'escape':
            self.cancel()

    # --- helpers -----------------------------------------------------------

    def _uncheck(self):
        action = getattr(getattr(self.ui, 'lame_action', None), 'Crop', None)
        if action is not None and action.isChecked():
            # Don't re-enter toggle_crop via the toggled signal.
            action.blockSignals(True)
            action.setChecked(False)
            action.blockSignals(False)

    def _status(self, message):
        manager = getattr(getattr(self.ui, 'io', None), 'status_manager', None)
        if manager is not None:
            manager.show_message(message)
        else:
            log(message, prefix="Crop")
