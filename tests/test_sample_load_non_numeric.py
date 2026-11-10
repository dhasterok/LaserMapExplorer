"""A stray text column must not take a sample load down.

``reset_data`` deliberately does not coerce non-numeric columns -- coercing
would silently turn real content into NaN. But it then typed them ``'Analyte'``
by default, and an 'Analyte' reaches ``cluster_data``, where
``np.isfinite(analyte_data)`` over an object array raises, and ``prep_data``,
where ``np.nanpercentile``/``np.min`` do the same. That exception escapes
``reset_data`` uncaught, so on the menu path the sample simply never appears --
no dialog, nothing in the status bar.

The real trigger was an importer writing an instrument footer timestamp into a
``Time [Sec]`` column, but one ``n/a`` or ``#DIV/0!`` anywhere in a hand-edited
csv does the same thing, which is why the guard is on dtype rather than on the
column's name.
"""
import numpy as np
import pandas as pd
import pytest

from src.data.DataHandling import LaserSampleObj


def write_sample(path, extra=None, nx=12, ny=10):
    """A minimal valid .lame.csv, optionally with an extra column."""
    xs, ys = np.meshgrid(np.arange(nx) * 10.0, np.arange(ny) * 5.0)
    df = pd.DataFrame({
        'Xc': xs.ravel(order='F'),
        'Yc': ys.ravel(order='F'),
        'Mg24': np.linspace(1.0, 50.0, nx * ny),
        'Fe57': np.linspace(100.0, 900.0, nx * ny),
    })
    if extra:
        for name, values in extra.items():
            df[name] = values
    df.to_csv(path, index=False)
    return df


def load(path):
    return LaserSampleObj(sample_id=path.stem, file_path=str(path),
                          outlier_method='none', negative_method='ignore')


NPIX = 120      # must stay above the k-optimal cluster sweep's sample floor


@pytest.fixture
def footer_column():
    """A column of time values with one instrument footer among them."""
    values = [f"{0.306 * (i + 1):.4f}" for i in range(NPIX - 1)]
    return values + ["          Printed:18/06/2022 00:25:28"]


def test_sample_with_a_text_column_still_loads(tmp_path, footer_column):
    path = tmp_path / "footer.lame.csv"
    write_sample(path, extra={'Time [Sec]': footer_column})

    sample = load(path)          # used to raise TypeError out of cluster_data

    assert len(sample.raw) == NPIX


def test_the_text_column_is_kept_out_of_the_analytes(tmp_path, footer_column):
    """Typed 'Special' with use=False, the established pattern for a column
    that isn't a concentration -- so it stays visible but out of the maths."""
    path = tmp_path / "footer.lame.csv"
    write_sample(path, extra={'Time [Sec]': footer_column})

    sample = load(path)

    assert sample.raw.get_attribute('Time [Sec]', 'data_type') == 'Special'
    assert not sample.raw.get_attribute('Time [Sec]', 'use')
    assert _analytes(sample) == ['Mg24', 'Fe57']


def test_the_column_is_not_coerced_away(tmp_path, footer_column):
    """The no-coerce policy is deliberate: the values are still there."""
    path = tmp_path / "footer.lame.csv"
    write_sample(path, extra={'Time [Sec]': footer_column})

    sample = load(path)

    assert sample.raw['Time [Sec]'].notna().all()


def _analytes(sample):
    return [c for c in sample.raw.columns
            if sample.raw.get_attribute(c, 'data_type') == 'Analyte']


@pytest.mark.parametrize("junk", ["#DIV/0!", "-", "<0.01", "below det."])
def test_one_unparseable_cell_anywhere_is_survivable(tmp_path, junk):
    """A single cell pandas cannot read as a number makes the whole column
    object dtype, which is what made this so hard to spot in a 30-column file."""
    path = tmp_path / "junk.lame.csv"
    column = [f"{v:.2f}" for v in np.linspace(1.0, 99.0, NPIX)]
    column[7] = junk
    write_sample(path, extra={'Au197': column})

    sample = load(path)

    assert len(sample.raw) == NPIX
    assert 'Au197' not in _analytes(sample)


@pytest.mark.parametrize("blank", ["n/a", "", "NA"])
def test_a_recognized_missing_value_stays_an_analyte(tmp_path, blank):
    """pandas reads these as NaN, so the column is still numeric and is still
    real data -- the guards must not quietly demote it."""
    path = tmp_path / "blank.lame.csv"
    column = [f"{v:.2f}" for v in np.linspace(1.0, 99.0, NPIX)]
    column[7] = blank
    write_sample(path, extra={'Au197': column})

    sample = load(path)

    assert 'Au197' in _analytes(sample)
    assert sample.raw['Au197'].isna().sum() == 1


def test_a_clean_sample_is_unaffected(tmp_path):
    """The guards must not change the normal path: every data column here is
    numeric and must stay an Analyte."""
    path = tmp_path / "clean.lame.csv"
    write_sample(path)

    sample = load(path)

    assert _analytes(sample) == ['Mg24', 'Fe57']
    for col in _analytes(sample):
        assert sample.processed.get_attribute(col, 'plot_min') is not None
