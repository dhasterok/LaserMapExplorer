"""End-member decomposition from site occupancies.

Kept as its own dispatch-by-name module (not part of ``sites.py``) so a
different mineral/method can be plugged in later without touching site
allocation. ``locock_2008`` is a simplified, garnet-specific implementation
of the Locock (2008) X-site/Y-site cation-proportion method covering the
six major pyralspite/ugrandite end-members -- it does not implement
Locock's additional minor end-members (majorite, knorringite, goldmanite,
kimzeyite, etc.), which is an acceptable Phase 1/garnet-only simplification.

Unlike ``config.py``/``sites.py`` (which never assume specific site names),
this function *does* assume garnet's conventional site names ('X'
dodecahedral, 'Y' octahedral) -- that's expected here, since a named
end-member method is inherently mineral-specific.
"""
from __future__ import annotations

from src.stoichiometry.config import MineralConfig
from src.stoichiometry.sites import SiteAllocationResult


def _locock_2008_garnet(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    x_site = site_allocation.sites.get("X")
    y_site = site_allocation.sites.get("Y")
    if x_site is None or y_site is None:
        raise ValueError("locock_2008 garnet end-member calculation requires 'X' and 'Y' sites in the config.")

    ca = x_site.elements.get("Ca", 0.0)
    mg = x_site.elements.get("Mg", 0.0)
    fe2 = x_site.elements.get("Fe2", 0.0)
    mn = x_site.elements.get("Mn", 0.0)
    x_divalent_total = ca + mg + fe2 + mn

    if x_divalent_total <= 0:
        return {member: 0.0 for member in config.end_members.members}

    pyrope = mg / x_divalent_total
    almandine = fe2 / x_divalent_total
    spessartine = mn / x_divalent_total
    ca_fraction = ca / x_divalent_total

    al_y = y_site.elements.get("Al", 0.0)
    fe3_y = y_site.elements.get("Fe3", 0.0)
    cr_y = y_site.elements.get("Cr", 0.0)
    y_trivalent_total = al_y + fe3_y + cr_y

    if y_trivalent_total > 0:
        grossular = ca_fraction * (al_y / y_trivalent_total)
        andradite = ca_fraction * (fe3_y / y_trivalent_total)
        uvarovite = ca_fraction * (cr_y / y_trivalent_total)
    else:
        grossular = andradite = uvarovite = 0.0

    fractions = {
        "pyrope": pyrope, "almandine": almandine, "spessartine": spessartine,
        "grossular": grossular, "andradite": andradite, "uvarovite": uvarovite,
    }
    total = sum(fractions.values())
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}

    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


_METHODS = {"locock_2008": _locock_2008_garnet}


def compute_end_members(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Compute end-member mol% (summing to 100) per ``config.end_members.method``."""
    method = config.end_members.method
    fn = _METHODS.get(method)
    if fn is None:
        raise ValueError(f"Unknown end-member method {method!r}; expected one of {sorted(_METHODS)}.")
    return fn(site_allocation, config)
