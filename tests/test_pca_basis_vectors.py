"""PCA basis-vector labelling.

``plot_pca_vectors`` labelled its rows with the sample's *Analyte* list
while sizing them from ``components_``, which is one column per field the
PCA was actually fit on -- every field flagged ``use``/``use_normalized``
across Analyte *and* Ratio types (see ``get_processed_data``). With a ratio
or a normalized variant selected the two counts differ and matplotlib
raised "The number of FixedLocator locations (21) ... does not match the
number of labels (17)".

Uses lightweight, PyQt-free stand-ins for ``SampleObj``/``AppData`` (only
what ``compute_pca`` touches), matching tests/test_hdbscan_clustering.py.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.app.DataAnalysis import DimensionalReduction
from src.data.ExtendedDF import AttributeDataFrame
from src.plotting.LamePlot import pca_field_labels

PCA_METHOD = 'PCA: Principal component analysis'

#: Analyte columns, plus one ratio -- the ratio is what makes the analysis
#: field list longer than the Analyte list.
ANALYTES = ['Al27', 'Ca43', 'Fe57', 'Sr88']
RATIO = 'Sr88 / Ca43'


class FakeSample:
    """Minimal stand-in for SampleObj -- only what compute_pca uses."""

    def __init__(self, df, mask):
        self.processed = df
        self.mask = mask
        self.dim_red_results = {}
        self.added_columns = {}

    def get_map_data(self, field, field_type='Analyte', norm='linear'):
        return {'array': self.processed[field]}

    def get_processed_data(self, field_types=('Analyte', 'Ratio')):
        columns = {}
        for field_type in field_types:
            for field in self.processed.match_attributes({'data_type': field_type, 'use': True}):
                columns[field] = self.processed[field].values
        df = pd.DataFrame(columns, index=self.processed.index)
        return df, list(columns.keys())

    def add_columns(self, data_type, names, values, mask=None):
        # Same row-count check the real SampleObj.add_columns makes -- this is
        # the one that reported "The number of rows in (array) must match the
        # number of `True` values in the mask."
        if mask is not None and values.shape[0] != mask.sum():
            raise ValueError("The number of rows in (array) must match the number of `True` values in the mask.")
        self.added_columns[data_type] = list(names)
        self.added_values = values


class FakeAppData:
    """Minimal stand-in for AppData -- only what compute_pca writes/reads."""

    def __init__(self):
        self.dim_red_method = PCA_METHOD
        self.update_pca_flag = True
        self.dim_red_x = 0
        self.dim_red_y = 0
        self.dim_red_x_max = 0
        self.dim_red_y_max = 0
        self.num_basis_for_precondition = 0
        self.sample_id = 'RM01'


@pytest.fixture
def sample():
    """A sample with four analytes and one ratio, all selected for analysis."""
    rng = np.random.default_rng(0)
    n = 200
    df = AttributeDataFrame({f: rng.uniform(1.0, 100.0, n) for f in ANALYTES})
    df[RATIO] = df['Sr88'] / df['Ca43']

    for field in ANALYTES:
        df.set_attribute(field, 'data_type', 'Analyte')
        df.set_attribute(field, 'use', True)
        df.set_attribute(field, 'norm', 'linear')
    df.set_attribute(RATIO, 'data_type', 'Ratio')
    df.set_attribute(RATIO, 'use', True)
    df.set_attribute(RATIO, 'norm', 'linear')

    return FakeSample(df, np.ones(n, dtype=bool))


@pytest.fixture
def pca_results(sample):
    app_data = FakeAppData()
    DimensionalReduction().compute_pca(sample, app_data)
    return sample.dim_red_results[PCA_METHOD]


def test_pca_runs_with_a_filter_applied(sample):
    """A filter/ROI leaves `data.mask` with fewer True values than there are
    rows; PCA has to analyse (and score) exactly those rows. Fitting the full
    frame made `add_columns` reject the scores as too long, which is what
    stopped dimensional reduction working after a filter had been used."""
    sample.mask[::3] = False
    n_analysed = int(sample.mask.sum())
    assert n_analysed < len(sample.processed)

    DimensionalReduction().compute_pca(sample, FakeAppData())

    assert sample.added_values.shape[0] == n_analysed
    assert sample.added_columns['PCA score'][0] == 'PC1'


def test_pca_ignores_masked_out_rows(sample):
    """The masked-out rows must not reach the fit -- if they did, extreme
    filtered values would still steer the components."""
    unfiltered = DimensionalReduction()
    unfiltered.compute_pca(sample, FakeAppData())
    all_rows = sample.dim_red_results[PCA_METHOD].components_.copy()

    # Make the rows we're about to mask out wild outliers.
    sample.processed.iloc[::3, :] *= 1000
    sample.mask[::3] = False
    DimensionalReduction().compute_pca(sample, FakeAppData())
    masked = sample.dim_red_results[PCA_METHOD].components_

    assert not np.allclose(all_rows, masked), \
        "components should reflect only the unmasked rows"


def test_compute_pca_records_the_analysis_field_names(pca_results):
    """The names have to survive the StandardScaler step -- scaling returns a
    bare array, and fitting on one leaves `feature_names_in_` unset."""
    assert list(pca_results.feature_names_in_) == ANALYTES + [RATIO]


def test_labels_cover_every_column_of_components(pca_results, sample):
    labels = pca_field_labels(pca_results, sample)

    assert len(labels) == pca_results.components_.shape[1]
    assert labels == ANALYTES + [RATIO]


def test_the_ratio_makes_the_analyte_list_the_wrong_length(pca_results, sample):
    """The exact mismatch behind the original ValueError: labelling from the
    Analyte list alone would be one short."""
    analytes = sample.processed.match_attribute('data_type', 'Analyte')

    assert len(analytes) != pca_results.components_.shape[1]


def test_labels_fall_back_to_generic_names_when_nothing_matches(pca_results, sample):
    """A PCA restored from an older session has no `feature_names_in_`; the
    labels must still line up with `components_` rather than crash the plot."""
    del pca_results.feature_names_in_

    labels = pca_field_labels(pca_results, sample)

    assert labels == [f'Var{i+1}' for i in range(pca_results.components_.shape[1])]


def test_labels_fall_back_to_the_analyte_list_when_it_fits(pca_results, sample):
    """Same missing-names case, but for a PCA over analytes only -- then the
    Analyte list is the right answer and stays in use."""
    del pca_results.feature_names_in_
    sample.processed.set_attribute(RATIO, 'use', False)

    app_data = FakeAppData()
    DimensionalReduction().compute_pca(sample, app_data)
    analyte_only = sample.dim_red_results[PCA_METHOD]
    del analyte_only.feature_names_in_

    assert pca_field_labels(analyte_only, sample) == ANALYTES
