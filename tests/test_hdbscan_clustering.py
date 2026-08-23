"""Characterization test for the new HDBSCAN-in-clr-space clustering method
(``Clustering.compute_clusters`` with ``cluster_method='HDBSCAN'`` in
src/app/DataAnalysis.py). Demonstrates the specific capability that
motivated adding it (see mineral_id.md): a small minority class survives as
its own cluster, and pixels that don't belong to any dense group are
flagged as noise -- something no fixed-k, every-point-gets-a-label method
(k-means, fuzzy c-means) can do regardless of how k is chosen.

Uses lightweight, PyQt-free stand-ins for ``SampleObj``/``AppData`` (only
the handful of attributes/methods ``compute_clusters`` actually touches),
so this runs without a QApplication -- matching the ``tests/test_stoichiometry_*.py``
convention of testing backend logic directly.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.app.DataAnalysis import Clustering
from src.data.ExtendedDF import AttributeDataFrame


class FakeSample:
    """Minimal stand-in for SampleObj -- only the members compute_clusters
    (and its _clr_feature_matrix helper) actually use.
    """

    def __init__(self, df: AttributeDataFrame, mask: np.ndarray):
        self.processed = df
        self.mask = mask
        self.cluster_results = {}
        self.silhouette_scores = {}

    def get_map_data(self, field, field_type='Analyte', norm='linear'):
        return {'array': self.processed[field]}

    def get_processed_data(self, field_types=('Analyte', 'Ratio')):
        columns = {}
        for field_type in field_types:
            for field in self.processed.match_attributes({'data_type': field_type, 'use': True}):
                columns[field] = self.processed[field].values
        df = pd.DataFrame(columns, index=self.processed.index)
        return df, list(columns.keys())

    def add_columns(self, data_type, name, values, mask):
        if name not in self.processed.columns:
            self.processed[name] = np.nan
        self.processed.loc[mask, name] = values


class FakeAppData:
    """Minimal stand-in for AppData -- only the cluster_* properties
    compute_clusters reads.
    """

    def __init__(self, method):
        self.sample_id = 'sample1'
        self.dim_red_precondition = False
        self.cluster_seed = 23
        self.cluster_method = method
        self.cluster_exponent = 2.1
        self.cluster_distance = 'euclidean'
        self.num_clusters = 2
        self.max_clusters = 10
        # min_cluster_size/min_samples are derived as
        # max(2, round(n_pixels * pct/100)) / max(1, round(min_cluster_size * factor));
        # with the 189-pixel synthetic dataset below (180 majority + 6 minority
        # + 3 boundary), 2.65% -> round(189*0.0265)=5 pixels, and a 0.6 factor
        # -> round(5*0.6)=3 -- reproducing the min_cluster_size=5/min_samples=3
        # pixel counts this test suite was originally verified against.
        self.cluster_min_size_pct = 2.65
        self.cluster_min_samples_factor = 0.6


def _make_sample_dataframe():
    """A large majority phase, a tiny (~3%) but tightly-clustered and
    compositionally distinct minority phase (mimicking a rare accessory
    mineral like zircon: Zr-dominant instead of Si-dominant), and a handful
    of isolated, mutually-distant "boundary/mixed" pixels that belong to
    neither group -- the exact scenario mineral_id.md flags as the failure
    mode for k-means/fuzzy c-means.
    """
    rng = np.random.default_rng(0)

    n_majority = 180
    majority = rng.normal(loc=[700000.0, 80000.0, 50.0], scale=[5000.0, 800.0, 5.0], size=(n_majority, 3))

    n_minority = 6
    minority = rng.normal(loc=[300000.0, 5000.0, 470000.0], scale=[2000.0, 100.0, 3000.0], size=(n_minority, 3))

    # near-pure single-element compositions -- isolated outliers, far apart
    # from each other and from both groups (verified against this exact
    # min_cluster_size/min_samples config) so they can't form a cluster of
    # their own
    boundary = np.array([
        [1.0, 1e6, 1.0],      # ~pure Al
        [1.0, 1.0, 1e6],      # ~pure Zr
        [1.0, 1e6, 1e6],      # Al+Zr, ~no Si
    ])

    data = np.vstack([majority, minority, boundary])
    labels_true = np.array(['majority'] * n_majority + ['minority'] * n_minority + ['boundary'] * len(boundary))

    df = AttributeDataFrame(pd.DataFrame(data, columns=['Si29', 'Al27', 'Zr90']))
    for col in df.columns:
        df.set_attribute(col, 'data_type', 'Analyte')
        df.set_attribute(col, 'use', True)
        df.set_attribute(col, 'use_normalized', False)
        df.set_attribute(col, 'norm', 'linear')

    mask = np.ones(len(df), dtype=bool)
    return df, mask, labels_true


def test_hdbscan_recovers_minority_cluster_and_flags_boundary_noise():
    df, mask, labels_true = _make_sample_dataframe()
    data = FakeSample(df, mask)
    app_data = FakeAppData('HDBSCAN')

    Clustering().compute_clusters(data, app_data, max_clusters=None)

    result = data.processed['HDBSCAN'].to_numpy()
    majority_ids = set(result[labels_true == 'majority'])
    minority_ids = set(result[labels_true == 'minority'])
    boundary_ids = set(result[labels_true == 'boundary'])

    # each true group maps onto exactly one cluster id, and majority/minority get different ids
    assert len(majority_ids) == 1
    assert len(minority_ids) == 1
    assert majority_ids != minority_ids

    # isolated boundary pixels are noise, remapped to this app's existing "id 99 = Mask" convention
    assert boundary_ids == {99}


def test_hdbscan_handles_negative_and_zero_analyte_values():
    """Regression test: real background-subtracted/calibrated LA-ICP-MS
    values routinely include exact zeros and small negative values near the
    detection limit (a background-subtraction artifact, not a real negative
    concentration). ``composition_stats.closure`` raises on negatives and
    plain ``clr`` produces inf/nan on zeros -- ``_clr_feature_matrix`` must
    floor negatives to zero and multiplicatively replace zeros before the
    clr transform, or this crashes on real data (caught via manual testing
    against an actual sample, not by the synthetic-data tests above, which
    happened not to include either case).
    """
    df, mask, labels_true = _make_sample_dataframe()
    # inject a few zeros and small negatives, as real censored/background-
    # subtracted data would have
    df.loc[df.index[0], 'Zr90'] = 0.0
    df.loc[df.index[1], 'Al27'] = -12.5
    data = FakeSample(df, mask)
    app_data = FakeAppData('HDBSCAN')

    Clustering().compute_clusters(data, app_data, max_clusters=None)

    result = data.processed['HDBSCAN'].to_numpy()
    assert np.all(np.isin(result, [0, 1, 99]))


def test_kmeans_forced_to_one_cluster_absorbs_the_minority():
    """Contrast case: a fixed-k, every-point-gets-a-label method has no way
    to express "this handful of pixels doesn't belong anywhere" -- with k
    forced to 1 (the fixed-k failure mode mineral_id.md describes: picking
    k from what looks like the obvious majority structure), every pixel,
    minority and boundary included, is forced into the same single cluster.
    """
    df, mask, labels_true = _make_sample_dataframe()
    data = FakeSample(df, mask)
    app_data = FakeAppData('k-means')
    app_data.num_clusters = 1

    Clustering().compute_clusters(data, app_data, max_clusters=None)

    result = data.processed['k-means'].to_numpy()
    assert len(set(result)) == 1
