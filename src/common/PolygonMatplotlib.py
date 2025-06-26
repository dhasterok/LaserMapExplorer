# Polygon.py (Matplotlib Version)
import numpy as np
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.lines import Line2D
import os
import pickle
from src.common.Logger import auto_log_methods, log

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
        self.poly.figure.canvas.draw_idle()

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
        self.poly.figure.canvas.draw_idle()

class SerializablePolygon:
    def __init__(self, p_id, verts, color='b', alpha=0.3):
        self.p_id = p_id
        self.verts = verts  # list of (x, y) tuples
        self.color = color
        self.alpha = alpha
        self.patch = None      # Matplotlib Polygon patch (set when drawn)
        self.vertex_markers = []  # Optionally store scatter objects

@auto_log_methods(logger_key='Polygon', show_args=True)
class PolygonManager:
    def __init__(self,parent, main_window, logger_options=None, logger_key=None):
        self.logger_options = logger_options
        self.logger_key = logger_key

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


    def enable_connections(self): # Connections
        self.cid_click = self.canvas.mpl_connect('button_press_event', self.onclick)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.onrelease)
        self.cid_move = self.canvas.mpl_connect('motion_notify_event', self.onmove)
        self.cid_key = self.canvas.mpl_connect('key_press_event', self.onkey)

    def add_samples(self):
        if self.main_window is None:
            return
        for sample_id in self.main_window.sample_ids:
            if sample_id not in self.polygons:
                self.polygons[sample_id] = {}

    def increment_pid(self):
        """Creates a new polygon ID"""
        self.p_id_gen += 1
        self.p_id = self.p_id_gen
        return self.p_id

    def initiate_axes(self,canvas):
        self.ax = canvas.axes
        self.canvas = canvas
        self.canvas.disable_distance_mode()
        self.enable_connections()

    def start_polygon(self,canvas):
        """Start polygon drawing for a particular sample_id."""
        self.initiate_axes(canvas)
        self._drawing = True
        self.current_verts = []
        self._remove_temp()

    def finish_polygon(self):
        if len(self.current_verts) >= 3:
            pid = self.increment_pid()
            verts = [tuple(v) for v in self.current_verts]
            color = 'b'
            alpha = 0.3
            # Add to data structure
            sample_id = self.main_window.app_data.sample_id
            if sample_id not in self.polygons:
                self.polygons[sample_id] = {}
            polygon_obj = SerializablePolygon(pid, verts, color, alpha)
            self.polygons[sample_id][pid] = polygon_obj
            # Draw on plot
            poly_patch = MplPolygon(verts, closed=True, edgecolor=color, fill=True, alpha=alpha)
            self.ax.add_patch(poly_patch)
            self.canvas.draw_idle()
            self._remove_temp()
        self._drawing = False
        self.parent.update_table_widget()  # Update the table in the main window

    # --- Saving and Loading ---
    def save_polygons(self, project_dir, sample_id):
        if sample_id in self.polygons:
            os.makedirs(os.path.join(project_dir, sample_id), exist_ok=True)
            for p_id, polygon in self.polygons[sample_id].items():
                file_name = os.path.join(project_dir, sample_id, f'polygon_{p_id}.poly')
                with open(file_name, 'wb') as file:
                    pickle.dump(polygon, file)
            print("Polygons saved successfully.")

    def load_polygons(self, project_dir, sample_id):
        directory = os.path.join(project_dir, sample_id)
        self.polygons.setdefault(sample_id, {})
        for file_name in os.listdir(directory):
            if file_name.endswith(".poly"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    polygon = pickle.load(file)
                    self.polygons[sample_id][polygon.p_id] = polygon
                    # Draw on axes
                    poly_patch = MplPolygon(polygon.verts, closed=True, edgecolor=polygon.color,
                                            fill=True, alpha=polygon.alpha)
                    self.ax.add_patch(poly_patch)
        self.canvas.draw_idle()
        self.parent.update_table_widget()  # Update the table in the main window
        print("Polygons loaded successfully.")

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
            hit_something = False
            for poly in self.polygons:
                if poly.is_selected:
                    for i, (vx, vy) in enumerate(poly.verts):
                        if np.hypot(event.xdata - vx, event.ydata - vy) < 0.05:
                            self.dragging_vertex = True
                            self.dragged_idx = i
                            self.selected_poly = poly
                            hit_something = True
                            return
                    if poly.poly.contains_point([event.x, event.y]):
                        self.dragging_poly = True
                        self.last_event_xy = (event.xdata, event.ydata)
                        self.selected_poly = poly
                        hit_something = True
                        return
            if not hit_something:
                for poly in self.polygons:
                    cont = poly.poly.contains_point([event.x, event.y])
                    if cont:
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
            new_verts = [[x+dx, y+dy] for x, y in self.selected_poly.verts]
            self.selected_poly.verts = new_verts
            self.selected_poly.poly.set_xy(new_verts)
            self.selected_poly._draw_vertices()
            self.last_event_xy = (event.xdata, event.ydata)


    def onkey(self, event):
        if self._drawing:
            if event.key == 'z' and self.current_verts:
                self.current_verts.pop()
                self._draw_temp()
            if event.key == 'escape':
                self._remove_temp()
                self._drawing = False
        elif self.selected_poly:
            if event.key in ['delete', 'backspace']:
                self.selected_poly.remove()
                self.polygons.remove(self.selected_poly)
                self.selected_poly = None
                self.canvas.draw_idle()

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

    def deselect_all(self):
        for poly in self.polygons:
            poly.deselect()
        self.selected_poly = None

    def plot_existing_polygon(self,canvas, p_id=None):
        """Plot the first (or specified) existing polygon for the current sample ID.

        - Selects the row in the table widget for the polygon.
        - Plots the polygon patch and, if present, the vertex scatter points.
        """
        sample_id = self.main_window.app_data.sample_id
        self.initiate_axes(canvas)

        if sample_id in self.polygons and len(self.polygons[sample_id]) > 0:
            if not p_id:
                # Get the first polygon ID and its corresponding polygon object
                p_id = next(iter(self.polygons[sample_id]))
            
            polygon = self.polygons[sample_id][p_id]

            # Clear any previous selection in the table
            self.main_window.tableWidgetPolyPoints.clearSelection()

            # Find and select the corresponding row in the table
            for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
                item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming ID in col 0
                if item and int(item.text()) == p_id:
                    self.main_window.tableWidgetPolyPoints.selectRow(row)
                    break

            # Remove the patch from axes if it exists (to avoid double-drawing)
            if getattr(polygon, 'patch', None) is not None:
                try:
                    polygon.patch.remove()
                except Exception:
                    pass  # If already removed
                polygon.patch = None

            # Draw the polygon patch on the axes
            from matplotlib.patches import Polygon as MplPolygon
            polygon.patch = MplPolygon(polygon.verts, closed=True,
                                    edgecolor=polygon.color,
                                    fill=True, alpha=polygon.alpha)
            self.ax.add_patch(polygon.patch)

            # Draw the vertex markers, if any (re-create if needed)
            if hasattr(polygon, 'vertex_markers'):
                for marker in polygon.vertex_markers:
                    try:
                        marker.remove()
                    except Exception:
                        pass
                polygon.vertex_markers = []
            else:
                polygon.vertex_markers = []
            for x, y in polygon.verts:
                marker = self.ax.scatter([x], [y], c='red', s=50, zorder=5)
                polygon.vertex_markers.append(marker)

            self.canvas.draw_idle()


    def clear_polygons(self):
        """Clear all existing polygons from the plot."""
        for sample_id, polygons in self.polygons.items():
            for polygon in polygons.values():
                if getattr(polygon, 'patch', None) is not None:
                    polygon.patch.remove()
                    polygon.patch = None
                if hasattr(polygon, 'vertex_markers'):
                    for marker in polygon.vertex_markers:
                        marker.remove()
                    polygon.vertex_markers = []
        self.canvas.draw_idle()
        self.parent.update_table_widget()  # Update the table in the main window
    
    def disconnect(self):
        self.canvas.mpl_disconnect(self.cid_click)
        self.canvas.mpl_disconnect(self.cid_release)
        self.canvas.mpl_disconnect(self.cid_move)
        self.canvas.mpl_disconnect(self.cid_key)
