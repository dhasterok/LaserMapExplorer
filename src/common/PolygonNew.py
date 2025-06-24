import pickle
import os
import numpy as np
from matplotlib.patches import Polygon as MplPolygon
from src.common.Logger import auto_log_methods, log

class Polygon:
    """Stores data about one polygon and references to the drawn Patch."""
    def __init__(self, p_id):
        self.p_id = p_id
        self.points = []   # list of (x, y)
        self.patch = None  # Matplotlib Patch reference

@auto_log_methods(logger_key='Polygon', prefix="POLYGON: ", show_args=True)
class PolygonManager:
    """
    Manages polygon creation, storage, and drawing on a Matplotlib axes.
    Includes save/load methods using the `pickle` module.
    """
    def __init__(self, parent, logger_options=None, logger_key=None):
        self.parent = parent
        # For multi-sample usage, you might have {sample_id: {p_id: Polygon}}.
        # For simplicity, this snippet just uses a single dict of polygons:
        self.polygons = {}    # {p_id: Polygon instance}
        self.p_id_gen = 0
        self.current_p_id = None

        # Creation mode flags
        self.is_drawing = False
        self.active_points = []  # points for polygon under construction

        # Moving existing polygon vertex
        self.selected_polygon_id = None
        self.selected_vertex_idx = -1
        self.vertex_picked_up = False
        self.canvas = None

        # Booleans controlling modes (Polygon creation)
        self.is_creating_polygon = False
        self.is_add_point_polygon = False

    # -------------------------------------------------------------------------
    # Polygon Creation
    # -------------------------------------------------------------------------
    def create_new_polygon(self):
        """Begin a new polygon by incrementing the ID and setting is_drawing=True."""
        self.p_id_gen += 1
        self.current_p_id = self.p_id_gen
        new_poly = Polygon(self.current_p_id)
        self.polygons[self.current_p_id] = new_poly
        self.is_drawing = True
        self.active_points.clear()

    

    def handle_polygon_click(self,canvas, event, axes, is_moving=False):
        """
        Called by MplCanvas on mouse click in polygon mode.
          - If is_moving=False => creation logic
          - If is_moving=True  => pick up or place a vertex
        """
        # update canvas if different
        if self.canvas != canvas:
            self.canvas = canvas

        if self.is_add_point_polygon:
            self.handle_polygon_add_point_click(event, axes)
        elif self.is_moving:
            self.handle_polygon_move_click(event, axes)
        else:
            self.handle_polygon_creation_click(event, axes)

    def handle_polygon_add_point_click(self, event, axes):
        """
        Insert a new vertex into the closest line segment of the selected polygon.
        For simplicity, we pick *one* polygon as 'current' or we loop over polygons 
        to find which one user is editing. 
        """
        if event.button != 1:  # only left-click for adding a vertex
            return

        # Example: Suppose we choose the polygon with ID self.current_p_id
        # Or you might do additional logic to pick which polygon is "selected"
        poly = self.polygons.get(self.current_p_id, None)
        if not poly:
            return
        
        x, y = event.xdata, event.ydata
        points = poly.points
        if len(points) < 2:
            # Not enough points for a line segment
            return

        # Find line segment with min distance from (x, y)
        min_distance = float('inf')
        insert_after_index = None

        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]  # loop back for last segment
            dist = self.distance_to_line_segment(x, y, p1[0], p1[1], p2[0], p2[1])
            if dist < min_distance:
                min_distance = dist
                insert_after_index = i

        # Insert (x,y) after that segment
        if insert_after_index is not None:
            # Insert new vertex
            points.insert(insert_after_index + 1, (x, y))

            # Re-draw the polygon
            self.update_polygon_patch(poly, axes)
    
    def distance_to_line_segment(self, px, py, x1, y1, x2, y2):
        """
        Returns min distance from (px,py) to line segment [ (x1,y1), (x2,y2) ].
        """
        # parametric t of the projection onto the line
        line_len_sq = (x2 - x1)**2 + (y2 - y1)**2
        if line_len_sq < 1e-12:
            # the segment's points are effectively the same
            return np.hypot(px - x1, py - y1)

        t = ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / line_len_sq
        # clamp t to [0,1]
        t = max(0, min(1, t))
        # projection
        proj_x = x1 + t*(x2 - x1)
        proj_y = y1 + t*(y2 - y1)
        return np.hypot(px - proj_x, py - proj_y)

    def update_polygon_patch(self, poly, axes):
        """
        Remove the old patch if present, create a new patch from updated points, 
        and add it to axes.
        """
        if poly.patch is not None:
            poly.patch.remove()
            poly.patch = None

        new_patch = MplPolygon(
            xy=poly.points,
            closed=True,
            facecolor=(0.4, 0.4, 0.8, 0.3),
            edgecolor='red',
            zorder=4
        )
        axes.add_patch(new_patch)
        poly.patch = new_patch

        # Force redraw if necessary
        axes.figure.canvas.draw_idle()

    def handle_polygon_creation_click(self, event, axes):
        """If we are in creation mode, left-click => add point, right-click => finalize."""
        if not self.is_drawing:
            return

        # Right-click => finalize polygon
        if event.button == 3:
            if len(self.active_points) >= 3:
                self.finalize_polygon(axes)
            self.is_drawing = False
        else:
            # Left-click => add a point
            x, y = event.xdata, event.ydata
            self.active_points.append((x, y))
            # Optional: scatter for visual feedback
            axes.scatter([x], [y], marker='x', color='red', zorder=5)

            if len(self.active_points) > 1:
                x0, y0 = self.active_points[-2]
                line, = axes.plot([x0, x], [y0, y], 'r-')
                # store line reference if you need to remove later

    def finalize_polygon(self, axes):
        """Close the polygon by adding a patch to the axes."""
        poly = self.polygons[self.current_p_id]
        poly.points = list(self.active_points)  # store a copy

        patch = MplPolygon(
            xy=poly.points,
            closed=True,
            facecolor=(0.4, 0.4, 0.8, 0.3),
            edgecolor='red',
            zorder=4
        )
        axes.add_patch(patch)
        poly.patch = patch

    # -------------------------------------------------------------------------
    # Polygon Move / Edit
    # -------------------------------------------------------------------------
    def handle_polygon_move_click(self, event, axes):
        """
        If user is in "move polygon vertex" mode:
          1) If not picked up a vertex, find nearest vertex
          2) Otherwise, place it
        """
        if not self.vertex_picked_up:
            # first click => pick up vertex
            found_poly, found_idx = self.find_nearest_vertex(event.xdata, event.ydata, max_dist=0.5)
            if found_poly is not None:
                self.selected_polygon_id = found_poly
                self.selected_vertex_idx = found_idx
                self.vertex_picked_up = True
        else:
            # second click => place vertex
            new_x, new_y = event.xdata, event.ydata
            self.update_polygon_vertex(self.selected_polygon_id, self.selected_vertex_idx, new_x, new_y, axes)
            self.vertex_picked_up = False
            self.selected_polygon_id = None
            self.selected_vertex_idx = -1

    def find_nearest_vertex(self, click_x, click_y, max_dist=1.0):
        """
        Return (polygon_id, vertex_index) for the nearest vertex if within max_dist,
        otherwise (None, -1).
        """
        best_poly = None
        best_idx = -1
        best_sqdist = max_dist**2
        for pid, poly in self.polygons.items():
            arr = np.array(poly.points)
            if arr.shape[0] == 0:
                continue
            dx = arr[:, 0] - click_x
            dy = arr[:, 1] - click_y
            sqdist = dx*dx + dy*dy
            idx_min = np.argmin(sqdist)
            if sqdist[idx_min] < best_sqdist:
                best_sqdist = sqdist[idx_min]
                best_idx = idx_min
                best_poly = pid
        return best_poly, best_idx

    def update_polygon_vertex(self, polygon_id, vertex_idx, new_x, new_y, axes):
        """Update a single vertex and re-draw the patch."""
        poly = self.polygons.get(polygon_id)
        if not poly:
            return
        if vertex_idx < 0 or vertex_idx >= len(poly.points):
            return

        pts = list(poly.points)
        pts[vertex_idx] = (new_x, new_y)
        poly.points = pts

        # re-draw patch
        if poly.patch is not None:
            poly.patch.remove()
        patch = MplPolygon(
            xy=poly.points,
            closed=True,
            facecolor=(0.4, 0.4, 0.8, 0.3),
            edgecolor='red',
            zorder=4
        )
        axes.add_patch(patch)
        poly.patch = patch

    # -------------------------------------------------------------------------
    # Clearing, Saving, and Loading Polygons
    # -------------------------------------------------------------------------
    def clear_polygons(self, axes):
        """Remove all polygons from the plot."""
        for pid, poly in self.polygons.items():
            if poly.patch is not None:
                poly.patch.remove()
        self.polygons.clear()
        axes.figure.canvas.draw_idle()

    def save_polygons(self, filepath):
        """
        Save the current polygons to a file (using pickle).
        We'll store just the polygon points in a dict: {p_id: [ (x,y), (x,y), ... ]}.
        """
        data = {}
        for pid, poly in self.polygons.items():
            data[pid] = poly.points

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        log(f"Saved {len(data)} polygons to {filepath}", prefix="POLYGON:")

    def load_polygons(self, filepath, axes):
        """
        Load polygons from a file and re-draw them on the given axes.
        Expects the same structure as produced by `save_polygons`.
        """
        if not os.path.exists(filepath):
            log(f"File not found: {filepath}", prefix="POLYGON")

        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        # Remove existing polygons from axes
        self.clear_polygons(axes)

        # Reconstruct polygons
        for pid, points in data.items():
            pid = int(pid)  # ensure correct type if stored as string
            if pid not in self.polygons:
                self.polygons[pid] = Polygon(pid)
            self.polygons[pid].points = points

            # Create the patch
            patch = MplPolygon(
                xy=points,
                closed=True,
                facecolor=(0.4, 0.4, 0.8, 0.3),
                edgecolor='red',
                zorder=4
            )
            axes.add_patch(patch)
            self.polygons[pid].patch = patch

            # Update p_id_gen if needed to avoid collisions
            if pid > self.p_id_gen:
                self.p_id_gen = pid

        axes.figure.canvas.draw_idle()

        log(f"Loaded {len(data)} polygons from {filepath}", prefix="POLYGON")
