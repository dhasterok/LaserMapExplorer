"""Tests for the profile-plot point-masking added to src/plotting/Profile.py:
Profile.excluded (a persistent exclusion mask, parallel to Profile.points),
Profiling._apply_mask_display (light-gray-vs-hidden rendering), and the
click-to-toggle (on_pick) / display-toggle (toggle_point_visibility) wiring.

Constructs Profiling directly with lightweight stand-ins for profile_dock/
main_window (only the attributes these specific methods touch), rather than
a full ProfileDock + MainWindow -- Profile.py isn't built standalone the way
src/calibration/ is, so this avoids needing a real running app.

Pure Python/matplotlib -- no real Qt widgets constructed (matplotlib uses
the Agg backend; QApplication is never instantiated).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.plotting.Profile import Profile, Profiling


class _StubComboBox:
    """No-op stand-in for profile_dock.profile_combobox -- just enough for
    Profiling.populate_combobox (called by load_profiles) to run without a
    real QComboBox."""
    def clear(self):
        pass

    def addItem(self, *args, **kwargs):
        pass


def _make_profiling():
    main_window = SimpleNamespace(app_data=SimpleNamespace(sample_id="sample1"))
    parent = SimpleNamespace(main_window=main_window, profile_combobox=_StubComboBox())
    profiling = Profiling(parent)
    profile = Profile(name="profile1")
    profiling.profiles = {"sample1": {"profile1": profile}}
    profiling.profile_name = "profile1"
    return profiling, profile


def _make_scatter_and_errorbar(ax, n=3, color="tab:blue"):
    x = list(range(n))
    y = [1.0] * n
    scatter = ax.scatter(x, y, color=color, picker=5)
    _, _, barlinecols = ax.errorbar(x, y, yerr=[0.1] * n, fmt="none", color=color)
    return scatter, barlinecols[0]


def test_profile_excluded_defaults_to_empty_dict():
    profile = Profile(name="p")
    assert profile.excluded == {}


def test_apply_mask_display_colors_masked_point_light_gray_by_default():
    profiling, _ = _make_profiling()
    fig, ax = plt.subplots()
    scatter, barlinecol = _make_scatter_and_errorbar(ax, n=3)

    excluded_mask = [False, True, False]
    profiling._apply_mask_display(scatter, barlinecol, excluded_mask, "tab:blue")

    facecolors = scatter.get_facecolors()
    assert tuple(facecolors[1]) == Profiling._MASKED_COLOR
    assert tuple(facecolors[0]) != Profiling._MASKED_COLOR
    assert tuple(facecolors[2]) != Profiling._MASKED_COLOR
    plt.close(fig)


def test_apply_mask_display_hides_masked_point_when_enabled():
    profiling, _ = _make_profiling()
    profiling.hide_masked_points_enabled = True
    fig, ax = plt.subplots()
    scatter, barlinecol = _make_scatter_and_errorbar(ax, n=3)

    excluded_mask = [False, True, False]
    profiling._apply_mask_display(scatter, barlinecol, excluded_mask, "tab:blue")

    facecolors = scatter.get_facecolors()
    assert facecolors[1][-1] == 0.0  # alpha 0 -- hidden
    assert facecolors[0][-1] != 0.0
    assert facecolors[2][-1] != 0.0
    plt.close(fig)


def test_on_pick_toggles_persistent_exclusion_and_survives_lookup():
    profiling, profile = _make_profiling()
    fig, ax = plt.subplots()
    scatter, barlinecol = _make_scatter_and_errorbar(ax, n=3)
    scatter.set_gid("Al27")
    profiling.fig = fig
    profiling.all_errorbars = [(scatter, barlinecol)]
    profiling.original_colors = {"Al27": "tab:blue"}
    profiling.edit_mode_enabled = True

    event = SimpleNamespace(artist=scatter, ind=[1])
    profiling.on_pick(event)

    assert profile.excluded["Al27"] == [False, True, False]
    facecolors = scatter.get_facecolors()
    assert tuple(facecolors[1]) == Profiling._MASKED_COLOR

    # Clicking the same point again un-masks it.
    profiling.on_pick(event)
    assert profile.excluded["Al27"] == [False, False, False]
    plt.close(fig)


def test_on_pick_does_nothing_when_edit_mode_disabled():
    profiling, profile = _make_profiling()
    fig, ax = plt.subplots()
    scatter, barlinecol = _make_scatter_and_errorbar(ax, n=3)
    scatter.set_gid("Al27")
    profiling.fig = fig
    profiling.all_errorbars = [(scatter, barlinecol)]
    profiling.original_colors = {"Al27": "tab:blue"}
    assert profiling.edit_mode_enabled is False  # default

    event = SimpleNamespace(artist=scatter, ind=[1])
    profiling.on_pick(event)

    assert profile.excluded == {}
    plt.close(fig)


def test_toggle_point_visibility_applies_to_every_masked_point_across_fields():
    profiling, profile = _make_profiling()
    fig, ax = plt.subplots()
    scatter_a, bar_a = _make_scatter_and_errorbar(ax, n=2, color="tab:blue")
    scatter_a.set_gid("Al27")
    scatter_b, bar_b = _make_scatter_and_errorbar(ax, n=2, color="tab:orange")
    scatter_b.set_gid("Ca43")
    profiling.fig = fig
    profiling.all_errorbars = [(scatter_a, bar_a), (scatter_b, bar_b)]
    profiling.original_colors = {"Al27": "tab:blue", "Ca43": "tab:orange"}
    profile.excluded = {"Al27": [True, False], "Ca43": [False, True]}

    assert profiling.hide_masked_points_enabled is False
    profiling.toggle_point_visibility()
    assert profiling.hide_masked_points_enabled is True

    assert scatter_a.get_facecolors()[0][-1] == 0.0
    assert scatter_b.get_facecolors()[1][-1] == 0.0

    profiling.toggle_point_visibility()
    assert profiling.hide_masked_points_enabled is False
    assert tuple(scatter_a.get_facecolors()[0]) == Profiling._MASKED_COLOR
    assert tuple(scatter_b.get_facecolors()[1]) == Profiling._MASKED_COLOR
    plt.close(fig)


def test_excluded_mask_survives_save_and_load_round_trip(tmp_path):
    profiling, profile = _make_profiling()
    profile.points = {'x': [0, 1], 'y': [0, 0], 'Al27': [[1.0], [2.0]]}
    profile.excluded = {'Al27': [True, False]}

    profiling.save_profiles(str(tmp_path), "sample1")

    profiling2, _ = _make_profiling()
    profiling2.profiles = {}
    profiling2.load_profiles(str(tmp_path), "sample1")

    loaded = profiling2.profiles["sample1"]["profile1"]
    assert loaded.excluded == {'Al27': [True, False]}


def test_toggle_edit_mode_only_flips_flag_no_display_side_effect():
    """Regression test: toggling Edit mode must not also hide/gray any
    points -- that used to happen as an accidental side effect (the same
    alpha-toggle loop as toggle_point_visibility ran inside
    toggle_edit_mode too)."""
    profiling, profile = _make_profiling()
    fig, ax = plt.subplots()
    scatter, barlinecol = _make_scatter_and_errorbar(ax, n=2, color="tab:blue")
    scatter.set_gid("Al27")
    profiling.fig = fig
    profiling.all_errorbars = [(scatter, barlinecol)]
    profiling.original_colors = {"Al27": "tab:blue"}
    profile.excluded = {"Al27": [True, False]}
    profiling._apply_mask_display(scatter, barlinecol, profile.excluded["Al27"], "tab:blue")
    before = scatter.get_facecolors().copy()

    profiling.toggle_edit_mode()
    assert profiling.edit_mode_enabled is True

    after = scatter.get_facecolors()
    assert (before == after).all()
    plt.close(fig)
