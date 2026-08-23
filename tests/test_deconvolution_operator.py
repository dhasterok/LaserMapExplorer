"""Unit tests for src/deconvolution/operator.py -- most importantly the
adjoint dot-product test the design spec requires (Sec 6.4/9.2):
<Ax, y> == <x, A^T y> to machine precision.

Pure Python/numpy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.kernels import boxcar_kernel, gaussian_kernel, symmetric_center, washout_kernel
from src.deconvolution.operator import ForwardOperator, build_along_line_psf


def _random_psfs(rng):
    """A handful of representative PSFs: even/odd length, symmetric/asymmetric.
    Adjoint self-consistency (what these feed) holds for *any* fixed center,
    so the default (geometric-midpoint) center is fine here even for the
    composite/causal cases -- physical alignment only matters for the
    step-response test further down, which builds its PSF via
    ``build_along_line_psf`` instead.
    """
    composite, _ = build_along_line_psf(
        (gaussian_kernel(1.0), symmetric_center(gaussian_kernel(1.0))),
        (boxcar_kernel(2.3), symmetric_center(boxcar_kernel(2.3))),
        (washout_kernel(2.0, 0.5), 0),
    )
    return [
        boxcar_kernel(3.0),                                    # odd, symmetric
        boxcar_kernel(4.0),                                    # even, symmetric
        boxcar_kernel(2.5),                                    # odd (3 taps), asymmetric weights
        washout_kernel(tau_s=1.5, dt_s=0.5),                     # causal, strongly asymmetric
        gaussian_kernel(sigma_pixels=1.2),                       # symmetric
        composite,
    ]


def test_adjoint_dot_product_identity_various_kernels():
    rng = np.random.default_rng(0)
    n = 40
    for psf in _random_psfs(rng):
        op = ForwardOperator(psf=psf, n=n)
        x = rng.normal(size=n)
        y = rng.normal(size=n)
        lhs = np.dot(op.matvec(x), y)
        rhs = np.dot(x, op.rmatvec(y))
        assert lhs == pytest.approx(rhs, rel=1e-10, abs=1e-10), f"adjoint mismatch for psf length {len(psf)}"


def test_linear_operator_wrapping_matches_direct_calls():
    psf = boxcar_kernel(3.0)
    n = 20
    op = ForwardOperator(psf=psf, n=n)
    lin = op.as_linear_operator()
    x = np.arange(n, dtype=float)
    assert np.allclose(lin.matvec(x), op.matvec(x))
    assert np.allclose(lin.rmatvec(x), op.rmatvec(x))


def test_mass_conservation_on_constant_input():
    """A@x applied to a constant field returns that constant in the
    interior (spec Sec 9.2's reference invariant) -- boundary samples are
    allowed to differ since the kernel zero-pads past the line ends."""
    psf = boxcar_kernel(5.0)
    n = 30
    op = ForwardOperator(psf=psf, n=n)
    x = np.full(n, 7.0)
    y = op.matvec(x)
    interior = y[5:-5]
    assert np.allclose(interior, 7.0)


def test_rejects_non_mass_conserving_psf():
    with pytest.raises(ValueError):
        ForwardOperator(psf=np.array([0.5, 0.3]), n=10)


def test_build_along_line_psf_composes_and_conserves_mass():
    boxcar = boxcar_kernel(2.0)
    psf, center = build_along_line_psf((boxcar, symmetric_center(boxcar)), (washout_kernel(1.0, 0.5), 0))
    assert psf.sum() == pytest.approx(1.0, abs=1e-9)
    assert center == symmetric_center(boxcar) + 0


def test_build_along_line_psf_requires_at_least_one_kernel():
    with pytest.raises(ValueError):
        build_along_line_psf()


def test_forward_operator_blurs_a_step_into_a_monotonic_transition_near_the_true_edge():
    """A synthetic sharp edge run through the composite (K's marginal (*) Pi
    (*) h_s) forward operator produces a smooth, monotonic transition
    centered near the true edge location -- Stage 1's basic sanity check.
    The full analytic-EMG closed-form comparison (spec eq. 5) is Stage 2's
    kernel-estimation closure check, deferred along with the rest of Stage 2
    in this pass.
    """
    n = 100
    edge_index = 50
    x = np.zeros(n)
    x[edge_index:] = 1000.0

    gauss = gaussian_kernel(1.5)
    boxcar = boxcar_kernel(2.0)
    psf, center = build_along_line_psf(
        (gauss, symmetric_center(gauss)), (boxcar, symmetric_center(boxcar)), (washout_kernel(3.0, 0.5), 0),
    )
    op = ForwardOperator(psf=psf, n=n, center=center)
    y = op.matvec(x)

    # Monotonic non-decreasing in the interior (a blurred step never
    # overshoots for these strictly-positive, mass-conserving kernels) --
    # the trailing few samples are excluded since zero-padding past the
    # array's right edge (no wrap-around, per spec Sec 10) legitimately
    # droops the plateau there, an expected boundary effect, not a defect.
    assert np.all(np.diff(y[:-10]) >= -1e-9)
    # The 50% crossing should sit close to the true edge (within a few
    # pixels, given the kernel widths used above).
    crossing = np.searchsorted(y, 500.0)
    assert abs(crossing - edge_index) <= 5
