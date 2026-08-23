# Mineral Classification and Stoichiometric Calibration — Design Specification

**Purpose.** Specification for the classification and final-calibration stages of LaME's
total-element-concentration pipeline for LA-ICP-MS maps, as agreed in a 2026-08-20 discussion
with a colleague. Covers: (3) mineral classification by cosine distance against a reference
composition library, (4) how the existing secondary-standard correction plugs in relative to
classification, (5) per-pixel stoichiometric ratio calculation, and (6) using those ratios to
set a final internal-standard or sum-normalization scale. Intended as the implementation brief
for a coding agent. Numerical core must be UI-free and independently importable/testable, per
LaME convention (see `plans/laicpms_map_correction_spec.md` §1 for the same principle applied to
the deconvolution stage).

---

## 1. Where this fits in the full pipeline

The agreed six-stage scheme, and where each stage currently stands:

| # | Stage | Status | Lives in |
|---|---|---|---|
| 1 | Background and drift correction | **Done** | `src/calibration/background.py`, `drift.py` |
| 2 | Deconvolution (spot mixing, smearing, washout) | Spec'd, not implemented | `plans/laicpms_map_correction_spec.md` |
| 3 | Classification by cosine distance to a mineral list | **New — this doc** | proposed `src/classification/` |
| 4 | Secondary standard correction, if applicable | Existing primitive, new integration | `src/calibration/standards.py` |
| 5 | Set stoichiometric ratios | Existing engine, new caller | `src/stoichiometry/pipeline.py` |
| 6 | Stoichiometric-ratio-based internal standard / normalization | **New — this doc** | proposed `src/stoichiometry/normalize_final.py` |

**Ordering constraint carried over from the deconvolution spec:** deconvolve (stage 2) before
computing any ratio (§7.1 of that document — `h * c_A / (h * c_B) ≠ h * (c_A / c_B)`). Classify on
deconvolved counts, not raw counts, once stage 2 exists; until then, classify on
background/drift-corrected counts as the best available input.

