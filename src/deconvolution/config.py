"""Deconvolution settings: dataclass + YAML defaults loader.

Mirrors ``src/calibration/reflib.py``'s dataclass+loader+validator idiom
(itself mirroring ``src/stoichiometry/config.py``). Loaded from
``resources/calibration/defaults.yaml``'s ``deconvolution:`` section -- that
file already existed for calibration-pipeline defaults but, before this,
was never actually loaded by any code; this is the first real wiring of it,
following the established idiom rather than inventing a new one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_DEFAULTS_PATH = "resources/calibration/defaults.yaml"


class DeconvolutionConfigError(ValueError):
    """Raised for missing/malformed deconvolution config fields."""


@dataclass
class DeconvolutionSettings:
    apply_shift: bool = False
    apply_washout: bool = False
    washout_tau_s: dict[str, float] = field(default_factory=dict)  # analyte -> tau (s); missing analyte = skip
    # Bidirectional-scan handling lives on InstrumentSettings
    # (src/calibration/geometry.py), not here -- it's an acquisition-geometry
    # fact (same category as scan_axis/reverse_x/reverse_y), not a
    # correction toggle, so it has one source of truth there.

    @classmethod
    def from_manual_entry(cls, **kwargs) -> "DeconvolutionSettings":
        """Constructs settings from GUI/CLI manual entry -- same pattern as
        ``InstrumentSettings.from_manual_entry`` (``src/calibration/geometry.py``),
        kept distinct from ``__init__`` so a future alternate constructor
        (e.g. from fitted kernel-estimation results, once Stage 2 exists)
        can be added without downstream callers changing.
        """
        return cls(**kwargs)


def _parse_deconvolution_section(raw: dict) -> DeconvolutionSettings:
    apply_shift = raw.get("apply_shift", False)
    apply_washout = raw.get("apply_washout", False)
    washout_tau_s = raw.get("washout_tau_s", {}) or {}

    if not isinstance(washout_tau_s, dict):
        raise DeconvolutionConfigError(
            f"'deconvolution.washout_tau_s' must be a mapping of analyte -> tau (s), got {washout_tau_s!r}."
        )
    for analyte, tau in washout_tau_s.items():
        try:
            tau_f = float(tau)
        except (TypeError, ValueError):
            raise DeconvolutionConfigError(f"'deconvolution.washout_tau_s.{analyte}' must be numeric, got {tau!r}.")
        if tau_f <= 0:
            raise DeconvolutionConfigError(f"'deconvolution.washout_tau_s.{analyte}' must be positive, got {tau_f!r}.")

    return DeconvolutionSettings(
        apply_shift=bool(apply_shift),
        apply_washout=bool(apply_washout),
        washout_tau_s={k: float(v) for k, v in washout_tau_s.items()},
    )


def load_default_deconvolution_settings(path: str | Path = DEFAULT_DEFAULTS_PATH) -> DeconvolutionSettings:
    """Loads the ``deconvolution:`` section of the shared calibration
    defaults YAML. Returns all-off defaults (``DeconvolutionSettings()``) if
    the file has no ``deconvolution:`` section at all -- this stays optional,
    same as every other manual-entry setting in this codebase.
    """
    path = Path(path)
    try:
        with path.open("r") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise DeconvolutionConfigError(f"Could not parse YAML in {path}: {e}") from e

    if raw is None or "deconvolution" not in raw:
        return DeconvolutionSettings()

    section = raw["deconvolution"]
    if not isinstance(section, dict):
        raise DeconvolutionConfigError(f"'deconvolution' section in {path} must be a mapping, got {type(section).__name__}.")
    return _parse_deconvolution_section(section)
