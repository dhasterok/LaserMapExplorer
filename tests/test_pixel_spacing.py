"""Pixel pitch from the coordinate columns.

``dx``/``dy`` were computed as ``range / nunique()``. ``n`` evenly spaced pixels
span ``n - 1`` gaps, so that understates the pitch by ``(n-1)/n`` — a 91-line map
1800 µm across reported 19.78 µm instead of 20. The value is not cosmetic: it
sets the scalebar, the map's aspect ratio, and the physical-to-index conversion
``LamePlot.plot_map_mpl`` uses to apply axis limits, so every map was slightly
wrong and the error grew as the pixel count fell.
"""
import numpy as np
import pandas as pd
import pytest

from src.data.DataHandling import LaserSampleObj, pixel_spacing


# --- the arithmetic ---------------------------------------------------------

@pytest.mark.parametrize("coord_range,n,expected", [
    (1800.0, 91, 20.0),        # 71A-Py 12, 20 um line spacing
    (1400.0, 141, 10.0),       # 72C-1
    (475.0, 476, 1.0),         # RM01, 1 um pixels
    (10.0, 2, 10.0),           # two pixels, one gap
])
def test_spacing_divides_by_the_number_of_gaps(coord_range, n, expected):
    assert pixel_spacing(coord_range, n, None) == pytest.approx(expected)


def test_a_single_pixel_keeps_the_previous_pitch():
    """One distinct coordinate spans no gaps, so it says nothing about pitch --
    and dividing by n-1 would be a ZeroDivisionError."""
    assert pixel_spacing(0.0, 1, 7.5) == 7.5


@pytest.mark.parametrize("coord_range,n", [(None, 91), (1800.0, None), (0.0, 0)])
def test_missing_inputs_fall_back(coord_range, n):
    assert pixel_spacing(coord_range, n, 3.0) == 3.0


# --- against real samples ---------------------------------------------------

def write_grid(path, dx, dy, nx, ny, x0=0.0, y0=0.0):
    """A .lame.csv on an exact dx by dy grid."""
    xs, ys = np.meshgrid(x0 + np.arange(nx) * dx, y0 + np.arange(ny) * dy)
    n = nx * ny
    pd.DataFrame({
        'Xc': xs.ravel(order='F'),
        'Yc': ys.ravel(order='F'),
        'Fe57': np.linspace(1.0, 100.0, n),
        'Cu65': np.linspace(5.0, 50.0, n),
    }).to_csv(path, index=False)


@pytest.mark.parametrize("dx,dy,nx,ny", [
    (20.0, 6.13496, 15, 40),       # line-scan geometry: anisotropic pixels
    (10.0, 3.988095, 12, 30),
    (1.0, 1.0, 20, 25),            # square, where the old bug was least visible
    (30.0, 9.2, 8, 50),
])
def test_dx_dy_match_the_real_grid_step(tmp_path, qapp, dx, dy, nx, ny):
    path = tmp_path / "grid.lame.csv"
    write_grid(path, dx, dy, nx, ny)

    sample = LaserSampleObj(sample_id="grid", file_path=str(path),
                            outlier_method='none', negative_method='ignore')

    assert sample.nx == nx
    assert sample.ny == ny
    assert sample.dx == pytest.approx(dx)
    assert sample.dy == pytest.approx(dy)


def test_the_error_was_worst_on_coarse_maps(tmp_path, qapp):
    """The old (n) divisor erred by (n-1)/n, so a 10-pixel axis was out by 10%
    while a 500-pixel one was out by 0.2% -- which is why it went unnoticed."""
    path = tmp_path / "coarse.lame.csv"
    write_grid(path, 100.0, 100.0, 10, 10)

    sample = LaserSampleObj(sample_id="coarse", file_path=str(path),
                            outlier_method='none', negative_method='ignore')

    assert sample.dx == pytest.approx(100.0)
    old = sample.x_range / sample.nx          # what it used to compute
    assert old == pytest.approx(90.0)         # 10% short


def test_spacing_is_unchanged_by_an_offset_origin(tmp_path, qapp):
    """Matrix imports store Xc 1-indexed (first pixel at dx, not 0); line imports
    store it 0-indexed. Pitch must not depend on which."""
    a, b = tmp_path / "zero.lame.csv", tmp_path / "offset.lame.csv"
    write_grid(a, 20.0, 5.0, 10, 10, x0=0.0, y0=0.0)
    write_grid(b, 20.0, 5.0, 10, 10, x0=20.0, y0=5.0)

    first = LaserSampleObj(sample_id="zero", file_path=str(a),
                           outlier_method='none', negative_method='ignore')
    second = LaserSampleObj(sample_id="offset", file_path=str(b),
                            outlier_method='none', negative_method='ignore')

    assert first.dx == pytest.approx(second.dx) == pytest.approx(20.0)
    assert first.dy == pytest.approx(second.dy) == pytest.approx(5.0)


def test_spacing_follows_a_crop(tmp_path, qapp):
    """Cropping keeps the pitch -- it removes pixels, it does not resample."""
    path = tmp_path / "grid.lame.csv"
    write_grid(path, 20.0, 5.0, 20, 20)
    sample = LaserSampleObj(sample_id="grid", file_path=str(path),
                            outlier_method='none', negative_method='ignore')

    sample.apply_crop((100.0, 240.0), (25.0, 60.0))

    assert sample.dx == pytest.approx(20.0)
    assert sample.dy == pytest.approx(5.0)
