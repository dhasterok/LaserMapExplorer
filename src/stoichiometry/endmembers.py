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


def _site_total(site_allocation: SiteAllocationResult, el: str) -> float:
    """Sum of ``el``'s apfu across every site it ended up in."""
    return sum(s.elements.get(el, 0.0) for s in site_allocation.sites.values())


def _olivine_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    mg = _site_total(site_allocation, "Mg")
    fe = _site_total(site_allocation, "Fe2") + _site_total(site_allocation, "Fe3")
    mn = _site_total(site_allocation, "Mn")
    ca = _site_total(site_allocation, "Ca")
    total = mg + fe + mn + ca
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}

    fractions = {"forsterite": mg, "fayalite": fe, "tephroite": mn, "ca_olivine": ca}
    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


def _feldspar_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """An/Ab/Or from Ca/Na/K ratios only -- Mg/Fe2+/etc. (present in the A
    site's apfu total) are deliberately excluded, matching the workbook's own
    "*based on Ca, Na, K ratios only" note and ``feldspar_MinPlotX.m``.
    """
    ca = _site_total(site_allocation, "Ca")
    na = _site_total(site_allocation, "Na")
    k = _site_total(site_allocation, "K")
    total = ca + na + k
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}

    fractions = {"anorthite": ca, "albite": na, "orthoclase": k}
    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


def _pyroxene_quad(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Wo/En/Fs quadrilateral only (the "ortho and calcic pyroxene" branch of
    ``pyroxene_fe3unknown.m``) -- the Na-endmember (jadeite/aegirine/
    kosmochlor) branch isn't implemented; the reference sample used to
    validate this has no Na to check it against anyway.
    """
    ca = _site_total(site_allocation, "Ca")
    mg = _site_total(site_allocation, "Mg")
    fe = _site_total(site_allocation, "Fe2") + _site_total(site_allocation, "Mn") + _site_total(site_allocation, "Fe3")
    total = ca + mg + fe
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}

    fractions = {"wollastonite": ca, "enstatite": mg, "ferrosilite": fe}
    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


def _spinel_xmg(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Ports ``spinel_Fe3unknown.m``'s end-member scheme: D-site trivalent
    fraction (Cr/Fe3+/Al/V) times A-site divalent fraction (Fe2+/Mg/Mn/Ni/
    Zn/Co) for 24 "normal spinel" members, plus 4 Si/Ti ulvospinel-group
    members (Si or Ti, which always sit in A, paired with the bulk Fe/Mg
    split). Member names are systematic (``{trivalent}_{divalent}``) except
    where a name is well-established and unambiguous (e.g. chromite,
    magnetite, hercynite, spinel, coulsonite and their Mg-analogues, and the
    four ulvospinel-group members) -- this avoids guessing at obscure/rare
    end-member names (e.g. Co- or Zn-bearing chromite/coulsonite variants)
    that aren't confidently attributable to a specific accepted mineral name.
    """
    d = site_allocation.sites.get("D")
    a = site_allocation.sites.get("A")
    if d is None or a is None:
        raise ValueError("spinel_xmg end-member calculation requires 'D' and 'A' sites in the config.")

    trivalent = {"cr": d.elements.get("Cr", 0.0), "fe3": d.elements.get("Fe3", 0.0),
                 "al": d.elements.get("Al", 0.0), "v": d.elements.get("V", 0.0)}
    d_total = sum(trivalent.values()) + d.elements.get("Fe2", 0.0) + d.elements.get("Mg", 0.0)
    x_trivalent = {k: (v / d_total if d_total > 0 else 0.0) for k, v in trivalent.items()}
    x_ulv_group = 1.0 - sum(x_trivalent.values()) if d_total > 0 else 0.0  # D's Fe2+/Mg fraction

    divalent = {"fe2": a.elements.get("Fe2", 0.0), "mg": a.elements.get("Mg", 0.0),
                "mn": a.elements.get("Mn", 0.0), "ni": a.elements.get("Ni", 0.0),
                "zn": a.elements.get("Zn", 0.0), "co": a.elements.get("Co", 0.0)}
    a_divalent_total = sum(divalent.values())
    x_divalent = {k: (v / a_divalent_total if a_divalent_total > 0 else 0.0) for k, v in divalent.items()}

    # Systematic-name (trivalent_divalent) -> common name, where confidently known.
    _COMMON_NAMES = {
        "cr_fe2": "chromite", "cr_mg": "magnesiochromite",
        "fe3_fe2": "magnetite", "fe3_mg": "magnesioferrite", "fe3_mn": "jacobsite",
        "fe3_ni": "trevorite", "fe3_zn": "franklinite",
        "al_fe2": "hercynite", "al_mg": "spinel", "al_mn": "galaxite", "al_zn": "gahnite",
        "v_fe2": "coulsonite", "v_mg": "magnesiocoulsonite",
    }
    fractions: dict[str, float] = {}
    for tri_key, tri_x in x_trivalent.items():
        for di_key, di_x in x_divalent.items():
            systematic = f"{tri_key}_{di_key}"
            name = _COMMON_NAMES.get(systematic, systematic)
            fractions[name] = tri_x * di_x

    si_total = _site_total(site_allocation, "Si")
    ti_total = _site_total(site_allocation, "Ti")
    si_ti_total = si_total + ti_total
    x_si = si_total / si_ti_total if si_ti_total > 0 else 0.0
    x_ti = 1.0 - x_si if si_ti_total > 0 else 0.0

    mg_total = _site_total(site_allocation, "Mg")
    fe2_total = _site_total(site_allocation, "Fe2")
    bulk_divalent_total = mg_total + fe2_total
    x_bulk_mg = mg_total / bulk_divalent_total if bulk_divalent_total > 0 else 0.0
    x_bulk_fe = 1.0 - x_bulk_mg if bulk_divalent_total > 0 else 0.0

    fractions["ahrensite"] = x_ulv_group * x_si * x_bulk_fe
    fractions["ringwoodite"] = x_ulv_group * x_si * x_bulk_mg
    fractions["ulvospinel"] = x_ulv_group * x_ti * x_bulk_fe
    fractions["qandilite"] = x_ulv_group * x_ti * x_bulk_mg

    total = sum(fractions.values())
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}
    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


