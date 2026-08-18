"""Synthesizes a pooled ``"<element> total"`` virtual raw channel from 2+
measured isotopes of the same element -- an opt-in precision tool for
elements whose individual isotopes are each low-abundance/low-count (e.g.
Pb-204), where combining several channels' raw counts before calibration
gives a materially better-precision estimate than any single isotope
alone.

Physical basis: ``CPS_i ~= k * concentration * abundance_i`` (k roughly
constant across isotopes of the same element under the same matrix/
instrument conditions). Summing across a chosen set of measured isotope
masses M and dividing by their COMBINED natural-abundance fraction
(``sum(abundance_i for i in M)``) rescales the sum to what would have
been measured if 100% of the element's natural abundance were captured.
This makes the pooled channel physically interpretable on its own (an
"as-if-100%-of-the-element" signal) and robust to a file where one
constituent isotope happens to be missing (the fraction is recomputed per
file from whichever of the requested masses are actually present there),
rather than an arbitrary, magnitude-only sum.

The abundance-fraction rescaling is NOT what makes the resulting
calibration correct, though -- ratio-based calibration already cancels a
fixed isotope subset's combined abundance fraction between sample and
standard the same way it does for a single isotope, as long as the same
subset is summed in both (see ``reflib.resolve_elemental_value``'s
docstring for the single-isotope case this generalizes). Once
synthesized, the pooled channel is just another raw CPS column and flows
through the existing background/drift/standard-bracketing calibration
machinery unmodified (see ``pipeline.run``, which calls
:func:`synthesize_pooled_channels` on every parsed file before background
detection) -- calibrated against the reference material's own elemental
value the same way any single isotope already is.

Only valid for elements whose isotopic composition is not itself the
signal of interest (i.e. NOT for radiogenic pairs like Pb-206/207/208,
Sr-87, Nd-143, Hf-176, Os-187 -- same caveat as
``massbias.natural_abundance_ratio``) -- offered here as an opt-in
precision tool for ordinary (non-isotope-specific) element quantification.

No PyQt imports -- matches background.py/standards.py/massbias.py's
headless convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.calibration.massbias import DEFAULT_ISOTOPE_TABLE_PATH, load_isotope_table
from src.calibration.rawfile import LineFileData
from src.calibration.reflib import POOLED_TOTAL_SUFFIX

TOTAL_SUFFIX = POOLED_TOTAL_SUFFIX  # re-exported for convenience -- reflib owns the naming constant (see its own comment)


@dataclass
class PooledElementSpec:
    element: str
    masses: list[int]  # every isotope of `element` a user has opted to pool -- usually every measured one


def pooled_channel_name(element: str) -> str:
    return f"{element}{TOTAL_SUFFIX}"


def is_pooled_channel_name(analyte: str) -> str | None:
    """Returns the element name if ``analyte`` is a pooled-channel name
    (see :func:`pooled_channel_name`), else ``None``."""
    if analyte.endswith(TOTAL_SUFFIX):
        return analyte[: -len(TOTAL_SUFFIX)]
    return None


def combined_abundance_fraction(
    element: str, masses: list[int],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> float | None:
    """Sum of ``masses``' natural-abundance fractions for ``element`` (from
    ``isotope_table``'s ``abundance_nominal`` column) -- e.g. Pb-206 +
    Pb-207 + Pb-208 (excluding Pb-204) is ~0.986. Returns ``None`` if the
    table is unavailable or none of ``masses`` resolve.
    """
    if isotope_table is None:
        return None
    table = isotope_table if isinstance(isotope_table, pd.DataFrame) else load_isotope_table(isotope_table)
    if table is None:
        return None
    rows = table[(table["symbol"] == element) & (table["atomic_mass"].astype(int).isin(masses))]
    if rows.empty:
        return None
    return float(rows["abundance_nominal"].sum())


def synthesize_pooled_channels(
    files: list[LineFileData], specs: list[PooledElementSpec],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> None:
    """Mutates every file in ``files`` in place, adding one new raw CPS
    column (and ``LineFileData.analytes`` entry) per spec --
    :func:`pooled_channel_name` -- equal to the sum of whichever of
    ``spec.masses`` are actually present in that file's own signal,
    divided by their combined natural-abundance fraction (see module
    docstring).

    Must run before background-window detection (see ``pipeline.run``) so
    the pooled channel gets the same background/drift/calibration
    treatment as any ordinary analyte column. A file missing every one of
    ``spec.masses``, or whose available subset has no resolvable combined
    abundance fraction, is left untouched for that spec (no pooled column
    added there) rather than raising -- matches how an unresolvable
    analyte is handled elsewhere in this pipeline.
    """
    if isotope_table is not None and not isinstance(isotope_table, pd.DataFrame):
        isotope_table = load_isotope_table(isotope_table)

    for spec in specs:
        name = pooled_channel_name(spec.element)
        for f in files:
            available_masses = [m for m in spec.masses if f"{spec.element}{m}" in f.signal.columns]
            if not available_masses:
                continue
            fraction = combined_abundance_fraction(spec.element, available_masses, isotope_table)
            if not fraction:
                continue
            available_cols = [f"{spec.element}{m}" for m in available_masses]
            f.signal[name] = f.signal[available_cols].sum(axis=1) / fraction
            if name not in f.analytes:
                f.analytes.append(name)
