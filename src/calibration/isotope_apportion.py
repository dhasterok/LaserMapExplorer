"""Derives per-isotope concentrations from a mass-bias-corrected isotope
ratio set (see ``massbias.py``) and an already-calibrated total-element
concentration (see ``standards.calibrate_standard``/``pipeline.
_build_calibrated_ppm_and_grid``).

Pure downstream algebra on already-corrected values -- no drift-fitting
concerns of its own, so kept separate from ``massbias.py``.

Given a SAMPLE's own mass-bias-corrected ratios (e.g. Pb206/Pb204,
Pb207/Pb204, Pb208/Pb204 -- preserving whatever radiogenic signal is
actually in that sample, not the standard's fixed ratio), each isotope's
fractional share of the total element is:

    share_normalizer = 1 / (1 + sum(R_i for every included companion i))
    share_i = R_i * share_normalizer

so ``ppm_i = total_element_ppm * share_i``. This is more scientifically
defensible than scaling by natural terrestrial abundance for the
radiogenic daughter isotopes this module was built for (Pb-206/207/208,
Sr-87, Nd-143, Hf-176, Os-187, ...): natural abundance assumes the
sample's isotopic composition matches the natural/terrestrial average,
which is exactly wrong for a pair whose whole point is that it varies
sample-to-sample (see ``massbias.resolve_truth_ratio``'s docstring).

``IsotopeShareSpec.mode == "natural_abundance"`` is offered anyway (see
``apportion_from_spec``) for the non-radiogenic case -- an isotope pair
with no certified reference-material ratio at all, where a fixed
terrestrial-abundance split is still more informative than nothing, with
the same "invalid for radiogenic pairs" caveat surfaced to the user by
the GUI rather than blocked here (this module has no way to know which
pairs are radiogenic, same limitation as ``massbias.natural_abundance_ratio``
itself).

No PyQt imports -- matches background.py/standards.py/massbias.py's
headless convention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src.calibration.massbias import DEFAULT_ISOTOPE_TABLE_PATH, natural_abundance_ratio


@dataclass
class IsotopeShareSpec:
    """Request to split one element's calibrated ppm across its isotopes.

    Attributes
    ----------
    element : str
        Element symbol, e.g. ``"Pb"``.
    normalizer_mass : int
        The ratio-denominator isotope mass, e.g. ``204`` for Pb.
    companion_masses : list[int]
        Numerator isotope masses to apportion, e.g. ``[206, 207, 208]``.
    total_ppm_source_mass : int or None, optional
        Which ``calibrated_ppm`` column supplies the total-element ppm.
        ``None`` (default) auto-picks the first of
        ``[normalizer_mass] + companion_masses`` actually present in
        ``calibrated_ppm``.
    mode : {"mass_bias", "natural_abundance"}, optional
        ``"mass_bias"`` (default) reads corrected ratios from the
        calibrated-ratio columns (see ``massbias.py``).
        ``"natural_abundance"`` ignores those and uses a fixed terrestrial
        abundance ratio per companion -- invalid for radiogenic daughter
        pairs (see ``massbias.resolve_truth_ratio``), offered for
        non-radiogenic pairs a user still wants split out by mass.
    """

    element: str
    normalizer_mass: int              # the ratio denominator isotope, e.g. 204 for Pb
    companion_masses: list[int]       # e.g. [206, 207, 208]
    total_ppm_source_mass: int | None = None  # which calibrated_ppm column supplies the
                                                # total-element ppm; None -> auto-pick the
                                                # first of [normalizer_mass] + companion_masses
                                                # actually present in calibrated_ppm.columns
    mode: str = "mass_bias"           # "mass_bias" (default -- read corrected ratios from
                                        # calibrated_ratio_columns, see massbias.py) or
                                        # "natural_abundance" (ignore calibrated_ratio_columns
                                        # entirely, use a fixed terrestrial-abundance ratio per
                                        # companion instead -- invalid for radiogenic daughter
                                        # pairs, see massbias.resolve_truth_ratio's docstring;
                                        # this mode exists for elements/use-cases where that
                                        # invalidity doesn't apply, e.g. non-radiogenic isotope
                                        # pairs a user still wants split out by mass).


@dataclass
class IsotopeShareResult:
    """Per-isotope concentrations from apportioning one element's total ppm.

    Attributes
    ----------
    ppm : dict[int, numpy.ndarray]
        Isotope mass -> per-sweep ppm array, including the normalizer mass.
    included_masses : list[int]
        Companion masses that actually had a usable corrected ratio, sorted.
    missing_masses : list[int]
        Requested companion masses with no corrected ratio available -- gaps
        reported rather than backfilled from natural abundance.
    """

    ppm: dict[int, np.ndarray] = field(default_factory=dict)   # mass -> per-sweep ppm, including normalizer
    included_masses: list[int] = field(default_factory=list)   # companions that actually had a corrected ratio
    missing_masses: list[int] = field(default_factory=list)    # requested companions with no corrected ratio available


def apportion_element_ppm(
    total_element_ppm: np.ndarray, corrected_ratios: dict[int, np.ndarray], normalizer_mass: int,
) -> IsotopeShareResult | None:
    """Split an element's calibrated total ppm across its isotopes.

    Parameters
    ----------
    total_element_ppm : numpy.ndarray
        The element's already-calibrated total concentration, one value
        per row/sweep.
    corrected_ratios : dict[int, numpy.ndarray]
        Numerator isotope mass -> per-row ``isotope / normalizer`` ratio,
        e.g. ``{206: R206, 207: R207, 208: R208}`` for Pb normalized to
        Pb204. Entries whose value is ``None`` are ignored.
    normalizer_mass : int
        Mass of the ratio-denominator isotope, e.g. ``204`` for Pb.

    Returns
    -------
    IsotopeShareResult or None
        Per-isotope ppm arrays (including the normalizer), with
        ``included_masses`` listing the companions used and
        ``missing_masses`` empty. ``None`` when ``corrected_ratios`` has no
        usable entries at all.

    Notes
    -----
    Uses exactly the isotopes with a resolvable corrected ratio as if they
    were the complete isotope set -- valid to the extent the normalizer
    plus included companions already account for ~100% of the element's
    natural isotope population (true for Pb/Sr/Nd/Hf's dominant isotopes).
    A companion with no corrected ratio is reported in ``missing_masses``
    rather than backfilled from natural abundance, so a real precision
    difference between the two is not hidden.

    The shares are ``share_normalizer = 1 / (1 + sum(R_i))`` and
    ``share_i = R_i * share_normalizer``, so
    ``ppm_i = total_element_ppm * share_i``.
    """
    usable = {
        mass: np.asarray(ratio, dtype=float)
        for mass, ratio in corrected_ratios.items()
        if ratio is not None
    }
    if not usable:
        return None

    total = np.asarray(total_element_ppm, dtype=float)
    ratio_sum = np.zeros_like(total, dtype=float)
    for ratio in usable.values():
        ratio_sum = ratio_sum + ratio

    with np.errstate(divide="ignore", invalid="ignore"):
        share_normalizer = 1.0 / (1.0 + ratio_sum)

    ppm = {normalizer_mass: total * share_normalizer}
    for mass, ratio in usable.items():
        ppm[mass] = total * ratio * share_normalizer

    return IsotopeShareResult(ppm=ppm, included_masses=sorted(usable), missing_masses=[])


_VALID_MODES = {"mass_bias", "natural_abundance"}


def apportion_from_spec(
    spec: IsotopeShareSpec, calibrated_ppm_columns: dict[str, np.ndarray], calibrated_ratio_columns: dict[str, np.ndarray],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> IsotopeShareResult | None:
    """Resolve an :class:`IsotopeShareSpec` against column dicts and apportion.

    Parameters
    ----------
    spec : IsotopeShareSpec
        Which element, normalizer, and companion masses to apportion, and
        in which mode.
    calibrated_ppm_columns : dict[str, numpy.ndarray]
        Calibrated elemental ppm keyed by analyte column name, e.g.
        ``{"Pb206": array(...), ...}`` (as on
        ``SampleCalibratedResult.calibrated_ppm``).
    calibrated_ratio_columns : dict[str, numpy.ndarray]
        Mass-bias-corrected isotope ratios keyed by column name, e.g.
        ``{"Pb206 / Pb204": array(...), ...}``. Consulted only in
        ``"mass_bias"`` mode.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Isotope table (or path) for ``"natural_abundance"`` mode. Defaults
        to :data:`~src.calibration.massbias.DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    IsotopeShareResult or None
        Apportioned per-isotope ppm with ``missing_masses`` populated for
        companions that could not be resolved. ``None`` when no
        total-element ppm column can be found or
        :func:`apportion_element_ppm` returns ``None``.

    Raises
    ------
    ValueError
        If ``spec.mode`` is not ``"mass_bias"`` or ``"natural_abundance"``.

    Notes
    -----
    In ``"mass_bias"`` mode each companion's corrected ratio is read from
    ``calibrated_ratio_columns``; a companion with no such column is added
    to ``missing_masses`` rather than backfilled from natural abundance
    (see the module docstring). In ``"natural_abundance"`` mode a fixed
    terrestrial ratio (see ``massbias.natural_abundance_ratio``) is used
    for every companion, constant across rows; a companion with no
    abundance entry goes to ``missing_masses``.
    """
    if spec.mode not in _VALID_MODES:
        raise ValueError(f"IsotopeShareSpec.mode must be one of {sorted(_VALID_MODES)}, got {spec.mode!r}.")

    element = spec.element
    normalizer = f"{element}{spec.normalizer_mass}"

    total_mass = spec.total_ppm_source_mass
    if total_mass is None:
        for candidate in [spec.normalizer_mass] + list(spec.companion_masses):
            if f"{element}{candidate}" in calibrated_ppm_columns:
                total_mass = candidate
                break
    if total_mass is None or f"{element}{total_mass}" not in calibrated_ppm_columns:
        return None
    total_element_ppm = np.asarray(calibrated_ppm_columns[f"{element}{total_mass}"], dtype=float)

    corrected_ratios: dict[int, np.ndarray] = {}
    missing: list[int] = []
    if spec.mode == "mass_bias":
        for mass in spec.companion_masses:
            col = f"{element}{mass} / {normalizer}"
            if col in calibrated_ratio_columns:
                corrected_ratios[mass] = calibrated_ratio_columns[col]
            else:
                missing.append(mass)
    else:  # "natural_abundance"
        for mass in spec.companion_masses:
            ratio = natural_abundance_ratio(element, mass, spec.normalizer_mass, isotope_table=isotope_table)
            if ratio is not None:
                corrected_ratios[mass] = np.full_like(total_element_ppm, ratio, dtype=float)
            else:
                missing.append(mass)

    result = apportion_element_ppm(total_element_ppm, corrected_ratios, spec.normalizer_mass)
    if result is None:
        return None
    result.missing_masses = missing
    return result
