# Task: Stoichiometric Mineral Formula Calculator (Garnet, Phase 1)

## Goal

Add a stoichiometric calculator to LaME that converts elemental concentrations
(ppm from LA-ICP-MS or wt.% oxide from XRF) into mineral formula units
(cations per formula unit, apfu), with correct crystallographic site
allocation, Fe2+/Fe3+ estimation, and end-member calculation. Start with
garnet (X3Y2Z3O12) as the only supported mineral, but design the backend so
additional minerals (pyroxene, amphibole) can be added later purely by adding
config files — no backend code changes.

## Before writing any code

1. Read through the existing codebase structure and identify:
   - Where the tool registry pattern lives and how existing tools are
     registered (I want this calculator to plug into that pattern).
   - How the observable/signal pattern is used for plot style and data
     updates, so the calculator's outputs can participate in it.
   - How ROI/polygon/cluster region definitions are stored and how existing
     summary-statistics tables for regions are built, so the new summary
     table can reuse that machinery rather than duplicating it.
   - How existing dock widgets are constructed (base classes, style
     conventions, how they're added to the main window) so the new dock
     widget matches conventions.
   - Where the existing map/quickview plotting machinery lives, and whether
     a derived (computed) quantity can be plotted through it as if it were
     an analyte, or whether that needs a small adapter.
2. Read `../global_geochemistry/src/molecular.py` and confirm its public
   API (molecular weight lookups, oxide/element conversion factors) before
   deciding what the new backend calls into vs. reimplements. Do not
   duplicate molecular-weight logic that already exists there.
3. Read `../global_geochemistry/src/data/mineral_abbrev_Whitney&Evans.xlsx`
   and confirm its structure (columns, key field) so mineral/end-member
   names and abbreviations used in labels and legends follow this
   convention consistently.
4. Summarize what you find and propose a file layout before implementing.

## Architecture constraints

- **Strict backend/UI separation.** All stoichiometric math, site-allocation
  logic, Fe redox estimation, and end-member calculation live in a pure
  Python module (or small package) with no PyQt imports and no dependency
  on the UI layer. It should be independently testable and callable from a
  script. The UI imports the backend, never the reverse.
- **Config-driven mineral definitions.** Mineral "recipes" (ideal formula,
  oxygen/cation normalization basis, site definitions, allowed elements per
  site with fill priority, end-member definitions) are external YAML (or
  JSON — pick one and be consistent) files, not hardcoded Python. Garnet is
  the first config; the loader/schema must not assume garnet-specific
  structure (e.g., don't hardcode "3 sites" or site names X/Y/Z).
- **UI is a floating QDockWidget**, following whatever base dock widget
  class/conventions already exist in the app. It should be dockable but
  default to floating. Keep the widget itself thin — it should call into
  the backend module and existing plotting/table infrastructure rather than
  reimplementing display logic.

## Backend module design

Please propose the exact module/function breakdown after exploring the
codebase, but at minimum the backend needs to support this pipeline:

1. **Input normalization** — accept either ppm (element basis) or wt.%
   (oxide basis) per analysis/pixel/spot, and convert to a common internal
   representation (moles of oxide per formula unit calculation) using
   `molecular.py` for molar weights and oxide stoichiometry.
2. **Trace element handling** — for each element, use the mineral config to
   classify it as (a) structural — include in site allocation even at trace
   level, (b) non-structural/excluded — flag and omit (e.g., inclusion
   contamination signatures), or (c) below detection limit — apply a
   user-selectable global treatment (zero / half-LOD / exclude from mole
   sum). This classification and the LOD treatment must be parameters, not
   buried defaults.
3. **Fe2+/Fe3+ (and other redox-sensitive elements) estimation** — support
   three modes, selectable by the user: all Fe2+, all Fe3+, and the Droop
   (1987) charge-balance estimate:

   F = 2 * X * (1 - T/S)

   where X = ideal oxygens (12 for garnet), T = ideal cation total for that
   oxygen basis (8 for garnet), S = cation total computed assuming all Fe is
   Fe2+. F is Fe3+ apfu; corrected Fe2+ = (all-Fe2+ Fe apfu) - F. Store and
   expose S and the residual for QC purposes, not just the final split.
   Design this so other redox-sensitive elements could later be handled
   similarly (config-flagged as redox-sensitive), even though garnet only
   needs Fe.
4. **Normalization** — normalize cation moles to the ideal oxygen count
   (config-specified, 12 for garnet) to get apfu.
5. **Site allocation** — given apfu values and the config's per-site
   allowed-element list and fill priority, allocate cations to sites (Z
   target 3.000, Y target 2.000, X target 3.000 for garnet), filling
   highest-priority/highest-charge-preference elements first and spilling
   remainder per the config-defined order (e.g., Al: Z first if Si
   deficient, else Y). Output per-site totals and per-element-per-site
   breakdown, plus a QC value (site total vs. ideal) for each site.
6. **End-member calculation** — decompose site occupancies into end-member
   proportions (pyrope/almandine/spessartine/grossular/andradite/uvarovite
   for garnet) per a documented method (e.g., Locock 2008); keep this as a
   separate function from site allocation so it can be swapped or extended
   per mineral later.
7. **QC diagnostics** — oxide total %, cation total vs. ideal per site,
   charge-balance residual, and a flag for likely hydrogarnet substitution
   (Z-site deficiency with genuinely low Si, not analytical noise) for
   garnet specifically — but implement the flag as a config-declarable
   check, not a hardcoded garnet-only branch, so other minerals can declare
   their own diagnostic checks later.
8. **Region/cluster summary statistics** — given a set of per-pixel/per-spot
   results and existing ROI/polygon/cluster definitions from the app,
   compute summary stats (mean, median, std, count, etc.) of apfu per site,
   Fe3+/ΣFe, and end-member % per region. Reuse the app's existing
   ROI-stats machinery if it's generic enough; otherwise write a thin
   adapter, not a parallel implementation.

## Config schema (garnet example — adjust as needed during implementation)

Propose a schema, but it should express at least:

```yaml
mineral: garnet
formula: X3Y2Z3O12
normalization:
  basis: oxygen
  ideal_oxygens: 12
  ideal_cations: 8
sites:
  Z:
    target: 3.0
    elements: [Si, Al, Fe3]
    priority: [Si, Al, Fe3]     # fill order when site is under-occupied
  Y:
    target: 2.0
    elements: [Al, Cr, Fe3, Ti]
    priority: [Al, Cr, Fe3, Ti]
  X:
    target: 3.0
    elements: [Ca, Mg, Fe2, Mn, Y, REE]
    priority: [Ca, Mg, Fe2, Mn, Y, REE]
redox:
  elements: [Fe]
  methods: [all_2plus, all_3plus, droop_1987]
  default_method: droop_1987
trace_elements:
  structural: [Y, Sc, Zn, Co, Ni]
  excluded: [Zr, Hf, Nb]   # example — flags likely inclusion contamination
end_members:
  method: locock_2008
  members: [pyrope, almandine, spessartine, grossular, andradite, uvarovite]
qc_checks:
  - hydrogarnet_substitution
```

## UI requirements

- Floating QDockWidget, consistent with existing dock widget base
  class/style.
- Element/oxide input mode selector (ppm vs. wt.%).
- Redox method selector (all Fe2+ / all Fe3+ / Droop) with the option to
  view all three side by side for comparison, not just the selected one.
- LOD treatment selector (zero / half-LOD / exclude).
- A results table (per-spot/pixel apfu, site totals, QC flags) — reuse
  existing table widget conventions if available.
- A summary table (region/cluster stats) — reuse the app's existing
  ROI/cluster summary table machinery if it's generic enough to extend.
- Where end-members are computed, route them through the existing
  map/quickview plotting machinery as if they were a derived analyte
  (confirm feasibility during the exploration step above).
- Trigger a recompute when the user changes redox method, LOD treatment, or
  input mode — don't require closing/reopening the dock widget.

## Testing / validation

- Unit tests for the backend module using at least one hand-checkable
  reference analysis (e.g., a published garnet EPMA analysis with known
  apfu and end-member results) to validate the pipeline end-to-end,
  independent of the UI.
- Unit tests for the Droop Fe3+ estimate against a hand-calculated case.
- Unit tests for config loading/validation (missing site, element assigned
  to no valid site, malformed YAML, etc. should raise clear errors, not
  silently produce wrong apfu).

## Deliverables

1. A short written summary of the codebase exploration (registry pattern,
   observable pattern, ROI-stats machinery, dock widget conventions,
   plotting adapter feasibility) before implementation begins.
2. Proposed file layout for backend module(s) and config file(s).
3. Backend module implementing the pipeline above, with unit tests.
4. `garnet.yaml` (or `.json`) config file.
5. Dock widget UI wired to the backend.
6. A short note on what would need to change to add a second mineral
   (e.g., pyroxene) — this should be small if the config-driven design
   worked as intended.

Please start with the exploration step and the proposed file layout/schema
before writing implementation code, so we can confirm the design fits the
existing architecture.
