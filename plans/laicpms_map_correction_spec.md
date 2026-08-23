# LA-ICP-MS Map Artifact Correction — Design Specification

**Purpose.** Specification for a physics-based processing module that corrects four coupled
artifacts in LA-ICP-MS elemental maps: **spot mixing**, **along-line smearing**, **per-analyte
location mismatch**, and **washout tailing**. Intended as the implementation brief for a coding
agent. Target host: LaME (`LaserMapExplorer`), PyQt6 desktop application, but the entire numerical
core must be UI-free and independently importable/testable.

**Audience for the code.** Research users who will read the source. Comment the math, cite the
equations by their numbers in this document, and keep variable names close to the symbols below.

---

## 1. Scope and design principles

1. **One forward model, several inverse strategies.** All four artifacts are components of a single
   linear operator `A`. Do not implement four unrelated "filters."
2. **Strict backend/UI separation.** Numerical core in `core/`, no Qt imports anywhere below the
   `ui/` boundary. All algorithms callable from a script or a notebook.
3. **Config-driven.** Instrument geometry, kernel parameterizations, and solver settings live in
   YAML; code contains no hard-coded instrument constants.
4. **Counts space is the working space.** All deconvolution and unmixing operate on raw counts (or
   counts-per-second with a known conversion), *before* internal standardization or calibration.
   Ratios and concentration calibration are strictly downstream. See §7.1.
5. **Every stage is separately testable** against a synthetic phantom with known ground truth (§9).
6. **Fail loudly on missing metadata.** The corrections depend on acquisition parameters (sweep
   time, dwell schedule, scan speed, scan direction per line). If they are absent, raise — do not
   silently assume defaults.
7. **American English** spellings throughout code, comments, and documentation.

---

## 2. Notation

| Symbol | Meaning | Units |
|---|---|---|
| `c_j(x)` | true concentration (or count-yield) field of analyte `j` | counts equiv. |
| `x = (s, y)` | position; `s` along-line, `y` cross-line | µm |
| `v` | laser stage speed | µm/s |
| `K(x)` | effective spot / ablation footprint kernel | 1/µm² |
| `h(t)` | cell + transport impulse response (washout) | 1/s |
| `τ`, `τ₁`, `τ₂` | washout time constants | s |
| `Δt` | sweep (cycle) period — time to cycle all analytes once | s |
| `τ_d,j` | dwell time of analyte `j` | s |
| `δ_j` | offset of analyte `j`'s dwell within the sweep cycle | s |
| `d_j[i]` | measured counts, analyte `j`, sample `i` along a line | counts |
| `f_k(x)` | mass fraction field of phase (endmember) `k` | — |
| `v_kj` | composition of endmember `k` in analyte `j` | counts equiv. |
| `A` | full forward operator (blur + shift + sampling) | — |
| `K_ph` | number of phases/endmembers; `J` = number of analytes | — |

---

## 3. Forward model

### 3.1 Continuous model

Instantaneous ablated flux as the spot traverses the sample:

$$u_j(t) = \int K(\mathbf{x} - \mathbf{x}_L(t))\, c_j(\mathbf{x})\, d^2x \tag{1}$$

Aerosol dispersion in cell and transport line, a **causal** impulse response:

$$h(t) = \sum_{k} \frac{A_k}{\tau_k} e^{-t/\tau_k},\quad t \ge 0,\qquad \sum_k A_k = 1 \tag{2}$$

The normalization $\int h\,dt = 1$ is mass conservation and must be enforced and unit-tested.

Detection: the quadrupole integrates analyte `j` over its dwell window within each sweep:

$$d_j[i] = \int_{t_i + \delta_j}^{t_i + \delta_j + \tau_{d,j}} (h * u_j)(t)\, dt + \text{Poisson noise} \tag{3}$$

### 3.2 Mapping to a spatial operator

Substituting $s = vt$ along a scan line, the composite along-line kernel is