def _xmg_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Single-member Mg/(Mg+Fe2+) ratio -- chloritoid/cordierite/chlorite's
    only "end-member"-like output in MinPlotX (no named mineral end-members,
    just this one diagnostic ratio). Reads across every site, since which
    site actually holds Mg/Fe2+ varies by mineral (cordierite's octahedral
    site, chloritoid's L1, etc.) and this ratio doesn't care which.
    """
    mg = _site_total(site_allocation, "Mg")
    fe2 = _site_total(site_allocation, "Fe2")
    denom = mg + fe2
    if denom <= 0:
        return {member: 0.0 for member in config.end_members.members}
    return {member: 100.0 * mg / denom for member in config.end_members.members}


def _ilmenite_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Two-tier: hematite fraction of the (Fe3+Ti) pool, then the remainder
    partitioned by Fe2+/Mn/Mg (ilmenite/pyrophanite/geikielite).
    """
    ti = _site_total(site_allocation, "Ti")
    fe3 = _site_total(site_allocation, "Fe3")
    fe2 = _site_total(site_allocation, "Fe2")
    mn = _site_total(site_allocation, "Mn")
    mg = _site_total(site_allocation, "Mg")

    ti_fe3_total = ti + fe3
    x_hematite = fe3 / ti_fe3_total if ti_fe3_total > 0 else 0.0
    x_il_gk_py = 1.0 - x_hematite if ti_fe3_total > 0 else 0.0

    divalent_total = fe2 + mn + mg
    x_ilmenite = x_il_gk_py * (fe2 / divalent_total) if divalent_total > 0 else 0.0
    x_pyrophanite = x_il_gk_py * (mn / divalent_total) if divalent_total > 0 else 0.0
    x_geikielite = x_il_gk_py * (mg / divalent_total) if divalent_total > 0 else 0.0

    fractions = {
        "hematite": x_hematite, "ilmenite": x_ilmenite,
        "pyrophanite": x_pyrophanite, "geikielite": x_geikielite,
    }
    total = sum(fractions.values())
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}
    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


