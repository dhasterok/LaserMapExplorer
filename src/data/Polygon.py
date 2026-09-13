# Polygon.py (Matplotlib Version)
from __future__ import annotations
from typing import Optional
import numpy as np
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.lines import Line2D
import copy
import os
import pickle
from src.control.Logger import auto_log_methods, log

class InteractivePolygon:
    def __init__(self, ax, verts):
        self.ax = ax
        self.verts = verts.copy()
        self.poly = MplPolygon(self.verts, closed=True, edgecolor='b', fill=True, alpha=0.3, picker=True)
        self.ax.add_patch(self.poly)
        self.marker_objs = []
        self.is_selected = False
        self._draw_vertices()

    def _draw_vertices(self):
        self._remove_markers()
        for x, y in self.verts:
            marker = self.ax.scatter([x], [y], c='red' if self.is_selected else 'blue', s=50, zorder=4)
            self.marker_objs.append(marker)
        self.ax.figure.canvas.draw_idle()

    def _remove_markers(self):
        for marker in self.marker_objs:
            marker.remove()
        self.marker_objs = []

    def select(self):
        self.poly.set_edgecolor('orange')
        self.poly.set_linewidth(2)
        self.is_selected = True
        self._draw_vertices()

    def deselect(self):
        self.poly.set_edgecolor('b')
        self.poly.set_linewidth(1)
        self.is_selected = False
        self._draw_vertices()

    def move_vertex(self, idx, new_xy):
        self.verts[idx] = new_xy
        self.poly.set_xy(self.verts)
        self._draw_vertices()


    def add_vertex(self, insert_after_idx, xy):
        self.verts.insert(insert_after_idx + 1, xy)
        self.poly.set_xy(self.verts)
        self._draw_vertices()


    def remove_vertex(self, idx):
        if len(self.verts) > 3:
            self.verts.pop(idx)
            self.poly.set_xy(self.verts)
            self._draw_vertices()


    def remove(self):
        self.poly.remove()
        self._remove_markers()
        self.ax.figure.canvas.draw_idle()

def detached_copy(polygon):
    """A copy of `polygon` with its matplotlib artists stripped.

    The live ``patch``/``vertex_markers`` reference the axes and figure, so
    pickling a polygon while it is on screen drags the whole figure into the
    file (megabytes instead of a few hundred bytes).

    Module-level rather than a ``PolygonManager`` staticmethod: the class's
    ``@auto_log_methods`` decorator rewraps static methods as plain functions,
    which loses the static binding.
    """
    clone = copy.copy(polygon)
    clone.patch = None
    clone.vertex_markers = []
    clone.is_selected = False
    return clone


class SerializablePolygon:
    """One polygon's geometry and mask role, as stored in a ``.poly`` file.

    ``in_out``, ``enabled`` and ``name`` are also declared as *class*
    attributes so polygons pickled before they existed still unpickle: the
    instance ``__dict__`` simply lacks them and attribute lookup falls back to
    these defaults. Don't remove the class-level values.
    """
    #: 'in' keeps the enclosed area, 'out' removes it (see `polygon_mask`).
    in_out = 'in'
    #: Whether this polygon contributes to the mask at all (the table's
    #: 'Analysis' checkbox).
    enabled = True
    #: Display name; None falls back to "Polygon <p_id>".
    name = None

    def __init__(self, p_id, verts, color='b', alpha=0.3, in_out='in', enabled=True, name=None):
        self.p_id = p_id
        self.verts = verts  # list of (x, y) tuples
        self.color = color
        self.alpha = alpha
        self.in_out = in_out
        self.enabled = enabled
        self.name = name
        self.patch: Optional[MplPolygon] = None  # Matplotlib Polygon patch (set when drawn)
        self.vertex_markers = []  # Optionally store scatter objects
        self.is_selected = False

    @property
    def display_name(self):
        """str : The polygon's name, or a default derived from its id."""
        return self.name or f'Polygon {self.p_id}'

    @property
    def is_out(self):
        """bool : True when this polygon removes its area from the mask."""
        return str(self.in_out).lower() == 'out'

    def select(self):
        self.is_selected = True
        if self.patch is not None:
            self.patch.set_edgecolor('orange')
            self.patch.set_linewidth(2)

    def deselect(self):
        self.is_selected = False
        if self.patch is not None:
            self.patch.set_edgecolor(self.color)
            self.patch.set_linewidth(1)

    def move_vertex(self, idx: int, new_xy: list[float]) -> None:
        self.verts[idx] = (float(new_xy[0]), float(new_xy[1]))
        if self.patch is not None:
            self.patch.set_xy(self.verts)

