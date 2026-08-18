"""Crystallographic site allocation from apfu values and a mineral config.

Generic priority-fill algorithm -- no site names/counts are hardcoded. Sites
are filled in the order they appear in the config (``config.site_order``);
within a site, elements are filled in that site's ``priority`` order. An
element shared between sites (e.g. Al in both Z and Y for garnet) naturally
"spills" to the next site that lists it once the earlier site's target is
met or the element runs out -- each site only draws from whatever's left in
a shared running pool.

An element is only capped at a site's remaining target space if some *later*
site in ``site_order`` also lists it -- i.e. it's genuinely shared and can
still be picked up downstream. If this is an element's only or last eligible
site, it's assigned in full even if that pushes the site's total past its
target. This matches MinPlotX's reference behavior (e.g. its garnet model:
Ti/Cr are always fully assigned to the octahedral site, never capped, since
no other site can hold them) and avoids silently discarding real
composition -- a hard cap-everywhere rule would drop e.g. Mn entirely
whenever Ca+Mg+Fe2+ alone already fill the X site.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.stoichiometry.config import MineralConfig


@dataclass
class SiteResult:
    name: str
    target: float
    total: float
    elements: dict[str, float]
    deficiency: float = field(init=False)  # target - total; negative means over-full

    def __post_init__(self):
        self.deficiency = self.target - self.total


@dataclass
class SiteAllocationResult:
    sites: dict[str, SiteResult]
    unallocated: dict[str, float]  # apfu left over after all sites are filled


def allocate_sites(apfu: dict[str, float], config: MineralConfig) -> SiteAllocationResult:
    """Allocate cation apfu to sites, dispatched by ``config.site_method``.

    Parameters
    ----------
    apfu : dict[str, float]
        Cation element/species (e.g. 'Fe2', 'Fe3') -> apfu. Redox-sensitive
        elements must already be split (see ``redox.estimate_fe_split``) --
        site element lists reference species like 'Fe2'/'Fe3', not 'Fe'.
    config : MineralConfig

    Returns
    -------
    SiteAllocationResult
    """
    fn = _SITE_METHODS.get(config.site_method)
    if fn is None:
        raise ValueError(f"Unknown site allocation method {config.site_method!r}; expected one of {sorted(_SITE_METHODS)}.")
    return fn(apfu, config)


def _allocate_priority_fill(apfu: dict[str, float], config: MineralConfig) -> SiteAllocationResult:
    """Generic priority-fill: the default for every mineral that doesn't set
    ``site_allocation.method`` in its config (see this module's docstring).
    """
    remaining = dict(apfu)
    site_results: dict[str, SiteResult] = {}
    site_order = config.site_order

    def has_later_site(el: str, idx: int) -> bool:
        return any(el in config.sites[later].elements for later in site_order[idx + 1:])

    for idx, site_name in enumerate(site_order):
        site = config.sites[site_name]
        site_total = 0.0
        site_elements: dict[str, float] = {}

        for el in site.priority:
            available = remaining.get(el, 0.0)
            if available <= 0:
                continue
            if has_later_site(el, idx):
                needed = site.target - site_total
                if needed <= 0:
                    continue  # not "break": later, uncapped elements in this site's priority list must still be considered
                take = min(available, needed)
            else:
                take = available  # this element's only/last eligible site -- take all of it, uncapped
            site_elements[el] = site_elements.get(el, 0.0) + take
            remaining[el] = available - take
            site_total += take

        site_results[site_name] = SiteResult(
            name=site_name, target=site.target, total=site_total, elements=site_elements
        )

    unallocated = {el: v for el, v in remaining.items() if v > 1e-12}
    return SiteAllocationResult(sites=site_results, unallocated=unallocated)


def _allocate_pyroxene_quad(apfu: dict[str, float], config: MineralConfig) -> SiteAllocationResult:
    """Pyroxene-specific (ports MinPlotX's ``pyroxene_fe3unknown.m``).

    T fills the same way the generic engine would (Si capped at target, then
    Al/Fe3+ spillover). M1 takes Ti/Cr/Mn/Al-remainder/Fe3-remainder in full
    (unconditional -- no other site claims them), then splits Mg and Fe2+ by
    the bulk ``XMg = Mg/(Mg+Fe2)`` ratio rather than "fill M1 to target
    first" -- this keeps Mg/Fe2+ distributed between M1 and M2 in proportion
    to bulk composition instead of concentrating one in M1. M2 (last site)
    takes whatever Mg/Fe2+ remain plus Ca/Na/K in full.

    Unlike MinPlotX's own code (which simply caps Si at T's target and
    doesn't track any excess beyond it), Si in excess of T's target ends up
    in ``unallocated`` here rather than silently vanishing -- consistent
    with this package's "never discard real composition" rule (see this
    module's docstring) for the rare, physically unusual case where a
    pyroxene has more than 2 apfu Si.
    """
    def g(el: str) -> float:
        return apfu.get(el, 0.0)

    t_target = config.sites["T"].target
    m1_target = config.sites["M1"].target
    m2_target = config.sites["M2"].target

    si_t = min(g("Si"), t_target)
    al_t = max(0.0, min(g("Al"), t_target - si_t))
    fe3_t = max(0.0, min(g("Fe3"), t_target - si_t - al_t))
    t_elements = {k: v for k, v in {"Si": si_t, "Al": al_t, "Fe3": fe3_t}.items() if v > 0}
    t_total = si_t + al_t + fe3_t

    al_m1 = g("Al") - al_t
    ti_m1 = g("Ti")
    cr_m1 = g("Cr")
    fe3_m1 = g("Fe3") - fe3_t
    mn_m1 = g("Mn")
    sum_before_mg = al_m1 + ti_m1 + cr_m1 + fe3_m1 + mn_m1

    mg_total, fe2_total = g("Mg"), g("Fe2")
    x_mg = mg_total / (mg_total + fe2_total) if (mg_total + fe2_total) > 0 else 0.0
    candidate_mg = x_mg * (m1_target - sum_before_mg)
    mg_m1 = max(0.0, candidate_mg if candidate_mg < mg_total else mg_total)

    remaining_m1_space = m1_target - (sum_before_mg + mg_m1)
    fe2_m1 = min(fe2_total, remaining_m1_space) if remaining_m1_space > 0 else 0.0

    m1_elements = {k: v for k, v in {
        "Al": al_m1, "Ti": ti_m1, "Cr": cr_m1, "Fe3": fe3_m1,
        "Mn": mn_m1, "Mg": mg_m1, "Fe2": fe2_m1,
    }.items() if v > 0}
    m1_total = sum(m1_elements.values())

    mg_m2 = max(0.0, mg_total - mg_m1)
    fe2_m2 = max(0.0, fe2_total - fe2_m1)
    m2_elements = {k: v for k, v in {
        "Mg": mg_m2, "Fe2": fe2_m2, "Ca": g("Ca"), "Na": g("Na"), "K": g("K"),
    }.items() if v > 0}
    m2_total = sum(m2_elements.values())

    site_results = {
        "T": SiteResult(name="T", target=t_target, total=t_total, elements=t_elements),
        "M1": SiteResult(name="M1", target=m1_target, total=m1_total, elements=m1_elements),
        "M2": SiteResult(name="M2", target=m2_target, total=m2_total, elements=m2_elements),
    }
    allocated = {
        "Si": si_t, "Al": al_t + al_m1, "Fe3": fe3_t + fe3_m1, "Ti": ti_m1, "Cr": cr_m1,
        "Mn": mn_m1, "Mg": mg_m1 + mg_m2, "Fe2": fe2_m1 + fe2_m2, "Ca": g("Ca"), "Na": g("Na"), "K": g("K"),
    }
    unallocated = {el: v - allocated.get(el, 0.0) for el, v in apfu.items()}
    unallocated = {el: v for el, v in unallocated.items() if v > 1e-9}

    return SiteAllocationResult(sites=site_results, unallocated=unallocated)


def _allocate_spinel_xmg(apfu: dict[str, float], config: MineralConfig) -> SiteAllocationResult:
    """Spinel-specific (ports MinPlotX's ``spinel_Fe3unknown.m``).

    Al/V/Cr/Fe3+ always fill D (octahedral) in full, and Si/Ti/Ni/Zn/Co/Mn
    always fill A (tetrahedral) in full -- none of these are shared between
    the two sites. Fe2+/Mg *are* shared, and are equipartitioned between D
    and A by the bulk ``XFe``/``XMg`` ratio, scaled by how much Si+Ti already
    occupies A (mirroring pyroxene's Mg/Fe2+ split, same rationale).
    """
    def g(el: str) -> float:
        return apfu.get(el, 0.0)

    d_target = config.sites["D"].target
    a_target = config.sites["A"].target

    al_d, v_d, cr_d, fe3_d = g("Al"), g("V"), g("Cr"), g("Fe3")

    mg_total, fe2_total = g("Mg"), g("Fe2")
    si_ti = g("Si") + g("Ti")
    divalent_total = mg_total + fe2_total
    x_mg = mg_total / divalent_total if divalent_total > 0 else 0.0
    x_fe = 1.0 - x_mg if divalent_total > 0 else 0.0

    if si_ti > 0:
        if si_ti >= divalent_total:
            fe2_d, mg_d = fe2_total, mg_total
        else:
            fe2_d, mg_d = si_ti * x_fe, si_ti * x_mg
    else:
        fe2_d, mg_d = 0.0, 0.0

    d_elements = {k: v for k, v in {
        "Al": al_d, "V": v_d, "Cr": cr_d, "Fe3": fe3_d, "Fe2": fe2_d, "Mg": mg_d,
    }.items() if v > 0}
    d_total = sum(d_elements.values())

    a_elements = {k: v for k, v in {
        "Si": g("Si"), "Ti": g("Ti"), "Ni": g("Ni"), "Zn": g("Zn"), "Co": g("Co"),
        "Mn": g("Mn"), "Fe2": max(0.0, fe2_total - fe2_d), "Mg": max(0.0, mg_total - mg_d),
    }.items() if v > 0}
    a_total = sum(a_elements.values())

    site_results = {
        "D": SiteResult(name="D", target=d_target, total=d_total, elements=d_elements),
        "A": SiteResult(name="A", target=a_target, total=a_total, elements=a_elements),
    }
    allocated: dict[str, float] = {}
    for elements in (d_elements, a_elements):
        for el, v in elements.items():
            allocated[el] = allocated.get(el, 0.0) + v
    unallocated = {el: v - allocated.get(el, 0.0) for el, v in apfu.items()}
    unallocated = {el: v for el, v in unallocated.items() if v > 1e-9}

    return SiteAllocationResult(sites=site_results, unallocated=unallocated)


def _allocate_tetra_fe3_ratio(apfu: dict[str, float], config: MineralConfig) -> SiteAllocationResult:
    """Sheet-silicate T/M(/...) split (serpentine, talc, chlorite, mica;
    ports their shared MinPlotX pattern). Si is T-exclusive (uncapped).
    Fe3+ is split between T and M by a *fixed* fraction
    (``config.tetra_fe3_ratio``), not by remaining site space -- a third
    apportionment mechanism alongside capped-spillover and equipartition.
    Al fills whatever T space is left after Si/Fe3+, with the remainder
    spilling to M. M takes the Al/Fe3+ remainders plus everything else in
    its own ``elements`` list, uncapped -- read from config rather than
    hardcoded, since these minerals' M-site element lists differ (talc adds
    Na/K, mica's is larger still).

    Any sites after M (e.g. mica's interlayer "I") are treated as fully
    independent of T/M -- each just takes whatever's left of its own
    ``elements`` list, unconditional. This assumes such trailing sites
    share no elements with T/M (true for every mineral using this method
    so far); a mineral that needed real spillover into a third site would
    need its own dedicated function instead.
    """
    def g(el: str) -> float:
        return apfu.get(el, 0.0)

    site_names = config.site_order
    t_name, m_name = site_names[0], site_names[1]
    t_cfg, m_cfg = config.sites[t_name], config.sites[m_name]

    si_t = g("Si")
    fe3_total = g("Fe3")
    fe3_t = fe3_total * config.tetra_fe3_ratio
    al_t = max(0.0, min(g("Al"), t_cfg.target - si_t - fe3_t))
    t_elements = {k: v for k, v in {"Si": si_t, "Fe3": fe3_t, "Al": al_t}.items() if v > 0}
    t_total = si_t + fe3_t + al_t

    m_elements = {"Al": g("Al") - al_t, "Fe3": fe3_total - fe3_t}
    for el in m_cfg.elements:
        if el not in ("Al", "Fe3"):
            m_elements[el] = g(el)
    m_elements = {k: v for k, v in m_elements.items() if v > 0}
    m_total = sum(m_elements.values())

    site_results = {
        t_name: SiteResult(name=t_name, target=t_cfg.target, total=t_total, elements=t_elements),
        m_name: SiteResult(name=m_name, target=m_cfg.target, total=m_total, elements=m_elements),
    }
    allocated = dict(t_elements)
    for el, v in m_elements.items():
        allocated[el] = allocated.get(el, 0.0) + v

    # Trailing independent sites (mica's interlayer "I", etc).
    for extra_name in site_names[2:]:
        extra_cfg = config.sites[extra_name]
        extra_elements = {el: g(el) for el in extra_cfg.elements if g(el) > 0}
        site_results[extra_name] = SiteResult(
            name=extra_name, target=extra_cfg.target, total=sum(extra_elements.values()), elements=extra_elements
        )
        for el, v in extra_elements.items():
            allocated[el] = allocated.get(el, 0.0) + v

    unallocated = {el: v - allocated.get(el, 0.0) for el, v in apfu.items()}
    unallocated = {el: v for el, v in unallocated.items() if v > 1e-9}

    return SiteAllocationResult(sites=site_results, unallocated=unallocated)


def _allocate_equipart(apfu: dict[str, float], config: MineralConfig) -> SiteAllocationResult:
    """Generic T/M/A equipartition pattern (epidote, allanite -- both
    epidote-group minerals with the same crystal-chemical shape). Assumes
    exactly 3 sites in ``config.site_order``:

    - First site ("T"): ordinary priority-fill-with-cap, same rule as
      ``_allocate_priority_fill`` (an element is capped only if a later
      site -- M or A -- also lists it).
    - Second site ("M"): elements exclusive to M (not also in A's list) are
      unconditional (taken in full, however much that leaves M over or
      under its target); elements *shared* with A -- e.g. Fe2+/Mn2+/Mg --
      are equipartitioned by their bulk ratio, scaled by whatever M-space
      remains after the unconditional ones (capped at 1, i.e. "all of it",
      once M-space exceeds the shared total) -- the 3-way analogue of
      pyroxene's Mg/Fe2+ M1/M2 split (see ``_allocate_pyroxene_quad``).
    - Third site ("A", last, uncapped): whatever's left of the
      equipartitioned elements, plus everything else in A's own list,
      unconditional.

    Which M elements are "equipartitioned" vs "unconditional" is inferred
    from config (an element in both M's and A's ``elements`` list is
    equipartitioned), not hardcoded -- so this one function serves any
    mineral with this same 3-site shape, whatever the exact element lists.
    """
    site_names = config.site_order
    if len(site_names) != 3:
        raise ValueError(f"'equipart' site method requires exactly 3 sites, got {site_names}.")
    t_name, m_name, a_name = site_names
    t_cfg, m_cfg, a_cfg = config.sites[t_name], config.sites[m_name], config.sites[a_name]

    remaining = dict(apfu)

    # T: ordinary priority-fill-with-cap.
    t_elements: dict[str, float] = {}
    t_total = 0.0
    for el in t_cfg.priority:
        available = remaining.get(el, 0.0)
        if available <= 0:
            continue
        if el in m_cfg.elements or el in a_cfg.elements:
            needed = t_cfg.target - t_total
            if needed <= 0:
                continue
            take = min(available, needed)
        else:
            take = available
        t_elements[el] = t_elements.get(el, 0.0) + take
        remaining[el] = available - take
        t_total += take

    # M: elements exclusive to M are unconditional; elements shared with A
    # are equipartitioned by bulk ratio, scaled by remaining M-space.
    equipart_elements = [el for el in m_cfg.elements if el in a_cfg.elements]
    unconditional_elements = [el for el in m_cfg.elements if el not in equipart_elements]

    m_elements: dict[str, float] = {}
    for el in unconditional_elements:
        v = remaining.get(el, 0.0)
        if v > 0:
            m_elements[el] = v
            remaining[el] = 0.0
    m_fixed_total = sum(m_elements.values())

    equipart_totals = {el: remaining.get(el, 0.0) for el in equipart_elements}
    divalent_total = sum(equipart_totals.values())
    m_remaining_space = max(0.0, m_cfg.target - m_fixed_total)
    share = min(m_remaining_space, divalent_total) / divalent_total if divalent_total > 0 else 0.0
    for el, total in equipart_totals.items():
        take = total * share
        if take > 0:
            m_elements[el] = m_elements.get(el, 0.0) + take
            remaining[el] = total - take
    m_total = sum(m_elements.values())

    # A (last, uncapped): equipartitioned-element leftovers, plus everything
    # else in A's own list, unconditional.
    a_elements: dict[str, float] = {}
    for el in a_cfg.elements:
        v = remaining.get(el, 0.0)
        if v > 0:
            a_elements[el] = v
            remaining[el] = 0.0
    a_total = sum(a_elements.values())

    site_results = {
        t_name: SiteResult(name=t_name, target=t_cfg.target, total=t_total, elements=t_elements),
        m_name: SiteResult(name=m_name, target=m_cfg.target, total=m_total, elements=m_elements),
        a_name: SiteResult(name=a_name, target=a_cfg.target, total=a_total, elements=a_elements),
    }
    unallocated = {el: v for el, v in remaining.items() if v > 1e-9}
    return SiteAllocationResult(sites=site_results, unallocated=unallocated)


_SITE_METHODS = {
    "priority_fill": _allocate_priority_fill,
    "pyroxene_quad": _allocate_pyroxene_quad,
    "spinel_xmg": _allocate_spinel_xmg,
    "tetra_fe3_ratio": _allocate_tetra_fe3_ratio,
    "equipart": _allocate_equipart,
}
