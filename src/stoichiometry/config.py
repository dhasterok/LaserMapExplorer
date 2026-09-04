"""Mineral config schema and YAML loader/validator.

A mineral "recipe" (ideal formula, oxygen/cation normalization basis, site
definitions with fill priority, redox handling, trace-element
classification, end-member definitions, QC checks) is expressed as a YAML
file matching :class:`MineralConfig`. The loader validates structure and
raises :class:`MineralConfigError` with a specific, actionable message --
never silently produces a config that would compute wrong apfu.

Site fill order (which site gets first claim on a shared element like Al)
is taken from the order sites appear in the YAML file itself, not a
separate config key -- Python/PyYAML preserve mapping insertion order, so
the file's own ``sites:`` ordering *is* the priority order.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class MineralConfigError(ValueError):
    """Raised for missing/malformed mineral config fields."""


@dataclass
class SiteConfig:
    name: str
    target: float
    elements: list[str]
    priority: list[str]


@dataclass
class RedoxConfig:
    elements: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    default_method: str = ""
    fixed_ratio: float = 0.0  # Fe3+/FeTotal for the 'fixed_ratio' method


@dataclass
class TraceElementConfig:
    structural: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)


@dataclass
class EndMemberConfig:
    method: str = ""
    members: list[str] = field(default_factory=list)
    # Optional, separate from `members`: diagnostic ratios (e.g. spinel's
    # Cr#/Mg#/Fe3+-over-R3+/X_usp) that a method may also compute and return
    # alongside the named end-member fractions. Kept structurally distinct
    # (not just more `members`) because they don't participate in the
    # sum-to-100 contract or dock.py's {abbrev}_dominant argmax -- a ratio
    # like Mg#=85 would otherwise spuriously "win" that column over any
    # single, more-diluted discrete end-member fraction. Still written out
    # as ordinary {abbrev}_{ratio} columns via the same write path. Empty
    # for every mineral that doesn't need this (the default).
    ratios: list[str] = field(default_factory=list)


@dataclass
class MineralConfig:
    mineral: str
    abbreviation: str  # short prefix for output column names (e.g. 'Grt' for garnet) -- see dock.py's column-naming
    formula: str
    basis: str
    ideal_oxygens: float
    ideal_cations: float
    sites: dict[str, SiteConfig]
    redox: RedoxConfig
    trace_elements: TraceElementConfig
    end_members: EndMemberConfig
    qc_checks: list[str] = field(default_factory=list)
    site_method: str = "priority_fill"
    tetra_fe3_ratio: float = 0.0  # fixed Fe3+ fraction routed to the first site, for the 'tetra_fe3_ratio' site method
    normalization_excludes: list[str] = field(default_factory=list)  # species excluded from the cation-basis target sum (e.g. ['S'] for sulfides)

    @property
    def site_order(self) -> list[str]:
        """Site names in fill-priority order (the order they appear in the config)."""
        return list(self.sites.keys())

    def all_site_elements(self) -> set[str]:
        return {el for site in self.sites.values() for el in site.elements}


VALID_REDOX_METHODS = {"all_2plus", "all_3plus", "droop_1987", "fixed_ratio"}
VALID_END_MEMBER_METHODS = {
    "locock_2008", "olivine_ratio", "feldspar_ratio", "pyroxene_quad", "spinel_xmg",
    "xmg_ratio", "ilmenite_ratio", "lawsonite_ratio", "epidote_ratio", "scapolite_ratio", "titanite_ratio",
    "monazite_huttonite_cheralite_ratio", "mica_cascade", "amphibole_ca_ratio", "amphibole_na_ratio", "carbonate_ratio",
    "monosulfide_ratio", "pyrite_group_ratio", "pentlandite_ratio", "pyrrhotite_vacancy_ratio",
    "orthopyroxene_ratio", "pyroxene_quad_jd_ae", "nepheline_kalsilite_ratio", "pyroxenoid_ratio",
}
VALID_SITE_METHODS = {"priority_fill", "pyroxene_quad", "spinel_xmg", "tetra_fe3_ratio", "equipart"}
# "anion" -- for sulfides, where S/As/Sb (normalization.excludes) are
# directly measured (not inferred via STANDARD_OXIDES like oxide O), so the
# anion itself can anchor the normalization; see normalize.normalize_to_measured_anion.
VALID_BASES = {"oxygen", "cation", "anion"}


def _require(d: dict, key: str, context: str) -> object:
    if key not in d:
        raise MineralConfigError(f"Missing required field '{key}' in {context}.")
    return d[key]


def _parse_site(name: str, raw: dict) -> SiteConfig:
    context = f"site '{name}'"
    if not isinstance(raw, dict):
        raise MineralConfigError(f"{context} must be a mapping, got {type(raw).__name__}.")
    target = _require(raw, "target", context)
    elements = _require(raw, "elements", context)
    priority = raw.get("priority", elements)

    if not isinstance(elements, list) or not elements:
        raise MineralConfigError(f"{context} 'elements' must be a non-empty list.")
    if not isinstance(priority, list) or not priority:
        raise MineralConfigError(f"{context} 'priority' must be a non-empty list.")
    if set(priority) != set(elements):
        raise MineralConfigError(
            f"{context} 'priority' must contain exactly the same elements as 'elements' "
            f"(got priority={priority}, elements={elements})."
        )
    try:
        target = float(target)
    except (TypeError, ValueError):
        raise MineralConfigError(f"{context} 'target' must be numeric, got {target!r}.")

    return SiteConfig(name=name, target=target, elements=list(elements), priority=list(priority))


def _parse_redox(raw: dict | None) -> RedoxConfig:
    if raw is None:
        return RedoxConfig()
    context = "redox"
    elements = raw.get("elements", [])
    methods = raw.get("methods", [])
    default_method = raw.get("default_method", "")
    fixed_ratio = raw.get("fixed_ratio", 0.0)

    for m in methods:
        if m not in VALID_REDOX_METHODS:
            raise MineralConfigError(
                f"{context} 'methods' contains unknown method '{m}'; valid methods are {sorted(VALID_REDOX_METHODS)}."
            )
    if default_method and default_method not in methods:
        raise MineralConfigError(
            f"{context} 'default_method' ({default_method!r}) must be one of 'methods' ({methods})."
        )
    try:
        fixed_ratio = float(fixed_ratio)
    except (TypeError, ValueError):
        raise MineralConfigError(f"{context} 'fixed_ratio' must be numeric, got {fixed_ratio!r}.")
    if "fixed_ratio" in methods and not (0.0 <= fixed_ratio <= 1.0):
        raise MineralConfigError(f"{context} 'fixed_ratio' must be in [0, 1], got {fixed_ratio!r}.")
    return RedoxConfig(elements=list(elements), methods=list(methods), default_method=default_method, fixed_ratio=fixed_ratio)


def _parse_trace_elements(raw: dict | None) -> TraceElementConfig:
    if raw is None:
        return TraceElementConfig()
    return TraceElementConfig(
        structural=list(raw.get("structural", [])),
        excluded=list(raw.get("excluded", [])),
    )


def _parse_end_members(raw: dict | None) -> EndMemberConfig:
    if raw is None:
        return EndMemberConfig()
    context = "end_members"
    method = raw.get("method", "")
    members = raw.get("members", [])
    ratios = raw.get("ratios", [])
    if method and method not in VALID_END_MEMBER_METHODS:
        raise MineralConfigError(
            f"{context} 'method' ({method!r}) is unknown; valid methods are {sorted(VALID_END_MEMBER_METHODS)}."
        )
    if not members:
        raise MineralConfigError(f"{context} 'members' must be a non-empty list.")
    return EndMemberConfig(method=method, members=list(members), ratios=list(ratios))


def _parse_site_method(raw: dict | None) -> tuple[str, float]:
    if raw is None:
        return "priority_fill", 0.0
    context = "site_allocation"
    if not isinstance(raw, dict):
        raise MineralConfigError(f"'{context}' must be a mapping, got {type(raw).__name__}.")
    method = raw.get("method", "priority_fill")
    if method not in VALID_SITE_METHODS:
        raise MineralConfigError(
            f"{context} 'method' ({method!r}) is unknown; valid methods are {sorted(VALID_SITE_METHODS)}."
        )
    tetra_fe3_ratio = raw.get("tetra_fe3_ratio", 0.0)
    try:
        tetra_fe3_ratio = float(tetra_fe3_ratio)
    except (TypeError, ValueError):
        raise MineralConfigError(f"{context} 'tetra_fe3_ratio' must be numeric, got {tetra_fe3_ratio!r}.")
    if method == "tetra_fe3_ratio" and not (0.0 <= tetra_fe3_ratio <= 1.0):
        raise MineralConfigError(f"{context} 'tetra_fe3_ratio' must be in [0, 1], got {tetra_fe3_ratio!r}.")
    return method, tetra_fe3_ratio


def parse_mineral_config(raw: dict) -> MineralConfig:
    """Parse an already-loaded dict (e.g. from ``yaml.safe_load``) into a
    validated :class:`MineralConfig`.

    Raises
    ------
    MineralConfigError
        For any missing/malformed/inconsistent field -- including an
        element referenced by a site's ``priority``/``elements`` list that
        doesn't match, an unknown redox/end-member method, or a
        ``default_method`` not present in ``methods``.
    """
    if not isinstance(raw, dict):
        raise MineralConfigError(f"Config root must be a mapping, got {type(raw).__name__}.")

    mineral = _require(raw, "mineral", "config")
    abbreviation = _require(raw, "abbreviation", "config")
    if not isinstance(abbreviation, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", abbreviation):
        raise MineralConfigError(
            f"'abbreviation' ({abbreviation!r}) must be a letters/digits string starting with a letter "
            "(it's used as an output column-name prefix, e.g. 'Grt' -> 'Grt_X')."
        )
    formula = _require(raw, "formula", "config")

    normalization = _require(raw, "normalization", "config")
    if not isinstance(normalization, dict):
        raise MineralConfigError("'normalization' must be a mapping.")
    basis = _require(normalization, "basis", "normalization")
    if basis not in VALID_BASES:
        raise MineralConfigError(f"'normalization.basis' ({basis!r}) must be one of {sorted(VALID_BASES)}.")
    ideal_oxygens = _require(normalization, "ideal_oxygens", "normalization")
    ideal_cations = _require(normalization, "ideal_cations", "normalization")
    try:
        ideal_oxygens = float(ideal_oxygens)
        ideal_cations = float(ideal_cations)
    except (TypeError, ValueError):
        raise MineralConfigError("'ideal_oxygens'/'ideal_cations' must be numeric.")
    normalization_excludes = list(normalization.get("excludes", []))

    sites_raw = _require(raw, "sites", "config")
    if not isinstance(sites_raw, dict) or not sites_raw:
        raise MineralConfigError("'sites' must be a non-empty mapping of site name -> site config.")
    sites = {name: _parse_site(name, site_raw) for name, site_raw in sites_raw.items()}

    redox = _parse_redox(raw.get("redox"))
    trace_elements = _parse_trace_elements(raw.get("trace_elements"))
    end_members = _parse_end_members(raw.get("end_members"))
    qc_checks = list(raw.get("qc_checks", []))
    site_method, tetra_fe3_ratio = _parse_site_method(raw.get("site_allocation"))

    config = MineralConfig(
        mineral=mineral,
        abbreviation=abbreviation,
        formula=formula,
        basis=basis,
        ideal_oxygens=ideal_oxygens,
        ideal_cations=ideal_cations,
        sites=sites,
        redox=redox,
        trace_elements=trace_elements,
        end_members=end_members,
        qc_checks=qc_checks,
        site_method=site_method,
        tetra_fe3_ratio=tetra_fe3_ratio,
        normalization_excludes=normalization_excludes,
    )

    # Cross-field validation: every element assigned to a site must not also
    # be silently unreachable -- and every redox element declared should be
    # usable somewhere in the site definitions (as e.g. 'Fe2'/'Fe3'),
    # otherwise a redox split would produce a species no site ever collects.
    site_elements = config.all_site_elements()
    for el in redox.elements:
        variants = {f"{el}2", f"{el}3"} | {el}
        if not (variants & site_elements):
            raise MineralConfigError(
                f"redox element '{el}' has no matching species (e.g. '{el}2'/'{el}3') "
                f"in any site's 'elements' list -- it would be estimated but never allocated."
            )

    return config


def load_mineral_config(path: str | Path) -> MineralConfig:
    """Load and validate a mineral config YAML file.

    Parameters
    ----------
    path : str or Path
        Path to a ``.yaml``/``.yml`` mineral config file.

    Returns
    -------
    MineralConfig

    Raises
    ------
    MineralConfigError
        If the file can't be parsed as YAML, or fails validation (see
        :func:`parse_mineral_config`).
    """
    path = Path(path)
    try:
        with path.open("r") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise MineralConfigError(f"Could not parse YAML in {path}: {e}") from e

    if raw is None:
        raise MineralConfigError(f"{path} is empty.")

    return parse_mineral_config(raw)
