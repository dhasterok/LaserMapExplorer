"""Per-analyte dwell-offset (delta_j) correction -- spec Sec 6.2's "quick-
look" resampling path (option 2), not the "fold into the operator" exact
path (option 1). Resampling is used here because Stage 3's other correction
(``washout.py``) is itself a direct closed-form filter, not a Poisson-
likelihood solve -- the noise correlation this resampling introduces (see
spec Sec 6.2) only actually matters once a Poisson-likelihood solver
(Stage 4, a later pass) is downstream of it. When that solver is added, this
correction should move into ``operator.py``'s comb-sampling instead, per the
spec's own stated preference.

delta_j (each analyte's sweep-position offset) is *derived*, not stored
metadata: analytes are read out sequentially within one sweep cycle, so
analyte index ``j`` in the sweep is measured ``j * dwell_time_ms`` after the
sweep's nominal start -- this assumes uniform per-analyte dwell time,
consistent with ``InstrumentSettings.dwell_time_ms`` already being a single
scalar rather than a per-analyte schedule.
"""
from __future__ import annotations

from scipy.ndimage import shift as _ndi_shift

import numpy as np


def sweep_offset_pixels(analyte_index: int, dwell_time_ms: float, sweep_s: float) -> float:
    """delta_j in units of sample pixels (one pixel = one sweep period), for
    the analyte at position ``analyte_index`` (0-based) within the sweep's
    analyte read-out order.
    """
    if dwell_time_ms < 0 or sweep_s <= 0:
        raise ValueError(f"dwell_time_ms must be >=0 and sweep_s > 0; got {dwell_time_ms!r}, {sweep_s!r}.")
    delta_j_s = analyte_index * (dwell_time_ms / 1000.0)
    return delta_j_s / sweep_s


def correct_shift(signal: np.ndarray, shift_pixels: float, order: int = 3) -> np.ndarray:
    """Shifts ``signal`` backward by ``shift_pixels`` (fractional pixels) to
    compensate for that analyte having been sampled ``shift_pixels`` sweep-
    periods later than the sweep's nominal start -- i.e. an analyte read out
    later in the cycle (larger ``sweep_offset_pixels``) gets shifted back
    toward the line's start to align it with earlier-read analytes' common
    spatial coordinate.

    Cubic-spline interpolation (``order=3``, the spec's "cubic-spline shift"
    option) via ``scipy.ndimage.shift``; ``mode="nearest"`` at the line ends
    rather than wrapping (no circular convolution, per spec Sec 10).
    """
    return _ndi_shift(signal, shift=-shift_pixels, order=order, mode="nearest")
