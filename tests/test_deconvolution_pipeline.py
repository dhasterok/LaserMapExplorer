"""Unit tests for src/deconvolution/pipeline.py's per-line orchestration.

Pure Python/numpy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.geometry import InstrumentSettings
from src.deconvolution.config import DeconvolutionSettings
from src.deconvolution.pipeline import correct_line


def _line_df(n=20, analytes=("Si29", "Ca43", "Fe57")):
    rng = np.random.default_rng(0)
    return pd.DataFrame({a: rng.uniform(100, 1000, size=n) for a in analytes})


def test_correct_line_noop_when_all_flags_off():
    df = _line_df()
    settings = DeconvolutionSettings()  # everything off by default
    instrument = InstrumentSettings(sweep_s=0.5, dwell_time_ms=10.0)
    result = correct_line(df, list(df.columns), settings, instrument, line_number=0)
    pd.testing.assert_frame_equal(result.corrected, df)
    for analyte, info in result.provenance.items():
        assert info["shift_applied"] is False
        assert info["washout_applied"] is False


def test_correct_line_applies_washout_only_for_configured_analytes():
    df = _line_df(analytes=("Si29", "Ca43"))
    settings = DeconvolutionSettings(apply_washout=True, washout_tau_s={"Si29": 2.0})
    instrument = InstrumentSettings(sweep_s=0.5, dwell_time_ms=10.0)
    result = correct_line(df, list(df.columns), settings, instrument, line_number=0)

    assert result.provenance["Si29"]["washout_applied"] is True
    assert result.provenance["Ca43"]["washout_applied"] is False
    assert not np.allclose(result.corrected["Si29"].to_numpy(), df["Si29"].to_numpy())
    assert np.allclose(result.corrected["Ca43"].to_numpy(), df["Ca43"].to_numpy())


def test_correct_line_applies_shift_using_column_order_as_sweep_order():
    df = _line_df(analytes=("Si29", "Ca43", "Fe57"))
    settings = DeconvolutionSettings(apply_shift=True)
    instrument = InstrumentSettings(sweep_s=0.5, dwell_time_ms=10.0)
    result = correct_line(df, list(df.columns), settings, instrument, line_number=0)

    # first analyte in sweep order has zero offset -> unchanged; later ones shift
    assert result.provenance["Si29"]["shift_pixels"] == 0.0
    assert np.allclose(result.corrected["Si29"].to_numpy(), df["Si29"].to_numpy())
    assert result.provenance["Fe57"]["shift_pixels"] > result.provenance["Ca43"]["shift_pixels"] > 0


def test_correct_line_does_not_mutate_input():
    df = _line_df()
    original = df.copy()
    settings = DeconvolutionSettings(apply_shift=True, apply_washout=True, washout_tau_s={"Si29": 1.0})
    instrument = InstrumentSettings(sweep_s=0.5, dwell_time_ms=10.0)
    correct_line(df, list(df.columns), settings, instrument, line_number=0)
    pd.testing.assert_frame_equal(df, original)


def test_correct_line_skips_gracefully_without_sweep_metadata():
    df = _line_df(analytes=("Si29",))
    settings = DeconvolutionSettings(apply_washout=True, washout_tau_s={"Si29": 1.0})
    instrument = InstrumentSettings()  # sweep_s unset
    result = correct_line(df, list(df.columns), settings, instrument, line_number=0)
    assert result.provenance["Si29"]["washout_applied"] is False
    pd.testing.assert_frame_equal(result.corrected, df)


def test_correct_line_bidirectional_flip_changes_result_on_odd_lines():
    df = _line_df(analytes=("Si29",), n=15)
    settings = DeconvolutionSettings(apply_washout=True, washout_tau_s={"Si29": 2.0})
    instrument = InstrumentSettings(sweep_s=0.5, dwell_time_ms=10.0, bidirectional_scan=True)

    even = correct_line(df, list(df.columns), settings, instrument, line_number=0)
    odd = correct_line(df, list(df.columns), settings, instrument, line_number=1)

    assert not np.allclose(even.corrected["Si29"].to_numpy(), odd.corrected["Si29"].to_numpy())
