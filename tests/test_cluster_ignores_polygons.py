"""Clustering and the cluster map ignore polygons.

Polygons are a field-map selection tool. Drawing one must not shrink the
population the clusters are fitted on, nor blank the cluster map outside it.
Everything else in the combined mask (crop, cluster and ROI masks) still
applies to both.
"""
import numpy as np
import pytest

from src.plotting.LamePlot import cluster_map_labels


# ---------------------------------------------------------------------------
# cluster_map_labels (pure)
# ---------------------------------------------------------------------------
def test_cluster_map_blanks_masked_and_unclustered_pixels_only():
    labels = np.array([0, 1, 2, 99, 1, 0])
    mask = np.array([True, True, True, True, False, True])

    shown = cluster_map_labels(labels, mask, valid_labels=[0, 1, 2])

    assert shown[:3].tolist() == [0.0, 1.0, 2.0]
    assert np.isnan(shown[3])       # never clustered
    assert np.isnan(shown[4])       # masked
    assert shown[5] == 0.0


def test_cluster_map_labels_copes_with_a_read_only_column():
    # what a pandas float column looks like under copy-on-write
    labels = np.array([0.0, 99.0, 1.0])
    labels.setflags(write=False)

    shown = cluster_map_labels(labels, np.ones(3, dtype=bool), valid_labels=[0, 1])

    assert np.isnan(shown[1]) and shown[[0, 2]].tolist() == [0.0, 1.0]
    assert labels.tolist() == [0.0, 99.0, 1.0]


# ---------------------------------------------------------------------------
# mask_without + compute_clusters on a real SampleObj
# ---------------------------------------------------------------------------
@pytest.fixture
def masked_sample(loaded_window):
    """``(window, data)`` for RM01 with a polygon mask covering half the map."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    data = window.app_data.current_data

    polygon_mask = np.ones(len(data.mask), dtype=bool)
    polygon_mask[: len(polygon_mask) // 2] = False
    data.polygon_mask = polygon_mask
    data.recompute_mask()
    assert not data.mask.all()
    return window, data


def test_mask_without_polygon_drops_only_the_polygon_component(masked_sample):
    _window, data = masked_sample

    without = data.mask_without('polygon')

    assert without.tolist() == data.crop_mask.astype(bool).tolist()
    # and without any exclusion it is exactly the stored mask
    assert data.mask_without().tolist() == data.mask.tolist()


def test_mask_without_keeps_the_other_components(masked_sample):
    _window, data = masked_sample
    cluster_mask = np.ones(len(data.mask), dtype=bool)
    cluster_mask[-1] = False
    data.cluster_mask = cluster_mask
    data.recompute_mask()

    without = data.mask_without('polygon')

    assert not without[-1]
    assert without[:-1].all()


def test_disabled_polygon_toggle_and_mask_without_agree(masked_sample):
    window, data = masked_sample
    window.toggle_polygon_mask(False)

    assert data.mask.tolist() == data.mask_without('polygon').tolist()


def test_kmeans_clusters_the_whole_map_despite_a_polygon(masked_sample):
    window, data = masked_sample
    app_data = window.app_data
    app_data.cluster_method = 'k-means'
    app_data.num_clusters = 2

    window.control_dock.clustering.compute_clusters(data, app_data, max_clusters=None)

    labels = data.processed['k-means'].values
    inside = data.mask_without('polygon')
    # every pixel the crop keeps got a real label, including the half the
    # polygon excludes
    assert np.isfinite(labels[inside]).all()
    assert not (labels[inside] == 99).any()
    assert set(np.unique(labels[inside])) <= {0.0, 1.0}
