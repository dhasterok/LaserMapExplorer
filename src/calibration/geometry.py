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
    """Manually entered instrument, laser, and scan-geometry parameters.

    Every field is optional; unset fields cause downstream diagnostics to
    fall back to unitless index spacing (see :func:`compute_pixel_spacing`).

    Attributes
    ----------
    instrument : str or None
        Instrument/system name. Provenance only -- nothing computes from it.
    spot_size_um : float or None
        Laser spot size in microns. Sets ``dx`` in pixel-spacing.
    sweep_s : float or None
        Sweep (line acquisition) time in seconds. Combined with
        ``speed_um_s`` to give ``dy``.
    speed_um_s : float or None
        Stage scan speed in microns per second. Combined with ``sweep_s``
        to give ``dy``.
    raster_length_um : float or None
        TOF-style total raster extent along the fast axis, in microns.
        Takes precedence over spot/sweep/speed when both raster fields are
        set.
    raster_width_um : float or None
        TOF-style total raster extent along the slow axis, in microns.
    scan_axis : {"Xc", "Yc"}
        Which axis is the fast/continuous scan direction. ``"Yc"`` swaps
        the computed ``(dx, dy)``. Defaults to ``"Xc"``.
    reverse_x : bool
        Whether the fast axis is scanned in reverse. Defaults to ``False``.
    reverse_y : bool
        Whether the slow axis is scanned in reverse. Defaults to ``False``.
    bidirectional_scan : bool
        Alternate lines scanned in opposite directions. When set,
        ``src/deconvolution/``'s washout correction must flip the causal
        tail direction on alternate lines to avoid herringbone artifacts
        (see ``plans/laicpms_map_correction_spec.md`` Sec 3.2). Defaults to
        ``False``.
    dwell_time_ms : float or None
        Per-analyte dwell time in milliseconds. Combined with
        ``sweeps_per_reading`` gives ``tau = dwell * sweeps`` for
        ``src/calibration/counts.py``'s Poisson count recovery
        (``provenance="metadata"``). Drives computation, not just display.
    sweeps_per_reading : int or None
        Number of sweeps averaged into each reported value. See
        ``dwell_time_ms``.
    laser_wavelength_nm : float or None
        Laser wavelength in nanometres. Provenance only.
    fluence_j_cm2 : float or None
        Laser fluence in J/cm^2. Provenance only.
    pulse_rate_hz : float or None
        Laser pulse repetition rate in Hz. Provenance only.
    notes : dict
        Free-form logbook fields not otherwise modeled (gas flow, operator,
        etc.). Retained for provenance; nothing computes from it.
    """

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
        """Construct settings from GUI/CLI manual entry.

        Parameters
        ----------
        **kwargs
            Any :class:`InstrumentSettings` field name mapped to its value.

        Returns
        -------
        InstrumentSettings
            A new instance with the supplied fields set and all others left
            at their defaults.

        Notes
        -----
        Kept as a distinct constructor (rather than calling ``__init__``
        directly everywhere) so a future ``from_logbook_file(path)``
        alternate constructor can be added once an instrument logbook format
        exists to parse, without any downstream consumer needing to change.
        """
        return cls(**kwargs)

    def is_blank(self) -> bool:
        """Whether no scan-geometry field has been entered.

        Returns
        -------
        bool
            ``True`` when ``spot_size_um``, ``sweep_s``, ``speed_um_s``,
            ``raster_length_um``, and ``raster_width_um`` are all unset.
            Provenance-only and Poisson-recovery fields are not considered.
        """
        return (
            self.spot_size_um is None and self.sweep_s is None and self.speed_um_s is None
            and self.raster_length_um is None and self.raster_width_um is None
        )


def compute_pixel_spacing(settings: InstrumentSettings) -> tuple[float, float]:
    """Pixel spacing ``(dx, dy)`` in microns from manual geometry settings.

    Parameters
    ----------
    settings : InstrumentSettings
        Manually entered geometry. Only the geometry fields are consulted
        (``raster_length_um``/``raster_width_um``, then ``spot_size_um``,
        ``speed_um_s``, ``sweep_s``, ``scan_axis``).

    Returns
    -------
    tuple[float, float]
        ``(dx, dy)`` in microns. Returns ``(1.0, 1.0)`` (unitless index
        spacing) when nothing has been entered, so index-based maps degrade
        gracefully rather than erroring.

    Notes
    -----
    Follows the same square-pixel-fallback convention used by
    ``MapImporter.compute_pixel_spacing()``: spot size gives ``dx``; sweep
    time * scan speed gives ``dy`` when both are given, else ``dy`` falls
    back to ``dx`` (square pixels). TOF-style raster length/width take
    precedence over spot/sweep/speed when supplied. A ``scan_axis`` of
    ``"Yc"`` swaps the two.

    Deliberately not imported from ``src/importers/MapImporter.py`` -- that
    function is entangled with the import dialog's table-widget state -- so
    this keeps a dependency-free copy of the same algorithm, keeping the two
    modules numerically consistent once this eventually feeds LaME's
    importer.
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
