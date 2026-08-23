"""Matrix-free along-line forward operator A (and its adjoint A^T): the
composite PSF = K's along-line marginal (*) Pi (*) h_s, eq. (4)'s 1D case.

No dense matrix is ever built, per the design spec's requirement (Sec 6.4)
that A/A^T be usable as ``scipy.sparse.linalg.LinearOperator``s so later
iterative solvers (Richardson-Lucy, Chambolle-Pock -- a later pass, not this
one) scale to real line lengths.

Getting a matrix-free convolution operator's adjoint exactly right is easy
to get subtly wrong at the boundaries, so the exact index algebra behind
``_convolve_same``/``rmatvec`` is written out here rather than left implicit,
and is exercised by the mandatory adjoint dot-product test in
``tests/test_deconvolution_operator.py`` (``<Ax,y> == <x,A^T y>`` to machine
precision, per spec Sec 6.4/9.2).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse.linalg import LinearOperator


def _convolve_same(x: np.ndarray, kernel: np.ndarray, center: int) -> np.ndarray:
    """``x`` convolved with ``kernel``, returning ``len(x)`` samples centered
    at offset ``center`` into the 'full' convolution -- the building block
    both ``matvec`` and ``rmatvec`` share (with different kernels/centers,
    see module docstring)."""
    n = len(x)
    full = np.convolve(x, kernel, mode="full")
    return full[center:center + n]


@dataclass
class ForwardOperator:
    """The along-line composite PSF as a matrix-free linear operator.

    Parameters
    ----------
    psf : np.ndarray
        Composite kernel (already K's marginal (*) Pi (*) h_s -- build via
        :func:`build_along_line_psf`, not raw ``numpy.convolve``, so the
        ``center`` below is derived correctly -- see that function and
        ``kernels.symmetric_center``'s docstring for why a naive geometric
        midpoint is wrong once a causal kernel (washout) is in the mix),
        normalized to sum to 1.
    n : int
        Length of the along-line signal this operator acts on.
    center : int, optional
        Index into ``psf`` that represents "zero shift" (where a
        single-sample impulse input would land, unblurred). Defaults to
        ``(len(psf) - 1) // 2`` -- correct for a single symmetric kernel
        (e.g. just a Gaussian or boxcar alone), but **must** be passed
        explicitly (from :func:`build_along_line_psf`) for any composite
        that includes ``washout_kernel``, whose own reference is 0, not its
        midpoint.
    """
    psf: np.ndarray
    n: int
    center: int | None = None

    def __post_init__(self):
        if not np.isclose(self.psf.sum(), 1.0, atol=1e-9):
            raise ValueError(
                f"psf must be mass-conserving (sum to 1); got sum={self.psf.sum()!r}. "
                "Build it from kernels.py's already-normalized kernels."
            )
        m = len(self.psf)
        if self.center is None:
            self.center = (m - 1) // 2
        if not (0 <= self.center <= m - 1):
            raise ValueError(f"center must be within [0, {m - 1}], got {self.center!r}.")
        self._adjoint_center = (m - 1) - self.center
        self._psf_rev = self.psf[::-1]

    def matvec(self, x: np.ndarray) -> np.ndarray:
        """A @ x -- the forward blur."""
        if len(x) != self.n:
            raise ValueError(f"expected length-{self.n} input, got {len(x)}.")
        return _convolve_same(x, self.psf, self.center)

    def rmatvec(self, y: np.ndarray) -> np.ndarray:
        """A^T @ y -- convolution with the reversed kernel at the
        complementary center, the exact adjoint of ``matvec`` (see module
        docstring)."""
        if len(y) != self.n:
            raise ValueError(f"expected length-{self.n} input, got {len(y)}.")
        return _convolve_same(y, self._psf_rev, self._adjoint_center)

    def as_linear_operator(self) -> LinearOperator:
        """Wraps this operator as a ``scipy.sparse.linalg.LinearOperator``,
        for later iterative solvers (Richardson-Lucy, Chambolle-Pock)."""
        return LinearOperator(
            shape=(self.n, self.n), matvec=self.matvec, rmatvec=self.rmatvec, dtype=self.psf.dtype,
        )


def build_along_line_psf(*kernels_with_centers: tuple[np.ndarray, int]) -> tuple[np.ndarray, int]:
    """Composes multiple mass-conserving 1D kernels (e.g. K's marginal, Pi,
    h_s from ``kernels.py``) into one PSF via successive convolution, per
    eq. (4), tracking the composite's reference center alongside it.

    Each argument is a ``(kernel, center)`` pair -- use
    ``kernels.symmetric_center(k)`` for a centered kernel (Gaussian, boxcar)
    or literal ``0`` for ``washout_kernel`` (always causal, see its
    docstring). Centers add under convolution (shifting either input by
    delta shifts the convolution by delta), which is exactly why a single
    global ``(total_length - 1) // 2`` recomputed from scratch -- what an
    earlier version of this function did -- silently misaligns the result
    whenever an asymmetric (causal) kernel is included: convolving a
    centered kernel with a causal one does *not* produce a symmetric
    composite, so its true center isn't its own geometric midpoint.

    Convolving mass-conserving kernels preserves mass conservation (the
    product of the kernels' sums, each 1, is still 1), so no renormalization
    is needed here -- ``ForwardOperator.__post_init__`` still checks it, as
    a guard against a caller passing an un-normalized kernel.
    """
    if not kernels_with_centers:
        raise ValueError("at least one (kernel, center) pair is required.")
    psf, center = kernels_with_centers[0]
    for k, c in kernels_with_centers[1:]:
        psf = np.convolve(psf, k, mode="full")
        center = center + c
    return psf, center
