"""Orchestrates the full per-analysis pipeline: input normalization -> redox
estimation -> site allocation -> end-member calculation -> QC.
"""
from __future__ import annotations

from dataclasses import dataclass

from global_geochemistry.utils.molecular import MolecularWeightCalculator

from src.stoichiometry import endmembers, normalize, qc, redox, sites
from src.stoichiometry.config import MineralConfig


@dataclass
class StoichiometryResult:
    apfu: dict[str, float]                # final apfu per cation species (Fe split if applicable)
    redox: redox.RedoxResult | None
    site_allocation: sites.SiteAllocationResult
    end_members: dict[str, float]         # mol%, sums to 100
    qc: dict
    exclusions: dict
    oxide_total_pct: float | None
    basis_used: str                       # 'cation' | 'oxygen' | 'anion' -- actual basis this analysis normalized on,
                                           # which can differ from config.basis for basis='anion' configs that fell
                                           # back to 'cation' because the anion (S/As/Sb) wasn't measured


def calculate(
    analysis: dict[str, float],
    config: MineralConfig,
    input_mode: str = "ppm",
    redox_method: str | None = None,
    lod_treatment: str = "zero",
    lod: dict[str, float] | None = None,
    below_lod: set[str] | None = None,
    mwc: MolecularWeightCalculator | None = None,
    ideal_cations_override: float | None = None,
) -> StoichiometryResult:
    """Run the full pipeline for one analysis (one spot/pixel/EPMA point).

    Parameters
    ----------
    analysis : dict[str, float]
        Element ppm or oxide wt.% -- see :func:`normalize.to_cation_moles`.
    config : MineralConfig
    input_mode : {'ppm', 'wt_percent', 'element_wt_percent'}
    redox_method : str, optional
        Defaults to ``config.redox.default_method``.
    lod_treatment : {'zero', 'half_lod', 'exclude'}
    lod, below_lod
        See :func:`normalize.to_cation_moles`.
    mwc : MolecularWeightCalculator, optional
        Reused instance for bulk (many-pixel) calls, to avoid rebuilding
        the atomic-weight table per analysis.
    ideal_cations_override : float, optional
        Overrides ``config.ideal_cations`` for this call, for minerals
        without one fixed formula (e.g. sulfide's generic config, where the
        normalization target is a per-analysis choice, not a config
        constant -- see :func:`normalize.normalize_to_cations`). Also used
        as the fallback target for ``basis: "anion"`` configs when the
        anion wasn't measured (see ``StoichiometryResult.basis_used``).

    Returns
    -------
    StoichiometryResult
    """
    mwc = mwc or MolecularWeightCalculator()

    moles, exclusions = normalize.to_cation_moles(
        analysis, input_mode, config, lod=lod, lod_treatment=lod_treatment, below_lod=below_lod, mwc=mwc
    )

    if config.redox.elements:
        redox_result = redox.estimate_fe_split(moles, config, method=redox_method)
        apfu = redox_result.apfu
        basis_used = config.basis
    else:
        redox_result = None
        if config.basis == "cation":
            apfu = normalize.normalize_to_cations(moles, config, ideal_cations=ideal_cations_override)
            basis_used = "cation"
        elif config.basis == "anion":
            # Anion (S/As/Sb) is directly measured for this tool's real
            # inputs, so it's used as the normalization anchor when present
            # -- but falls back to cation-basis (same as basis='cation'
            # configs) rather than raising, since not every analysis
            # collects it. Not a silent degrade: basis_used records which
            # path actually ran.
            if normalize.measured_anion_moles(moles, config) > 0:
                apfu = normalize.normalize_to_measured_anion(moles, config)
                basis_used = "anion"
            else:
                apfu = normalize.normalize_to_cations(moles, config, ideal_cations=ideal_cations_override)
                basis_used = "cation"
        else:  # 'oxygen'
            apfu = normalize.normalize_to_oxygen(moles, config)
            basis_used = "oxygen"

    site_allocation = sites.allocate_sites(apfu, config)
    end_member_result = endmembers.compute_end_members(site_allocation, config)
    qc_result = qc.run_qc_checks(config, apfu, site_allocation, redox_result)
    oxide_total = normalize.oxide_total_percent(analysis, input_mode)

    return StoichiometryResult(
        apfu=apfu,
        redox=redox_result,
        site_allocation=site_allocation,
        end_members=end_member_result,
        qc=qc_result,
        exclusions=exclusions,
        oxide_total_pct=oxide_total,
        basis_used=basis_used,
    )