$$\mathrm{PSF}(s, y) = K(s, y) *_s \Pi_{v\tau_d}(s) *_s h_s(s),\qquad h_s(s) = h(s/v)/v \tag{4}$$

with $\Pi_L$ the boxcar of width `L` (laser travel during the dwell).

**Artifact ↔ model term mapping — implement each as a named, separable component:**

| Artifact | Model term | Direction | Character | Invertibility |
|---|---|---|---|---|
| Mixing | `K` | 2D (only cross-line term) | symmetric | ill-posed; needs priors |
| Smearing | `Π_{vτ_d}` | along-line | symmetric, sinc zeros | mildly ill-posed |
| Location mismatch | `δ_j` | along-line | pure shift | **exact** |
| Washout | `h_s` | along-line | causal, asymmetric | well-posed but noise-amplifying |

**Bidirectional scanning.** If alternate lines are scanned in opposite directions, the causal
direction of `h_s` **flips** in sample coordinates on alternate lines. The operator must carry a
per-line direction flag and apply the exponential tail in the correct sense. This is a common source
of "herringbone" artifacts and must be handled in v1, not deferred.

---

## 4. Package layout

Follow LaME's feature-based `tools/` convention:

```
lame/tools/mapcorr/
├── __init__.py                 # public API surface only
├── config/
│   ├── instrument.schema.yaml  # validated schema for acquisition metadata
│   └── defaults.yaml           # solver defaults, never instrument constants
├── core/
│   ├── model.py                # AcquisitionModel: metadata container + validation
│   ├── kernels.py              # K, h, Π parameterizations; normalization; sampling
│   ├── operator.py             # ForwardOperator: A, A^T, matrix-free LinearOperator
│   ├── washout.py              # recursive exact/regularized 1D inverse filters
│   ├── deconv.py               # Poisson RL, RL-TV, Chambolle–Pock / ADMM
│   ├── priors.py               # vector TV, L1 (inclusions), positivity, simplex proj.
│   ├── unmix.py                # FCM, archetypal/VCA endmembers, weighted NNLS
│   ├── inclusions.py           # sparse point-source layer, matched filtering
│   ├── esf.py                  # edge-spread fitting, in-situ kernel estimation
│   ├── transforms.py           # log / clr / ilr and inverses
│   └── diagnostics.py          # residual maps, whiteness tests, mass balance
├── phantom/
│   ├── generate.py             # synthetic ground-truth scenes
│   └── metrics.py              # scoring functions (§9.3)
├── pipeline.py                 # staged orchestration, provenance recording
└── tests/
```

UI integration (a dock widget) is **out of scope for the first implementation**. Expose
`pipeline.run(dataset, config) -> Dataset` and let the UI wrap it later.

---

## 5. Data model

Use `xarray` throughout, consistent with LaME's NetCDF4/HDF5 group-per-modality schema.

```python
# Dataset dims: (line, sample, analyte)
ds["counts"]        # (line, sample, analyte) float32 or int32, raw counts
ds["dwell_time"]    # (analyte,) seconds
ds["sweep_offset"]  # (analyte,) seconds, δ_j within the cycle
ds["scan_dir"]      # (line,) +1 / -1
ds.attrs = {
    "sweep_period": ...,     # Δt, s
    "stage_speed": ...,      # v, µm/s
    "spot_size": ...,        # µm (and shape: "circle" | "square")
    "line_spacing": ...,     # µm
    "rep_rate": ...,         # Hz
    "fluence": ...,          # J/cm²
}
```

`AcquisitionModel` wraps this, validates against the YAML schema, and derives:
`pixel_pitch_along = v * Δt`, `boxcar_length_j = v * τ_d,j`, `shift_pixels_j = δ_j / Δt`
(generally fractional — see §6.2).

**Provenance.** Every stage appends to `ds.attrs["mapcorr_history"]`: stage name, parameters,
solver iterations, convergence metric, timestamp, module version. Corrections must be traceable and
reproducible; never overwrite raw counts in place.

---

## 6. Algorithms

### 6.1 Kernel estimation (`kernels.py`, `esf.py`)

