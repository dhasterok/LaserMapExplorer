"""Input normalization: ppm (element basis) or wt.% (oxide basis) analyses
-> cation moles -> oxygen-basis apfu.

Uses ``global_geochemistry.utils.molecular.MolecularWeightCalculator`` for
molar weights -- no molecular-weight logic is reimplemented here.
"""
from __future__ import annotations

import re

from global_geochemistry.utils.molecular import MolecularWeightCalculator

from src.stoichiometry.config import MineralConfig

# Standard assumed oxide form per cation, used to compute how many oxygens
# each cation's mole contributes when normalizing to the ideal oxygen basis.
# For ppm (element-basis) input there's no oxide form given directly, so
# this fixed convention applies; for wt.%-oxide input the oxide form comes
# from the input key itself, but redox-sensitive elements (Fe here) still
# need this table's 'Fe' entry as the initial "assume Fe2+" reference basis
# (see redox.py -- this is exactly Droop's (1987) S-basis assumption).
STANDARD_OXIDES: dict[str, str] = {
    "Si": "SiO2", "Ti": "TiO2", "Al": "Al2O3", "Cr": "Cr2O3",
    "Fe": "FeO", "Fe2": "FeO", "Fe3": "Fe2O3",
    "Mn": "MnO", "Mg": "MgO", "Ca": "CaO",
    "Na": "Na2O", "K": "K2O", "P": "P2O5",
    "Ni": "NiO", "Co": "CoO", "Zn": "ZnO", "Sc": "Sc2O3",
    "Y": "Y2O3", "REE": "Y2O3",  # trivalent REE assumed to behave like Y at the X-site
    "Zr": "ZrO2", "Hf": "HfO2", "Nb": "Nb2O5", "V": "V2O3",
}

_OXIDE_RE = re.compile(r"^([A-Z][a-z]?)(\d*)O(\d*)$")


def _parse_simple_oxide(formula: str) -> tuple[str, int, int]:
    """Parse a simple (single-cation) oxide formula, e.g. 'Al2O3' -> ('Al', 2, 3).

    Only handles the ``Cation_nO_m`` shape used by mineral oxide formulas --
    not general nested formulas (see ``MolecularWeightCalculator`` for that).
    """
    m = _OXIDE_RE.match(formula)
    if not m:
        raise ValueError(
            f"Could not parse '{formula}' as a simple oxide formula (expected e.g. 'SiO2', 'Al2O3')."
        )
    cation, n_cation_str, n_oxygen_str = m.groups()
    n_cation = int(n_cation_str) if n_cation_str else 1
    n_oxygen = int(n_oxygen_str) if n_oxygen_str else 1
    return cation, n_cation, n_oxygen


