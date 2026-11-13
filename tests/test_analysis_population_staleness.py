"""Clustering and PCA results know which region they were fitted on.

Both fit only the *unmasked* pixels and write their output into
``processed`` for those rows alone, leaving the rest NaN. Nothing about the
stored result recorded which region that was, and re-clustering was gated
solely on ``update_cluster_flag`` -- set only by a clustering *parameter*
setter or ``change_sample``. So once clustering had run, every mask change
was invisible to it:

* Cluster inside an ROI, then switch the ROI off or delete it and
  re-cluster: the recompute was skipped outright and the old, ROI-shaped
  labels stayed on screen. This is the reported bug.
* The reverse too, and more quietly: cluster the whole map, apply an ROI,
  and the first run inside the ROI was skipped -- full-map labels shown as
  though they described the ROI, with nothing looking wrong.

``SampleObj`` now fingerprints the mask and the field set each analysis was
fitted on, and the two are treated differently on purpose:

* a changed **field set** recomputes, unasked -- the stored result is a fit
  in a feature space that is gone;
* a changed **mask** is reported as *stale* and left alone, because the fit
  is still valid (it is what the cluster groups, cluster-defined ROIs and
  any exported figure were built from) and because clustering's own mask
  includes ``cluster_mask``, which is *derived* from the labels -- refitting
  on every mask change would move the labels out from under the mask that
  defined them.

Re-running is explicit: the Re-run button on each page.
"""
import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# the fingerprint itself
# ---------------------------------------------------------------------------
@pytest.fixture
def sample(sample_factory, qapp):
    from src.data.DataHandling import LaserSampleObj
    return LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore negatives',
        ref_chem=pd.Series(dtype=float),
    )


def test_nothing_recorded_is_not_stale(sample):
    """A project reloaded from disk restores labels without replaying the run
    that made them. Crying stale over every such result would teach the user
    to ignore the indicator."""
    mask, fields = sample.analysis_population('polygon')
    assert sample.analysis_mask_changed('cluster', mask) is False
    assert sample.analysis_fields_changed('cluster', fields) is False


def test_the_population_it_was_fitted_on_is_not_stale(sample):
    mask, fields = sample.analysis_population('polygon')
    sample.record_analysis_population('cluster', mask, fields)

    assert sample.analysis_mask_changed('cluster', mask) is False
    assert sample.analysis_fields_changed('cluster', fields) is False


