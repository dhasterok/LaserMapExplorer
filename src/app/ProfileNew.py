import pickle
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.collections import PathCollection

class Profile:
    """
    Holds data for one profile and references to drawn lines/scatters.

    Attributes
    ----------
    name : str
        The name of this profile (e.g. "Profile 1").
    x, y : list of float
        Coordinates of each point in the profile.
    radius : float
        Radius used for averaging around each point.
    stats : list of dict
        For each point, store computed stats (e.g., {'mean':val, 'std':val}).
    lines : list
        References to matplotlib Line2D objects (so we can remove/update them).
    scatters : list
        References to matplotlib PathCollection objects or single scatter for each point.
    """
    def __init__(self, name, radius=5.0):
        self.name = name
        self.x = []
        self.y = []
        self.radius = radius
        self.stats = []  # parallel to x, y; each entry is a dict of stats

        self.lines = []
        self.scatters = []

class Profiling:
    """
    Manages multiple profiles for multiple samples, with:
      - Multi-sample logic ( self.profiles[sample_id][profile_name] )
      - Radius-based averaging
      - Optional mask/ROI from polygons
      - Saving/loading of profile data

    Attributes
    ----------
    profiles : dict
        Nested dict: { sample_id: { profile_name: Profile(...) } }
    current_sample_id : str
        The sample under creation/edit.
    current_profile_name : str
        The profile name under creation/edit.
    is_active : bool
        Whether we are in the middle of creating a new profile.
    temp_x, temp_y : list
        Temporary lists that store user-clicked points before finalizing.
    data_accessor : callable
        A user-supplied function or reference to retrieve the 2D array for a given sample ID.
        E.g. data_accessor(sample_id) -> np.ndarray
    polygon_manager : object
        Reference to a PolygonManager, if you want to do ROI masking. The snippet
        shows how you might check if a point is inside a polygon.
    """

    def __init__(self, data_accessor=None, polygon_manager=None):
        # Example: profiles stored as { sample_id: { profile_name: Profile } }
        self.profiles = {}
        self.current_sample_id = None
        self.current_profile_name = None

        # Creation state
        self.is_active = False
        self.temp_x = []
        self.temp_y = []
        self.temp_radius = 5.0  # default radius for new profiles

        # External references
        self.data_accessor = data_accessor      # function or object to get data arrays
        self.polygon_manager = polygon_manager  # for optional ROI masking

        # For moving an existing point
        self.moving_point_picked = False
        self.selected_profile_name = None
        self.selected_point_idx = -1

    # -------------------------------------------------------------------------
    # Creating a New Profile
    # -------------------------------------------------------------------------
    def create_new_profile(self, sample_id, profile_name, radius=5.0):
        """
        Start building a new profile for a specific sample ID, with a given name.
        Optionally set a radius for averaging.
        """
        if sample_id not in self.profiles:
            self.profiles[sample_id] = {}

        prof = Profile(name=profile_name, radius=radius)
        self.profiles[sample_id][profile_name] = prof
        self.current_sample_id = sample_id
        self.current_profile_name = profile_name

        self.temp_x.clear()
        self.temp_y.clear()
        self.temp_radius = radius
        self.is_active = True

    # -------------------------------------------------------------------------
    # Mouse Click / Profile Creation
    # -------------------------------------------------------------------------
    def handle_profile_click(self, event, axes, is_moving=False):
        """
        Called from MplCanvas when user clicks in profile mode.
        - If not moving => creation logic (left-click adds a point, right-click finalize)
        - If moving => pick up or place a profile point
        """
        if is_moving:
            self.handle_profile_move_click(event, axes)
        else:
            self.handle_profile_creation_click(event, axes)

    def handle_profile_creation_click(self, event, axes):
        """Left-click => add point, Right-click => finalize."""
        if not self.is_active:
            return  # not building a new profile right now

        # Right-click => finalize
        if event.button == 3:
            self.finalize_profile(axes)
            self.is_active = False
        else:
            # left-click => add point
            x, y = event.xdata, event.ydata
            self.temp_x.append(x)
            self.temp_y.append(y)

            sc = axes.scatter([x], [y], marker='o', color='blue', zorder=5)
            prof = self.get_current_profile()
            if prof:
                prof.scatters.append(sc)

    def finalize_profile(self, axes):
        """
        Once user right-clicks, we store the points in the final Profile object,
        then optionally draw a connecting line and do radius-based averaging.
        """
        prof = self.get_current_profile()
        if not prof:
            return

        prof.x = list(self.temp_x)
        prof.y = list(self.temp_y)

        # If we want a connecting line:
        line, = axes.plot(prof.x, prof.y, 'b--', label=prof.name)
        prof.lines.append(line)

        # Now do radius-based averaging for each point, optionally respecting ROI
        prof.stats = self.radius_based_averaging(prof, sample_id=self.current_sample_id)

    def radius_based_averaging(self, profile_obj, sample_id):
        """
        For each point in the given profile, gather data from the array within `radius`
        and compute stats (mean, std, etc.). If a polygon ROI is present, only include
        points inside the polygon.

        Returns
        -------
        stats_list : list of dict
            One dict per point, e.g. {'mean': val, 'std': val, 'n': count}
        """
        # Access the array for this sample
        arr = None
        if self.data_accessor:
            arr = self.data_accessor(sample_id)  # must return a 2D numpy array
        if arr is None:
            # Could return empty if no data
            return []

        # We assume `arr` has shape (height, width).
        # Possibly also we store spacing dx, dy or something. We'll assume 1:1 pixel spacing here.

        stats_list = []
        for (xx, yy) in zip(profile_obj.x, profile_obj.y):
            # Round to nearest pixel coords
            i, j = int(round(yy)), int(round(xx))

            # Collect points in radius
            radius_px = profile_obj.radius
            values = []

            # Example: naive approach scanning local window:
            i_min = max(0, i - int(radius_px))
            i_max = min(arr.shape[0], i + int(radius_px) + 1)
            j_min = max(0, j - int(radius_px))
            j_max = min(arr.shape[1], j + int(radius_px) + 1)

            for ii in range(i_min, i_max):
                for jj in range(j_min, j_max):
                    dist_sq = (ii - i)**2 + (jj - j)**2
                    if dist_sq <= radius_px**2:
                        # Optional: check if inside polygon ROI
                        if self.is_in_roi(jj, ii, sample_id):
                            values.append(arr[ii, jj])

            if len(values) == 0:
                stats_list.append({'mean': np.nan, 'std': np.nan, 'n': 0})
            else:
                vals = np.array(values, dtype=float)
                mean_val = np.mean(vals)
                std_val  = np.std(vals, ddof=1)
                stats_list.append({
                    'mean': mean_val,
                    'std': std_val,
                    'n': len(vals)
                })

        return stats_list

    def is_in_roi(self, x_pix, y_pix, sample_id):
        """
        Check whether the pixel (x_pix, y_pix) is inside the polygon ROI(s).
        If no polygon manager or no polygons, return True (no masking).
        Adapt this logic to your own multi-polygon or multi-sample usage.
        """
        if not self.polygon_manager:
            return True  # no polygons => all included

        # Suppose polygon_manager has a dict: polygons[sample_id][p_id] = ...
        # We'll do a naive check: if ANY polygon encloses (x_pix, y_pix), include it
        # or you can invert logic to exclude if outside.
        sample_polys = self.polygon_manager.polygons.get(sample_id, {})
        # if sample_id not found, no polygons => pass
        if not sample_polys:
            return True

        # convert pixel coords to float if needed
        px, py = float(x_pix), float(y_pix)

        # for each polygon, check if inside
        for p_id, poly in sample_polys.items():
            if poly.patch is not None:
                # Use polygon patch's "contains_point" method, if you want
                # But note that patch is in data coordinates, so x_pix,y_pix
                # must match. If your canvas transforms are different, adapt.
                if poly.patch.contains_point((px, py)):
                    return True

        return False

    def get_current_profile(self):
        """Helper to get the Profile object for current_sample_id/current_profile_name."""
        if self.current_sample_id in self.profiles:
            if self.current_profile_name in self.profiles[self.current_sample_id]:
                return self.profiles[self.current_sample_id][self.current_profile_name]
        return None

    # -------------------------------------------------------------------------
    # Profile Move Logic
    # -------------------------------------------------------------------------
    def handle_profile_move_click(self, event, axes):
        """
        If user is in "move profile point" mode:
        1) If no point picked => find nearest point
        2) Otherwise => place it
        """
        if not self.moving_point_picked:
            found_sample, found_profile, found_idx = self.find_nearest_profile_point(
                event.xdata, event.ydata, max_dist=0.5)
            if found_sample is not None:
                self.current_sample_id = found_sample
                self.selected_profile_name = found_profile
                self.selected_point_idx = found_idx
                self.moving_point_picked = True
        else:
            newx, newy = event.xdata, event.ydata
            self.update_profile_point(self.current_sample_id, self.selected_profile_name,
                                      self.selected_point_idx, newx, newy, axes)
            self.moving_point_picked = False
            self.selected_profile_name = None
            self.selected_point_idx = -1

    def find_nearest_profile_point(self, click_x, click_y, max_dist=1.0):
        """
        Return (sample_id, profile_name, idx) for the nearest profile point if within
        max_dist, else (None, None, -1).
        """
        best_sample = None
        best_profile = None
        best_idx = -1
        best_sqdist = max_dist**2

        # Loop over all sample IDs and profiles
        for s_id, p_dict in self.profiles.items():
            for p_name, prof in p_dict.items():
                arr_x = np.array(prof.x)
                arr_y = np.array(prof.y)
                if arr_x.size == 0:
                    continue
                dx = arr_x - click_x
                dy = arr_y - click_y
                sqdist = dx*dx + dy*dy
                idx_min = np.argmin(sqdist)
                if sqdist[idx_min] < best_sqdist:
                    best_sqdist = sqdist[idx_min]
                    best_idx = idx_min
                    best_sample = s_id
                    best_profile = p_name

        return best_sample, best_profile, best_idx

    def update_profile_point(self, sample_id, profile_name, point_idx, new_x, new_y, axes):
        """Update a single point in the profile and re-draw line/scatter/stats."""
        prof = self.profiles.get(sample_id, {}).get(profile_name, None)
        if not prof:
            return
        if point_idx < 0 or point_idx >= len(prof.x):
            return

        prof.x[point_idx] = new_x
        prof.y[point_idx] = new_y

        # Re-draw lines
        for ln in prof.lines:
            ln.remove()
        prof.lines.clear()
        line, = axes.plot(prof.x, prof.y, 'b--', label=prof.name)
        prof.lines.append(line)

        # Re-draw scatters
        for sc in prof.scatters:
            sc.remove()
        prof.scatters.clear()
        for (xx, yy) in zip(prof.x, prof.y):
            s = axes.scatter([xx], [yy], marker='o', color='blue', zorder=5)
            prof.scatters.append(s)

        # Optionally re-compute radius-based stats for the updated point 
        # or for all points in the profile. The snippet redoes them all:
        prof.stats = self.radius_based_averaging(prof, sample_id=sample_id)

    # -------------------------------------------------------------------------
    # Clearing, Saving, Loading
    # -------------------------------------------------------------------------
    def clear_profiles(self, axes):
        """Remove all profiles from the plot (all samples)."""
        for s_id, p_dict in self.profiles.items():
            for p_name, prof in p_dict.items():
                for ln in prof.lines:
                    ln.remove()
                prof.lines.clear()
                for sc in prof.scatters:
                    sc.remove()
                prof.scatters.clear()
        self.profiles.clear()
        axes.figure.canvas.draw_idle()

    def save_profiles(self, filepath):
        """
        Save the current profiles to a file (using pickle).
        We'll store a structure like:
        {
          sample_id: {
            profile_name: {
              'x': [...], 'y': [...], 'radius': float, 'stats': [...],
              # add any other fields you need
            },
            ...
          },
          ...
        }
        """
        data = {}

        for s_id, p_dict in self.profiles.items():
            data[s_id] = {}
            for p_name, prof in p_dict.items():
                # gather the needed fields
                data[s_id][p_name] = {
                    'x': prof.x,
                    'y': prof.y,
                    'radius': prof.radius,
                    'stats': prof.stats
                }

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        print(f"[Profiling] Saved profiles to {filepath}")

    def load_profiles(self, filepath, axes):
        """
        Load profiles from a pickle file and re-draw them on the given axes.
        We'll recreate the lines/scatters for each loaded profile.
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        # Clear existing
        self.clear_profiles(axes)

        # Re-build self.profiles from `data`
        for s_id, p_dict in data.items():
            if s_id not in self.profiles:
                self.profiles[s_id] = {}
            for p_name, fields in p_dict.items():
                prof = Profile(p_name, radius=fields.get('radius', 5.0))
                prof.x = fields.get('x', [])
                prof.y = fields.get('y', [])
                prof.stats = fields.get('stats', [])
                self.profiles[s_id][p_name] = prof

                # Now re-draw lines
                if len(prof.x) > 1:
                    line, = axes.plot(prof.x, prof.y, 'b--', label=prof.name)
                    prof.lines.append(line)

                # Re-draw scatters
                for (xx, yy) in zip(prof.x, prof.y):
                    s = axes.scatter([xx], [yy], marker='o', color='blue', zorder=5)
                    prof.scatters.append(s)

        axes.figure.canvas.draw_idle()
        print(f"[Profiling] Loaded profiles from {filepath}")
