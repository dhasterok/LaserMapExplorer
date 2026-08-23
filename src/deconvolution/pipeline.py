"""Per-line orchestration: shift -> washout, in that order (matches the
spec's along-line PSF composition order, eq. 4 -- Pi/h_s act on an already
correctly-located sample stream). Called once per line from
``src/calibration/pipeline.py``'s ``_build_calibrated_ppm_and_grid`` on
``BackgroundResult.background_corrected_signal`` (already background/drift
corrected, still pre-calibration counts -- see spec Sec 7.1's ordering
constraint).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.calibration.geometry import InstrumentSettings
from src.deconvolution.config import DeconvolutionSettings
from src.deconvolution.shift import correct_shift, sweep_offset_pixels
from src.deconvolution.washout import invert_washout


@dataclass
class LineDeconvolutionResult:
    corrected: pd.DataFrame
    provenance: dict[str, dict] = field(default_factory=dict)  # analyte -> info


def correct_line(
    signal_df: pd.DataFrame,
    analytes: list[str],
    settings: DeconvolutionSettings,
    instrument_settings: InstrumentSettings,
    line_number: int,
) -> LineDeconvolutionResult:
    """Applies the enabled corrections to one line's per-analyte signal.

    Parameters
    ----------
    signal_df : pd.DataFrame
        Index = row number, columns = analyte (same shape as
        ``BackgroundResult.background_corrected_signal``).
    analytes : list[str]
        Analyte columns **in sweep read-out order** -- position in this list
        is what ``shift.sweep_offset_pixels`` uses to derive delta_j. Must
        match the raw file's actual column order (``LineFileData.analytes``),
        not an arbitrary/sorted order.
    settings : DeconvolutionSettings
    instrument_settings : InstrumentSettings
        Supplies ``sweep_s`` (= Delta t), ``dwell_time_ms``, and
        ``bidirectional_scan``.
    line_number : int
        0-based line index, used only to decide the washout causal direction
        when ``instrument_settings.bidirectional_scan`` is set (odd lines
        are treated as reverse-direction).

    Returns
    -------
    LineDeconvolutionResult
        ``corrected`` is a copy of ``signal_df`` -- the input is never
        mutated, same "never overwrite raw counts in place" principle as the
        design spec's provenance requirement (Sec 5).
    """
    corrected = signal_df.copy()
    provenance: dict[str, dict] = {}
    dt_s = instrument_settings.sweep_s
    reverse_line = bool(instrument_settings.bidirectional_scan) and (line_number % 2 == 1)

    for j, analyte in enumerate(analytes):
        if analyte not in corrected.columns:
            continue
        info: dict = {"shift_applied": False, "washout_applied": False, "flags": []}
        col = corrected[analyte].to_numpy(dtype=float, copy=True)

        if settings.apply_shift and instrument_settings.dwell_time_ms is not None and dt_s:
            shift_pixels = sweep_offset_pixels(j, instrument_settings.dwell_time_ms, dt_s)
            col = correct_shift(col, shift_pixels)
            info["shift_applied"] = True
            info["shift_pixels"] = shift_pixels

        if settings.apply_washout and analyte in settings.washout_tau_s and dt_s:
            tau_s = settings.washout_tau_s[analyte]
            line_signal = col[::-1] if reverse_line else col
            result = invert_washout(line_signal, tau_s, dt_s)
            col = result.corrected[::-1] if reverse_line else result.corrected
            info.update(
                washout_applied=True, tau_s=tau_s,
                noise_amplification=result.noise_amplification,
                negative_count=result.negative_count, flags=result.flags,
            )

        corrected[analyte] = col
        provenance[analyte] = info

    return LineDeconvolutionResult(corrected=corrected, provenance=provenance)
