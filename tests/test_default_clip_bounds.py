"""Outlier-clipping bounds are percentiles, not fractions.

``prep_data``'s clipping passes a column's ``lower_bound``/``upper_bound``
straight to ``np.nanpercentile``, which takes 0-100. ``reset_data`` gives
analytes 0.05 and 99.5 in exactly those units, but ``SampleObj.__init__``
defined the *defaults* as ``0.005``/``0.995`` -- the same intent written as
fractions, and a factor of 100 out.

Analytes never saw it, because ``reset_data`` overwrites their bounds with
the percentile values. Everything created through ``add_columns`` took the
defaults: ratios, calculated fields, PCA and cluster scores, stoichiometry
outputs. Clipping those at "the 0.995th percentile" pinned the top 99% of
the column to one number, so the field became a near-constant and its map a
flat wash of colour.

It was found twice over on RM01, from the two directions it can be reached:

* ``Ca43 / Fe57`` read ``0.000621`` everywhere, against a true median of
  ``0.0354`` -- via ``prep_data('all')``.
* A calculated Eu/Eu* read ``-0.850`` everywhere, against a true median of
  ``0.111`` -- via ``update_norm(norm=..., field=...)``, a scale change on a
  single field, which calls ``prep_data(field)`` and clips every column.

Both numbers are exactly the 0.995th percentile of the field concerned.
"""
import numpy as np
import pandas as pd
import pytest

from src.data.DataHandling import LaserSampleObj

# What reset_data assigns analytes, and so what every column should default to.
EXPECTED_BOUNDS = {
    'lower_bound': 0.05,
    'upper_bound': 99.5,
    'diff_lower_bound': 0.05,
    'diff_upper_bound': 99,
}


@pytest.fixture
def sample(sample_factory, qapp):
    return LaserSampleObj(
        sample_id='RM01', file_path=str(sample_factory('RM01')),
        outlier_method='none', negative_method='ignore negatives',
        ref_chem=pd.Series(dtype=float),
    )


# --- the defaults themselves ------------------------------------------------

@pytest.mark.parametrize("attr,expected", EXPECTED_BOUNDS.items())
def test_defaults_are_in_percentile_units(sample, attr, expected):
    default_attr = {
        'lower_bound': '_default_lower_bound',
        'upper_bound': '_default_upper_bound',
        'diff_lower_bound': '_default_difference_lower_bound',
        'diff_upper_bound': '_default_difference_upper_bound',
    }[attr]
    assert getattr(sample, default_attr) == expected


@pytest.mark.parametrize("attr,expected", EXPECTED_BOUNDS.items())
def test_an_added_column_gets_the_same_bounds_as_an_analyte(sample, attr, expected):
    """The asymmetry was the bug: analytes got percentiles, added columns
    got fractions, and only the latter were destroyed."""
    sample.add_columns('Calculated', 'derived', np.linspace(1.0, 100.0, len(sample.processed)))

    analyte = sample.processed.match_attribute('data_type', 'Analyte')[0]
    assert sample.processed.get_attribute(analyte, attr) == expected
    assert sample.processed.get_attribute('derived', attr) == expected


# --- what it did to the data ------------------------------------------------

def spread(sample, column):
    values = sample.processed[column].values.astype(float)
    values = values[np.isfinite(values)]
    return len(np.unique(np.round(values, 12))), float(np.median(values))


def test_a_ratio_keeps_its_variation_through_prep_data(sample):
    sample.compute_ratio('Sr88', 'Ca43')
    unique_before, median_before = spread(sample, 'Sr88 / Ca43')

    sample.prep_data('all')

    unique_after, median_after = spread(sample, 'Sr88 / Ca43')
    # Clipping may trim the extreme tail; it must not collapse the column.
    assert unique_after > 0.9 * unique_before, \
        f'ratio collapsed from {unique_before} to {unique_after} distinct values'
    assert median_after == pytest.approx(median_before, rel=1e-6)


def test_a_scale_change_on_one_field_does_not_flatten_another(sample):
    """``update_norm(field=...)`` calls ``prep_data(field)``, whose clipping
    loop runs over *every* column -- the route that flattened Eu*."""
    n = len(sample.processed)
    values = np.linspace(-1.0, 50.0, n)
    sample.add_columns('Calculated', 'derived', values)
    unique_before, median_before = spread(sample, 'derived')

    sample.update_norm(norm='log', field='Sr88')

    unique_after, median_after = spread(sample, 'derived')
    assert unique_after > 0.9 * unique_before
    assert median_after == pytest.approx(median_before, rel=1e-6)


def test_the_column_does_not_become_its_own_low_percentile(sample):
    """The signature of the bug: every value equal to the 0.995th percentile,
    which is also then the column maximum."""
    n = len(sample.processed)
    sample.add_columns('Calculated', 'derived', np.linspace(1.0, 1000.0, n))
    tiny_percentile = np.nanpercentile(sample.processed['derived'].values, 0.995)

    sample.prep_data('all')

    after = sample.processed['derived'].values.astype(float)
    assert np.nanmax(after) > tiny_percentile * 10
    assert np.nanmedian(after) != pytest.approx(tiny_percentile)


def test_analytes_are_unchanged(sample):
    """They always carried percentile bounds, so this must stay true."""
    before = sample.processed['Sr88'].values.copy()
    sample.prep_data('all')
    assert np.allclose(sample.processed['Sr88'].values, before, equal_nan=True)


def test_extreme_outliers_are_still_clipped(sample):
    """The clipping must still do its job -- the fix restores the bounds to
    what was intended, it does not disable them."""
    spiked = sample.raw['Sr88'].values.copy()
    spiked[0] = 1e9                      # one absurd pixel
    sample.raw['Sr88'] = spiked

    sample.prep_data('all')

    assert sample.processed['Sr88'].values.max() < 1e9


def test_carried_columns_are_not_clipped(sample):
    """Calculated/PCA/stoichiometry columns are restored *after* the clipping
    loop (see prep_data), so an expression's result reaches the user as the
    user computed it. Documented here because it is a deliberate asymmetry
    with ratios, which are regenerated before clipping and so are clipped."""
    n = len(sample.processed)
    values = np.full(n, 1.0)
    values[0] = 1e9
    sample.add_columns('Calculated', 'spiky', values)

    sample.prep_data('all')

    assert sample.processed['spiky'].values.max() == 1e9