def test_a_narrower_mask_is_stale(sample):
    mask, fields = sample.analysis_population('polygon')
    sample.record_analysis_population('cluster', mask, fields)

    narrower = mask.copy()
    narrower[: len(narrower) // 2] = False

    assert sample.analysis_mask_changed('cluster', narrower) is True
    assert sample.analysis_fields_changed('cluster', fields) is False


def test_a_changed_field_set_is_reported_separately(sample):
    mask, fields = sample.analysis_population('polygon')
    sample.record_analysis_population('cluster', mask, fields)

    assert sample.analysis_fields_changed('cluster', fields[:-1]) is True
    assert sample.analysis_mask_changed('cluster', mask) is False


def test_each_analysis_is_tracked_independently(sample):
    mask, fields = sample.analysis_population('polygon')
    sample.record_analysis_population('cluster', mask, fields)

    narrower = mask.copy()
    narrower[0] = False
    assert sample.analysis_mask_changed('cluster', narrower) is True
    assert sample.analysis_mask_changed('dim_red', narrower) is False


def test_analysis_fields_matches_get_processed_data(sample):
    """The fingerprint must describe the matrix actually analysed."""
    df, use_fields = sample.get_processed_data()
    assert sample.analysis_fields() == tuple(use_fields)
    assert list(df.columns) == list(use_fields)


def test_analysis_population_excludes_what_it_is_told_to(sample):
    """Clustering passes 'polygon', matching the mask compute_clusters uses."""
    polygon_mask = np.ones(sample.n_pixels, dtype=bool)
    polygon_mask[0] = False
    sample.polygon_mask = polygon_mask
    sample.recompute_mask()

    with_polygon, _ = sample.analysis_population()
    without_polygon, _ = sample.analysis_population('polygon')

    assert not with_polygon[0]
    assert without_polygon.all()


# ---------------------------------------------------------------------------
# the reported bug, through the real UI entry point
# ---------------------------------------------------------------------------
@pytest.fixture
def clustered_window(loaded_window):
    """``(window, data, page)`` with RM01 clustered over the whole map."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    data = window.app_data.current_data
    page = window.control_dock.clustering

    page.compute_clusters_update_groups()
    assert clustered_pixels(data, window.app_data.cluster_method) == data.n_pixels
    return window, data, page


def clustered_pixels(data, method):
    """How many pixels carry a real cluster id (not NaN, not the 99 sentinel)."""
    labels = data.processed[method].values.astype(float)
    return int(np.sum(np.isfinite(labels) & (labels != 99)))


def add_half_map_roi(data):
    """Commit an ROI covering roughly half the map, and return its id."""
    field = data.processed.match_attributes({'data_type': 'Analyte', 'use': True})[0]
    values = data.processed[field].values.astype(float)
    data.filter_df = pd.DataFrame([{
        'use': True, 'field_type': 'Analyte', 'field': field, 'norm': 'linear',
        'min': np.nanmedian(values), 'max': np.nanmax(values),
        'operator': 'and', 'persistent': True,
    }])
    data.apply_field_filters()
    roi_id = data.add_roi(name='half')
    assert data.mask.sum() < data.n_pixels, 'the ROI did not narrow the mask'
    return roi_id


def add_complementary_roi(data):
    """A second region covering the half `add_half_map_roi` left out."""
    field = data.processed.match_attributes({'data_type': 'Analyte', 'use': True})[0]
    values = data.processed[field].values.astype(float)
    data.filter_df = pd.DataFrame([{
        'use': True, 'field_type': 'Analyte', 'field': field, 'norm': 'linear',
        'min': np.nanmin(values), 'max': np.nanmedian(values),
        'operator': 'and', 'persistent': True,
    }])
    data.apply_field_filters()
    return data.add_roi(name='other half')


def test_applying_an_roi_marks_the_clusters_stale(clustered_window):
    window, data, page = clustered_window
    assert page.cluster_results_stale() is False

    add_half_map_roi(data)

    assert page.cluster_results_stale() is True


def test_a_stale_result_is_kept_not_silently_refitted(clustered_window):
    """The deliberate half of the design: the fit on screen is the one the
    cluster groups and any cluster-defined ROI were built from."""
    window, data, page = clustered_window
    method = window.app_data.cluster_method
    before = data.processed[method].values.copy()

    add_half_map_roi(data)
    page.compute_clusters_update_groups()

    assert np.array_equal(data.processed[method].values, before, equal_nan=True)


def test_re_run_fits_the_roi(clustered_window):
    window, data, page = clustered_window
    method = window.app_data.cluster_method
    add_half_map_roi(data)

    page.compute_clusters_update_groups(force=True)

    assert clustered_pixels(data, method) == data.mask.sum() < data.n_pixels
    assert page.cluster_results_stale() is False


@pytest.mark.parametrize("release", ['toggle_off', 'delete'])
def test_releasing_the_roi_lets_the_full_map_be_reclustered(clustered_window, release):
    """The reported bug: re-clustering after the ROI was turned off or deleted
    only ever reclustered the pixels the ROI had left unmasked."""
    window, data, page = clustered_window
    method = window.app_data.cluster_method
    roi_id = add_half_map_roi(data)
    page.compute_clusters_update_groups(force=True)
    assert clustered_pixels(data, method) < data.n_pixels

    if release == 'toggle_off':
        window.toggle_roi_mask(False)
    else:
        data.remove_roi(roi_id)
    assert data.mask.sum() == data.n_pixels, 'the mask itself did not widen'

    assert page.cluster_results_stale() is True
    page.compute_clusters_update_groups(force=True)

    assert clustered_pixels(data, method) == data.n_pixels
    assert page.cluster_results_stale() is False


def test_deselecting_an_roi_marks_it_stale_too(clustered_window):
    """Unchecking a region in the ROI table changes roi_selection_mask
    without removing anything from the stack.

    Two regions are needed: `recompute_roi_assignments` reads an *empty*
    selection as "every region in the stack", so unchecking the only one
    leaves the mask exactly where it was (and so, correctly, not stale).
    """
    window, data, page = clustered_window
    first = add_half_map_roi(data)
    second = add_complementary_roi(data)
    data.selected_rois = [first, second]
    data.recompute_roi_assignments()
    page.compute_clusters_update_groups(force=True)
    assert page.cluster_results_stale() is False
    both = data.mask.sum()

    data.selected_rois = [first]
    data.recompute_roi_assignments()

    assert data.mask.sum() < both
    assert page.cluster_results_stale() is True


def test_a_changed_analyte_selection_recomputes_without_being_asked(clustered_window):
    """A fit in a feature space the user has since changed is not worth
    keeping, so this one does not wait for Re-run."""
    window, data, page = clustered_window
    method = window.app_data.cluster_method
    dropped = data.processed.match_attributes({'data_type': 'Analyte', 'use': True})[-1]
    before = data.processed[method].values.copy()

    data.processed.set_attribute(dropped, 'use', False)
    page.compute_clusters_update_groups()

    assert not np.array_equal(data.processed[method].values, before, equal_nan=True)
    assert page.cluster_results_stale() is False


def test_a_parameter_change_still_recomputes(clustered_window):
    """update_cluster_flag's original job is untouched."""
    window, data, page = clustered_window
    method = window.app_data.cluster_method

    window.app_data.num_clusters = 3
    page.compute_clusters_update_groups()

    labels = data.processed[method].values
    assert len(np.unique(labels[labels != 99])) == 3


# ---------------------------------------------------------------------------
# what the user is shown
# ---------------------------------------------------------------------------
def visible(label):
    """``isVisible()`` is False for everything under a dock that was never
    shown, so ask about the label's own state within its parent."""
    return label.isVisibleTo(label.parentWidget())


def test_the_notice_appears_and_clears_with_the_staleness(clustered_window):
    window, data, page = clustered_window
    assert visible(page.labelClusterStale) is False

    add_half_map_roi(data)
    assert page.update_stale_indicator() is True
    assert visible(page.labelClusterStale) is True

    page.compute_clusters_update_groups(force=True)
    assert visible(page.labelClusterStale) is False


def test_a_plot_refresh_updates_the_notice(clustered_window):
    """Every mask change reaches update_SV via schedule_update, so the notice
    must not wait for the user to open the Clustering page."""
    window, data, page = clustered_window
    add_half_map_roi(data)

    window.refresh_analysis_stale_indicators()

    assert visible(page.labelClusterStale) is True


def test_the_re_run_button_forces_a_refit(clustered_window):
    window, data, page = clustered_window
    method = window.app_data.cluster_method
    add_half_map_roi(data)

    page.toolButtonClusterRerun.click()

    assert clustered_pixels(data, method) == data.mask.sum() < data.n_pixels


# ---------------------------------------------------------------------------
# dimensional reduction, same defect
# ---------------------------------------------------------------------------
@pytest.fixture
def pca_window(loaded_window):
    """``(window, data, page)`` with RM01's PCA computed over the whole map."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    data = window.app_data.current_data
    page = window.control_dock.dimreduction

    page.compute_dim_red_if_needed()
    assert data.processed.match_attribute('data_type', 'PCA score')
    return window, data, page


def scored_pixels(data):
    return int(np.isfinite(data.processed['PC1'].values.astype(float)).sum())


def test_pca_is_not_refitted_on_every_refresh(pca_window):
    """The call sites tested ``match_attribute('data_type', 'pca score')`` --
    lowercase, which matches nothing, since the attribute is written as
    'PCA score'. So the gate was always open and a full PCA ran on every
    refresh of a dimensional-reduction plot."""
    window, data, page = pca_window
    assert data.processed.match_attribute('data_type', 'pca score') == []

    before = data.processed['PC1'].values.copy()
    page.compute_dim_red_if_needed()

    assert np.array_equal(data.processed['PC1'].values, before, equal_nan=True)


def test_applying_an_roi_marks_the_scores_stale(pca_window):
    window, data, page = pca_window
    assert page.dim_red_results_stale() is False

    add_half_map_roi(data)

    assert page.dim_red_results_stale() is True
    assert page.update_stale_indicator() is True
    assert visible(page.labelDimRedStale) is True


def test_pca_re_run_fits_the_current_region(pca_window):
    window, data, page = pca_window
    add_half_map_roi(data)

    page.compute_dim_red_if_needed(force=True)

    assert scored_pixels(data) == data.mask.sum() < data.n_pixels
    assert page.dim_red_results_stale() is False
    assert visible(page.labelDimRedStale) is False


def test_releasing_the_roi_lets_pca_refit_the_full_map(pca_window):
    window, data, page = pca_window
    roi_id = add_half_map_roi(data)
    page.compute_dim_red_if_needed(force=True)
    assert scored_pixels(data) < data.n_pixels

    data.remove_roi(roi_id)
    page.compute_dim_red_if_needed(force=True)

    assert scored_pixels(data) == data.n_pixels


def test_pca_recomputes_on_a_changed_analyte_selection(pca_window):
    window, data, page = pca_window
    dropped = data.processed.match_attributes({'data_type': 'Analyte', 'use': True})[-1]
    before = data.processed['PC1'].values.copy()

    data.processed.set_attribute(dropped, 'use', False)
    page.compute_dim_red_if_needed()

    assert not np.array_equal(data.processed['PC1'].values, before, equal_nan=True)
    assert page.dim_red_results_stale() is False
