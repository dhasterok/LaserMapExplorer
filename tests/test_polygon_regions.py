"""Regions of interest defined by polygon geometry (`SampleObj.add_polygon_roi`).

Linked polygons form one region; this is where such a region enters the ROI
machinery, so that the existing per-region reporting (`roi_percentages`,
`regionstats.region_stats`, the ROI map) covers polygons too.

Pure data-layer tests -- no QApplication, using the synthetic sample from
tests/conftest.py (a 40x30 grid).
"""
import copy

import numpy as np
import pandas as pd
import pytest

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.data.DataHandling import LaserSampleObj
from src.stoichiometry import regionstats


@pytest.fixture
def sample(synthetic_sample_csv):
    return LaserSampleObj(
        sample_id='RM01', file_path=str(synthetic_sample_csv),
        outlier_method='Chauvenet criterion', negative_method='ignore negatives',
        ref_chem=pd.Series(dtype=float),
    )


def rect(x0, y0, x1, y1, in_out='in'):
    """One polygon member, in the shape `add_polygon_roi` expects."""
    return {'verts': [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 'in_out': in_out}


def pixels_of(sample, roi_id):
    return int((sample.processed['ROI'].values == roi_id).sum())


def test_polygon_roi_claims_the_pixels_it_encloses(sample):
    roi_id = sample.add_polygon_roi([rect(2, 2, 8, 6)], name='Garnet', color='#ff0000')

    assert roi_id == 1
    assert 'ROI' in sample.processed.columns
    # interior of a 6x4 box, boundary pixels decided by Path.contains_points
    assert 0 < pixels_of(sample, roi_id) <= 7 * 5
    # everything else is unassigned
    assert pixels_of(sample, 0) == len(sample.processed) - pixels_of(sample, roi_id)


def test_linked_polygons_become_one_region(sample):
    """Two disjoint outlines, one region id -- the point of linking."""
    roi_id = sample.add_polygon_roi([rect(1, 1, 5, 5), rect(20, 1, 25, 5)], name='Garnet')

    ids = set(np.unique(sample.processed['ROI'].values))
    assert ids == {0, roi_id}
    # both patches contribute
    assert pixels_of(sample, roi_id) > 0
    col = sample.processed['Xc'].values
    claimed = sample.processed['ROI'].values == roi_id
    assert claimed[col < 100].any() and claimed[col > 150].any()


def test_out_member_cuts_a_hole_in_its_own_region(sample):
    with_hole = sample.add_polygon_roi([rect(1, 1, 15, 10), rect(5, 4, 9, 7, 'out')])
    holed = pixels_of(sample, with_hole)

    # compare against the same box with no 'out' member
    sample.roi_stack.clear()
    sample.selected_rois.clear()
    solid_id = sample.add_polygon_roi([rect(1, 1, 15, 10)])
    solid = pixels_of(sample, solid_id)

    assert 0 < holed < solid


def test_filter_and_polygon_regions_coexist_and_later_wins(sample):
    """Stack order stays priority order regardless of how a region is defined."""
    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    sample.filter_df = pd.DataFrame([{
        'use': True, 'field_type': 'Analyte', 'field': analyte, 'norm': 'linear',
        'min': -np.inf, 'max': np.inf, 'operator': 'and', 'persistent': False,
    }])
    filter_id = sample.add_roi(name='Everything', color='#00ff00')
    # the filter matches every pixel, so the polygon region added on top of it
    # must still claim its own area
    polygon_id = sample.add_polygon_roi([rect(2, 2, 8, 6)], name='Grain')

    assert pixels_of(sample, polygon_id) > 0
    assert pixels_of(sample, filter_id) == len(sample.processed) - pixels_of(sample, polygon_id)


def test_percentages_and_region_stats_cover_polygon_regions(sample):
    roi_id = sample.add_polygon_roi([rect(2, 2, 12, 8)], name='Grain')

    percentages = sample.roi_percentages()
    assert roi_id in percentages
    assert 0 < percentages[roi_id]['pct_total'] < 100

    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    summary = regionstats.region_stats(
        sample.processed, sample.mask, 'ROI', [analyte], exclude_ids=[],
    )
    assert roi_id in set(summary['ROI'])
    assert f'{analyte}_mean' in summary.columns


def test_recreating_a_region_updates_it_rather_than_duplicating(sample):
    roi_id = sample.add_polygon_roi([rect(2, 2, 6, 6)], source='group:1')
    small = pixels_of(sample, roi_id)

    assert sample.polygon_roi_for_source('group:1') == roi_id
    assert sample.polygon_roi_for_source('group:2') is None

    sample.update_polygon_roi(roi_id, [rect(2, 2, 14, 10)])

    assert len(sample.roi_stack) == 1
    assert pixels_of(sample, roi_id) > small


def test_geometry_is_snapshotted_not_referenced(sample):
    """Editing the list you passed in must not silently move the region."""
    members = [rect(2, 2, 8, 6)]
    roi_id = sample.add_polygon_roi(members)
    before = pixels_of(sample, roi_id)

    members[0]['verts'] = [(0, 0), (30, 0), (30, 20), (0, 20)]
    sample.recompute_roi_assignments()

    assert pixels_of(sample, roi_id) == before


def test_filter_only_operations_tolerate_a_geometry_region(sample):
    """duplicate_roi/update_roi_filter must not blow up on a region that has
    no filter definition, and must not overwrite its geometry.
    """
    roi_id = sample.add_polygon_roi([rect(2, 2, 8, 6)], name='Grain', source='group:1')
    claimed = pixels_of(sample, roi_id)
    geometry = copy.deepcopy(next(r for r in sample.roi_stack if r['id'] == roi_id)['polygons'])

    copy_id = sample.duplicate_roi(roi_id)
    assert copy_id is not None
    # The duplicate sits on top of the stack, so it wins the pixels both
    # cover -- the documented priority rule, same as for filter regions.
    assert pixels_of(sample, copy_id) == claimed
    # the copy is independent: it keeps the geometry but not the source key,
    # so refreshing the original later won't overwrite it
    copy_entry = next(r for r in sample.roi_stack if r['id'] == copy_id)
    assert copy_entry['source'] is None
    assert sample.polygon_roi_for_source('group:1') == roi_id

    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    sample.update_roi_filter(roi_id, pd.DataFrame([{
        'use': True, 'field_type': 'Analyte', 'field': analyte, 'norm': 'linear',
        'min': -np.inf, 'max': np.inf, 'operator': 'and', 'persistent': False,
    }]))

    entry = next(r for r in sample.roi_stack if r['id'] == roi_id)
    assert entry['filter_df'] is None
    assert entry['polygons'] == geometry
