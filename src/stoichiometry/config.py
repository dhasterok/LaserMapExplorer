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


@dataclass
class TraceElementConfig:
    structural: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)


@dataclass
class EndMemberConfig:
    method: str = ""
    members: list[str] = field(default_factory=list)


@dataclass
class MineralConfig:
    mineral: str
    formula: str
    basis: str
    ideal_oxygens: float
    ideal_cations: float
    sites: dict[str, SiteConfig]
    redox: RedoxConfig
    trace_elements: TraceElementConfig
    end_members: EndMemberConfig
    qc_checks: list[str] = field(default_factory=list)

    @property
    def site_order(self) -> list[str]:
        """Site names in fill-priority order (the order they appear in the config)."""
        return list(self.sites.keys())

    def all_site_elements(self) -> set[str]:
        return {el for site in self.sites.values() for el in site.elements}


VALID_REDOX_METHODS = {"all_2plus", "all_3plus", "droop_1987"}
VALID_END_MEMBER_METHODS = {"locock_2008"}


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

    for m in methods:
        if m not in VALID_REDOX_METHODS:
            raise MineralConfigError(
                f"{context} 'methods' contains unknown method '{m}'; valid methods are {sorted(VALID_REDOX_METHODS)}."
            )
    if default_method and default_method not in methods:
        raise MineralConfigError(
            f"{context} 'default_method' ({default_method!r}) must be one of 'methods' ({methods})."
        )
    return RedoxConfig(elements=list(elements), methods=list(methods), default_method=default_method)


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
    if method and method not in VALID_END_MEMBER_METHODS:
        raise MineralConfigError(
            f"{context} 'method' ({method!r}) is unknown; valid methods are {sorted(VALID_END_MEMBER_METHODS)}."
        )
    if not members:
        raise MineralConfigError(f"{context} 'members' must be a non-empty list.")
    return EndMemberConfig(method=method, members=list(members))


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
    formula = _require(raw, "formula", "config")

    normalization = _require(raw, "normalization", "config")
    if not isinstance(normalization, dict):
        raise MineralConfigError("'normalization' must be a mapping.")
    basis = _require(normalization, "basis", "normalization")
    ideal_oxygens = _require(normalization, "ideal_oxygens", "normalization")
    ideal_cations = _require(normalization, "ideal_cations", "normalization")
    try:
        ideal_oxygens = float(ideal_oxygens)
        ideal_cations = float(ideal_cations)
    except (TypeError, ValueError):
        raise MineralConfigError("'ideal_oxygens'/'ideal_cations' must be numeric.")

    sites_raw = _require(raw, "sites", "config")
    if not isinstance(sites_raw, dict) or not sites_raw:
        raise MineralConfigError("'sites' must be a non-empty mapping of site name -> site config.")
    sites = {name: _parse_site(name, site_raw) for name, site_raw in sites_raw.items()}

    redox = _parse_redox(raw.get("redox"))
    trace_elements = _parse_trace_elements(raw.get("trace_elements"))
    end_members = _parse_end_members(raw.get("end_members"))
    qc_checks = list(raw.get("qc_checks", []))

    config = MineralConfig(
        mineral=mineral,
        formula=formula,
        basis=basis,
        ideal_oxygens=ideal_oxygens,
        ideal_cations=ideal_cations,
        sites=sites,
        redox=redox,
        trace_elements=trace_elements,
        end_members=end_members,
        qc_checks=qc_checks,
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
