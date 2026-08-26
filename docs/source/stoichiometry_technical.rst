Stoichiometric Calculations: Technical Details
*************************************************

This page describes the math behind the :doc:`Stoichiometry dock <stoichiometry>`. It follows the conventions of `MinPlotX <https://serc.carleton.edu/research_education/equilibria/minplotx.html>`_ and Droop (1987) wherever a mineral needs charge-balance estimation, and each mineral's specific formula, sites, and end-members are declared in its own YAML config -- see :doc:`mineral_configs` for the full, current content of every one.

Every analysis is run through five stages, in order:

1. :ref:`stoich-tech-normalization` -- raw analysis -> cation moles
2. :ref:`stoich-tech-basis` -- cation moles -> apfu (cations per formula unit), on a cation, oxygen, or anion basis
3. :ref:`stoich-tech-redox` -- Fe\ :sup:`2+`/Fe\ :sup:`3+` split, for minerals that need it
4. :ref:`stoich-tech-sites` -- apfu -> crystallographic site occupancies
5. :ref:`stoich-tech-endmembers` -- site occupancies -> end-member mol%

:ref:`stoich-tech-qc` runs alongside stages 3-4 and reports diagnostics rather than changing any computed value.

The mineral config schema itself (``src/stoichiometry/config.py``) declares, per mineral: its ideal formula, normalization basis, ideal oxygen/cation totals, site definitions (target apfu, member elements, fill priority), which elements need redox estimation and by which methods, which end-member method applies, and which QC checks to run. The loader validates every field and raises a specific error rather than silently producing a config that would compute the wrong apfu.

.. _stoich-tech-normalization:

1. Input Normalization
========================

A raw analysis is converted to cation moles via ``src/stoichiometry/normalize.py``'s ``to_cation_moles``, which accepts three input modes:

- ``ppm`` -- element symbol -> ppm (typical LA-ICP-MS output). Moles are ``(ppm * 1e-6) / atomic_weight``.
- ``wt_percent`` -- oxide formula -> wt.% (typical EPMA/XRF output). Moles are ``(wt% / oxide_molecular_weight) * n_cations_per_oxide``.
- ``element_wt_percent`` -- element symbol -> wt.% (sulfide/metal analyses reported as elements rather than oxides).

Molecular weights come from ``global_geochemistry.utils.molecular.MolecularWeightCalculator`` -- no molecular-weight table is reimplemented in *LaME*.

**Below-detection-limit treatment** (``lod_treatment``) controls how a value flagged below detection limit is handled: ``zero`` (default), ``half_lod`` (half the supplied detection-limit value), or ``exclude`` (dropped from the analysis entirely, not treated as zero).

**Trace-element exclusion**: any element listed in a config's ``trace_elements.excluded`` is dropped before mole conversion -- non-structural contamination that shouldn't be allocated to any site.

.. _stoich-tech-basis:

2. Normalization Basis
========================

Cation moles are unnormalized (an absolute quantity). Each mineral's config declares one ``normalization.basis`` -- ``cation``, ``oxygen``, or ``anion`` -- which fixes the reference total that apfu are ultimately reported against.

Cation basis (T-basis)
------------------------

Moles are scaled so the total cation count equals the config's ``ideal_cations`` (:math:`T`), excluding any species in ``normalization_excludes`` (e.g. S for sulfides) from the sum:

.. math::

   \mathrm{apfu}_i = m_i \cdot \frac{T}{\sum_{j \notin \text{excludes}} m_j}

This is valence-independent -- moles don't encode charge, so this is the correct reference basis regardless of which redox hypothesis is ultimately chosen for a redox-sensitive element. It's the basis Droop's (1987) charge-balance formula is defined in terms of (see :ref:`stoich-tech-redox`).

Oxygen basis (S-basis)
-------------------------

Moles are scaled so the total oxygen-equivalent equals the config's ``ideal_oxygens`` (:math:`X`), using each cation's standard assumed oxide form (e.g. Fe assumed as FeO, Al as Al\ :sub:`2`\ O\ :sub:`3`) to compute how many oxygens each cation's mole contributes:

.. math::

   \mathrm{apfu}_i = m_i \cdot \frac{X}{\sum_j m_j \cdot (n_{O} / n_{cation})_j}

Anion basis
-------------

For sulfides and sulfosalts, S (or S+As+Sb) is measured directly rather than inferred from an oxide-form assumption. When the config's ``normalization.basis`` is ``anion`` and the anion was actually measured in this analysis, moles are scaled so the anion total equals ``ideal_oxygens`` (reused as a generic "ideal anchor total" field) instead:

