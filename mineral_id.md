Mineral identification using an LA-ICP-MS is not necessarily the ideal way to classify mineralogy because there are faster more accurate and higher resolution methods.  However, if all you have is the LA-ICP-MS map, or we want to classify pixels based on composition, then we need a way to do this.  I have used clustering (k-means, fuzzy c-means) to determine the different classes.  It works well with large classes so major minerals, but perhaps not as well when there are some minerals that are a small fraction of the number of pixels.  I'd like to think about ways to do this.  There at least two reasons to do so, determining the percentage of each type of mineral and determining the specific compositions of individual minerals.  We of course would need a library to associate the compositions with specific minerals or solid solutions.  The other challenge with classifying pixels is that it is often random pixels and not combined by any geometric affinity.  There are challenges with mixed pixels of three types, ones that sit on boundaries or in cracks and inclusions where the feature mixes mineral compositions in a single pixel.

What I'm looking for are some ideas to move forward with a mineral identification, classification and area statistics.
This is a nice problem because it sits at the intersection of three literatures that mostly don't talk to each other: compositional data analysis, hyperspectral unmixing from remote sensing, and automated mineralogy (QEMSCAN/TIMA-style). Let me work through the pieces, because I think the mixed-pixel problem and the rare-phase problem actually want different machinery, and lumping them into one clustering step is why k-means/FCM underperforms.

## Reframe: unmixing, not clustering

The physically correct model for an LA-ICP-MS pixel is a linear mixture. The ablated volume samples a mass-weighted combination of phases, so for pixel $i$ with measured composition $\mathbf{x}_i$ (element mass fractions or calibrated concentrations):

$$\mathbf{x}_i = \sum_{k=1}^{K} f_{ik}\,\mathbf{m}_k + \boldsymbol{\epsilon}_i, \qquad f_{ik} \ge 0, \quad \sum_k f_{ik} = 1$$

where $\mathbf{m}_k$ are endmember (mineral) compositions and $f_{ik}$ are *mass* fractions of ablated material. This is exactly the linear mixing model from hyperspectral imaging, and it's arguably *more* valid for LA-ICP-MS than for reflectance spectra, where linearity is an approximation. The caveats are ablation-yield differences between phases (a soft mineral in a crack contributes disproportionate mass per unit area) and the fact that the mixing kernel isn't just the pixel—it's the spot plus washout smearing, which is why your forward-model deconvolution work should sit upstream of any classification. Classify the deconvolved map, not the raw one.

This reframing buys you three things at once:

1. **Mixed pixels are no longer a nuisance class.** A boundary pixel is just a pixel with two nonzero $f_{ik}$. You don't need to either force it into a cluster or discard it.
2. **Endmember extraction algorithms exist that are specifically good at geometry, not density.** Vertex Component Analysis (VCA), N-FINDR, and simplex volume maximization find the *vertices* of the data simplex. A rare mineral that appears pure in even a handful of pixels defines a vertex regardless of how few pixels it occupies—this directly attacks your small-class problem, which is fundamentally a density-weighting pathology of k-means/FCM (their objective is dominated by the big clusters, so a phase that's 0.5% of pixels gets absorbed as "noise" in a major cluster).
3. **Area statistics become sums of fractions**, which is statistically better than hard counts (more below).

Archetypal analysis is the statistics-literature version of the same idea and has decent Python implementations; NMF with a sum-to-one constraint is another route, though vanilla NMF vertices aren't guaranteed to be near data points, which matters for interpretability.

## The rare-phase problem specifically

Even with vertex-seeking methods, a mineral that *never* appears pure (e.g., micron-scale zircon inclusions smaller than your spot) has no vertex in the data. Two complementary strategies:

**Hierarchical peeling.** Fit the major phases first (FCM or unmixing with small $K$), then compute residuals $\mathbf{r}_i = \mathbf{x}_i - \hat{\mathbf{x}}_i$ and analyze the residual map. Accessory phases scream in residual space: a pixel that's 95% plagioclase + 5% monazite fits the plagioclase model except for a wildly anomalous LREE+P residual. Cluster or threshold the residuals, add the implied endmembers, refit. This is essentially matching pursuit over minerals.

**Chemical gating.** Accessories are usually the *reason* people run these maps, and they have pathognomonic signatures: Zr for zircon, P+LREE for monazite, P+Ca for apatite, Ti for rutile/titanite, Cr for chromite. A rule-based prescreen (flag pixels where Zr > threshold, etc.) before clustering, with flagged pixels excluded from the major-phase fit and handled separately, is unglamorous but robust, and it's how the commercial automated-mineralogy packages actually work under the hood. In LaME this could be a user-editable gate table rather than hardcoded rules.

Also worth trying: HDBSCAN in a log-ratio space. Density-based clustering doesn't force rare points into big clusters and naturally labels boundary-mixed pixels as "noise" (unclustered), which you can then unmix against the identified cores. The clr/ilr transform matters here—Euclidean distance on raw concentrations is dominated by SiO₂ and the majors, whereas log-ratio distance treats a 10× enrichment in Zr as equally informative as a 10× change in Si. Given your prior compositional-data work, I'd default to clr with a multiplicative replacement for zeros/censored values, and be aware that FCM in clr space with a Euclidean metric is a different (better-behaved) animal than FCM on concentrations.

## Distinguishing the three mixed-pixel types

Composition alone can't separate boundary pixels from crack-fill from inclusions—they're all mixtures. Geometry can:

- **Boundary pixels**: the two dominant endmembers in the unmixed fractions should match the classified phases of the pixel's neighbors on either side, and boundary pixels form connected curvilinear sets. Test: does $\arg\max_2 f_{ik}$ agree with adjacent domain labels?
- **Inclusions**: isolated pixels (or small blobs) whose minor endmember does *not* appear in any neighbor. Morphologically: high residual/minor-fraction pixels that survive an opening operation on the major-phase mask.
- **Cracks/fill**: linear features, often with a characteristic contaminant signature (alteration phases, epoxy elements), detectable with a ridge filter (Frangi/Hessian-based) on the minor-fraction map.

More formally, a Markov random field prior on the labels—Potts model, solved with graph cuts (`PyMaxflow` is fine)—gives you spatial regularization with a single smoothness parameter $\beta$:

$$\hat{\mathbf{z}} = \arg\min_{\mathbf{z}} \sum_i -\log p(\mathbf{x}_i \mid z_i) + \beta \sum_{\langle i,j \rangle} \mathbb{1}[z_i \ne z_j]$$

My honest take: for mineral maps a full MRF is often overkill and can erase real fine-scale features (exactly the accessories you care about). A lighter touch—unmix per-pixel, then apply spatial logic only to *interpret* mixed pixels, not to relabel them—preserves more information. I'd prototype the light version first.

## Library matching and solid solutions

For attaching names, convert mineral formulas to expected element mass fractions and match in log-ratio space. Two important design decisions:

**Solid solutions are lines and planes, not points.** Plagioclase is a segment between albite and anorthite compositions; match by projecting the pixel/endmember composition onto the segment and reporting both the mineral and the solved composition parameter ($X_{An}$). Generally, a solid solution with $p$ independent substitutions is a $p$-dimensional simplex in composition space, and the match is a constrained least-squares projection. This is a feature, not a bug—it delivers your second goal (specific compositions of individual minerals) as a byproduct: the fitted endmember composition per grain, or even a per-pixel $X_{An}$ map within the plagioclase domain.

**LA-ICP-MS doesn't give you closed compositions.** You typically calibrate to an internal standard and don't measure O, and light elements (Li, Be, B may be there, but H, C aren't). So the match metric should be built on ratios of measured elements only—subcompositional coherence is exactly what the log-ratio framework guarantees. A stoichiometric sanity check (cation ratios: Si/Al, Ca/(Ca+Na), Mg#) as a secondary filter catches misidentifications that pass a distance test.

Prior art worth mining: XMapTools does supervised classification + solid-solution projection for EPMA maps and its papers (Lanari et al.) document the machinery; the mineral library problem itself has been solved several times (you could bootstrap from the RRUFF/IMA list plus a curated set of ~50 rock-forming formulas rather than anything exhaustive).

## Area statistics done right

With hard classification, modal abundance is a pixel count and mixed pixels bias it (boundary pixels systematically inflate whichever phase wins the argmax). With unmixing, the unbiased estimator is the mean fraction:

$$\hat{A}_k^{(\text{mass})} = \frac{1}{N}\sum_i f_{ik}$$

Two corrections matter:

1. **Mass vs. area/volume.** $f_{ik}$ are ablated-mass fractions. Modal mineralogy is conventionally volume (or area) percent: $A_k^{(\text{vol})} \propto \hat{A}_k^{(\text{mass})} / \rho_k$, normalized. Densities come free with the library. Differential ablation yield is a second-order correction you probably flag rather than fix.
2. **Uncertainty.** Pixel values are spatially correlated (spot overlap, washout), so a naive binomial error on the count is optimistic. Block bootstrap over spatial tiles gives honest confidence intervals on modes, and it's cheap.

## A pipeline sketch for LaME

1. Deconvolve/correct with your forward model (washout, smearing).
2. Transform to clr (or ilr) with censored-value handling.
3. Chemical gates flag candidate accessory pixels (user-editable table).
4. Extract major endmembers (VCA or FCM cluster centers on ungated pixels—your existing FCM slots in here; the FCM memberships with $m \to$ appropriate fuzzifier are a serviceable stand-in for $f_{ik}$ if you don't want a separate NNLS step, though constrained least squares against fixed endmembers is more physical).
5. Per-pixel NNLS unmixing against the endmember set; residual analysis → add accessory endmembers → refit.
6. Library match endmembers (point minerals + solid-solution projections), report solved compositions.
7. Spatial interpretation pass: label boundary/inclusion/crack pixels using fraction maps + morphology.
8. Modal statistics from summed fractions with density correction and block-bootstrap CIs.

The single highest-leverage change from what you're doing now is step 5: replacing "every pixel gets a cluster" with "every pixel gets a fraction vector." It converts your two failure modes—rare phases and mixed pixels—from bugs into measurements. If you want, I can work through the constrained unmixing math (NNLS with sum-to-one via the standard augmentation trick, and how it interacts with clr space, which is subtle because linear mixing is linear in *concentrations*, not in log-ratios—so you unmix in raw space but cluster/match in log-ratio space), or prototype the residual-peeling loop on synthetic data.