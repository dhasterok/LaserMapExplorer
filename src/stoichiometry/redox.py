"""Fe2+/Fe3+ (and, in principle, other redox-sensitive element) estimation.

Three modes: all divalent, all trivalent, and the Droop (1987) charge-balance
estimate. All three start from the same "assume the redox element is in its
lower/reference valence" oxygen-basis normalization -- exactly Droop's own
S-basis convention -- so the three methods are directly comparable.

The scaffolding (S/T bookkeeping, all_2plus/all_3plus/droop_1987 dispatch)
is written generically against ``config.redox.elements``, so a future
redox-sensitive element reuses it -- but the Droop formula itself is
specifically an Fe method from the published literature; a different
element would need its own charge-balance formula plugged in alongside it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.stoichiometry import normalize
from src.stoichiometry.config import MineralConfig

VALID_METHODS = {"all_2plus", "all_3plus", "droop_1987"}


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

    # S-basis: assume `element` is fully divalent (e.g. Fe as FeO) -- this is
    # the fixed reference normalization both Droop's formula and the two
    # simple hypotheses are defined relative to.
    s_basis_apfu = normalize.normalize_to_oxygen(moles, config)
    S = sum(s_basis_apfu.values())
    T = config.ideal_cations
    X = config.ideal_oxygens
    element_total = s_basis_apfu.get(element, 0.0)

    if method == "all_2plus":
        apfu = dict(s_basis_apfu)
        two_plus = apfu.pop(element, 0.0)
        apfu[f"{element}2"] = two_plus
        return RedoxResult(method=method, element=element, apfu=apfu,
                            species_2plus_apfu=two_plus, species_3plus_apfu=0.0, S=S, T=T)

    if method == "all_3plus":
        apfu = normalize.normalize_to_oxygen(moles, config, redox_oxide_overrides={element: normalize.STANDARD_OXIDES[f"{element}3"]})
        three_plus = apfu.pop(element, 0.0)
        apfu[f"{element}3"] = three_plus
        return RedoxResult(method=method, element=element, apfu=apfu,
                            species_2plus_apfu=0.0, species_3plus_apfu=three_plus, S=S, T=T)

    # droop_1987: F = 2 * X * (1 - T/S); clipped to [0, element_total] since
    # neither a negative nor an over-total Fe3+ split is physically meaningful
    # (S <= T means no charge-balance evidence for any Fe3+ at all).
    F = 2.0 * X * (1.0 - T / S) if S > 0 else 0.0
    F = min(max(F, 0.0), element_total)
    two_plus = element_total - F

    apfu = dict(s_basis_apfu)
    apfu.pop(element, None)
    apfu[f"{element}2"] = two_plus
    apfu[f"{element}3"] = F
    return RedoxResult(method=method, element=element, apfu=apfu,
                        species_2plus_apfu=two_plus, species_3plus_apfu=F, S=S, T=T)
