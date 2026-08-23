"""Diagnostic figure/table smoke tests for src/deconvolution/diagnostics.py
-- "doesn't raise" plus a few structural checks, same convention as
tests/test_calibration_diagnostics.py.

Pure Python -- no PyQt/QApplication needed (matplotlib uses the Agg backend).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.diagnostics import (
    build_deconvolution_report_df, plot_noise_amplification_summary, plot_washout_correction,
)


def _sample_provenance():
    return {
        0: {
            "Si29": {"shift_applied": True, "shift_pixels": 0.5, "washout_applied": True,
                      "tau_s": 2.0, "noise_amplification": 3.2, "negative_count": 1, "flags": ["negative_counts"]},
            "Ca43": {"shift_applied": False, "washout_applied": False},
        },
        1: {
            "Si29": {"shift_applied": True, "shift_pixels": 0.5, "washout_applied": True,
                      "tau_s": 2.0, "noise_amplification": 3.6, "negative_count": 0, "flags": []},
            "Ca43": {"shift_applied": False, "washout_applied": False},
        },
    }


def test_build_deconvolution_report_df_shape():
    df = build_deconvolution_report_df(_sample_provenance())
    assert len(df) == 4
    assert set(df["analyte"]) == {"Si29", "Ca43"}
    assert set(df.columns) >= {"line", "analyte", "shift_applied", "washout_applied", "tau_s", "noise_amplification", "negative_count", "flags"}


def test_plot_noise_amplification_summary_does_not_raise():
    df = build_deconvolution_report_df(_sample_provenance())
    fig, ax = plt.subplots()
    plot_noise_amplification_summary(ax, df)
    plt.close(fig)


def test_plot_noise_amplification_summary_handles_no_washout():
    import pandas as pd
    df = pd.DataFrame({"analyte": ["Si29"], "washout_applied": [False], "noise_amplification": [None]})
    fig, ax = plt.subplots()
    plot_noise_amplification_summary(ax, df)
    plt.close(fig)


def test_plot_washout_correction_does_not_raise():
    before = np.linspace(100, 1000, 30)
    after = before * 1.1
    fig, ax = plt.subplots()
    plot_washout_correction(ax, before, after, dt_s=0.5, analyte="Si29", tau_s=2.0)
    plt.close(fig)
