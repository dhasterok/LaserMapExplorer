"""Export calibrated data, QC report, and diagnostic figures to disk.

No PyQt imports -- usable from a headless script or the GUI's export buttons.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt

from src.calibration import diagnostics
from src.calibration.pipeline import SampleCalibratedResult


def export_calibrated_csv(result: SampleCalibratedResult, path: str | Path) -> Path:
    """Write calibrated ppm data joined with its grid/position columns to CSV.

    Parameters
    ----------
    result : SampleCalibratedResult
        A calibrated sample. ``grid_index`` and ``calibrated_ppm`` are
        always written; ``calibrated_ratios`` and ``isotopic_ppm`` are
        joined in when non-empty.
    path : str or pathlib.Path
        Destination CSV path.

    Returns
    -------
    pathlib.Path
        The path written to (``Path(path)``).

    Notes
    -----
    ``isotopic_ppm`` columns get an ``isotopic_`` prefix, since they can
    otherwise collide with a ``calibrated_ppm`` column of the same analyte
    name (e.g. ``"Pb206"``) that holds a different -- elemental vs.
    isotope-apportioned -- number (see
    ``SampleCalibratedResult.isotopic_ppm``).
    """
    path = Path(path)
    merged = result.grid_index.join(result.calibrated_ppm)
    if not result.calibrated_ratios.empty:
        merged = merged.join(result.calibrated_ratios)
    if not result.isotopic_ppm.empty:
        merged = merged.join(result.isotopic_ppm.add_prefix("isotopic_"))
    merged.to_csv(path, index=False)
    return path


def _accuracy_rows_to_dicts(rows) -> list[dict]:
    """Serialize accuracy rows to JSON-ready dicts.

    Parameters
    ----------
    rows : Iterable[AccuracyRow]
        Accuracy rows whose ``time`` attribute is a ``datetime``.

    Returns
    -------
    list[dict]
        One dict per row, with ``time`` replaced by its ISO-8601 string.
    """
    out = []
    for r in rows:
        d = asdict(r)
        d["time"] = r.time.isoformat()
        out.append(d)
    return out


def _standard_result_to_dict(sr) -> dict:
    """Flatten a standard calibration result to a JSON-ready dict.

    Parameters
    ----------
    sr : StandardCalibrationResult
        Per-standard calibration output, including drift fits and accuracy
        tables.

    Returns
    -------
    dict
        Scalar QC fields plus per-analyte drift-fit orders and serialized
        accuracy tables (``holdout_accuracy_table`` is ``None`` when absent).
    """
    return {
        "standard_label": sr.standard_label,
        "split_enabled": sr.split_enabled,
        "skipped_analytes": sr.skipped_analytes,
        "excluded_outliers": sr.excluded_outliers,
        "calibration_factor": sr.calibration_factor,
        "drift_fit_orders": {a: f.order for a, f in sr.drift_fits.items()},
        "accuracy_table": _accuracy_rows_to_dicts(sr.accuracy_table),
        "holdout_accuracy_table": (
            _accuracy_rows_to_dicts(sr.holdout_accuracy_table) if sr.holdout_accuracy_table is not None else None
        ),
    }


def export_qc_report_json(result: SampleCalibratedResult, path: str | Path) -> Path:
    """Write provenance, per-file timing, and standard QC/accuracy tables to JSON.

    Parameters
    ----------
    result : SampleCalibratedResult
        A calibrated sample; supplies provenance, QC report, file timing,
        and per-standard results.
    path : str or pathlib.Path
        Destination JSON path.

    Returns
    -------
    pathlib.Path
        The path written to (``Path(path)``).

    Notes
    -----
    This is the natural future payload for
    ``ProjectModel.SampleCalibration.payload`` (see
    ``src/project/ProjectModel.py``), though wiring that up is deferred --
    this function only produces the JSON, it does not touch a project
    manifest.
    """
    path = Path(path)
    timing_df = diagnostics.build_timing_report_df(result.files, result.backgrounds)
    for col in ("acquired_at", "bg_start_time", "bg_end_time", "ablation_start_time", "ablation_end_time"):
        if col in timing_df.columns:
            timing_df[col] = timing_df[col].astype(str)

    report = {
        "sample_label": result.sample_label,
        "provenance": result.provenance,
        "qc_report": result.qc_report,
        "timing": timing_df.to_dict(orient="records"),
        "standards": {label: _standard_result_to_dict(sr) for label, sr in result.standard_results.items()},
    }
    with path.open("w") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def export_figures(
    result: SampleCalibratedResult, output_dir: str | Path, analytes: list[str] | None = None
) -> list[Path]:
    """Save a batch of diagnostic figures as PNGs under ``output_dir``.

    Parameters
    ----------
    result : SampleCalibratedResult
        A calibrated sample, supplying backgrounds, per-standard results,
        session drift fits, and calibrated maps.
    output_dir : str or pathlib.Path
        Directory to write PNGs into. Created (with parents) if absent.
    analytes : list[str] or None, optional
        Analytes to plot. When ``None``, defaults to every column of
        ``result.calibrated_ppm`` (and, per standard, its calibration-factor
        keys).

    Returns
    -------
    list[pathlib.Path]
        Every PNG path written, in creation order. Figures produced:
        background drift, standard-vs-reference, standard QC series (per
        standard and analyte), and calibrated-stage index maps (per
        analyte).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if analytes is None:
        default_analytes = sorted(result.calibrated_ppm.columns) if not result.calibrated_ppm.empty else []
    else:
        default_analytes = list(analytes)

    background_groups = {result.sample_label: result.backgrounds}
    background_groups.update({
        lbl: [occ.background for occ in sr.occurrences] for lbl, sr in result.standard_results.items()
    })
    reference_labels = set(result.standard_results)

    for label, sr in result.standard_results.items():
        standard_analytes = default_analytes or sorted(sr.calibration_factor.keys())
        for analyte in standard_analytes:
            fig, ax = plt.subplots()
            diagnostics.plot_background_drift(
                ax, background_groups, result.session_background_drift.get(analyte), analyte,
                reference_labels=reference_labels,
            )
            out = output_dir / f"background_drift_{label}_{analyte}.png"
            fig.savefig(out)
            plt.close(fig)
            written.append(out)

            fig, ax = plt.subplots()
            diagnostics.plot_standard_vs_reference(ax, sr, analyte)
            out = output_dir / f"standard_vs_reference_{label}_{analyte}.png"
            fig.savefig(out)
            plt.close(fig)
            written.append(out)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
            diagnostics.plot_standard_qc_series(ax1, ax2, sr, analyte)
            fig.tight_layout()
            out = output_dir / f"standard_qc_series_{label}_{analyte}.png"
            fig.savefig(out)
            plt.close(fig)
            written.append(out)

    for analyte in default_analytes:
        if analyte not in result.calibrated_ppm.columns:
            continue
        fig, ax = plt.subplots()
        diagnostics.plot_index_map(
            ax, result.calibrated_ppm[analyte], result.grid_index, title=f"{analyte}: calibrated (ppm)",
            cbar_label="ppm",
        )
        out = output_dir / f"map_calibrated_{analyte}.png"
        fig.savefig(out)
        plt.close(fig)
        written.append(out)

    return written