def _lawsonite_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Single member, a product of two site fractions (not a simple ratio):
    (Al fraction of the M site) x (Ca fraction of the A site).
    """
    m_site = site_allocation.sites.get("M")
    a_site = site_allocation.sites.get("A")
    if m_site is None or a_site is None:
        raise ValueError("lawsonite_ratio end-member calculation requires 'M' and 'A' sites in the config.")
    al_fraction = (m_site.elements.get("Al", 0.0) / m_site.total) if m_site.total > 0 else 0.0
    ca_fraction = (a_site.elements.get("Ca", 0.0) / a_site.total) if a_site.total > 0 else 0.0
    return {member: 100.0 * al_fraction * ca_fraction for member in config.end_members.members}


def _epidote_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Clinozoisite/epidote/Cr-epidote from the M site's trivalent pool
    (Al/Cr/Fe3+), minus the 2 apfu of Al that's always present as a
    structural baseline. Piemontite (the Mn3+ analogue) is dropped -- Mn3+
    isn't modeled in this batch (see module docstring / config docstring),
    so all Mn is Mn2+ and there's no Mn3+ pool to compute it from.
    """
    m_site = site_allocation.sites.get("M")
    if m_site is None:
        raise ValueError("epidote_ratio end-member calculation requires an 'M' site in the config.")
    al = m_site.elements.get("Al", 0.0)
    cr = m_site.elements.get("Cr", 0.0)
    fe3 = m_site.elements.get("Fe3", 0.0)
    denom = al + cr + fe3 - 2.0
    if denom <= 0:
        return {member: 0.0 for member in config.end_members.members}
    fractions = {"clinozoisite": al - 2.0, "epidote": fe3, "cr_epidote": cr}
    return {member: 100.0 * max(fractions.get(member, 0.0), 0.0) / denom for member in config.end_members.members}


def _scapolite_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Two independent flat ratios off raw apfu -- scapolite has a single
    site in this config, so this is equivalent to using apfu directly.
    """
    al = _site_total(site_allocation, "Al")
    ca = _site_total(site_allocation, "Ca")
    mg = _site_total(site_allocation, "Mg")
    sr = _site_total(site_allocation, "Sr")
    ba = _site_total(site_allocation, "Ba")
    mn = _site_total(site_allocation, "Mn")
    fe = _site_total(site_allocation, "Fe")  # scapolite has no redox split -- plain 'Fe', not 'Fe2'/'Fe3'
    fractions = {
        "eq_anorthite": max((al - 3.0) / 3.0, 0.0),
        "meionite_divalent": max((ca + mg + sr + ba + mn + fe) / 4.0, 0.0),
    }
    return {member: 100.0 * fractions.get(member, 0.0) for member in config.end_members.members}


def _titanite_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Single member: Ti's fraction of the octahedral site."""
    oct_site = site_allocation.sites.get("Oct")
    if oct_site is None:
        raise ValueError("titanite_ratio end-member calculation requires an 'Oct' site in the config.")
    if oct_site.total <= 0:
        return {member: 0.0 for member in config.end_members.members}
    return {member: 100.0 * oct_site.elements.get("Ti", 0.0) / oct_site.total for member in config.end_members.members}


