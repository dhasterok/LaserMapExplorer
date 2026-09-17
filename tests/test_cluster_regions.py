"""Regions of interest defined by clusters (`SampleObj.add_cluster_roi`).

Linked clusters form one class; this is where such a class enters the ROI
machinery, so that the existing per-region reporting (`roi_percentages`,
`regionstats.region_stats`, the ROI map) covers clusters too -- and so a
cluster-defined region can coexist with polygon- and filter-defined ones.

Pure data-layer tests -- no QApplication, using the synthetic sample from
tests/conftest.py (a 40x30 grid).
"""
import numpy as np
import pandas as pd
import pytest

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.data.DataHandling import LaserSampleObj
from src.stoichiometry import regionstats

METHOD = 'k-means'


@pytest.fixture
def sample(synthetic_sample_csv):
    s = LaserSampleObj(
        sample_id='RM01', file_path=str(synthetic_sample_csv),
        outlier_method='Chauvenet criterion', negative_method='ignore negatives',
        ref_chem=pd.Series(dtype=float),
    )
    # Stand in for a clustering run: four stripes across the map, the same
    # shape Clustering.compute_clusters writes (int labels stored as float).
    labels = (np.arange(len(s.processed)) % 4).astype(float)
    s.add_columns('Cluster', METHOD, labels)
    return s


def rect(x0, y0, x1, y1, in_out='in'):
    return {'verts': [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 'in_out': in_out}


def pixels_of(sample, roi_id):
    return int((sample.processed['ROI'].values == roi_id).sum())


def cluster_size(sample, label):
    return int((sample.processed[METHOD].values == label).sum())


def test_cluster_roi_claims_exactly_its_clusters_pixels(sample):
    roi_id = sample.add_cluster_roi(METHOD, [1], name='Plagioclase', color='#ff0000')

    assert roi_id == 1
    assert pixels_of(sample, roi_id) == cluster_size(sample, 1)
    claimed = sample.processed['ROI'].values == roi_id
    np.testing.assert_array_equal(claimed, sample.processed[METHOD].values == 1)


def test_linked_clusters_become_one_region(sample):
    """Two cluster labels, one region id -- the point of linking."""
    roi_id = sample.add_cluster_roi(METHOD, [0, 2], name='Plagioclase')

    assert set(np.unique(sample.processed['ROI'].values)) == {0, roi_id}
    assert pixels_of(sample, roi_id) == cluster_size(sample, 0) + cluster_size(sample, 2)


def test_membership_is_snapshotted_not_referenced(sample):
    """Re-linking the clusters must not silently move the region."""
    members = [0, 2]
    roi_id = sample.add_cluster_roi(METHOD, members)
    before = pixels_of(sample, roi_id)

    members.append(3)
    sample.recompute_roi_assignments()

    assert pixels_of(sample, roi_id) == before


def test_recreating_a_region_updates_it_rather_than_duplicating(sample):
    source = f'cluster:{METHOD}:0'
    roi_id = sample.add_cluster_roi(METHOD, [0], source=source)
    small = pixels_of(sample, roi_id)

    assert sample.roi_for_source(source) == roi_id
    assert sample.roi_for_source(f'cluster:{METHOD}:1') is None

    sample.update_cluster_roi(roi_id, METHOD, [0, 1])

    assert len(sample.roi_stack) == 1
    assert pixels_of(sample, roi_id) > small


def test_cluster_and_polygon_regions_coexist_and_later_wins(sample):
    """Stack order stays priority order regardless of how a region is defined."""
    cluster_id = sample.add_cluster_roi(METHOD, [0, 1, 2, 3], name='Everything')
    polygon_id = sample.add_polygon_roi([rect(2, 2, 8, 6)], name='Grain')

    assert pixels_of(sample, polygon_id) > 0
    assert pixels_of(sample, cluster_id) == len(sample.processed) - pixels_of(sample, polygon_id)


def test_percentages_and_region_stats_cover_cluster_regions(sample):
    roi_id = sample.add_cluster_roi(METHOD, [1, 3], name='Plagioclase')

    percentages = sample.roi_percentages()
    assert roi_id in percentages
    assert percentages[roi_id]['pct_total'] == pytest.approx(50.0)

    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    summary = regionstats.region_stats(
        sample.processed, sample.mask, 'ROI', [analyte], exclude_ids=[],
    )
    assert roi_id in set(summary['ROI'])
    assert f'{analyte}_mean' in summary.columns


def test_a_region_whose_cluster_column_is_gone_claims_nothing(sample):
    """Re-clustering under another method must not break every other region."""
    missing_id = sample.add_cluster_roi('fuzzy c-means', [0], name='Stale')
    live_id = sample.add_cluster_roi(METHOD, [1], name='Live')

    assert pixels_of(sample, missing_id) == 0
    assert pixels_of(sample, live_id) == cluster_size(sample, 1)


def test_reclustering_rebinds_a_region_to_the_new_clusters(sample):
    """A cluster region records ids, not pixels -- so it follows the labels.

    Unlike a polygon region (geometry, always meaningful), cluster ids only
    mean something relative to one clustering run. Pinning the behaviour here
    because it is surprising: the region silently covers whatever the new
    clusters with those ids cover.
    """
    roi_id = sample.add_cluster_roi(METHOD, [0, 1], name='Plagioclase')
    before = pixels_of(sample, roi_id)

    # re-run clustering: same column, different partition (2 clusters, not 4)
    labels = (np.arange(len(sample.processed)) % 2).astype(float)
    sample.add_columns('Cluster', METHOD, labels)
    sample.recompute_roi_assignments()

    after = pixels_of(sample, roi_id)
    assert after != before
    assert after == len(sample.processed)  # ids 0 and 1 are now every pixel


def test_filter_only_operations_tolerate_a_cluster_region(sample):
    """duplicate_roi/update_roi_filter must not blow up on a region with no
    filter definition, and must not overwrite its cluster membership.
    """
    source = f'cluster:{METHOD}:0'
    roi_id = sample.add_cluster_roi(METHOD, [0], name='Plagioclase', source=source)
    claimed = pixels_of(sample, roi_id)

    copy_id = sample.duplicate_roi(roi_id)
    assert copy_id is not None
    # The duplicate sits on top of the stack, so it wins the pixels both
    # cover -- the documented priority rule, same as for every other kind.
    assert pixels_of(sample, copy_id) == claimed
    copy_entry = next(r for r in sample.roi_stack if r['id'] == copy_id)
    assert copy_entry['clusters'] == [0]
    assert copy_entry['cluster_method'] == METHOD
    # the copy is independent: refreshing the original later won't overwrite it
    assert copy_entry['source'] is None
    assert sample.roi_for_source(source) == roi_id

    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    sample.update_roi_filter(roi_id, pd.DataFrame([{
        'use': True, 'field_type': 'Analyte', 'field': analyte, 'norm': 'linear',
        'min': -np.inf, 'max': np.inf, 'operator': 'and', 'persistent': False,
    }]))

    entry = next(r for r in sample.roi_stack if r['id'] == roi_id)
    assert entry['filter_df'] is None
    assert entry['clusters'] == [0]
