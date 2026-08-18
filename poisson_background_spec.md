# Spec: Poisson-Aware Background Estimation, Drift Correction, and Detection Limits

**Target:** LaME calibration module (LA-ICP-MS raw data reduction)
**Status:** Design spec for implementation
**Context:** Background subtraction currently uses mean ± SE per background window and an
ordinary least-squares polynomial drift fit. This fails for low-count channels where the
background is mostly zero with occasional single-ion events. This spec replaces that with a
unified Poisson treatment that also handles high-count channels correctly.

---

## 1. Problem statement

For many trace-element channels (e.g., Yb172), background windows report mostly 0 CPS with
occasional values quantized at multiples of a fixed step (~3.2, ~6.4, ~9.6 CPS). These are
individual Poisson counting events (1, 2, 3 ions) divided by the counting time, not a
continuous background with Gaussian noise. Consequences of the current Gaussian treatment:

1. **SE = 0 for all-zero windows** — asserts perfect knowledge of the background where
   uncertainty is actually largest (95% one-sided Poisson upper limit for 0 observed counts
   is 3.0 counts).
2. **OLS polynomial drift fit** is invalid: wrong error model (homoscedastic Gaussian vs.
   Poisson, Var = mean), can go negative, and fits noise — at λ ≈ 0.2 counts/window over
   ~100 windows there are only ~20 total counts, with no statistical power to resolve drift.