Kernels must be **measured**, not assumed. Provide three estimation routes:

**(a) Single-pulse response.** Fit eq. (2) to the decay of an isolated pulse (e.g. NIST 610).
Return single- and double-exponential fits with AIC/BIC comparison. Test whether `h` is
element-dependent (it usually is not, since it is aerosol transport, but memory-prone elements such
as Hg, B, and Au deviate — report per-analyte fits and flag outliers).

**(b) Edge-spread function from a sharp material couple.** The along-line PSF is the derivative of
the ESF. Fit the analytic **exponentially modified Gaussian** (Gaussian spot ⊛ causal exponential):

$$\mathrm{PSF}(s) = \frac{1}{2\tau_s}\exp\!\left(\frac{\sigma^2}{2\tau_s^2} - \frac{s-\mu}{\tau_s}\right)\mathrm{erfc}\!\left(\frac{\sigma}{\sqrt{2}\,\tau_s} - \frac{s-\mu}{\sqrt{2}\,\sigma}\right) \tag{5}$$

Fit its cumulative form to the measured edge profile, with free parameters `(µ, σ, τ_s, level_A,
level_B)`. Scanning the same edge in both directions and confirming that `τ_s` reverses sign
relative to the scan direction is the validation that the asymmetry is washout and not real zoning.

**(c) In-situ estimation from the sample itself** (§7.3) — fit eq. (5) to unmixed fraction profiles
across internal phase boundaries. This is the preferred production route because it requires no
extra standards and captures session-specific conditions.

**Closure check (mandatory test):** the PSF from route (b) must equal `K ⊛ Π ⊛ h_s` built from
route (a) within tolerance. Implement as a test, and expose as a QC report.

### 6.2 Location mismatch — exact correction

`δ_j` is known from the sweep schedule. Two implementations, in order of preference:

1. **Fold into the operator.** `A` samples analyte `j` on a comb offset by `δ_j/Δt` pixels. No
   resampling, no noise correlation. This is correct and is the default.
2. **Resample** (only for the quick-look path): band-limited (sinc/Lanczos) or cubic-spline shift.
   Document that this correlates noise between neighboring samples and therefore invalidates the
   pure-Poisson likelihood downstream.

### 6.3 Washout — recursive inverse (`washout.py`)

For a single exponential sampled at `Δt`, with `a = exp(−Δt/τ)`, the measurement is AR(1):

$$m[n] = a\,m[n-1] + (1-a)\,u[n] \quad\Longrightarrow\quad u[n] = \frac{m[n] - a\,m[n-1]}{1-a} \tag{6}$$

An exact two-tap FIR inverse — no FFT, no ringing. Noise amplification (white-noise approximation):

$$\frac{\mathrm{Var}(\hat u)}{\mathrm{Var}(m)} \approx \frac{1 + a^2}{(1-a)^2} \tag{7}$$

Benign for `τ ≲ Δt`; severe for `τ ≫ Δt`. **Implement eq. (7) as a reported diagnostic** so the user
sees the noise penalty before accepting the result.

For a double exponential, the discrete transfer function is two-pole/one-zero:

$$H(z) = \frac{b_0 + b_1 z^{-1}}{1 - a_1 z^{-1} - a_2 z^{-2}}$$

so the inverse filter is recursive with a pole at `−b₁/b₀`. **Check minimum phase** (`|b₁/b₀| < 1`)
and refuse to run the naive inverse if violated; fall back to the regularized solver.

Because eq. (6) is unconstrained it will produce negative counts wherever a large-contrast tail is
subtracted from a low-abundance phase. Provide it as the fast path, but make the **positivity-
constrained Poisson solver (§6.4) the default** for quantitative work.

### 6.4 Regularized inversion (`deconv.py`, `priors.py`)

MAP estimate with Poisson likelihood, positivity, and an edge-preserving prior:

$$\hat{c} = \arg\min_{c \ge 0}\ \sum_i \Big[(Ac)_i - d_i \ln (Ac)_i\Big] + \lambda\, R(c) \tag{8}$$