def to_cation_moles(
    analysis: dict[str, float],
    input_mode: str,
    config: MineralConfig,
    lod: dict[str, float] | None = None,
    lod_treatment: str = "zero",
    below_lod: set[str] | None = None,
    mwc: MolecularWeightCalculator | None = None,
) -> tuple[dict[str, float], dict[str, object]]:
    """Convert a raw analysis to cation moles (unnormalized -- any consistent
    absolute basis works, since oxygen normalization is a ratio).

    Parameters
    ----------
    analysis : dict[str, float]
        Element symbol -> ppm (``input_mode='ppm'``), or oxide formula ->
        wt.% (``input_mode='wt_percent'``).
    input_mode : {'ppm', 'wt_percent'}
    config : MineralConfig
    lod : dict[str, float], optional
        Detection-limit value per input key, required for 'half_lod' treatment.
    lod_treatment : {'zero', 'half_lod', 'exclude'}
        How to treat keys flagged in ``below_lod``.
    below_lod : set[str], optional
        Input keys (element or oxide, matching ``analysis``'s own keys)
        reported as below detection limit.
    mwc : MolecularWeightCalculator, optional
        Reused instance; a new one is created if not given.

    Returns
    -------
    moles : dict[str, float]
        Cation element symbol -> moles.
    exclusions : dict
        ``{'excluded': [...], 'below_lod_treated': {key: treatment}}`` --
        which input keys were dropped as non-structural/contamination
        (``config.trace_elements.excluded``) or LOD-excluded, for QC/audit.
    """
    if input_mode not in ("ppm", "wt_percent"):
        raise ValueError(f"Unknown input_mode {input_mode!r}; expected 'ppm' or 'wt_percent'.")
    if lod_treatment not in ("zero", "half_lod", "exclude"):
        raise ValueError(f"Unknown lod_treatment {lod_treatment!r}; expected 'zero', 'half_lod', or 'exclude'.")

    mwc = mwc or MolecularWeightCalculator()
    lod = lod or {}
    below_lod = below_lod or set()
    excluded_set = set(config.trace_elements.excluded)

    moles: dict[str, float] = {}
    exclusions: dict[str, object] = {"excluded": [], "below_lod_treated": {}}

    for key, value in analysis.items():
        if input_mode == "wt_percent":
            cation, n_cation, _ = _parse_simple_oxide(key)
        else:
            cation, n_cation = key, 1

        if cation in excluded_set:
            exclusions["excluded"].append(cation)  # type: ignore[union-attr]
            continue

        v = value
        if key in below_lod:
            if lod_treatment == "zero":
                v = 0.0
            elif lod_treatment == "half_lod":
                if key not in lod:
                    raise ValueError(
                        f"'{key}' is flagged below_lod but no LOD value was provided for 'half_lod' treatment."
                    )
                v = lod[key] / 2.0
            else:  # exclude
                exclusions["below_lod_treated"][key] = "excluded"  # type: ignore[index]
                continue
            exclusions["below_lod_treated"][key] = lod_treatment  # type: ignore[index]

        if v is None:
            continue

        if input_mode == "wt_percent":
            oxide_mw = mwc.molecular_weight(key)
            cation_moles = (v / oxide_mw) * n_cation
        else:
            atomic_mw = mwc.molecular_weight(cation)
            cation_moles = (v * 1e-6) / atomic_mw

        moles[cation] = moles.get(cation, 0.0) + cation_moles

    return moles, exclusions


def normalize_to_oxygen(
    moles: dict[str, float],
    config: MineralConfig,
    redox_oxide_overrides: dict[str, str] | None = None,
) -> dict[str, float]:
    """Scale cation moles so total oxygen-equivalent equals ``config.ideal_oxygens``.

    Parameters
    ----------
    moles : dict[str, float]
        Output of :func:`to_cation_moles`.
    config : MineralConfig
    redox_oxide_overrides : dict[str, str], optional
        Element -> oxide formula, overriding :data:`STANDARD_OXIDES` for
        this call (e.g. ``{'Fe': 'Fe2O3'}`` for an all-Fe3+ hypothesis).

    Returns
    -------
    dict[str, float]
        Cation element -> apfu (cations per formula unit).
    """
    redox_oxide_overrides = redox_oxide_overrides or {}
    total_o_equiv = 0.0
    o_per_cation: dict[str, float] = {}

    for el, mol in moles.items():
        oxide = redox_oxide_overrides.get(el) or STANDARD_OXIDES.get(el)
        if oxide is None:
            raise ValueError(f"No standard oxide form known for element '{el}' -- cannot compute its oxygen contribution.")
        _, n_cation, n_oxygen = _parse_simple_oxide(oxide)
        ratio = n_oxygen / n_cation
        o_per_cation[el] = ratio
        total_o_equiv += mol * ratio

    if total_o_equiv <= 0:
        raise ValueError("Total oxygen-equivalent is zero or negative; check the input analysis.")

    k = config.ideal_oxygens / total_o_equiv
    return {el: mol * k for el, mol in moles.items()}


def oxide_total_percent(analysis: dict[str, float], input_mode: str) -> float | None:
    """Sum of input oxide wt.% (QC diagnostic) -- ``None`` for ppm-basis input."""
    if input_mode != "wt_percent":
        return None
    return float(sum(analysis.values()))