**Background/drift is deliberately its own step**, separate from any drift folded into
calibration — see prior project decision on keeping the gas-blank drift fit and the
standard-drift fit independent (`src/calibration/background.py`'s
`fit_session_background_drift` vs. `standards.py`'s `drift_fits`). Nothing in this spec revisits
that; stage 1 output is simply this pipeline's input.

**Relation to `plans/mineral_id.md`.** An earlier design conversation recorded there argued for
*unmixing* (NNLS against extracted endmembers) rather than *hard classification*, specifically to
handle mixed pixels and rare phases without either forcing them into one class or discarding
them. Cosine-distance classification, as agreed with the colleague, is a hard classifier: every
pixel gets assigned to its single nearest mineral (or flagged unclassified). This is simpler to
implement and to reason about, and it is what downstream stages 5–6 need (stoichiometric site
allocation requires a specific formula, not a fractional blend of two formulas). The cost is
exactly the mixed-pixel/rare-phase weakness `mineral_id.md` describes. §3.4 below defines an
explicit ambiguity flag so mixed/boundary pixels are marked rather than silently misclassified;
full unmixing remains a documented alternative, not something this spec implements.

---

## 2. Notation

| Symbol | Meaning |
|---|---|
| `x_i` | measured composition vector for pixel/spot `i` (elements or oxides, calibrated units) |
| `r_m` | reference composition vector for mineral/end-member `m` in the library |
| `E_i` | set of elements measured (and above LOD) for pixel `i` |
| `E_m` | set of elements defined in reference `m`'s composition |
| `cos(x, r)` | cosine similarity, `x·r / (‖x‖‖r‖)`, restricted to `E_i ∩ E_m` |
| `ẑ_i` | assigned mineral label for pixel `i` (or `None` if unclassified) |
| `g_i` | ambiguity gap, top-1 vs. top-2 cosine similarity for pixel `i` |
| `config_m` | `MineralConfig` from `resources/minerals/<mineral>.yaml` (site allocation, existing) |
| `apfu_i` | atoms-per-formula-unit vector from `stoichiometry.pipeline.calculate` for pixel `i` |
| `T_i` | ideal stoichiometric total (oxide wt.% or cation sum) implied by `apfu_i` and `config_m` |
| `s_i` | per-pixel scale factor converting relative (uncalibrated-total) concentrations to absolute |

---

## 3. Classification (`src/classification/`)

### 3.1 Reference composition library — a new resource, distinct from `resources/minerals/*.yaml`

`resources/minerals/*.yaml` already encodes *site-allocation* recipes (target apfu per site, fill
priority, redox handling, end-member methods) — everything needed to compute stoichiometry
**once a mineral is known**. It does not carry a representative bulk composition, so it cannot be
used directly as a classification target.

Add a new library, one composition vector per mineral or named end-member (e.g., separate
entries for anorthite/albite/orthoclase, not just one for "feldspar"), sourced from published
reference compositions (webmineral.com, RRUFF, or a curated rock-forming-mineral set — see
`plans/mineral_id.md`'s note on bootstrapping from RRUFF/IMA plus ~50 curated formulas rather
than an exhaustive database).

```
resources/mineral_reference_compositions/
├── schema.yaml                 # validated shape, mirrors config.py's MineralConfigError pattern
├── anorthite.yaml
├── albite.yaml
├── orthoclase.yaml
├── garnet_almandine.yaml
...
```

Each entry:

```yaml
mineral: anorthite
end_member_of: feldspar          # links back to resources/minerals/feldspar.yaml for stage 5
formula: CaAl2Si2O8
composition:                     # oxide wt.% or element ppm, source-labeled
  basis: oxide_wt_percent
  values: {SiO2: 43.2, Al2O3: 36.7, CaO: 20.1}
source: webmineral.com           # citation/provenance, required
```

Composition values should be **ideal/stoichiometric**, not an average of natural analyses —
cosine similarity is about matching the elemental *pattern*, and an ideal end-member composition
is the least ambiguous target. Trace-element-only accessory phases (zircon, monazite, apatite —
already have `resources/minerals/*.yaml` entries) need reference vectors dominated by their
diagnostic trace elements (Zr; P+LREE; P+Ca), consistent with the "chemical gating" idea in
`mineral_id.md` §"The rare-phase problem specifically" — cosine distance against a
trace-element-heavy reference vector is effectively that gating, done uniformly instead of via
hand-written threshold rules.

### 3.2 Distance metric and element handling

$$\cos(\mathbf{x}_i, \mathbf{r}_m) = \frac{\sum_{j \in E_i \cap E_m} x_{ij}\, r_{mj}}
{\sqrt{\sum_{j \in E_i \cap E_m} x_{ij}^2}\ \sqrt{\sum_{j \in E_i \cap E_m} r_{mj}^2}} \tag{1}$$

Restricting the dot product to `E_i ∩ E_m` (subcompositional coherence) is required — LA-ICP-MS
analyses do not measure a closed composition (no O, generally no light elements), and different
minerals' reference vectors will have different element sets. Do not zero-fill missing elements;
that biases the score toward whichever reference has the most overlap with the analyte suite,
independent of match quality. Require a minimum overlap (`|E_i ∩ E_m| ≥ n_min`, config default
3) before a reference is scored at all; otherwise it is excluded from the candidate set for that
pixel, not scored as a poor match.

Cosine similarity is scale-invariant by construction — the same property that makes it robust to
per-pixel ablation-yield variation also means it is **not** a substitute for calibration
(stage 4/5 still needed for absolute abundances); it only needs *relative* element proportions to
already be right, i.e. it should run on primary-standard-calibrated data (or at minimum
drift-corrected CPS with consistent relative sensitivities across elements), not raw uncalibrated
counts.

Run in linear space, not log-ratio space. `mineral_id.md` recommends clr for *clustering* to
avoid a Euclidean metric being dominated by SiO2/majors — cosine similarity does not have that
failure mode the same way (it already normalizes by vector length), and linear space keeps trace
diagnostic elements (Zr, P+LREE) directly interpretable in the dot product without a
zero/censored-value replacement step. Revisit only if trace-poor vs. trace-rich pixels of the
same true mineral are found to separate incorrectly in practice.

### 3.3 Assignment

$$\hat{z}_i = \arg\max_m \cos(\mathbf{x}_i, \mathbf{r}_m) \tag{2}$$

subject to `cos(x_i, r_{ẑ_i}) ≥ τ_min` (config threshold, default 0.95 — tune against a labeled
validation set, §6); below threshold, `ẑ_i = None` (unclassified), reported not silently dropped.

### 3.4 Ambiguity flag (the mixed-pixel guard)

$$g_i = \cos(\mathbf{x}_i, \mathbf{r}_{(1)}) - \cos(\mathbf{x}_i, \mathbf{r}_{(2)}) \tag{3}$$

where `(1)`, `(2)` are the top two matches. Small `g_i` means the pixel sits between two mineral
references — plausibly a boundary/mixed pixel per `mineral_id.md`'s taxonomy, not confidently one
phase. Flag pixels with `g_i < g_min` (config, default 0.02) as **ambiguous**; they still get
`ẑ_i` set to the top match (so stages 5–6 have something to run), but the flag must propagate
through to stage 6 and to any exported map, since stage 6's normalization assumes the label is
correct. Do not attempt geometric disambiguation (boundary vs. inclusion vs. crack, per
`mineral_id.md` §"Distinguishing the three mixed-pixel types") in v1 — flag and report only.

### 3.5 Solid solutions

Classify against individual end-members (anorthite, albite, orthoclase), not the group
("feldspar"), then resolve to the group's `MineralConfig` (`end_member_of` in §3.1's schema) for
stage 5. If the top-2 matches are end-members of the *same* solid solution (e.g., anorthite +
albite), that is expected — solid solutions are compositional segments, and a pixel between two
end-members is a real intermediate composition, not an ambiguous classification. `g_i` should
therefore be computed **after grouping same-solution end-members** (compare the best cross-group
match against the best within-group match) so plagioclase of intermediate An content is not
spuriously flagged as boundary-mixed with, say, K-feldspar.