Poisson (not Gaussian) because count rates in trace-element maps are low and Poisson correctly
down-weights low-count pixels.

**Prior — joint (vector) TV across analytes.** Mineral boundaries are shared by all analytes:

$$R_{\mathrm{VTV}}(c) = \sum_{\mathbf{x}} \sqrt{\sum_j \|\nabla c_j(\mathbf{x})\|^2} \tag{9}$$

The coupling lets high-count majors stabilize edge locations for noisy traces. This is the single
largest expected accuracy gain of the deconvolution stage; scalar per-analyte TV is a strictly worse
baseline and should exist only for comparison.

**Solvers, implement in this order:**

1. **Richardson–Lucy** (EM for Poisson + positivity), with one-step-late TV damping:
   $$c^{(k+1)} = \frac{c^{(k)}}{A^\top \mathbf{1} + \lambda\, \partial R/\partial c}\ \odot\ A^\top\!\left(\frac{d}{A c^{(k)}}\right) \tag{10}$$
   Simple, robust, good baseline. Guard the denominator; clamp `Ac` away from zero.
2. **Chambolle–Pock (PDHG)** for the full non-smooth problem. The proximal operator of the Poisson
   term `f(x) = x − d log x` is closed form:
   $$\mathrm{prox}_{\sigma f}(y) = \tfrac{1}{2}\left[(y - \sigma) + \sqrt{(y-\sigma)^2 + 4\sigma d}\right] \tag{11}$$

`A` and `Aᵀ` must be **matrix-free** (`scipy.sparse.linalg.LinearOperator`). The along-line part is a
per-line 1D convolution (embarrassingly parallel across lines); the spot kernel is a 2D FFT. Verify
the adjoint numerically with a dot-product test — `⟨Ax, y⟩ == ⟨x, Aᵀy⟩` to machine precision — as a
required unit test.

**λ selection:** provide (i) manual, (ii) discrepancy principle against the Poisson expectation
(normalized residual → 1), (iii) L-curve. Report the chosen value.

### 6.5 Unmixing (`unmix.py`)

**Step 1 — cluster to identify phases.** Fuzzy c-means in **log or ilr space** (traces are
lognormal-ish and span orders of magnitude). Use the FCM membership

$$u_{ik} = \left[\sum_{l}\left(\frac{\|v_i - \mu_k\|}{\|v_i - \mu_l\|}\right)^{2/(m-1)}\right]^{-1} \tag{12}$$

**only** for (a) phase labeling and (b) flagging ambiguous pixels via low `max_k u_ik`.

> **Critical:** `u_ik` is *not* a mass fraction. It is an inverse-distance weight controlled by the
> fuzzifier `m` — changing `m` changes every "fraction" while the data are unchanged. It is
> monotonic in `f_A` along a binary tie-line and equals 0.5 at the midpoint by symmetry, but is
> nonlinear elsewhere. Compute fractions from the physics (step 3). Emit a warning if any code path
> attempts to use memberships as fractions.

**Step 2 — endmembers from core pixels.** Mixed pixels drag cluster centroids along the tie-line.
Estimate `v_k` from eroded phase masks (high membership, morphologically eroded by ≥ 2 PSF widths),
then iterate: cluster → erode → recompute `v_k` → unmix → re-cluster. Also implement a
simplex-vertex alternative (VCA, N-FINDR, or archetypal analysis), which targets the vertices rather
than the means and is more appropriate when mixed pixels are abundant.

For zoned minerals a single point in composition space is wrong. Support optional **endmember
fields** `v_k(x)`, smoothly varying within a grain (low-order polynomial or heavily smoothed), with
sharp variation carried entirely by `f`.

**Step 3 — fractions in linear counts space.** Mixing is linear in mass, hence in counts:
`v_obs = f_A v_A + (1 − f_A) v_B`. Cluster in log/ilr space, then transform back — mixing lines are
straight in linear space and **curved** in log-ratio space. Closed-form weighted projection onto the
tie-line:

$$\hat{f}_A = \frac{(\mathbf{v}_{\mathrm{obs}} - \mathbf{v}_B)^\top W (\mathbf{v}_A - \mathbf{v}_B)}{(\mathbf{v}_A - \mathbf{v}_B)^\top W (\mathbf{v}_A - \mathbf{v}_B)},\qquad \text{clipped to } [0,1] \tag{13}$$

with `W = diag(1/σ_j²)` (Poisson: `σ_j² ≈ d_j`, floored to avoid division by zero). High-count
majors dominate, as they should. For `K_ph > 2` candidates (triple junctions, boundary + inclusion),
use sum-to-one-constrained NNLS: augment the design matrix with a row of ones weighted by a large
`ρ` and solve with `scipy.optimize.nnls`.

**Step 4 — residual map as a hypothesis test.** With `J ≫ K_ph`, the system is heavily
overdetermined, so

$$r(\mathbf{x}) = \big\|\mathbf{v}_{\mathrm{obs}} - \hat{f}_A\mathbf{v}_A - (1-\hat{f}_A)\mathbf{v}_B\big\|_W \tag{14}$$

is a per-pixel test of the binary-mixture hypothesis. Normalize to a reduced χ² with `J − 1` degrees
of freedom. High residual ⇒ third phase, sub-spot inclusion, internal zoning, or residual washout
contamination. **Expose `r(x)` as a first-class output layer** — it localizes exactly the pixels the
other corrections must handle.

**Caveat to document in the API:** `f` is an *ablated-mass* fraction, not an areal fraction. Phases
with different ablation yields bias the geometric interpretation (not the mass bookkeeping).

### 6.6 Fraction-space inversion — the target architecture

Substituting the mixing model into the forward model:

$$c_j(\mathbf{x}) = \sum_k f_k(\mathbf{x})\, v_{kj} \quad\Longrightarrow\quad d_j = \sum_k (A f_k)\, v_{kj} + \varepsilon_j \tag{15}$$

Every analyte map is generated by the same `K_ph` fraction fields, and the blur acts on them
identically. Invert for `f_k` rather than for `J` separate concentration maps:

- unknowns reduced from `J` maps to `K_ph ≪ J` maps;
- natural hard constraints `0 ≤ f_k ≤ 1`, `Σ_k f_k = 1` (simplex projection in `priors.py`);
- the prior is far stronger — fractions are near-binary and piecewise constant;
- trace elements inherit sharp boundaries from the majors through the *physics*, not through a
  regularizer, and the problem is correspondingly better conditioned.

Optionally solve jointly for `v_kj` (blind/semi-blind), initialized from §6.5 — but keep this behind
a flag, and validate against the fixed-endmember case first.

### 6.7 Inclusions and point sources (`inclusions.py`)

Decompose `c = c_bg + Σ_k m_k δ(x − x_k)`, with **L1 sparsity** on the point-source layer and TV on
the background. A sub-spot inclusion produces, in the data, a scaled copy of the along-line PSF —
spike plus exponential tail — so:

1. **Matched filter** the data against the PSF template to localize inclusions and estimate total
   masses `m_k`. Note that `m_k` is well determined even when peak concentration is not.
2. **Subtract fitted tails** to decontaminate downstream pixels along the line.
3. **Interline discrimination:** a spike present in one line but absent in both neighbors bounds the
   object's cross-line extent below the line spacing ⇒ inclusion. A feature coherent across lines ⇒
   lamella or vein ⇒ belongs in the TV background, not the sparse layer. Implement this test
   explicitly; it is the main disambiguator.

### 6.8 Diagnostics (`diagnostics.py`)

- **Anisotropy of autocorrelation.** Neither smearing nor washout acts cross-line, so the cross-line
  direction is an uncontaminated reference. Along-line vs. cross-line autocorrelation width measures
  residual along-line blur directly, before and after correction.
- **Residual whiteness.** Post-inversion residuals `(d − Ac)/√(Ac)` should be ~N(0,1) and spatially
  white. Report Ljung–Box or a 2D power spectrum; structured residuals indicate kernel misfit.
