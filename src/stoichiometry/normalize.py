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
    "B": "B2O3", "Li": "Li2O",  # tourmaline's T/B-site and Y-site (elbaite) trace/structural cations
    "Y": "Y2O3", "REE": "Y2O3",  # trivalent REE assumed to behave like Y at the X-site
    "Zr": "ZrO2", "Hf": "HfO2", "Nb": "Nb2O5", "V": "V2O3",
    "Ba": "BaO", "Sr": "SrO",
    # Individual lanthanides (allanite, monazite-adjacent trace chemistry) --
    # 'REE' above is a generic fallback for anything not listed individually.
    "La": "La2O3", "Ce": "Ce2O3", "Pr": "Pr2O3", "Nd": "Nd2O3", "Sm": "Sm2O3",
    "Eu": "Eu2O3", "Gd": "Gd2O3", "Tb": "Tb2O3", "Dy": "Dy2O3", "Ho": "Ho2O3",
    "Er": "Er2O3", "Tm": "Tm2O3", "Yb": "Yb2O3", "Lu": "Lu2O3",
    "Th": "ThO2", "U": "UO2", "Pb": "PbO",
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
        Element symbol -> ppm (``input_mode='ppm'``), oxide formula -> wt.%
        (``input_mode='wt_percent'``), or element symbol -> wt.%
        (``input_mode='element_wt_percent'`` -- sulfide/metal analyses,
        reported as elements rather than oxides, e.g. 'S', 'Fe', 'Cu').
    input_mode : {'ppm', 'wt_percent', 'element_wt_percent'}
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
    if input_mode not in ("ppm", "wt_percent", "element_wt_percent"):
        raise ValueError(f"Unknown input_mode {input_mode!r}; expected 'ppm', 'wt_percent', or 'element_wt_percent'.")
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
        elif input_mode == "element_wt_percent":
            atomic_mw = mwc.molecular_weight(cation)
            cation_moles = v / atomic_mw
        else:  # ppm
            atomic_mw = mwc.molecular_weight(cation)
            cation_moles = (v * 1e-6) / atomic_mw

        moles[cation] = moles.get(cation, 0.0) + cation_moles

    return moles, exclusions


def normalize_to_oxygen(
    moles: dict[str, float],
    config: MineralConfig,
) -> dict[str, float]:
    """Scale cation moles so total oxygen-equivalent equals ``config.ideal_oxygens``.

    Used only as intermediate scaffolding for Droop's (1987) charge-balance
    formula (see ``redox.py``) -- the resulting total (Droop's "S") is what
    that formula is defined in terms of. Not the basis final apfu are
    reported on; see :func:`normalize_to_cations` for that.

    Parameters
    ----------
    moles : dict[str, float]
        Output of :func:`to_cation_moles`.
    config : MineralConfig

    Returns
    -------
    dict[str, float]
        Cation element -> apfu (cations per formula unit), oxygen-basis.
    """
    total_o_equiv = 0.0
    o_per_cation: dict[str, float] = {}

    for el, mol in moles.items():
        oxide = STANDARD_OXIDES.get(el)
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


def normalize_to_cations(
    moles: dict[str, float],
    config: MineralConfig,
    ideal_cations: float | None = None,
) -> dict[str, float]:
    """Scale cation moles so total cations equal ``config.ideal_cations`` (T)
    -- the basis final apfu are reported on (the Droop 1987 / MinPlotX
    convention).

    Valence-independent: moles don't encode charge, so this same T-basis
    apfu is the correct reference regardless of which redox hypothesis
    (all-2+/all-3+/Droop) is ultimately chosen for a redox-sensitive element.

    ``config.normalization_excludes`` (e.g. ``['S']`` for sulfides) removes
    those species from the *sum* used to compute the scale factor -- they're
    anions, not part of "how many cations to normalize to" -- but they're
    still scaled and included in the returned dict, same as everything else.

    Parameters
    ----------
    moles : dict[str, float]
        Output of :func:`to_cation_moles`.
    config : MineralConfig
    ideal_cations : float, optional
        Overrides ``config.ideal_cations`` for this call -- lets a caller
        pick a different normalization target per analysis (e.g. sulfide's
        generic config, where the target isn't tied to one fixed formula;
        see ``pipeline.calculate``'s ``ideal_cations_override``).

    Returns
    -------
    dict[str, float]
        Cation element -> apfu (cations per formula unit), cation-basis.
    """
    excludes = set(config.normalization_excludes)
    total = sum(v for el, v in moles.items() if el not in excludes)
    if total <= 0:
        raise ValueError("Total cation moles is zero or negative; check the input analysis.")

    k = (ideal_cations if ideal_cations is not None else config.ideal_cations) / total
    return {el: mol * k for el, mol in moles.items()}


def measured_anion_moles(moles: dict[str, float], config: MineralConfig) -> float:
    """Sum of ``config.normalization_excludes``' moles (e.g. S, or S+As+Sb)
    -- the *directly measured* anion total a ``basis: "anion"`` config
    anchors on. Exposed separately from :func:`normalize_to_measured_anion`
    so callers (``pipeline.calculate``) can check it's actually nonzero
    before committing to the anion basis, and fall back to
    :func:`normalize_to_cations` when the anion wasn't collected in this
    analysis (absent from the input, or zeroed by LOD treatment).
    """
    return sum(moles.get(el, 0.0) for el in config.normalization_excludes)


def normalize_to_measured_anion(
    moles: dict[str, float],
    config: MineralConfig,
) -> dict[str, float]:
    """Scale cation moles so the *directly measured* anion total (``config.
    normalization_excludes``' elements -- S, or S+As+Sb for sulfosalts) equals
    ``config.ideal_oxygens`` (reused here as the generic "ideal anchor-basis
    total" field, the same reuse ``ideal_cations`` already gets for the
    cation basis).

    Unlike :func:`normalize_to_oxygen` (which infers an oxide-basis oxygen
    total from cation moles via ``STANDARD_OXIDES`` valence assumptions,
    since O usually isn't measured directly), this anchors on an anion
    that *is* directly measured by this tool's real inputs (LA-ICP-MS/EPMA
    element wt%) -- so no oxide-form lookup is needed, and the metal
    (cation) side is left to float freely. That's the point: real
    non-stoichiometry (e.g. pyrrhotite's Fe-vacancy) then shows up directly
    and intuitively as a metal apfu deficiency, rather than being
    mathematically present-but-hidden behind a metal total forced to
    exactly its nominal target the way :func:`normalize_to_cations` would
    produce.

    Parameters
    ----------
    moles : dict[str, float]
        Output of :func:`to_cation_moles`.
    config : MineralConfig

    Returns
    -------
    dict[str, float]
        Element -> apfu, anion-basis.
    """
    total_anion = measured_anion_moles(moles, config)
    if total_anion <= 0:
        raise ValueError(
            "Total measured anion moles (config.normalization_excludes) is zero or negative; "
            "check the input analysis, or fall back to normalize_to_cations if the anion wasn't measured."
        )

    k = config.ideal_oxygens / total_anion
    return {el: mol * k for el, mol in moles.items()}


def oxide_total_percent(analysis: dict[str, float], input_mode: str) -> float | None:
    """Sum of input oxide/element wt.% (QC diagnostic) -- ``None`` for ppm-basis input."""
    if input_mode not in ("wt_percent", "element_wt_percent"):
        return None
    return float(sum(analysis.values()))