---

## 4. Secondary standard correction — where it plugs in

`src/calibration/standards.py` already computes per-standard-label calibration curves and
handles primary + secondary standard orchestration (module docstring: "multiple standard types
... are orchestrated by `pipeline.py` calling this module once per label"). What's new here is
*when* a secondary correction is selected: matrix-matched secondary standards (e.g., a
plagioclase-matrix glass vs. a garnet-matrix glass) are only well-defined once the pixel's matrix
is known, i.e., after classification (stage 3).

Add a lookup, mineral label → secondary standard label (config-driven, not hard-coded — same
principle as the deconvolution spec's §1.3 "config-driven, no hard-coded instrument constants").
Where `ẑ_i` has no matching secondary standard, apply the default/primary-only calibration and
flag the pixel as `secondary_standard: none` rather than silently skipping the correction.
Unclassified (`ẑ_i = None`) pixels always fall back to default calibration.

---

## 5. Stoichiometric ratios

Direct reuse of the existing engine — no new math here, only a new caller. For each classified
pixel:

```python
config_m = load_mineral_config(f"resources/minerals/{group_of(z_i)}.yaml")
result_i = pipeline.calculate(analysis=x_i, config=config_m, input_mode=..., mwc=shared_mwc)
```

`group_of(z_i)` resolves an end-member label (e.g. `anorthite`) to its group config file (e.g.
`feldspar.yaml`) via the reference library's `end_member_of` field (§3.1). Unclassified pixels
skip this stage entirely (no `MineralConfig` to run against) — this is expected, not an error;
report the unclassified fraction as a QC metric (§7).

Batch this per-mineral-group rather than per-pixel where possible (reuse one `MolecularWeightCalculator`
instance and one loaded `MineralConfig` across all pixels sharing a label), mirroring
`pipeline.calculate`'s own `mwc` reuse parameter, which exists for exactly this bulk-call case.

---

## 6. Final normalization from stoichiometric ratios

This is the "stoichiometric internal standardization" technique used when no directly-measured
internal standard (e.g., an independently determined major-element concentration) is available
for a pixel: the *known* stoichiometry of the classified mineral supplies the missing constraint
that converts relative, uncalibrated-total LA-ICP-MS data into absolute concentrations.

Two modes, both driven by `apfu_i` / `result_i.end_members` from stage 5:

### 6.1 Mode A — fixed per-pixel internal standard

Pick one analyte (config-selectable per mineral group, e.g. Si for silicates, Ca for carbonates)
and assign it the concentration implied by the classified mineral's ideal formula (`config_m`) —
exactly the role a directly-measured internal standard normally plays, substituted by the
stoichiometric assumption. All other analytes in pixel `i` are then scaled by:

$$s_i = \frac{v_{\mathrm{internal},\,\mathrm{ideal}}}{x_{i,\,\mathrm{internal}}} \tag{4}$$

where `v_internal,ideal` comes from `config_m`'s formula and `x_i,internal` is the pixel's
measured (relative-calibration) value for that same analyte. This mode is a per-pixel fixed
value in the sense that the *assumed* internal-standard concentration is the same ideal value for
every pixel of that mineral, regardless of how that pixel's other trace elements vary — it does
not adapt to solid-solution position. Use it when the classified phase is close to end-member
(low intra-group compositional variance), otherwise prefer Mode B.

### 6.2 Mode B — group sum/mean/median normalization

Instead of anchoring on one assumed analyte, use the full stoichiometric closure: `config_m` plus
`apfu_i` imply an ideal total (oxide wt.% sum ≈ 100, or ideal cation sum `config_m.ideal_cations`)
that the pixel's measured total should reproduce once correctly scaled:

$$s_i = \frac{T_{\mathrm{ideal}}}{T_i^{\mathrm{measured}}},\qquad
T_i^{\mathrm{measured}} = \sum_{j} x_{ij}\ \text{(oxide-equivalent, same convention as}\
\texttt{normalize.oxide\_total\_percent}\text{)} \tag{5}$$

Two aggregation choices, config-selectable:

- **Per-pixel**: apply `s_i` from eq. (5) directly to pixel `i`. Sensitive to single-pixel noise
  in the measured total.
- **Per-classified-group mean/median**: compute `s_i` for every pixel with label `ẑ_i = m`, then
  apply `median({s_i : ẑ_i = m})` (or mean) to *all* pixels of that label. More robust — a
  single noisy pixel's total no longer determines its own scale factor — at the cost of erasing
  genuine pixel-to-pixel variation in, e.g., alteration or minor non-stoichiometry. Default to
  median (robust to the same kind of outlier pixels `standards.py`'s existing MAD screen already
  guards against elsewhere in this pipeline) unless the group is small (`n < 10`, use per-pixel
  and flag).

Report both `s_i` and which aggregation mode produced it per pixel (provenance, same principle as
the deconvolution spec's `mapcorr_history` — corrections must be traceable, never silently
overwrite the pre-normalization values in place).

**Ambiguous pixels (§3.4) must not contribute to a group's mean/median `s_i`.** Flag them, and
still apply the group's already-computed factor to them if desired for display, but exclude them
from computing that factor in the first place — a boundary pixel's mismatched-mineral composition
would otherwise bias every pixel of that label.

---

## 7. Diagnostics and QC

- **Classification confidence map** — `cos(x_i, r_ẑi)` and `g_i` (eq. 1, 3) as exportable layers,
  same spirit as the deconvolution spec's residual map (§6.5 step 4 there) — localizes exactly
  the pixels later stages should be treated cautiously.
- **Unclassified fraction** — count and spatial distribution of `ẑ_i = None` pixels; a high
  fraction likely means the reference library is missing a phase present in the sample, not that
  the threshold is wrong — report both possibilities.
- **Per-group scale-factor spread** (Mode B) — report the distribution of `s_i` within a
  classified group before collapsing to mean/median; a bimodal distribution suggests two
  populations were classified under one label (reference library too coarse, e.g. plagioclase
  end-members not separated).
- **Closure check** — after applying `s_i`, the pixel's oxide total should equal `T_ideal` by
  construction (Mode B) or the internal-standard analyte should equal `v_internal,ideal`
  (Mode A); assert this as a unit test on synthetic data, not just trust the algebra.

---

## 8. Staged implementation plan

**Stage A — Reference library infrastructure.** Schema + loader for
`resources/mineral_reference_compositions/` (mirrors `config.py`'s `MineralConfigError` pattern).
Populate with the mineral groups already in `resources/minerals/*.yaml` (end-members split out
per §3.1). *Accept:* loader round-trips and validates against malformed entries; every existing
`resources/minerals/*.yaml` group has ≥1 reference composition.

**Stage B — Classification core.** `src/classification/cosine.py`: eq. (1)–(3), element-overlap
handling, ambiguity flag, solid-solution grouping (§3.5). Pure functions, no I/O. *Accept:*
recovers the correct label on synthetic pure-endmember inputs; correctly reports `g_i` near 0 for
a 50/50 synthetic mix of two references; correctly excludes a reference from scoring when overlap
`< n_min`.

**Stage C — Pipeline integration.** Wire classification output into secondary-standard selection
(§4) and into `stoichiometry.pipeline.calculate` (§5), batched per label. *Accept:* end-to-end run
on a small real dataset produces per-pixel `ẑ_i`, `apfu_i`, and QC layers without raising on
unclassified pixels.

**Stage D — Final normalization.** `src/stoichiometry/normalize_final.py`: Mode A (eq. 4) and
Mode B (eq. 5) with the per-pixel/group aggregation switch. *Accept:* closure check (§7) passes on
synthetic single-phase data for both modes; group-median mode is measurably less sensitive to a
single planted noisy pixel than per-pixel mode, on synthetic data with one outlier injected.

**Stage E — UI integration.** Out of scope here, per the same principle as the deconvolution
spec's Stage 9 — design the API so `StoichiometryDock` (or a new classification dock) only needs
to call a `pipeline.run()`-style entry point plus the diagnostic layers from §7.

---

## 9. Open questions for the maintainer

1. **Classification-before-secondary-standard ordering** (as in the colleague's outline, §4
   above) assumes the *primary* calibration alone gives element ratios accurate enough to
   classify correctly, and that matrix-matched secondary correction is a refinement applied
   after. Confirm this is intended, versus classifying after secondary correction if a
   matrix-independent secondary standard is normally used.
2. **Reference library provenance** — is a single ideal (stoichiometric) composition per
   end-member sufficient, or should natural-analysis reference ranges (with associated
   uncertainty) be supported, e.g. to compute a similarity confidence interval rather than a
   point cosine value?
3. **Threshold tuning** (`τ_min` §3.3, `g_min` §3.4, `n_min` §3.2) — defaults above are
   placeholders; need a labeled validation set (e.g. EPMA-cross-checked pixels) to tune against,
   per §6/§9.3 pattern in the deconvolution spec.
4. **Mode A vs. Mode B default** — should the pipeline default to Mode B (group
   median) uniformly, or should the choice be per-mineral-group config (e.g. Mode A for
   near-end-member phases like quartz/rutile, Mode B for solid solutions with real intra-group
   compositional spread)?
5. **Interaction with stage 2 (deconvolution).** Once implemented, should classification run
   twice — once pre-deconvolution as a fast QC pass, once post-deconvolution as the production
   classification — or only post-deconvolution?