- **Mass conservation.** `Σ A c == Σ c` to within edge effects. Unit-test it.
- **Noise amplification** from eq. (7), reported per analyte.

---

## 7. Ordering constraints (do not violate)

1. **Deconvolve before ratioing.** `h * c_A / (h * c_B) ≠ h * (c_A / c_B)`. Ratios cancel
   multiplicative common-mode ablation-yield fluctuations but do **not** remove washout, and a mixed
   pixel's ratio is a nonlinear count-weighted blend. Internal standardization and calibration are
   strictly downstream of all corrections.
2. **Cluster in log/ilr space; unmix in linear counts space.** (§6.5 step 3)
3. **Estimate endmembers from eroded cores, not from all pixels.** (§6.5 step 2)
4. **Correct `δ_j` inside the operator, not by resampling**, whenever the Poisson likelihood is used
   downstream.

---

## 8. Staged implementation plan

Each stage ships with tests and a phantom-based acceptance criterion.

**Stage 0 — Infrastructure.**
`AcquisitionModel`, YAML schema + validation, xarray I/O, provenance logging, phantom generator
(§9.1), metrics (§9.3). *Accept:* round-trip a phantom through I/O with no data change; metadata
validation rejects malformed configs.

**Stage 1 — Forward operator.**
`K`, `Π`, `h_s`, `δ_j`, per-line scan direction; matrix-free `A`/`Aᵀ`. *Accept:* adjoint dot-product
test to machine precision; mass conservation; a simulated edge reproduces the analytic EMG of
eq. (5).

**Stage 2 — Kernel estimation.**
Single-pulse fitting, ESF fitting, closure check. *Accept:* recovers phantom `(σ, τ, boxcar)` within
5% at realistic count rates; bidirectional sign flip detected correctly.

**Stage 3 — Fast 1D correction path.**
`δ_j` shift + recursive washout inverse (eq. 6), per line, with noise-amplification reporting.
*Accept:* boundary localization error < 0.25 pixel on a noiseless phantom; documented failure mode
(negative counts) reproduced and reported rather than hidden.

**Stage 4 — Poisson RL with positivity.**
Per-line 1D first, then full 2D with the spot kernel. *Accept:* beats Stage 3 in RMSE at realistic
Poisson noise; no negative values; monotone likelihood improvement.

**Stage 5 — Unmixing and the residual layer.**
FCM/archetypal endmembers, weighted tie-line projection (eq. 13), NNLS for `K_ph > 2`, residual map
(eq. 14). *Accept:* recovers phantom `f_A` with bias < 0.02 in boundary pixels; residual map flags
≥ 90% of planted inclusions and third-phase pixels.

**Stage 6 — Joint vector-TV deconvolution.**
Chambolle–Pock, eq. (8)–(9)+(11). *Accept:* trace-element boundary localization improves measurably
relative to scalar TV at matched data fidelity.

**Stage 7 — Fraction-space inversion.**
Eq. (15) with simplex constraints. *Accept:* better conditioned and lower fraction RMSE than
Stage 6 → post-hoc unmixing, on phantoms with low-count traces.

**Stage 8 — Sparse inclusion layer.**
Matched filtering, L1 layer, interline discrimination. *Accept:* recovers planted inclusion masses
within 10%; correctly separates a one-line spike from a cross-line-coherent lamella.

**Stage 9 — LaME UI integration.** Out of scope here; design the API so a dock widget only needs
`pipeline.run()` plus the diagnostic layers.

---

## 9. Test harness

### 9.1 Phantom generator (`phantom/generate.py`)

Parameterized synthetic scenes with known ground truth:

- **P1 — Straight vertical boundary**, two phases, contrast 10× and 1000×. Tests everything 1D.
- **P2 — Boundary oblique to the scan direction.** Separates along- from cross-line effects.
- **P3 — Sub-spot inclusion** in a low-abundance matrix, contrast 10⁴, placed both on-line and
  between lines.
