"""Fe2+/Fe3+ (and, in principle, other redox-sensitive element) estimation.

Four modes: all divalent, all trivalent, a fixed user-ratio split, and the
Droop (1987) charge-balance estimate. All four report apfu on
``config.basis`` -- ``"cation"`` uses the T-basis (cation-count-fixed
normalization, ``normalize.normalize_to_cations``; valence-independent,
since moles don't encode charge, so it's the same reference regardless of
which hypothesis is chosen), ``"oxygen"`` uses the S-basis (oxygen-count-
fixed) directly with no further rescale. Which basis a mineral uses tracks
*why* it needs charge-balance in the first place: garnet/olivine/pyroxene/
spinel all do Droop-style estimation, which is mathematically defined in
terms of, and only self-consistent on, the T-basis (see ``normalize.
normalize_to_cations``'s docstring) -- that's genuinely required, not a
style choice, so ``droop_1987`` requires ``basis: cation``. Most other
minerals (MinPlotX's actual convention for anything that doesn't do
charge-balance estimation) report Fe on the S-basis with no rescale, since
there's no T/S reconciliation to justify one.

The scaffolding (S/T bookkeeping, dispatch) is written generically against
``config.redox.elements``, so a future redox-sensitive element reuses it --
but the Droop formula itself is specifically an Fe method from the published
literature; a different element would need its own charge-balance formula
plugged in alongside it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.stoichiometry import normalize
from src.stoichiometry.config import MineralConfig

VALID_METHODS = {"all_2plus", "all_3plus", "droop_1987", "fixed_ratio"}


@dataclass
class RedoxResult:
    method: str
    element: str
    apfu: dict[str, float]      # final apfu, with `element` replaced by `{element}2`/`{element}3`
    species_2plus_apfu: float
    species_3plus_apfu: float
    S: float                    # cation total, all-2+ oxygen-basis (Droop's S)
    T: float                    # ideal cation total (config.ideal_cations)
    residual: float = field(init=False)

    def __post_init__(self):
        self.residual = self.S - self.T


def estimate_fe_split(
    moles: dict[str, float],
    config: MineralConfig,
    method: str | None = None,
) -> RedoxResult:
    """Estimate the divalent/trivalent split for ``config.redox.elements[0]``
    (Fe, for garnet).

    Parameters
    ----------
    moles : dict[str, float]
        Pre-oxygen-normalization cation moles (output of
        :func:`normalize.to_cation_moles`) -- *not* apfu. Passed
        unnormalized so this function can independently renormalize under
        different valence assumptions (all_2plus vs all_3plus need
        different total-oxygen bases).
    config : MineralConfig
    method : str, optional
        One of ``config.redox.methods``; defaults to ``config.redox.default_method``.

    Returns
    -------
    RedoxResult
    """
    if not config.redox.elements:
        raise ValueError("Mineral config declares no redox-sensitive elements.")
    element = config.redox.elements[0]

    method = method or config.redox.default_method
    if method not in VALID_METHODS:
        raise ValueError(f"Unknown redox method {method!r}; expected one of {sorted(VALID_METHODS)}.")
    if method not in config.redox.methods:
        raise ValueError(f"Redox method {method!r} is not enabled for this mineral (config.redox.methods={config.redox.methods}).")
    if method == "droop_1987" and config.basis != "cation":
        raise ValueError("droop_1987 is only self-consistent on the T-basis; this config declares basis="
                          f"{config.basis!r}, expected 'cation'.")

    # T-basis: cation-count-fixed normalization, valence-independent (moles
    # don't encode charge).
    t_basis_apfu = normalize.normalize_to_cations(moles, config)
    T = config.ideal_cations

    # S-basis: oxygen-count-fixed, assuming `element` is fully divalent (e.g.
    # Fe as FeO). Always computed -- needed by droop_1987 as intermediate
    # scaffolding, and as the S/residual diagnostic regardless of method --
    # but only used for *reporting* apfu when config.basis == 'oxygen'.
    s_basis_apfu = normalize.normalize_to_oxygen(moles, config)
    S = sum(s_basis_apfu.values())
    X = config.ideal_oxygens

    reporting_apfu = t_basis_apfu if config.basis == "cation" else s_basis_apfu
    element_total = reporting_apfu.get(element, 0.0)

    if method == "all_2plus":
        apfu = dict(reporting_apfu)
        apfu.pop(element, None)
        apfu[f"{element}2"] = element_total
        return RedoxResult(method=method, element=element, apfu=apfu,
                            species_2plus_apfu=element_total, species_3plus_apfu=0.0, S=S, T=T)

    if method == "all_3plus":
        apfu = dict(reporting_apfu)
        apfu.pop(element, None)
        apfu[f"{element}3"] = element_total
        return RedoxResult(method=method, element=element, apfu=apfu,
                            species_2plus_apfu=0.0, species_3plus_apfu=element_total, S=S, T=T)

    if method == "fixed_ratio":
        # No charge-balance computation -- just split element_total by the
        # user/config-supplied fraction directly (MinPlotX's actual
        # mechanism for most minerals that don't estimate Fe3+ from charge
        # balance; see this module's docstring).
        F = config.redox.fixed_ratio * element_total
        two_plus = element_total - F
        apfu = dict(reporting_apfu)
        apfu.pop(element, None)
        apfu[f"{element}2"] = two_plus
        apfu[f"{element}3"] = F
        return RedoxResult(method=method, element=element, apfu=apfu,
                            species_2plus_apfu=two_plus, species_3plus_apfu=F, S=S, T=T)

    # droop_1987: F = 2 * X * (1 - T/S); clipped to [0, element_total] since
    # neither a negative nor an over-total Fe3+ split is physically meaningful
    # (S <= T means no charge-balance evidence for any Fe3+ at all). F comes
    # out already on the T-basis (see normalize_to_cations' docstring / the
    # module docstring's derivation), so it's used as-is, not rescaled --
    # guaranteed consistent with reporting_apfu here since droop_1987 always
    # requires basis: cation (checked above).
    F = 2.0 * X * (1.0 - T / S) if S > 0 else 0.0
    F = min(max(F, 0.0), element_total)
    two_plus = element_total - F

    apfu = dict(reporting_apfu)
    apfu.pop(element, None)
    apfu[f"{element}2"] = two_plus
    apfu[f"{element}3"] = F
    return RedoxResult(method=method, element=element, apfu=apfu,
                        species_2plus_apfu=two_plus, species_3plus_apfu=F, S=S, T=T)