def _monazite_huttonite_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Monazite/huttonite mole fraction straight from the T site's P:Si
    split. The huttonite substitution (REE3+ + P5+ = Th4+ + Si4+) pairs Si
    1:1 with Th at the T/A sites respectively, so T's own P vs. Si occupancy
    already *is* the monazite:huttonite ratio -- same "read one site's own
    occupancy fraction" shape as ``_titanite_ratio``, just with two named
    members instead of one.
    """
    t_site = site_allocation.sites.get("T")
    if t_site is None:
        raise ValueError("monazite_huttonite_ratio end-member calculation requires a 'T' site in the config.")
    if t_site.total <= 0:
        return {member: 0.0 for member in config.end_members.members}
    fractions = {"monazite": t_site.elements.get("P", 0.0), "huttonite": t_site.elements.get("Si", 0.0)}
    return {member: 100.0 * fractions.get(member, 0.0) / t_site.total for member in config.end_members.members}


def _mica_cascade(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Mica's cascading di/trioctahedral classification (ports MinPlotX's
    scheme). Not a flat ratio like every other end-member method here --
    a sequence of nested splits, each producing a fraction of what the
    previous split left over:

    1. Tri- vs di-octahedral, from the M site's total occupancy (M
       under-filled toward 2 -> dioctahedral; toward 3 -> trioctahedral;
       linearly blended in between via ``clamp(M_total - 2, 0, 1)``).
    2. Within the dioctahedral share: celadonite-group (Fe3+/Al-Tschermak
       substitution) vs. "true mica" group (muscovite/margarite/
       paragonite/pyrophyllite), from the M site's trivalent (Al+Fe3+)
       occupancy relative to its ideal value of 1.
          - Celadonite group splits Fe3+-celadonite vs. Al-celadonite by
            the M site's Fe3+:Al ratio.
          - True-mica group splits into charged (K/Na/Ca-bearing:
            muscovite/paragonite/margarite) vs. vacant-interlayer
            (pyrophyllite), then the charged portion splits by the
            interlayer site's K:Na:Ca ratio.
    3. Within the trioctahedral share: Mg-Al-Tschermak-free
       (phlogopite/annite) vs. Al-Tschermak-substituted
       (eastonite/siderophyllite) pairs, from the T site's Si occupancy
       relative to its ideal value of 2; each pair then splits by the M
       site's Mg:Fe2+ ratio.

    Every split's own set of fractions sums to 1 by construction, so the
    10 final members (each multiplied by its tri/di-octahedral share) sum
    to 100 overall.
    """
    t_site = site_allocation.sites.get("T")
    m_site = site_allocation.sites.get("M")
    i_site = site_allocation.sites.get("I")
    if t_site is None or m_site is None or i_site is None:
        raise ValueError("mica_cascade end-member calculation requires 'T', 'M', and 'I' sites in the config.")

    x_tri_oct = min(max(m_site.total - 2.0, 0.0), 1.0)
    x_di_oct = 1.0 - x_tri_oct

    al_m = m_site.elements.get("Al", 0.0)
    fe3_m = m_site.elements.get("Fe3", 0.0)
    fe2_m = m_site.elements.get("Fe2", 0.0)
    mg_m = m_site.elements.get("Mg", 0.0)
    si_t = t_site.elements.get("Si", 0.0)
    ca_i = i_site.elements.get("Ca", 0.0)
    na_i = i_site.elements.get("Na", 0.0)
    k_i = i_site.elements.get("K", 0.0)

    # Dioctahedral suite.
    trivalent_m = al_m + fe3_m
    x_msum = min(max(trivalent_m - 1.0, 0.0), 1.0)  # "true mica" (charged + vacant) fraction
    x_celtot = 1.0 - x_msum  # celadonite-group fraction
    x_fe3cel = fe3_m / trivalent_m if trivalent_m > 0 else 0.0
    x_celadonite = x_fe3cel * x_celtot
    x_al_celadonite = x_celtot - x_celadonite

    interlayer_total = ca_i + na_i + k_i
    x_charged = interlayer_total * x_msum
    x_pyrophyllite = x_msum - x_charged
    x_margarite = x_charged * (ca_i / interlayer_total) if interlayer_total > 0 else 0.0
    x_paragonite = x_charged * (na_i / interlayer_total) if interlayer_total > 0 else 0.0
    x_muscovite = x_charged * (k_i / interlayer_total) if interlayer_total > 0 else 0.0

    # Trioctahedral suite.
    x_phlann = min(max(si_t - 2.0, 0.0), 1.0)  # Tschermak-free (phlogopite+annite) fraction
    x_sideast = 1.0 - x_phlann  # Al-Tschermak-substituted (siderophyllite+eastonite) fraction
    x_mg = mg_m / (mg_m + fe2_m) if (mg_m + fe2_m) > 0 else 0.0
    x_phlogopite = x_phlann * x_mg
    x_annite = x_phlann - x_phlogopite
    x_eastonite = x_sideast * x_mg
    x_siderophyllite = x_sideast - x_eastonite

    fractions = {
        "celadonite": x_di_oct * x_celadonite,
        "al_celadonite": x_di_oct * x_al_celadonite,
        "margarite": x_di_oct * x_margarite,
        "paragonite": x_di_oct * x_paragonite,
        "muscovite": x_di_oct * x_muscovite,
        "pyrophyllite": x_di_oct * x_pyrophyllite,
        "phlogopite": x_tri_oct * x_phlogopite,
        "annite": x_tri_oct * x_annite,
        "eastonite": x_tri_oct * x_eastonite,
        "siderophyllite": x_tri_oct * x_siderophyllite,
    }
    return {member: 100.0 * fractions.get(member, 0.0) for member in config.end_members.members}


