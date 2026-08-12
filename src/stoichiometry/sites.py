"""Crystallographic site allocation from apfu values and a mineral config.

Generic priority-fill algorithm -- no site names/counts are hardcoded. Sites
are filled in the order they appear in the config (``config.site_order``);
within a site, elements are filled in that site's ``priority`` order. An
element shared between sites (e.g. Al in both Z and Y for garnet) naturally
"spills" to the next site that lists it once the earlier site's target is
met or the element runs out -- each site only draws from whatever's left in
a shared running pool.
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
    """Allocate cation apfu to sites per the config's fill priority.

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
    remaining = dict(apfu)
    site_results: dict[str, SiteResult] = {}

    for site_name in config.site_order:
        site = config.sites[site_name]
        site_total = 0.0
        site_elements: dict[str, float] = {}

        for el in site.priority:
            available = remaining.get(el, 0.0)
            if available <= 0:
                continue
            needed = site.target - site_total
            if needed <= 0:
                break
            take = min(available, needed)
            site_elements[el] = site_elements.get(el, 0.0) + take
            remaining[el] = available - take
            site_total += take

        site_results[site_name] = SiteResult(
            name=site_name, target=site.target, total=site_total, elements=site_elements
        )

    unallocated = {el: v for el, v in remaining.items() if v > 1e-12}
    return SiteAllocationResult(sites=site_results, unallocated=unallocated)