.. math::

   \mathrm{apfu}_i = m_i \cdot \frac{X}{\sum_{j \in \text{excludes}} m_j}

This leaves the metal (cation) side free to float, so real non-stoichiometry -- e.g. pyrrhotite's Fe-vacancy -- shows up directly as a metal apfu deficiency rather than being hidden behind a metal total forced to its nominal target. If the anion wasn't measured in a given analysis, this falls back to the cation basis above rather than raising -- ``StoichiometryResult.basis_used`` records which path actually ran.

.. _stoich-tech-redox:

3. Redox Estimation
======================

For minerals with a redox-sensitive element declared (``redox.elements`` -- Fe, currently), ``src/stoichiometry/redox.py`` splits its total apfu into divalent/trivalent species (``Fe2``/``Fe3``) by one of four methods:

- ``all_2plus`` / ``all_3plus`` -- assign the entire measured total to one valence state, no charge-balance computation.
- ``fixed_ratio`` -- split by a fixed, config- or user-supplied Fe\ :sup:`3+`/Fe\ :sub:`total` fraction.
- ``droop_1987`` -- estimate Fe\ :sup:`3+` from charge-balance, following `Droop (1987) <https://doi.org/10.1180/minmag.1987.051.361.10>`_:

  .. math::

     F = 2X\left(1 - \frac{T}{S}\right)

  where :math:`X` is the ideal oxygen total, :math:`T` is the ideal cation total, and :math:`S` is the cation total computed on the oxygen basis assuming the element is entirely divalent. :math:`F` (apfu of Fe\ :sup:`3+`) is clipped to :math:`[0, \text{element total}]`, since :math:`S \le T` means there's no charge-balance evidence for any Fe\ :sup:`3+` at all. ``droop_1987`` is only self-consistent on the cation (T) basis, and configs that request it must declare ``basis: cation``.

Which basis a mineral reports Fe on tracks *why* it needs charge-balance in the first place: garnet, olivine, pyroxene, and spinel all use Droop-style estimation (cation basis); most other minerals report Fe on the oxygen basis directly with no rescale, since there's no T/S reconciliation to justify one.

.. _stoich-tech-sites:

4. Site Allocation
=====================

``src/stoichiometry/sites.py`` allocates apfu to crystallographic sites by a generic priority-fill algorithm -- no site names or counts are hardcoded anywhere in the backend. Sites are filled in the order they appear in the mineral's YAML file (PyYAML preserves mapping order, so the file's own ``sites:`` ordering *is* the fill-priority order); within a site, its own ``priority`` list sets fill order among that site's elements.