def _amphibole_ca_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Two independent, continuous diagnostics for calcic/subcalcic
    amphiboles (tremolite-actinolite-ferro-actinolite-hornblende group).

    Not a discrete Leake (1997) classification -- that needs A-site Na+K,
    Ti, and a charge-balance Fe3+ estimate this port doesn't compute (see
    amphibole.yaml's redox comment: fixed_ratio only, no 13eCNK-style
    estimator). Mirrors ``_scapolite_ratio``'s "independent flat ratios"
    shape (each its own 0-100 value, not a set summing to 100) rather than
    inventing named end-members this port can't validate without a
    reference workbook.

    - mg_number: Mg/(Mg+Fe2+Mn) across the whole C+B octahedral pool --
      ~100 for tremolite, ~0 for ferro-actinolite, continuous in between
      (actinolite has no separate formula -- it's the same ratio's middle
      third by the usual Mg# 0.5/0.9 naming convention).
    - tschermak_fraction: T-site Al(iv) as a fraction of its 2 apfu ceiling
      -- 0 across the tremolite-actinolite-ferro-actinolite quadrilateral
      (Al(iv)=0), rising toward 100 for tschermakitic/hornblende-group
      compositions. Doesn't distinguish which hornblende species (edenite,
      pargasite, tschermakite, magnesio-hornblende, ...) -- same
      "quadrilateral only, no further branch" simplification as
      ``_pyroxene_quad``'s dropped Na-pyroxene branch.
    """
    t_site = site_allocation.sites.get("T")
    if t_site is None:
        raise ValueError("amphibole_ca_ratio end-member calculation requires a 'T' site in the config.")
    mg = _site_total(site_allocation, "Mg")
    fe2 = _site_total(site_allocation, "Fe2")
    mn = _site_total(site_allocation, "Mn")
    denom = mg + fe2 + mn
    mg_number = 100.0 * mg / denom if denom > 0 else 0.0
    al_t = t_site.elements.get("Al", 0.0)
    tschermak_fraction = 100.0 * min(al_t, 2.0) / 2.0
    values = {"mg_number": mg_number, "tschermak_fraction": tschermak_fraction}
    return {member: values.get(member, 0.0) for member in config.end_members.members}


def _amphibole_na_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Two independent, continuous diagnostics for sodic amphiboles
    (glaucophane-riebeckite group). Same shape/caveats as
    ``_amphibole_ca_ratio`` -- see its docstring and glaucophane.yaml.

    - mg_number: Mg/(Mg+Fe2+Mn) across the C+B octahedral pool --
      glaucophane (~100) toward ferroglaucophane (~0).
    - fe3_c_fraction: C-site Fe3+/(Al+Fe3+) -- 0 for the Al-dominant
      glaucophane/ferroglaucophane pair, 100 for the Fe3+-dominant
      riebeckite/magnesio-riebeckite pair. This port has no charge-balance
      Fe3+ estimator (redox.fixed_ratio only, default 0.0), so this stays
      0 unless the analysis is run with a nonzero fixed Fe3+ fraction --
      riebeckite/magnesio-riebeckite compositions won't show up from
      Fe-oxide-only input by default.
    """
    c_site = site_allocation.sites.get("C")
    if c_site is None:
        raise ValueError("amphibole_na_ratio end-member calculation requires a 'C' site in the config.")
    mg = _site_total(site_allocation, "Mg")
    fe2 = _site_total(site_allocation, "Fe2")
    mn = _site_total(site_allocation, "Mn")
    denom = mg + fe2 + mn
    mg_number = 100.0 * mg / denom if denom > 0 else 0.0
    al_c = c_site.elements.get("Al", 0.0)
    fe3_c = c_site.elements.get("Fe3", 0.0)
    trivalent_c = al_c + fe3_c
    fe3_c_fraction = 100.0 * fe3_c / trivalent_c if trivalent_c > 0 else 0.0
    values = {"mg_number": mg_number, "fe3_c_fraction": fe3_c_fraction}
    return {member: values.get(member, 0.0) for member in config.end_members.members}


