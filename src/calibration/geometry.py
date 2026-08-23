"""Manual-entry instrument/geometry settings.

There is usually no instrument logbook available, so -- mirroring how
``src/importers/MapImporter.py`` already handles this exact gap for its own
imports (a manual-entry table for spot size / sweep-time-or-speed /
length-width / scan axis / swap-reverse, defaulting to square-pixel spacing
when left blank) -- this module lets geometry be entered by hand rather than
requiring a logbook to exist. Nothing here is required: every field defaults
to unset, and index-based diagnostics fall back to unitless spacing.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InstrumentSettings:
    instrument: str | None = None                  # instrument/system name (provenance only)
    spot_size_um: float | None = None
    sweep_s: float | None = None
    speed_um_s: float | None = None
    raster_length_um: float | None = None      # TOF-style: total raster extent, fast axis
    raster_width_um: float | None = None        # TOF-style: total raster extent, slow axis
    scan_axis: str = "Xc"                        # 'Xc' or 'Yc' -- which axis is the fast/continuous scan
    reverse_x: bool = False
    reverse_y: bool = False
    bidirectional_scan: bool = False               # alternate lines scanned in opposite directions --
                                                    # src/deconvolution/'s washout correction must flip the
                                                    # causal tail's direction on alternate lines when this is
                                                    # set, or it produces "herringbone" artifacts (see
                                                    # plans/laicpms_map_correction_spec.md Sec 3.2)
    dwell_time_ms: float | None = None            # per-analyte dwell time -- combined with
    sweeps_per_reading: int | None = None          # sweeps_per_reading gives tau = dwell*sweeps for
                                                    # src/calibration/counts.py's Poisson count recovery
                                                    # (provenance="metadata"); unlike the free-form notes
                                                    # below, these two drive computation, not just display.
    laser_wavelength_nm: float | None = None       # laser wavelength (provenance only)
    fluence_j_cm2: float | None = None             # laser fluence (provenance only)
    pulse_rate_hz: float | None = None             # laser pulse repetition rate (provenance only)
    notes: dict = field(default_factory=dict)     # free-form logbook fields not otherwise modeled
                                                    # (gas flow, operator, etc.) -- retained for
                                                    # provenance even though nothing computes from them

    @classmethod
    def from_manual_entry(cls, **kwargs) -> "InstrumentSettings":
        """Constructs settings from GUI/CLI manual entry.

        Kept as a distinct constructor (rather than calling ``__init__``
        directly everywhere) so a future ``from_logbook_file(path)``
        alternate constructor can be added once an instrument logbook format
        exists to parse, without any downstream consumer needing to change.
        """
        return cls(**kwargs)

    def is_blank(self) -> bool:
        return (
            self.spot_size_um is None and self.sweep_s is None and self.speed_um_s is None
            and self.raster_length_um is None and self.raster_width_um is None
        )


def compute_pixel_spacing(settings: InstrumentSettings) -> tuple[float, float]:
    """(dx, dy) in microns, following the same square-pixel-fallback convention
    used by ``MapImporter.compute_pixel_spacing()``.

    Spot size gives dx; sweep time * scan speed gives dy when both are given,
    else dy falls back to dx (square pixels). TOF-style raster length/width
    take precedence over spot/sweep/speed when supplied. Deliberately not
    imported from ``src/importers/MapImporter.py`` -- that function is
    entangled with the import dialog's table-widget state -- this keeps a
    dependency-free copy of the same algorithm so the two modules stay
    numerically consistent once this eventually feeds LaME's importer.

    Returns ``(1.0, 1.0)`` (unitless index spacing) when nothing has been
    entered, so index-based maps degrade gracefully rather than erroring.
    """
    if settings.raster_length_um is not None and settings.raster_width_um is not None:
        dx, dy = settings.raster_length_um, settings.raster_width_um
    elif settings.spot_size_um is not None:
        dx = settings.spot_size_um
        if settings.speed_um_s is not None and settings.sweep_s is not None:
            dy = settings.speed_um_s * settings.sweep_s
        else:
            dy = dx  # square-pixel fallback
    else:
        return 1.0, 1.0

    if settings.scan_axis == "Yc":
        dx, dy = dy, dx

    return dx, dy
