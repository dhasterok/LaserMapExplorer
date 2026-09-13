"""Tests for the Qt-free polygon mask computation (``src/data/polygon_mask.py``).

The behaviour that matters here is the union: two disjoint polygons used to
intersect, which emptied the mask and greyed out the whole map as soon as a
second region was drawn.
"""
import numpy as np
import pytest

from src.data.polygon_mask import pixel_coordinates, polygon_mask

# A 10-row x 20-col map.
ARRAY_SIZE = (10, 20)
N = ARRAY_SIZE[0] * ARRAY_SIZE[1]


def square(x0, y0, x1, y1):
    """Axis-aligned rectangle as a vertex list."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


@pytest.mark.parametrize('order', ['F', 'C'])
def test_pixel_coordinates_match_the_reshaped_image(order):
    """Each data point maps to the pixel it occupies in the displayed map."""
    points = pixel_coordinates(ARRAY_SIZE, order, N)
    assert points.shape == (N, 2)

    # Reshaping the data indices the same way the map is built must put index k
    # at the (row, col) that pixel_coordinates reports for it.
    image = np.reshape(np.arange(N), ARRAY_SIZE, order=order)
    for k in (0, 1, 7, N // 3, N - 1):
        col, row = points[k]
        assert image[int(row), int(col)] == k


@pytest.mark.parametrize('order', ['F', 'C'])
def test_single_polygon_keeps_only_its_own_area(order):
    mask = polygon_mask([(square(2, 2, 6, 5), 'in')], ARRAY_SIZE, order, N)

    points = pixel_coordinates(ARRAY_SIZE, order, N)
    inside = (points[:, 0] >= 2) & (points[:, 0] <= 6) & (points[:, 1] >= 2) & (points[:, 1] <= 5)
    # Boundary pixels are decided by Path.contains_points, so only assert the
    # strict interior is kept and everything well outside is dropped.
    strict = (points[:, 0] > 2) & (points[:, 0] < 6) & (points[:, 1] > 2) & (points[:, 1] < 5)
    assert mask[strict].all()
    assert not mask[~inside].any()


def test_disjoint_polygons_union_rather_than_intersect():
    """Two separate regions both stay selected (the old code gave zero)."""
    a = (square(1, 1, 4, 4), 'in')
    b = (square(10, 1, 13, 4), 'in')

    mask_a = polygon_mask([a], ARRAY_SIZE, 'F', N)
    mask_b = polygon_mask([b], ARRAY_SIZE, 'F', N)
    mask_both = polygon_mask([a, b], ARRAY_SIZE, 'F', N)

    assert mask_a.sum() > 0 and mask_b.sum() > 0
    assert mask_both.sum() == mask_a.sum() + mask_b.sum()
    np.testing.assert_array_equal(mask_both, mask_a | mask_b)


def test_out_polygon_carves_a_hole_in_an_in_polygon():
    outer = (square(1, 1, 15, 8), 'in')
    hole = (square(4, 3, 8, 6), 'out')

    kept = polygon_mask([outer, hole], ARRAY_SIZE, 'F', N)
    outer_only = polygon_mask([outer], ARRAY_SIZE, 'F', N)
    hole_only = polygon_mask([hole], ARRAY_SIZE, 'F', N)

    assert kept.sum() < outer_only.sum()
    # Nothing inside the hole survives, and nothing outside the outer polygon
    # is resurrected.
    assert not (kept & ~hole_only).any()
    assert (kept <= outer_only).all()


def test_out_polygon_alone_excludes_only_itself():
    """With no 'in' polygon the mask starts all-True."""
    mask = polygon_mask([(square(4, 3, 8, 6), 'out')], ARRAY_SIZE, 'F', N)

    assert 0 < mask.sum() < N
    excluded = polygon_mask([(square(4, 3, 8, 6), 'in')], ARRAY_SIZE, 'F', N)
    np.testing.assert_array_equal(mask, ~excluded)


def test_no_polygons_keeps_everything():
    assert polygon_mask([], ARRAY_SIZE, 'F', N).all()


def test_degenerate_polygons_are_ignored():
    """Fewer than three vertices cannot bound an area."""
    assert polygon_mask([([(1, 1), (4, 4)], 'in')], ARRAY_SIZE, 'F', N).all()
    assert polygon_mask([([], 'in'), (None, 'in')], ARRAY_SIZE, 'F', N).all()


def test_grouping_alone_changes_nothing():
    """Linking two 'in' polygons must not alter which pixels are kept.

    Groups exist to give regions identity; the mask is the same union either
    way. This is the guarantee that linking is safe to use mid-analysis.
    """
    a, b = square(1, 1, 4, 4), square(10, 1, 13, 4)

    ungrouped = polygon_mask([(a, 'in'), (b, 'in')], ARRAY_SIZE, 'F', N)
    grouped = polygon_mask([(a, 'in', 7), (b, 'in', 7)], ARRAY_SIZE, 'F', N)

    np.testing.assert_array_equal(ungrouped, grouped)


def test_out_linked_into_a_group_holes_only_that_group():
    """The point of per-group 'out': exclude an inclusion inside one grain
    without punching the same hole through every other region.
    """
    # Two overlapping 'in' regions in separate groups, and an 'out' that sits
    # inside both but is linked only to the first.
    left = (square(1, 1, 10, 8), 'in', 1)
    right = (square(5, 1, 15, 8), 'in', 2)
    hole = (square(6, 3, 8, 6), 'out', 1)

    kept = polygon_mask([left, right, hole], ARRAY_SIZE, 'F', N)

    hole_pixels = polygon_mask([(square(6, 3, 8, 6), 'in')], ARRAY_SIZE, 'F', N)
    right_only = polygon_mask([(square(5, 1, 15, 8), 'in')], ARRAY_SIZE, 'F', N)

    # group 2 still covers its own area, including where the hole overlaps it
    assert (kept & hole_pixels).any(), "group 2 should keep the pixels group 1 excluded"
    assert (right_only <= kept).all(), "the unlinked group must be untouched"


def test_ungrouped_out_still_subtracts_globally():
    """An 'out' polygon that belongs to no group keeps its old behaviour."""
    region = (square(1, 1, 15, 8), 'in', 1)
    hole = (square(6, 3, 8, 6), 'out')  # ungrouped

    kept = polygon_mask([region, hole], ARRAY_SIZE, 'F', N)
    hole_pixels = polygon_mask([(square(6, 3, 8, 6), 'in')], ARRAY_SIZE, 'F', N)

    assert not (kept & hole_pixels).any()


def test_group_of_only_out_polygons_subtracts_globally():
    """A group with nothing to include can only take away."""
    region = (square(1, 1, 15, 8), 'in')
    hole = (square(6, 3, 8, 6), 'out', 4)

    kept = polygon_mask([region, hole], ARRAY_SIZE, 'F', N)
    hole_pixels = polygon_mask([(square(6, 3, 8, 6), 'in')], ARRAY_SIZE, 'F', N)

    assert not (kept & hole_pixels).any()


def test_group_region_can_be_computed_on_its_own():
    """One group's polygons, passed alone, give that group's region -- which
    is how a linked group becomes a single ROI.
    """
    members = [(square(1, 1, 10, 8), 'in', 3), (square(6, 3, 8, 6), 'out', 3)]

    as_group = polygon_mask(members, ARRAY_SIZE, 'F', N)
    standalone = polygon_mask([(square(1, 1, 10, 8), 'in'), (square(6, 3, 8, 6), 'out')],
                              ARRAY_SIZE, 'F', N)

    np.testing.assert_array_equal(as_group, standalone)


def test_in_out_is_case_insensitive():
    """The table stores 'In'/'Out' with an initial capital."""
    lower = polygon_mask([(square(2, 2, 6, 5), 'in')], ARRAY_SIZE, 'F', N)
    upper = polygon_mask([(square(2, 2, 6, 5), 'In')], ARRAY_SIZE, 'F', N)
    np.testing.assert_array_equal(lower, upper)