def _carbonate_ratio(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Calcite/magnesite/siderite/rhodochrosite fractions from the single
    rhombohedral cation site -- same shape as ``_olivine_ratio`` (a
    different site, different member names, identical Mg/Fe/Mn/Ca-ratio
    math). Dolomite/ankerite compositions aren't a separate named member
    here; they show up as ~50:50 calcite:magnesite (or calcite:siderite)
    blends, consistent with how this package already reports other solid
    solutions (plagioclase's An-Ab-Or, olivine's Fo-Fa) as continuous
    end-member percentages rather than binned species names.
    """
    ca = _site_total(site_allocation, "Ca")
    mg = _site_total(site_allocation, "Mg")
    fe = _site_total(site_allocation, "Fe")  # no redox split for carbonates -- plain 'Fe', assumed Fe2+
    mn = _site_total(site_allocation, "Mn")
    total = ca + mg + fe + mn
    if total <= 0:
        return {member: 0.0 for member in config.end_members.members}
    fractions = {"calcite": ca, "magnesite": mg, "siderite": fe, "rhodochrosite": mn}
    return {member: 100.0 * fractions.get(member, 0.0) / total for member in config.end_members.members}


_METHODS = {
    "locock_2008": _locock_2008_garnet,
    "olivine_ratio": _olivine_ratio,
    "feldspar_ratio": _feldspar_ratio,
    "pyroxene_quad": _pyroxene_quad,
    "spinel_xmg": _spinel_xmg,
    "xmg_ratio": _xmg_ratio,
    "ilmenite_ratio": _ilmenite_ratio,
    "lawsonite_ratio": _lawsonite_ratio,
    "epidote_ratio": _epidote_ratio,
    "scapolite_ratio": _scapolite_ratio,
    "titanite_ratio": _titanite_ratio,
    "monazite_huttonite_ratio": _monazite_huttonite_ratio,
    "mica_cascade": _mica_cascade,
    "amphibole_ca_ratio": _amphibole_ca_ratio,
    "amphibole_na_ratio": _amphibole_na_ratio,
    "carbonate_ratio": _carbonate_ratio,
}


def compute_end_members(site_allocation: SiteAllocationResult, config: MineralConfig) -> dict[str, float]:
    """Compute end-member mol% (summing to 100) per ``config.end_members.method``.

    Returns ``{}`` if the config declares no end-member scheme at all (an
    omitted ``end_members:`` block) -- some minerals (serpentine, talc) have
    no end-member concept in MinPlotX, this isn't an error.
    """
    method = config.end_members.method
    if not method:
        return {}
    fn = _METHODS.get(method)
    if fn is None:
        raise ValueError(f"Unknown end-member method {method!r}; expected one of {sorted(_METHODS)}.")
    return fn(site_allocation, config)
