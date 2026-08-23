"""QC diagnostics, dispatched generically by name from ``config.qc_checks``.

Each check is a registered function, not an ``if mineral == 'garnet':``
branch -- a new mineral declares its own checks in its own YAML without
backend changes. An unknown check name raises rather than being silently
skipped, matching the rest of this package's "clear errors over silent
wrong output" convention.
"""
from __future__ import annotations

from typing import Any

from src.stoichiometry.config import MineralConfig
from src.stoichiometry.redox import RedoxResult
from src.stoichiometry.sites import SiteAllocationResult


def check_hydrogarnet_substitution(
    config: MineralConfig,
    apfu: dict[str, float],
    site_allocation: SiteAllocationResult,
    redox_result: RedoxResult | None,
    threshold: float = 0.05,
) -> dict[str, Any]:
    """Flag likely hydrogarnet substitution ((OH)4 for SiO4), garnet-specific.

    A genuine hydrogarnet signal is Si itself falling short of the Z-site
    target *and* the whole Z site remaining under-occupied (not made up by
    Al/Fe3+) -- distinguishing it from ordinary analytical noise, which
    Al/Fe3+ spillover into Z would already resolve.
    """
    z = site_allocation.sites.get("Z")
    if z is None:
        return {"flag": False, "reason": "no 'Z' site in this config"}

    si_apfu = apfu.get("Si", 0.0)
    si_deficiency = z.target - si_apfu
    z_deficiency = z.deficiency

    flagged = (si_deficiency > threshold) and (z_deficiency > threshold * 0.5)
    return {
        "flag": flagged,
        "si_deficiency": si_deficiency,
        "z_site_deficiency": z_deficiency,
    }


def check_cation_anion_ratio(
    config: MineralConfig,
    apfu: dict[str, float],
    site_allocation: SiteAllocationResult,
    redox_result: RedoxResult | None,
) -> dict[str, Any]:
    """Real measured cation-total : anion-total apfu ratio (``config.
    normalization_excludes``' elements, e.g. S/As/Sb, vs everything else).

    Basis-invariant -- ``apfu`` is a uniformly-scaled dict regardless of
    which basis produced it, so this ratio is the same real physical value
    whether ``apfu`` came from cation-, oxygen-, or anion-basis
    normalization. That's what makes it useful as a first-pass mineral
    classifier on the generic ``sulfide.yaml`` config, *before* committing
    to any specific formula's target: ~1:1 suggests a monosulfide, ~1:2
    pyrite-type, ~9:8 pentlandite-type, etc.
    """
    excludes = set(config.normalization_excludes)
    anion_total = sum(v for el, v in apfu.items() if el in excludes)
    cation_total = sum(v for el, v in apfu.items() if el not in excludes)
    ratio = cation_total / anion_total if anion_total > 0 else float("nan")
    return {"cation_total": cation_total, "anion_total": anion_total, "cation_to_anion_ratio": ratio}


_CHECKS = {
    "hydrogarnet_substitution": check_hydrogarnet_substitution,
    "cation_anion_ratio": check_cation_anion_ratio,
}


def run_qc_checks(
    config: MineralConfig,
    apfu: dict[str, float],
    site_allocation: SiteAllocationResult,
    redox_result: RedoxResult | None,
) -> dict[str, Any]:
    """Run every check named in ``config.qc_checks`` and collect results,
    plus the always-available site-total and charge-balance diagnostics.

    Returns
    -------
    dict
        ``{'site_totals': {name: {'total','target','deficiency'}}, ...checks by name}``.
        If ``redox_result`` is given, also includes ``'S'``, ``'T'``, ``'charge_balance_residual'``.
    """
    result: dict[str, Any] = {
        "site_totals": {
            name: {"total": s.total, "target": s.target, "deficiency": s.deficiency}
            for name, s in site_allocation.sites.items()
        }
    }
    if redox_result is not None:
        result["S"] = redox_result.S
        result["T"] = redox_result.T
        result["charge_balance_residual"] = redox_result.residual

    for name in config.qc_checks:
        fn = _CHECKS.get(name)
        if fn is None:
            raise ValueError(f"Unknown QC check {name!r}; expected one of {sorted(_CHECKS)}.")
        result[name] = fn(config, apfu, site_allocation, redox_result)

    return result