3. **Background level and detection limit are conflated.** For near-zero backgrounds the
   background estimate is a fraction of a count, but the detection limit is several counts
   (Currie's constant term: L_D = 2.71 counts even at zero background).

## 2. Design overview

One code path for all channels, built on a Poisson GLM:

```
raw CPS ──► recover integer counts (Section 3) ──► Poisson GLM drift fit + LRT (Section 4)
                                                        │
                                                        ├─► background rate λ̂(t) + CI
                                                        ├─► Currie L_C, L_D (Section 5)
                                                        └─► subtraction + uncertainty (Section 6)
```

- **Low-count channels:** GLM collapses to a pooled constant (LRT rejects drift), exact
  Poisson intervals, Currie limits from counting statistics.
- **High-count channels:** GLM is asymptotically equivalent to weighted least squares;
  Gaussian behavior is recovered automatically in the large-μ limit. No per-element
  branching needed.
- **Counts unavailable:** graceful degradation via quasi-Poisson or conservative bounds
  (Section 3.3), with provenance surfaced in the UI.

## 3. Recovering integer counts from CPS

All statistics below are natural in counts, n = CPS × τ, where τ is the effective counting
time per reported value (dwell × sweeps averaged). τ may not be supplied by the user.

### 3.1 Preferred: user-supplied or file-metadata dwell times

If the import format carries dwell/sweep metadata, use it: τ = dwell_time × n_sweeps per
channel. Always run the quantization estimator (3.2) anyway as a cross-check; disagreement
indicates metadata errors (wrong sweep count is common).

### 3.2 Fallback: infer τ from quantization

If the instrument reports CPS = n/τ with integer n, every reported value is an integer
multiple of the elementary step Δ = 1/τ. Estimate Δ as the effective GCD of the distinct
nonzero low values, robust to float noise, via grid search:

```python
import numpy as np

def estimate_quantum(cps, dmin=0.1, dmax=100.0, nsteps=20000):
    """Estimate elementary CPS step Delta = 1/tau from quantized data.

    Only works when counts are low enough that quantization is visible —
    which is exactly the regime where the Poisson treatment is needed.
    Returns None if not estimable.
    """
    v = np.asarray(cps, float)
    v = v[v > 0]
    if len(v) < 3:
        return None
    deltas = np.geomspace(dmin, dmax, nsteps)

    def score(d):
        r = v / d
        # variance-normalized distance from nearest integers so larger n
        # (larger absolute float error) is not unfairly penalized
        return np.mean((r - np.round(r)) ** 2 / np.maximum(np.round(r), 1))

    s = np.array([score(d) for d in deltas])
    # Harmonics: if Delta fits, so do Delta/2, Delta/3, ...
    # The true quantum is the LARGEST candidate achieving near-minimum score.
    good = s < 1.05 * s.min() + 1e-12
    return deltas[good].max()


def cps_to_counts(cps, delta):
    """Convert CPS to integer counts given quantum delta. Returns (n, tau) or (None, None)."""
    n = np.round(np.asarray(cps) / delta)
    ok = np.allclose(cps, n * delta, rtol=0, atol=0.25 * delta)
    return (n.astype(int), 1.0 / delta) if ok else (None, None)
```

**Cross-channel consistency check:** all isotopes in one method usually share dwell
structure. Estimate Δ per low-count channel; require agreement (identical τ or small-integer
ratios). Agreement across ≥3 channels → high confidence; apply recovered τ to channels where
quantization was marginal.

**Known failure modes:**
- High-count channels: quantization invisible. Not a problem — Gaussian treatment is valid
  there and does not need counts (Section 4, large-μ limit; empirical variance suffices).
- Data already interpolated/smoothed/drift-corrected upstream: quantization destroyed.
- Dead-time correction: nonlinear rescaling destroys exact quantization, but at background
  rates of a few CPS the effect is ~1e-6 and irrelevant. At high rates it matters, but high
  rates ⇒ Gaussian regime anyway.
- Dual detector modes (pulse vs. analog cross-calibrated per sweep) can produce two
  interleaved quantization ladders. Signature: GCD search returns a suspiciously small Δ
  with a subset of points non-integer. Flag rather than force.

### 3.3 Degraded mode: counts unrecoverable

- **Quasi-Poisson GLM:** same log-link fit, dispersion φ estimated so Var = φμ. Caveat:
  with mostly-zero data φ is poorly constrained; L_C/L_D inherit that vagueness.
- **Conservative bound:** smallest distinct nonzero CPS value is an integer multiple of the
  quantum ⇒ Δ ≤ min(cps > 0) ⇒ τ ≥ 1/min(cps > 0). Gives conservative (large) detection
  limits.
- **UI provenance requirement:** surface the counting-time provenance, e.g.
  - "Counting time inferred from data: 0.31 s (high confidence, 5 channels agree)"
  - "Counting time unknown; detection limits are approximate (conservative bound)"

## 4. Drift model: Poisson GLM with likelihood-ratio test

Model per channel, with background windows indexed by i:

    n_i ~ Poisson(mu_i),    log(mu_i) = log(tau_i) + sum_{k=0..p} beta_k * t_i^k

- `log(tau_i)` offset handles unequal counting times.
- Log link guarantees positive predicted background.
- Poisson likelihood correctly weights zero-heavy data.

Test whether drift is statistically supported: likelihood-ratio test of order-p polynomial
vs. constant (p = 0). Deviance difference ~ chi-square(p) under H0.

```python
import numpy as np
import statsmodels.api as sm
from scipy.stats import chi2

def fit_background_drift(n, tau, t, max_order=3, alpha=0.05):
    """n: integer counts per background window; tau: counting time (s); t: window times.

    Returns fitted GLM (drift model if LRT significant, else constant model).
    Predicted background rate in CPS = model.predict(...) / tau.
    """
    t = (t - t.mean()) / t.std()          # condition the polynomial
    offset = np.log(tau)

    X0 = np.ones((len(n), 1))
    m0 = sm.GLM(n, X0, family=sm.families.Poisson(), offset=offset).fit()

    Xp = np.vander(t, max_order + 1, increasing=True)
    mp = sm.GLM(n, Xp, family=sm.families.Poisson(), offset=offset).fit()

    lr = m0.deviance - mp.deviance
    p_val = chi2.sf(lr, df=max_order)
    return (mp, p_val) if p_val < alpha else (m0, p_val)
```

**Constant-model estimate** (the usual outcome for low-count channels):

    lambda_hat = (sum n_i) / (sum tau_i)

with the exact (Garwood) confidence interval, N = sum(n_i), T = sum(tau_i):

    lower = chi2.ppf(alpha/2, 2N) / (2T)          # 0 if N == 0
    upper = chi2.ppf(1 - alpha/2, 2N + 2) / (2T)

Note: an all-zero channel gets lambda_hat = 0 but upper ≈ 3.0/T — the interval is never
degenerate, unlike SE = 0 under the current Gaussian treatment.

**High-count behavior:** for λτ ≳ 20–30 per window the Poisson GLM reproduces weighted
least squares (Gaussian approximation is the large-μ limit of the likelihood), so no
special-casing is required for major-element channels.

**Implementation notes:**
- Consider testing orders incrementally (0 → 1 → 2 → 3) rather than 0 vs. max_order, to
  avoid selecting an order-3 fit when order-1 suffices. AIC across orders is an acceptable
  alternative to sequential LRT.
- Center/scale time before building the Vandermonde matrix (already in the sketch) to avoid
  ill-conditioning over multi-hour sessions.
- statsmodels is the suggested dependency; if avoiding it, Poisson IRLS is ~20 lines of
  numpy, and the constant model needs no solver at all.

## 5. Detection limits (Currie 1968)

Two distinct thresholds, both in **net counts** above background, with μ_B = expected
background counts in the *sample* integration window (background rate × sample counting
time — note the sample integration time may differ from background window time):

- **Critical level L_C** — decision threshold, controls false positives at rate α:
  - Gaussian regime (μ_B large, paired subtraction): L_C = 2.33 √μ_B (α = 0.05)
  - Near-zero regime: smallest n such that P(N ≥ n | μ_B) < α, using the Poisson CDF
    directly.
- **Detection limit L_D** — smallest true signal detected with probability 1 − β:

      L_D ≈ 2.71 + 4.65 √μ_B      (counts, α = β = 0.05)

  The constant term matters: at μ_B = 0 exactly, L_D = 2.71 counts. Example: τ = 0.31 s
  ⇒ L_D ≈ 8.7 CPS even when the background estimate is a fraction of a count. In
  concentration units L_D shrinks as 1/√τ with longer integration.

Report **both** the background estimate (with CI) and L_D per channel. They are different
numbers and both belong in the calibration report/UI.

## 6. Background subtraction and uncertainty propagation

1. Subtract expected background: `n_net = n_gross − λ̂(t) · τ_sample`.
2. **Allow negative net counts.** Do not clip at zero — clipping biases every downstream
   average, filter, and ratio positively. Flag values with n_net < L_C as non-detects for
   display, but retain signed values in the data model.
3. Uncertainty: `Var(n_net) ≈ n_gross + τ_sample² · Var(λ̂)`. The λ̂ term is shared
   (correlated) across all pixels using that background estimate — keep it as a separate
   covariance term for map-level statistics; for low-count channels it is negligible
   against shot noise.

## 7. Suggested module structure

```
tools/calibration/background/
├── quantum.py        # estimate_quantum, cps_to_counts, cross-channel consistency
├── drift.py          # fit_background_drift (Poisson GLM + LRT), Garwood intervals
├── currie.py         # L_C, L_D in counts / CPS / concentration units
├── subtract.py       # net-count subtraction, variance propagation, non-detect flags
└── provenance.py     # counting-time provenance record for UI/report
```

### Public API sketch

```python
@dataclass
class BackgroundResult:
    lambda_fn: Callable[[np.ndarray], np.ndarray]  # background rate CPS vs time
    lambda_ci: tuple                                # (lower, upper) fn or constants
    model: str                                      # "constant" | "poly(k)" | "quasi-poisson"
    drift_pvalue: float
    tau: float | None                               # effective counting time (s)
    tau_provenance: str                             # "metadata" | "inferred" | "bounded" | "unknown"
    L_C_cps: float
    L_D_cps: float
```

## 8. Test cases

1. **Synthetic low-count:** simulate Poisson(λτ = 0.2), 100 windows, verify LRT selects
   constant model ≥ 95% of runs; verify Garwood CI coverage.
2. **Synthetic drift:** λ(t) linearly doubling over session at λτ = 50; verify LRT detects
   drift and GLM matches WLS estimate within tolerance.
3. **Quantum recovery:** synthesize CPS = Poisson(0.3)/0.31 with float32 rounding; verify
   estimate_quantum recovers Δ = 1/0.31 within 1%, and that the harmonic guard picks the
   largest valid Δ.
4. **All-zero channel:** verify λ̂ = 0, CI upper > 0, L_D = 2.71 counts, no divide-by-zero.
5. **Regression vs. current behavior:** high-count channel (λτ = 1000) — new pipeline
   matches existing mean ± SE / OLS results within statistical tolerance.
6. **Real data:** Yb172 session from the motivating figure — confirm quantized levels map
   to n ∈ {0,1,2,3}, constant model selected, L_D ≈ 8–9 CPS.

## 9. References

- Currie, L.A. (1968). Limits for qualitative detection and quantitative determination.
  *Analytical Chemistry* 40(3), 586–593.
- Garwood, F. (1936). Fiducial limits for the Poisson distribution. *Biometrika* 28, 437–442.
