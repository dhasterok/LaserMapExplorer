"""ROIs and cluster groups round-trip through a saved project.

Pure data-layer tests: export from one sample, go through the manifest's
JSON, replay onto a fresh copy of the same sample, and compare.
"""
import json

import numpy as np
import pandas as pd
import pytest

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.data.DataHandling import LaserSampleObj
from src.data.cluster_groups import cluster_groups
from src.project.ProjectModel import (
    SampleProcessingState,
    _processing_state_from_dict,
    _processing_state_to_dict,
    load_cluster_labels,
    save_cluster_labels,
)


@pytest.fixture
def make_sample(synthetic_sample_csv):
    def make():
        return LaserSampleObj(
            sample_id='RM01', file_path=str(synthetic_sample_csv),
            outlier_method='Chauvenet criterion', negative_method='ignore negatives',
            ref_chem=pd.Series(dtype=float),
        )
    return make


def _through_json(state):
    """What a save followed by a load does to a processing state."""
    return _processing_state_from_dict(json.loads(json.dumps(_processing_state_to_dict(state))))


def _add_kmeans_labels(sample):
    n = sample.processed.shape[0]
    labels = (np.arange(n) % 4).astype(float)
    sample.add_columns('Cluster', 'k-means', labels)
    return labels


def _build_rois(sample):
    """One filter-, one polygon- and one cluster-defined ROI."""
    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    values = sample.processed[analyte].values
    sample.add_filter(field_type='Analyte', field=analyte,
                      min_val=float(np.nanmin(values)), max_val=float(np.nanmedian(values)))
    sample.add_roi(name='Low', color='#ff0000')

    sample.add_polygon_roi(
        [{'verts': [(0, 0), (10, 0), (10, 10), (0, 10)], 'in_out': 'in'}],
        name='Square', color='#00ff00', source='polygon:1',
    )
    sample.add_cluster_roi('k-means', [1, 2], name='Grains', color='#0000ff',
                           source='cluster:k-means:1')


def test_rois_round_trip(make_sample):
    original = make_sample()
    _add_kmeans_labels(original)
    _build_rois(original)
    original.reorder_roi_stack([3, 1, 2])
    original.selected_rois = [1, 3]
    original.recompute_roi_assignments()

    state = _through_json(original.export_processing_state())

    restored = make_sample()
    _add_kmeans_labels(restored)
    restored.apply_processing_state(state)

    assert [r['id'] for r in restored.roi_stack] == [3, 1, 2]
    assert [r['name'] for r in restored.roi_stack] == ['Grains', 'Low', 'Square']
    assert [r['color'] for r in restored.roi_stack] == ['#0000ff', '#ff0000', '#00ff00']
    assert restored.selected_rois == [1, 3]
    assert restored.roi_for_source('cluster:k-means:1') == 3
    np.testing.assert_array_equal(restored.processed['ROI'].values, original.processed['ROI'].values)
    np.testing.assert_array_equal(restored.roi_selection_mask, original.roi_selection_mask)
    # every kind of region actually claims pixels
    assert set(np.unique(restored.processed['ROI'].values)) >= {1, 2, 3}


def test_cluster_groups_round_trip(make_sample):
    original = make_sample()
    original.cluster_entries = {
        'k-means': {
            'entries': {
                0: {'name': 'Quartz', 'color': '#111111', 'link': []},
                1: {'name': 'Garnet', 'color': '#222222', 'link': [1, 3]},
                2: {'name': 'Cluster 3', 'color': '#333333', 'link': []},
                3: {'name': 'Cluster 4', 'color': '#222222', 'link': [1, 3]},
            },
            'selected_clusters': [1, 3],
        },
    }

    state = _through_json(original.export_processing_state())
    restored = make_sample()
    restored.apply_processing_state(state)

    groups = restored.cluster_entries['k-means']
    assert all(isinstance(k, int) for k in groups['entries'])
    assert groups == original.cluster_entries['k-means']
    assert cluster_groups(groups['entries']) == [(0, [0]), (1, [1, 3]), (2, [2])]


def test_cluster_labels_sidecar_round_trip(make_sample, tmp_path):
    original = make_sample()
    labels = _add_kmeans_labels(original)
    labels_with_gaps = labels.copy()
    labels_with_gaps[:5] = np.nan  # rows outside the clustering mask
    original.add_columns('Cluster', 'HDBSCAN', labels_with_gaps)

    path = tmp_path / 'RM01' / 'clusters.npz'
    assert save_cluster_labels(original, path)

    restored = make_sample()
    assert sorted(load_cluster_labels(restored, path)) == ['HDBSCAN', 'k-means']
    np.testing.assert_array_equal(restored.processed['k-means'].values, labels)
    np.testing.assert_array_equal(restored.processed['HDBSCAN'].values, labels_with_gaps)
    assert 'k-means' in restored.processed.match_attribute('data_type', 'Cluster')


def test_cluster_labels_sidecar_removed_when_no_clusters(make_sample, tmp_path):
    path = tmp_path / 'RM01' / 'clusters.npz'
    path.parent.mkdir()
    path.write_bytes(b'stale')

    assert not save_cluster_labels(make_sample(), path)
    assert not path.exists()


def test_manifest_without_new_keys_loads_empty():
    state = _processing_state_from_dict({'applied_filters': [], 'masks': []})

    assert state.rois == []
    assert state.selected_rois == []
    assert state.cluster_groups == {}


def test_untouched_sample_leaves_rois_alone(make_sample):
    sample = make_sample()
    sample.apply_processing_state(SampleProcessingState())
    assert sample.roi_stack == []
    assert sample.cluster_entries == {}


def test_preprocessing_rebuild_keeps_clusters_and_rois(make_sample):
    """Changing the outlier method rebuilds `processed` from `raw`; cluster
    labels and ROIs must survive it (a project reload hits this path)."""
    sample = make_sample()
    labels = _add_kmeans_labels(sample)
    sample.add_cluster_roi('k-means', [1, 2], name='Grains', color='#0000ff')
    roi_before = sample.processed['ROI'].values.copy()

    sample.outlier_method = 'none' if sample.outlier_method != 'none' else 'Chauvenet criterion'

    np.testing.assert_array_equal(sample.processed['k-means'].values, labels)
    assert 'k-means' in sample.processed.match_attribute('data_type', 'Cluster')
    np.testing.assert_array_equal(sample.processed['ROI'].values, roi_before)