An element shared between two sites (e.g. Al in both a tetrahedral and octahedral site) draws from one running pool: it fills the earlier site up to that site's target, then whatever's left "spills" into the next site that lists it. An element is only capped at a site's remaining target space if some *later* site in the fill order also lists it -- if a site is an element's only or last eligible site, it's assigned in full even if that pushes the site's total past its target, rather than silently discarding real composition (this matches MinPlotX's reference behavior, e.g. its garnet model always fully assigns Ti/Cr to the octahedral site since no other site can hold them).

A handful of minerals (pyroxene's quadrilateral split, spinel's X/Mg partitioning) use a specialized site-allocation method instead of generic priority-fill, declared via a config's ``site_allocation.method``.

.. _stoich-tech-endmembers:

5. End-Member Decomposition
==============================

``src/stoichiometry/endmembers.py`` converts site occupancies into end-member mol%, dispatched by the method name in a config's ``end_members.method``. Most minerals use a simple ratio method -- an end-member's fraction is that site's relevant cation divided by the site's total (e.g. olivine's forsterite = Mg / (Mg+Fe+Mn+Ca) at its X site) -- scaled so the reported fractions sum to 100.

Garnet uses a simplified implementation of the `Locock (2008) <https://doi.org/10.1016/j.cageo.2007.05.017>`_ X-site/Y-site cation-proportion method, covering the six major pyralspite/ugrandite end-members (pyrope, almandine, spessartine, grossular, andradite, uvarovite). The X-site divalent cations (Ca, Mg, Fe\ :sup:`2+`, Mn) set the pyrope/almandine/spessartine/Ca-bearing fractions; among the Ca-bearing fraction, the Y-site trivalent cations (Al, Fe\ :sup:`3+`, Cr) further split it into grossular/andradite/uvarovite. Locock's additional minor end-members (majorite, knorringite, goldmanite, kimzeyite, etc.) aren't implemented.

Spinel-magnetite is the one mineral with a **tiered** end-member scheme, since the classic 4 (trivalent) x 6 (divalent) spinel-prism cross-product produces 24+ named end-members in practice, most of them below EPMA-noise-level significance. A folded trivalent-equivalent basis {Al, Cr, Fe\ :sup:`3+`, a pseudo-trivalent [Fe\ :sup:`2+`\ Ti] component that absorbs the coupled 2Fe\ :sup:`3+` ⇌ Fe\ :sup:`2+` + Ti\ :sup:`4+` substitution} crossed with {Mg, Fe\ :sup:`2+`} gives 8 always-on Tier 1 members (spinel, hercynite, magnesiochromite, chromite, magnesioferrite, magnetite, qandilite, ulvospinel). Mn and Zn each add a Tier 2 trio/pair of named members once their own share of the divalent axis crosses a small threshold (an apfu-fraction proxy for "actually present," not a literal wt% conversion); V does the same for a Tier 3 pair (coulsonite, magnesiocoulsonite) on the trivalent axis. Every cation that never gets a named cell here -- Ni, Co (dropped entirely; at EPMA detection limits they're noise, and where they genuinely matter it's an LA-ICP-MS trace-element question, not this calculator), an untriggered Mn/Zn/V, or Si (which plays no axis role at all -- ringwoodite/ahrensite are transition-zone/shock silicate-spinel phases that belong in a separate calculator, not this oxide one) -- falls into an ``other`` residual, flagged by the ``spinel_other_fraction`` QC check (:ref:`stoich-tech-qc`) when it exceeds 5%. Four standard, tier-independent ratios -- Cr# = Cr/(Cr+Al), Mg# = Mg/(Mg+Fe\ :sup:`2+`), Fe\ :sup:`3+`/ΣR\ :sup:`3+`, and X\ :sub:`usp` = Ti/(Ti+Fe\ :sup:`3+`) -- are reported as the primary diagnostic output (``end_members.ratios``, kept structurally separate from the tiered ``members`` so a high ratio value can't spuriously dominate a "which phase" map); the named end-member fractions are a secondary convenience for the names that actually appear in the literature.

.. _stoich-tech-qc:

6. QC Diagnostics
====================

``src/stoichiometry/qc.py`` runs generic, always-available diagnostics plus any checks a mineral's config names in ``qc_checks``:

- **Site totals**: each site's total apfu, target, and deficiency (target minus total; negative means over-full), for every site regardless of config.
- **Charge-balance residual** (:math:`S - T`, redox-sensitive minerals only): how far the all-divalent oxygen-basis cation total (Droop's :math:`S`) sits from the ideal cation total (:math:`T`) -- the same quantity :ref:`Droop's Fe3+ formula <stoich-tech-redox>` is built from.
- **Hydrogarnet substitution** (garnet-specific, ``hydrogarnet_substitution``): flags likely (OH)\ :sub:`4` for SiO\ :sub:`4` substitution when Si genuinely falls short of its site target *and* the whole site remains under-occupied -- distinguishing a real hydrogarnet signal from ordinary analytical noise, which Al/Fe\ :sup:`3+` spillover into that site would already resolve on its own.
- **Cation:anion ratio** (sulfides, ``cation_anion_ratio``): the real measured cation-total : anion-total apfu ratio. This is basis-invariant (the same physical value regardless of which basis produced the apfu), which makes it useful as a first-pass classifier on the generic ``sulfide`` config before committing to any specific mineral's formula -- roughly 1:1 suggests a monosulfide, 1:2 a pyrite-type, 9:8 a pentlandite-type, and so on.

References
============

- Droop, G.T.R. (1987) A general equation for estimating Fe\ :sup:`3+` concentrations in ferromagnesian silicates and oxides from microprobe analyses, using stoichiometric criteria. *Mineralogical Magazine*, 51, 431-435. `doi:10.1180/minmag.1987.051.361.10 <https://doi.org/10.1180/minmag.1987.051.361.10>`_
- Locock, A.J. (2008) An Excel spreadsheet to recast analyses of garnet into end-member components, and a synopsis of the crystal chemistry of natural silicate garnets. *Computers & Geosciences*, 34, 1769-1780. `doi:10.1016/j.cageo.2007.05.017 <https://doi.org/10.1016/j.cageo.2007.05.017>`_
- Whitney, D.L. and Evans, B.W. (2010) Abbreviations for names of rock-forming minerals. *American Mineralogist*, 95, 185-187. `doi:10.2138/am.2010.3371 <https://doi.org/10.2138/am.2010.3371>`_
- `MinPlotX <https://serc.carleton.edu/research_education/equilibria/minplotx.html>`_ -- the reference convention this package's normalization-basis and site-allocation choices follow.
