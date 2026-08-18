"""Manual, local-only verification of the calibration backend against a real
raw-data directory.

NOT a committed pytest fixture and NOT run in CI -- the real instrument
files are outside the repo (Google Drive) and are proprietary-instrument
CSVs that shouldn't be committed. Run this by hand during development:

    python scripts/calibration_manual_check.py [raw_dir] [analyte1,analyte2,...]

Defaults to the 25B-1 raw-data folder used during development. Prints
per-sample timing/background/drift/calibration summaries and writes a JSON
QC report + diagnostic figures to scratch/calibration_manual_check/<label>/
for visual inspection.

The seeded resources/calibration/reference_materials/NIST610.yaml ships with
placeholder (null) values -- until real reference values are entered,
calibrated_ppm will legitimately come back empty for every analyte. This
script still exercises parsing, background detection, session background
drift, and standard drift fitting end to end against the real files, and the
printed 'skipped analytes' / 'fallback background window' counts are exactly
the kind of real-world edge case the plan calls out feeding back into new
synthetic regression fixtures.
"""
from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration import io_export, pipeline, reflib

DEFAULT_RAW_DIR = (
    "/Users/dhasterok/Library/CloudStorage/GoogleDrive-dhasterok@gmail.com/"
    "My Drive/laser_mapping/Sam_garnet_maps/raw data/25B-1"
)
DEFAULT_ANALYTES = ["Al27", "Ca43", "Mg24", "Fe57", "Sr88", "La139"]
REFERENCE_LIBRARY_DIR = project_root / "resources" / "calibration" / "reference_materials"
OUTPUT_DIR = project_root / "scratch" / "calibration_manual_check"


def main() -> int:
    raw_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_RAW_DIR)
    analytes = sys.argv[2].split(",") if len(sys.argv) > 2 else DEFAULT_ANALYTES

    if not raw_dir.exists():
        print(f"Raw directory not found: {raw_dir}")
        return 1

    reference_library = reflib.load_reference_library(REFERENCE_LIBRARY_DIR)
    print(f"Loaded {len(reference_library)} reference material(s): {sorted(reference_library)}")

    results = pipeline.run(
        raw_dir, standard_names={"NIST610"}, reference_library=reference_library,
        drift_order=1, background_drift_order=1, split_odd_even=True, accuracy_threshold=2.0,
    )

    if not results:
        print("No non-standard sample labels found -- nothing to calibrate.")
        return 0

    for label, result in results.items():
        print(f"\n=== Sample: {label} ===")
        print(f"  files: {len(result.files)}")
        print(f"  primary standard: {result.provenance.get('primary_standard')}")
        print(f"  calibrated_ppm shape: {result.calibrated_ppm.shape}")

        n_fallback = sum(1 for b in result.backgrounds if b.window.method == "fallback_fixed_window")
        print(f"  files using fallback background window: {n_fallback} / {len(result.backgrounds)}")

        for std_label, sr in result.standard_results.items():
            print(
                f"  standard {std_label}: {len(sr.occurrences)} occurrences, "
                f"{len(sr.calibration_factor)} calibrated analytes, "
                f"{len(sr.skipped_analytes)} skipped (no reference value): {sr.skipped_analytes[:8]}{'...' if len(sr.skipped_analytes) > 8 else ''}"
            )
            n_flagged = sum(1 for r in sr.accuracy_table if r.flagged)
            n_flagged_holdout = (
                sum(1 for r in sr.holdout_accuracy_table if r.flagged) if sr.holdout_accuracy_table else None
            )
            print(f"    fit-group flagged: {n_flagged}/{len(sr.accuracy_table)}, holdout-group flagged: {n_flagged_holdout}")

        out_dir = OUTPUT_DIR / label
        out_dir.mkdir(parents=True, exist_ok=True)
        io_export.export_qc_report_json(result, out_dir / "qc_report.json")
        written = io_export.export_figures(result, out_dir / "figures", analytes=analytes)
        print(f"  wrote QC report + {len(written)} figure(s) to {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