- **P4 — Triple junction**, three phases.
- **P5 — Zoned grain**, smooth internal gradient inside a sharp exterior boundary. Tests that TV
  does not staircase real zoning and that endmember fields are needed.
- **P6 — Realistic composite**: several grains, a vein, scattered inclusions, `J = 20` analytes
  spanning 6 orders of magnitude in count rate.

All must support bidirectional scanning, configurable `τ`, `σ`, `Δt`, `v`, line spacing, and Poisson
noise at specified count rates. Ground truth `c_j`, `f_k`, `v_kj`, and inclusion positions/masses
are returned alongside the simulated data.

### 9.2 Reference invariants (unit tests)

- `∫h = 1`; `Σ(Ac) = Σc` up to edge truncation.
- Adjoint dot-product test.
- Eq. (6) exactly inverts a noiseless AR(1) sequence.
- Reversing scan direction reverses the sign of the fitted `τ_s` in eq. (5).
- Unmixing a pure endmember returns `f = 1` and residual ≈ 0.
- `A` applied to a constant field returns that constant (interior).

### 9.3 Metrics (`phantom/metrics.py`)

- **Boundary localization error** (sub-pixel, from fitted ESF center) — the headline metric.
- Per-analyte RMSE and bias, stratified by count rate.
- Fraction RMSE, and bias specifically in boundary pixels.
- Inclusion mass recovery and false-positive/negative rates.
- Effective resolution: along-line vs. cross-line autocorrelation width, before/after.
- Noise amplification realized vs. predicted by eq. (7).

Every stage's benchmark results should be reproducible from a single scripted entry point and
recorded to a results file for regression tracking.

---

## 10. Numerical pitfalls to guard against

- **Zeros in the Poisson likelihood.** Clamp `Ac ≥ ε`; do not take `log 0`.
- **Negative counts** after unconstrained inverse filtering — expected, must be reported, never
  silently clipped without a flag.
- **Edge effects** at line starts/ends: the causal tail requires either an equilibration prefix or
  explicit masking. Do not wrap-around (no circular convolution) — the physics is causal, not
  periodic.
- **Fractional-pixel shifts** must be exact within the operator; the `δ_j` comb offset is generally
  not an integer number of samples.
- **Dead time and detector mode switching** (pulse↔analog) break Poisson statistics. Detect and flag
  affected pixels; do not attempt to deconvolve across a mode switch without correction.
- **Down-hole fractionation** in raster mode adds a slow along-line trend distinct from washout —
  do not absorb it into `τ`. Consider an explicit slow-trend term or pre-detrending.
- **Memory-prone elements** (Hg, B, Au) may have genuinely element-specific, longer `h` — support
  per-analyte `τ` and flag deviants.
- **Float32 vs float64:** accumulate solver state in float64; store outputs in float32.

---

## 11. Prior art to consult before finalizing parameterizations

Work by van Elteren and coworkers (in *J. Anal. At. Spectrom.*) on modeling and deconvolving
LA-ICP-MS image degradation is directly relevant to §3 and §6.1 and should be reviewed for kernel
parameterization conventions and reported washout time constants. Hyperspectral unmixing literature
(VCA, N-FINDR, archetypal analysis) covers §6.5 step 2 thoroughly. Poisson image deconvolution with
TV (Richardson–Lucy variants, Chambolle–Pock) covers §6.4.

---

## 12. Open questions for the maintainer

1. Is `h` measurably element-dependent on the target instrument? Determines whether `A` is separable
   across analytes.
2. Are exported datasets consistently bidirectional or unidirectional? Affects default config.
3. Should the spot kernel `K` include depth-dependent ablation weighting, or is a 2D footprint
   adequate at the fluences in use?
4. Preferred `K_ph` selection: user-specified, or automatic (silhouette / gap statistic / fuzzy
   validity index)?
5. Does LaME's existing project schema have a natural home for the derived layers (`f_k`, residual
   map, inclusion catalog), or is a new group needed?