@auto_log_methods(logger_key='Polygon')
class PolygonManager:
    def __init__(self,parent, main_window ):

        self.parent = parent
        self.main_window = main_window
        
        self.polygons = {}  # {sample_id: {p_id: SerializablePolygon}}
        self.p_id_gen = 0   # global counter (can be made per-sample if needed)
        self.p_id = 0

        self.current_verts = []
        self.current_line = None
        self.vertex_markers = []
        self._drawing = False
        self.selected_poly = None
        self.dragging_vertex = False
        self.dragged_idx = None
        self.dragging_poly = False
        self.last_event_xy = None

        self.cid_click = None
        self.cid_release = None
        self.cid_move = None
        self.cid_key = None


    def enable_connections(self): # Connections
        self.cid_click = self.canvas.mpl_connect('button_press_event', self.onclick)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.onrelease)
        self.cid_move = self.canvas.mpl_connect('motion_notify_event', self.onmove)
        self.cid_key = self.canvas.mpl_connect('key_press_event', self.onkey)

    def add_samples(self):
        if self.main_window is None:
            return
        for sample_id in self.main_window.app_data.sample_list:
            if sample_id not in self.polygons:
                self.polygons[sample_id] = {}

    def clear_all(self):
        """Reset to no samples/polygons -- see `Profiling.clear_all()`'s
        docstring for why this is needed (`add_samples()` only ever adds).
        """
        self.polygons = {}
        self.p_id_gen = 0
        self.p_id = 0

    def _seed_pid(self):
        """Raise the id counter above every id already in use.

        Without this, a freshly loaded project starts counting from 0 again and
        the next new polygon overwrites a loaded one.
        """
        used = [p_id for polys in self.polygons.values() for p_id in polys]
        if used:
            self.p_id_gen = max(self.p_id_gen, max(used))

    def increment_pid(self):
        """Creates a new polygon ID"""
        self._seed_pid()
        self.p_id_gen += 1
        self.p_id = self.p_id_gen
        return self.p_id

    def initiate_axes(self,canvas):
        # Drop the handlers bound to the previous canvas first -- `update_SV`
        # builds a new canvas on every replot, and stale connections otherwise
        # keep firing (and calling draw_idle) on a detached figure.
        self.disconnect()
        self.ax = canvas.axes
        self.canvas = canvas
        self.canvas.disable_distance_mode()
        self.enable_connections()

    def set_mask_overlay_visible(self, visible):
        """Show/hide the field map's masked-area overlay without replotting.

        The overlay (see `LamePlot.plot_map_mpl`) dims everything outside the
        current mask, which is what makes an existing selection stand out --
        but it also dims the area being outlined. Hiding the artist keeps the
        canvas and the in-progress event connections intact; triggering a
        replot instead would swap the canvas out mid-draw.
        """
        canvas = getattr(self, 'canvas', None)
        overlay = getattr(canvas, 'mask_overlay', None)
        if overlay is None:
            return
        try:
            overlay.set_visible(visible)
            canvas.draw_idle()
        except Exception as e:
            log(f"could not toggle mask overlay: {e}", prefix="Polygon")

    def start_polygon(self,canvas):
        """Start polygon drawing for a particular sample_id."""
        self.initiate_axes(canvas)
        self._drawing = True
        self.current_verts = []
        self._remove_temp()
        # show the full map while outlining
        self.set_mask_overlay_visible(False)

    def finish_polygon(self):
        added = False
        if len(self.current_verts) >= 3:
            pid = self.p_id  # already incremented by Create Polygon button click
            verts: list[tuple[float, float]] = [(float(v[0]), float(v[1])) for v in self.current_verts]
            color = 'b'
            alpha = 0.3
            # Add to data structure
            sample_id = self.main_window.app_data.sample_id
            if sample_id not in self.polygons:
                self.polygons[sample_id] = {}
            polygon_obj = SerializablePolygon(pid, verts, color, alpha)
            self.polygons[sample_id][pid] = polygon_obj
            self._remove_temp()
            added = True
        self._drawing = False
        self.set_mask_overlay_visible(True)
        if added:
            # redraw through the one drawing path, so the new polygon looks
            # like every other one and becomes the selected one
            self.draw_polygons(self.canvas, p_id=self.p_id)
        self.disconnect()  # stop canvas events until next Create Polygon click
        if added:
            self.notify_model_changed()

    def notify_model_changed(self):
        """Tell the owning tab the polygon set changed, so it can resync.

        Only for *model* changes (added/removed/edited polygons). Redrawing on
        its own must not go through here -- rebuilding the table on every
        replot is what used to reset the per-polygon 'Analysis' checkboxes and
        re-check the toolbar's polygon mask toggle.
        """
        if self.parent is not None and hasattr(self.parent, 'refresh_polygons'):
            self.parent.refresh_polygons()

    # --- Saving and Loading ---
    def save_polygons(self, project_dir, sample_id):
        if sample_id not in self.polygons:
            return

        directory = os.path.join(project_dir, sample_id)
        os.makedirs(directory, exist_ok=True)

        for p_id, polygon in self.polygons[sample_id].items():
            file_name = os.path.join(directory, f'polygon_{p_id}.poly')
            with open(file_name, 'wb') as file:
                pickle.dump(detached_copy(polygon), file)

        # Drop files for polygons that no longer exist -- otherwise a deleted
        # polygon reappears the next time the project is loaded.
        keep = {f'polygon_{p_id}.poly' for p_id in self.polygons[sample_id]}
        for file_name in os.listdir(directory):
            if file_name.endswith('.poly') and file_name not in keep:
                try:
                    os.remove(os.path.join(directory, file_name))
                except OSError as e:
                    log(f"could not remove stale polygon file {file_name}: {e}", prefix="Warning")

        log("Polygons saved successfully.", prefix="Polygon")


    def load_polygons(self, project_dir, sample_id):
        directory = os.path.join(project_dir, sample_id)
        self.polygons.setdefault(sample_id, {})
        if not os.path.isdir(directory):
            # sample had no saved polygons -- nothing to load
            return
        for file_name in os.listdir(directory):
            if file_name.endswith(".poly"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    polygon = pickle.load(file)
                    # A polygon saved by an older version may carry a stale
                    # patch from the figure it was drawn on; drawing is
                    # `draw_polygons`' job, once a canvas is available.
                    polygon.patch = None
                    polygon.vertex_markers = []
                    self.polygons[sample_id][polygon.p_id] = polygon

        # keep new polygons from colliding with the ids just loaded
        self._seed_pid()

        if hasattr(self, 'canvas'):
            self.draw_polygons(self.canvas)
        self.notify_model_changed()
        log("Polygons loaded successfully.", prefix="Polygon")

    # --- Helpers (Matplotlib) ---
    def _remove_temp(self):
        if self.current_line is not None:
            self.current_line.remove()
            self.current_line = None
        for m in self.vertex_markers:
            m.remove()
        self.vertex_markers = []
        self.canvas.draw_idle()

    def onclick(self, event):
        if event.inaxes != self.ax:
            return
        # --- Polygon Drawing Mode ---
        if self._drawing:
            if event.button == 1:  # left click to add vertex
                self.current_verts.append([event.xdata, event.ydata])
                self._draw_temp(event)
            elif event.button == 3 and len(self.current_verts) >= 3:  # right click to finish
                self.finish_polygon()
        else:
            # --- Polygon Editing Mode ---
            sample_id = self.main_window.app_data.sample_id
            current_polys = list(self.polygons.get(sample_id, {}).values())
            hit_something = False
            for poly in current_polys:
                if poly.is_selected:
                    for i, (vx, vy) in enumerate(poly.verts):
                        if np.hypot(event.xdata - vx, event.ydata - vy) < 0.05:
                            self.dragging_vertex = True
                            self.dragged_idx = i
                            self.selected_poly = poly
                            hit_something = True
                            return
                    if poly.patch is not None and poly.patch.contains_point([event.x, event.y]):
                        self.dragging_poly = True
                        self.last_event_xy = (event.xdata, event.ydata)
                        self.selected_poly = poly
                        hit_something = True
                        return
            if not hit_something:
                for poly in current_polys:
                    if poly.patch is not None and poly.patch.contains_point([event.x, event.y]):
                        self.deselect_all()
                        poly.select()
                        self.selected_poly = poly
                        hit_something = True
                        break
                if not hit_something:
                    self.deselect_all()

    def onrelease(self, event):
        self.dragging_vertex = False
        self.dragged_idx = None
        self.dragging_poly = False
        self.last_event_xy = None

    def onmove(self, event):
        if self._drawing:
            self._draw_temp(event)
        elif self.dragging_vertex and self.selected_poly:
            if event.xdata is not None and event.ydata is not None:
                self.selected_poly.move_vertex(self.dragged_idx, [event.xdata, event.ydata])
        elif self.dragging_poly and self.selected_poly and self.last_event_xy:
            dx = event.xdata - self.last_event_xy[0]
            dy = event.ydata - self.last_event_xy[1]
            new_verts = [(x+dx, y+dy) for x, y in self.selected_poly.verts]
            self.selected_poly.verts = new_verts
            if self.selected_poly.patch is not None:
                self.selected_poly.patch.set_xy(new_verts)
            self.last_event_xy = (event.xdata, event.ydata)


    def onkey(self, event):
        if self._drawing:
            if event.key == 'z' and self.current_verts:
                self.current_verts.pop()
                self._draw_temp()
            if event.key == 'escape':
                self._remove_temp()
                self._drawing = False
                self.set_mask_overlay_visible(True)
        elif self.selected_poly:
            if event.key in ['delete', 'backspace']:
                self.remove_polygons([self.selected_poly.p_id])
                # keep the table and mask in step -- otherwise the deleted
                # polygon's row survives and the next mask update raises
                self.notify_model_changed()

    def _draw_temp(self, event=None):
        self._remove_temp()
        if not self.current_verts:
            return
        xs, ys = zip(*self.current_verts)
        self.vertex_markers = [self.ax.scatter([x], [y], c='green', s=40, zorder=5) for x, y in self.current_verts]
        if event and event.xdata is not None and event.ydata is not None:
            xs = list(xs) + [event.xdata]
            ys = list(ys) + [event.ydata]
        if self.current_line is not None:
            self.current_line.remove()
        self.current_line = Line2D(xs, ys, c='gray', ls='-', marker='o', zorder=4)
        self.ax.add_line(self.current_line)
        self.canvas.draw_idle()

    def _remove_artists(self, polygon):
        """Take `polygon`'s patch and vertex markers off the axes, if drawn.

        An instance method, not a staticmethod: ``@auto_log_methods`` rewraps
        static methods as plain functions, which loses the static binding.
        """
        if getattr(polygon, 'patch', None) is not None:
            try:
                polygon.patch.remove()
            except Exception:
                pass  # already gone, or its axes were discarded
            polygon.patch = None
        for marker in getattr(polygon, 'vertex_markers', []):
            try:
                marker.remove()
            except Exception:
                pass
        polygon.vertex_markers = []

    def remove_polygons(self, p_ids, sample_id=None):
        """Delete polygons by id, artists and all.

        The one removal path -- the toolbar's Delete action, the polygon
        table's context menu and the canvas Delete key all come through here.
        Callers follow it with `notify_model_changed` so the table and mask
        resync.

        Parameters
        ----------
        p_ids : iterable of int
            Polygon ids to remove. Ids that aren't present are skipped.
        sample_id : str, optional
            Defaults to the current sample.

        Returns
        -------
        list of int
            The ids actually removed.
        """
        if sample_id is None:
            sample_id = self.main_window.app_data.sample_id

        polygons = self.polygons.get(sample_id, {})
        removed = []
        for p_id in list(p_ids):
            polygon = polygons.pop(p_id, None)
            if polygon is None:
                continue
            self._remove_artists(polygon)
            if self.selected_poly is polygon:
                self.selected_poly = None
            removed.append(p_id)

        if removed and hasattr(self, 'canvas'):
            self.canvas.draw_idle()

        return removed

    def deselect_all(self):
        sample_id = self.main_window.app_data.sample_id
        for poly in self.polygons.get(sample_id, {}).values():
            poly.deselect()
        self.selected_poly = None

    #: Edge colour for an 'out' polygon -- one that removes its area.
    OUT_COLOR = 'firebrick'

    def draw_polygons(self, canvas, p_id=None):
        """Draw every polygon of the current sample on `canvas`.

        All of them are drawn, not just one: outlining a new region is
        guesswork if the regions already selected are invisible. The selected
        polygon is highlighted and shows its vertices; 'out' polygons (which
        remove their area from the mask) are drawn in `OUT_COLOR`.

        Parameters
        ----------
        canvas : MplCanvas
            Canvas to draw on. Also becomes the canvas this manager listens to.
        p_id : int, optional
            Polygon to select. Defaults to keeping the current selection.
        """
        self.initiate_axes(canvas)
        self.clear_plot()

        sample_id = self.main_window.app_data.sample_id
        polygons = self.polygons.get(sample_id, {})
        if not polygons:
            self.canvas.draw_idle()
            return

        if p_id is None and self.selected_poly is not None:
            p_id = self.selected_poly.p_id
        if p_id not in polygons:
            p_id = None

        self.selected_poly = polygons.get(p_id) if p_id is not None else None

        for pid, polygon in polygons.items():
            selected = pid == p_id
            polygon.is_selected = selected
            edgecolor = self.OUT_COLOR if polygon.is_out else polygon.color

            # Outline only: the selected area is the one the mask overlay
            # leaves undimmed, so filling it would hide the data being
            # inspected. The edge carries the state instead.
            polygon.patch = MplPolygon(polygon.verts, closed=True,  # type: ignore[arg-type]
                                       edgecolor='orange' if selected else edgecolor,
                                       linewidth=2.5 if selected else 1.5,
                                       linestyle='--' if polygon.is_out else '-',
                                       fill=False)
            self.ax.add_patch(polygon.patch)

            polygon.vertex_markers = []
            if selected:
                for x, y in polygon.verts:
                    polygon.vertex_markers.append(self.ax.scatter([x], [y], c='red', s=50, zorder=5))

        self.canvas.draw_idle()

    def plot_existing_polygon(self, canvas, p_id=None):
        """Select `p_id` (the first polygon by default) and redraw.

        Kept as the name older call sites use; `draw_polygons` is the real
        entry point and draws every polygon, not only the selected one.
        """
        sample_id = self.main_window.app_data.sample_id
        polygons = self.polygons.get(sample_id, {})
        if p_id is None and polygons:
            p_id = next(iter(polygons))

        self.draw_polygons(canvas, p_id=p_id)


    def clear_plot(self):
        """Remove all polygon patches and vertex markers from the canvas for the current sample."""
        sample_id = self.main_window.app_data.sample_id
        for polygon in self.polygons.get(sample_id, {}).values():
            self._remove_artists(polygon)
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()

    def clear_polygons(self):
        """Remove every sample's polygon artists from the canvas.

        Drawing only -- the model is untouched, and the table is deliberately
        *not* rebuilt here. Rebuilding it on each replot used to reset the
        per-polygon 'Analysis' checkboxes and re-check the toolbar's polygon
        mask toggle. Model changes go through `notify_model_changed` instead.
        """
        for polygons in self.polygons.values():
            for polygon in polygons.values():
                self._remove_artists(polygon)
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()


    def disconnect(self):
        if not hasattr(self, 'canvas') or self.cid_click is None:
            return
        self.canvas.mpl_disconnect(self.cid_click)
        self.canvas.mpl_disconnect(self.cid_release)
        self.canvas.mpl_disconnect(self.cid_move)
        self.canvas.mpl_disconnect(self.cid_key)
        self.cid_click = self.cid_release = self.cid_move = self.cid_key = None
