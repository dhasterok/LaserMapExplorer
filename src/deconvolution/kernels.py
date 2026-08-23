"""Along-line 1D kernel parameterizations: the dwell-time boxcar (Pi), the
causal washout exponential (h_s), and the spot footprint's along-line
marginal (K's 1D profile). See ``plans/laicpms_map_correction_spec.md``
eq. (2) and (4).

Every kernel here is normalized to sum to 1 (the discrete analogue of
``integral h dt = 1``, mass conservation) -- enforced by explicit
renormalization after truncation rather than left as an approximation, so
``kernel.sum() == 1.0`` holds to machine precision regardless of truncation
length. This is required before any kernel is used inside ``operator.py``,
since mass conservation is one of this package's mandatory unit tests (spec
Sec 9.2).
"""
from __future__ import annotations

import numpy as np


def symmetric_center(kernel: np.ndarray) -> int:
    """Reference-center index for a kernel built by :func:`boxcar_kernel` or
    :func:`gaussian_kernel` -- both are centered on their geometric midpoint,
    so this is just ``(len(kernel) - 1) // 2``. Do **not** use this for
    :func:`washout_kernel`: that kernel is causal and its reference index is
    always 0 (see its docstring) -- a geometric-midpoint center would be
    physically wrong for a one-sided decaying exponential, shifting the
    composite PSF built in ``operator.build_along_line_psf`` far from the
    true sample location once convolved with a symmetric kernel. This
    distinction matters: getting it wrong doesn't break the operator's
    adjoint property (any fixed center still yields a self-consistent
    matvec/rmatvec pair), but it does silently misalign the blurred signal
    relative to the true one.
    """
    return (len(kernel) - 1) // 2


def boxcar_kernel(width_pixels: float) -> np.ndarray:
    """Pi_{v*tau_d}(s): the boxcar the laser travels during one dwell window,
    in units of sample pixels. Centered/symmetric -- the measured value at a
    sample is treated as the average of the true signal over the spatial
    interval straddling that sample, not a forward- or backward-looking
    average. (The instrument's own causal dwell-timing offset is handled
    separately, by ``shift.py``'s delta_j -- this kernel only captures the
    *smearing*, not the *location*.)

    A fractional ``width_pixels`` (the common case -- dwell length is rarely
    an exact multiple of the pixel pitch) is handled by giving the two edge
    taps partial weight equal to the fractional pixel coverage, rather than
    rounding to the nearest integer width.
    """
    if width_pixels <= 0:
        raise ValueError(f"boxcar width must be positive, got {width_pixels!r}.")

    n_full = int(np.floor(width_pixels))
    remainder = width_pixels - n_full

    if remainder < 1e-12:
        weights = np.ones(max(n_full, 1))
    else:
        # One extra partial-weight tap beyond the full-weight taps, split
        # symmetrically isn't meaningful for an odd total, so the partial
        # tap is appended and the whole kernel is centered by the caller
        # (operator.py aligns kernels on their centroid, not their first tap).
        weights = np.ones(n_full + 1)
        weights[-1] = remainder

    return weights / weights.sum()


def washout_kernel(tau_s: float, dt_s: float, min_mass_fraction: float = 1.0 - 1e-12) -> np.ndarray:
    """h_s(s)/v, discretized at the line's sample pitch dt_s = pixel_pitch/v:
    the causal exponential aerosol-washout response, eq. (2)/(6):

        h[n] = (1 - a) * a**n,  n = 0, 1, 2, ...,  a = exp(-dt_s / tau_s)

    which is exactly the AR(1) form ``washout.py``'s recursive inverse
    (eq. 6) assumes. Truncated once the remaining tail contributes less than
    ``1 - min_mass_fraction`` of the total mass, then renormalized to sum to
    exactly 1 -- an infinite geometric tail can never be represented exactly
    in finite storage, so exact conservation is enforced by construction
    rather than approximated by a very long truncation.

    **Reference center is always 0** (``h[0]`` is the zero-delay/"no shift"
    tap) -- this kernel is causal, not centered like
    :func:`boxcar_kernel`/:func:`gaussian_kernel`; see
    :func:`symmetric_center`'s docstring for why that distinction matters
    when composing kernels.
    """
    if tau_s <= 0 or dt_s <= 0:
        raise ValueError(f"tau_s and dt_s must be positive, got tau_s={tau_s!r}, dt_s={dt_s!r}.")

    a = np.exp(-dt_s / tau_s)
    if a <= 0:
        return np.array([1.0])

    # sum_{n=0}^{N-1} (1-a) a^n = 1 - a**N  -> solve for N hitting min_mass_fraction.
    n_taps = max(1, int(np.ceil(np.log(1.0 - min_mass_fraction) / np.log(a))))
    n = np.arange(n_taps)
    h = (1.0 - a) * a**n
    return h / h.sum()


def gaussian_kernel(sigma_pixels: float, min_mass_fraction: float = 1.0 - 1e-12) -> np.ndarray:
    """K's along-line marginal: the ablation spot footprint's 1D profile
    projected onto the scan direction, modeled as Gaussian (sigma in sample
    pixels). This is *not* the full 2D spot-mixing kernel (which also acts
    cross-line) -- see this package's docstring and the design spec's
    Sec 6.1/Table in Sec 3.2 for the along-line-only scope of this pass.

    Truncated symmetrically once the remaining two-sided tail is below
    ``1 - min_mass_fraction``, then renormalized to sum to exactly 1, same
    rationale as :func:`washout_kernel`.
    """
    if sigma_pixels <= 0:
        raise ValueError(f"sigma_pixels must be positive, got {sigma_pixels!r}.")

    # One-sided tail probability under a standard normal beyond z sigma:
    # solve erfc(z/sqrt(2))/2 = (1-min_mass_fraction)/2 for the half-width z.
    from scipy.special import erfcinv
    z = erfcinv(1.0 - min_mass_fraction) * np.sqrt(2.0)
    half_width = max(1, int(np.ceil(z * sigma_pixels)))
    n = np.arange(-half_width, half_width + 1)
    h = np.exp(-0.5 * (n / sigma_pixels) ** 2)
    return h / h.sum()
