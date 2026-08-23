"""Deconvolution QC: before/after line-profile plotting, a noise-
amplification summary plot, and a per-analyte provenance summary table.
Draws into a passed-in ``Axes`` -- no PyQt, same convention as
``src/calibration/diagnostics.py``; the dock widget calls these, they don't
call back into it.
"""
from __future__ import annotations

import pandas as pd


def plot_washout_correction(ax, before, after, dt_s: float, analyte: str, tau_s: float | None = None) -> None:
    """Before/after line profile for one analyte's washout correction.
    Takes raw signal arrays directly (not ``SampleCalibratedResult``'s
    provenance, which only stores summary diagnostics -- see
    :func:`plot_noise_amplification_summary` for the plot the dock actually
    uses against that summary).
    """
    t = [i * dt_s for i in range(len(before))]
    ax.plot(t, before, label="before", alpha=0.7)
    ax.plot(t, after, label="after", alpha=0.7)
    title = f"{analyte} washout correction"
    if tau_s is not None:
        title += f" (tau={tau_s:.3g} s)"
    ax.set_title(title)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("counts")
    ax.legend()


def plot_noise_amplification_summary(ax, report_df: pd.DataFrame) -> None:
    """Per-analyte noise-amplification factor (eq. 7), averaged across
    lines -- the spec's explicit requirement (Sec 6.3) that this diagnostic
    ship as a first-class, always-visible output, not just a number buried
    in a table. One bar per analyte that had washout applied; analytes with
    no washout correction (no tau entered) are omitted, not shown as zero.
    """
    washed = report_df[report_df["washout_applied"] == True]  # noqa: E712
    if washed.empty:
        ax.set_title("No washout correction applied")
        return
    summary = washed.groupby("analyte")["noise_amplification"].mean().sort_values()
    ax.barh(summary.index, summary.values)
    ax.set_xlabel("noise amplification, Var(u_hat)/Var(m)  (eq. 7)")
    ax.set_title("Washout noise amplification by analyte (mean across lines)")
    ax.axvline(1.0, color="gray", linestyle="--", linewidth=1)


def build_deconvolution_report_df(provenance: dict) -> pd.DataFrame:
    """Flattens ``LineDeconvolutionResult.provenance`` (or a
    line-number-keyed dict of those) into one QC table: one row per
    (line, analyte), columns for which corrections ran, tau used, the eq.(7)
    noise-amplification factor, negative-count, and flags.
    """
    rows = []
    for line_number, per_analyte in provenance.items():
        for analyte, info in per_analyte.items():
            rows.append({
                "line": line_number,
                "analyte": analyte,
                "shift_applied": info.get("shift_applied", False),
                "shift_pixels": info.get("shift_pixels"),
                "washout_applied": info.get("washout_applied", False),
                "tau_s": info.get("tau_s"),
                "noise_amplification": info.get("noise_amplification"),
                "negative_count": info.get("negative_count"),
                "flags": ", ".join(info.get("flags", [])),
            })
    return pd.DataFrame(rows)
