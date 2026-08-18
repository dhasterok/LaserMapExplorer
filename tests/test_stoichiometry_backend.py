"""Backend pipeline tests: a hand-checkable reference garnet analysis, and a
hand-calculated Droop (1987) Fe3+ estimate.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline, redox
from src.stoichiometry.config import load_mineral_config

GARNET_YAML_PATH = project_root / "resources" / "minerals" / "garnet.yaml"


@pytest.fixture(scope="module")
def garnet_config():
    return load_mineral_config(GARNET_YAML_PATH)


# ---------------------------------------------------------------------------
# Reference garnet EPMA-style analysis.
#
# Derived (not hand-transcribed from a paper) from a chosen "true" apfu
# composition so the whole chain is auditable end to end:
#
#   True apfu: Si=3.000 (Z); Al=1.800, Fe3+=0.200 (Y); Fe2+=2.200, Mg=0.500,
#              Mn=0.200, Ca=0.100 (X)   [cation total = 8.0, O total = 12.0]
#
# wt.% oxide = 100 * (apfu * oxide_molar_weight / n_cations_in_oxide) / total_mass,
# with total Fe (2.2+0.2=2.4 apfu) reported as a single 'FeO' (total-Fe-as-FeO)
# column, matching typical EPMA reporting convention:
#
#   SiO2  = 100 * (3.0 * 60.0843)      / 484.392 = 37.2122
#   Al2O3 = 100 * (1.8 * 101.9613/2)   / 484.392 = 18.9444
#   FeO   = 100 * (2.4 * 71.8444)      / 484.392 = 35.5965
#   MgO   = 100 * (0.5 * 40.3044)      / 484.392 =  4.1603
#   MnO   = 100 * (0.2 * 70.9374)      / 484.392 =  2.9289
#   CaO   = 100 * (0.1 * 56.0774)      / 484.392 =  1.1577
#
# (molar weights from global_geochemistry's MolecularWeightCalculator;
# total_mass = sum of the six unnormalized masses above = 484.392)
#
# This input has no source of charge imbalance other than the deliberate
# Fe-valence ambiguity (all Fe reported as FeO), so the pipeline should
# round-trip back to the true apfu above almost exactly: Droop recovers the
# true Fe2+/Fe3+ split, and -- since apfu are reported on the cation-fixed
# (T) basis, not left inflated on the oxygen-basis S -- every other cation
# lands on its true value too, not just its site total.
# ---------------------------------------------------------------------------
REFERENCE_ANALYSIS = {
    "SiO2": 37.2122,
    "Al2O3": 18.9444,
    "FeO": 35.5965,
    "MgO": 4.1603,
    "MnO": 2.9289,
    "CaO": 1.1577,
}


def test_reference_analysis_recovers_known_fe3_split(garnet_config):
    result = pipeline.calculate(REFERENCE_ANALYSIS, garnet_config, input_mode="wt_percent", redox_method="droop_1987")

    # Droop recovers the true Fe2+/Fe3+ split essentially exactly for this
    # clean synthetic case, since the only "error" introduced relative to
    # the true composition is exactly the Fe2+/Fe3+ ambiguity Droop's
    # formula is designed to resolve.
    assert result.redox is not None
    assert result.redox.species_3plus_apfu == pytest.approx(0.200, abs=1e-3)
    assert result.redox.species_2plus_apfu == pytest.approx(2.200, abs=1e-3)

    # S (all-Fe2+ cation total, oxygen-basis) comes out above T=8 -- exactly
    # the signal that there's real Fe3+ present -- and the residual is small
    # (this input has no other source of charge imbalance). S/T is Droop's
    # internal scaffolding only; final apfu are reported on the T basis (see
    # the site-allocation test below), so this residual doesn't propagate
    # into the other cations.
    assert result.redox.T == 8.0
    assert result.redox.S == pytest.approx(8.067, abs=1e-2)
    assert result.redox.residual > 0


def test_reference_analysis_site_allocation_matches_targets(garnet_config):
    result = pipeline.calculate(REFERENCE_ANALYSIS, garnet_config, input_mode="wt_percent", redox_method="droop_1987")

    sites = result.site_allocation.sites
    assert sites["Z"].total == pytest.approx(3.0, abs=1e-3)
    assert sites["Y"].total == pytest.approx(2.0, abs=1e-3)
    assert sites["X"].total == pytest.approx(3.0, abs=1e-3)
    assert not result.site_allocation.unallocated

    # Z site is essentially all Si (as expected -- Al/Fe3 only spill into Z
    # if Si itself is deficient, which it isn't here).
    assert sites["Z"].elements["Si"] == pytest.approx(3.0, abs=1e-3)
    # X site recovers the true per-element composition, not just the total --
    # confirms apfu aren't silently inflated before site allocation.
    assert sites["X"].elements["Fe2"] == pytest.approx(2.200, abs=1e-3)
    assert sites["X"].elements["Mg"] == pytest.approx(0.500, abs=1e-3)
    assert sites["X"].elements["Mn"] == pytest.approx(0.200, abs=1e-3)
    assert sites["X"].elements["Ca"] == pytest.approx(0.100, abs=1e-3)


def test_reference_analysis_end_members_are_almandine_dominant(garnet_config):
    result = pipeline.calculate(REFERENCE_ANALYSIS, garnet_config, input_mode="wt_percent", redox_method="droop_1987")

    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    # X-site is dominated by Fe2+ (2.2 of 3.0 apfu) -> almandine should be
    # the dominant end-member, consistent with pyrope/spessartine/grossular
    # being present but minor. True-composition fractions of X's divalent
    # total (3.0 apfu): Fe2+=2.2/3=73.33%, Mg=0.5/3=16.67%, Mn=0.2/3=6.67%,
    # Ca=0.1/3=3.33% (of which nearly all is grossular, since Y is almost
    # all Al with only a trace of Fe3+).
    assert em["almandine"] == pytest.approx(73.33, abs=0.5)
    assert em["pyrope"] == pytest.approx(16.67, abs=0.5)
    assert em["spessartine"] == pytest.approx(6.67, abs=0.5)
    assert em["almandine"] > em["pyrope"] > em["spessartine"] > em["grossular"]


def test_reference_analysis_qc_no_hydrogarnet_flag(garnet_config):
    result = pipeline.calculate(REFERENCE_ANALYSIS, garnet_config, input_mode="wt_percent", redox_method="droop_1987")
    assert result.qc["hydrogarnet_substitution"]["flag"] is False
    assert result.oxide_total_pct == pytest.approx(100.0, abs=1e-6)


def test_all_2plus_and_all_3plus_are_selectable(garnet_config):
    r2 = pipeline.calculate(REFERENCE_ANALYSIS, garnet_config, input_mode="wt_percent", redox_method="all_2plus")
    assert r2.redox.species_3plus_apfu == 0.0
    assert r2.redox.species_2plus_apfu > 0

    r3 = pipeline.calculate(REFERENCE_ANALYSIS, garnet_config, input_mode="wt_percent", redox_method="all_3plus")
    assert r3.redox.species_2plus_apfu == 0.0
    assert r3.redox.species_3plus_apfu > 0


# ---------------------------------------------------------------------------
# Droop (1987) hand-calculated case, isolated from oxide/molecular-weight
# chemistry entirely -- direct moles input chosen so every step is exact
# arithmetic:
#
#   moles = {'Si': 3.0, 'Fe': 4.0}      (arbitrary consistent mass basis)
#
#   S-basis (oxygen-fixed, Droop's formula scaffolding only):
#   O-equivalent = 3.0*2 (SiO2) + 4.0*1 (FeO) = 10.0
#   k_S = ideal_oxygens / O-equivalent = 12 / 10 = 1.2
#   S = (3.0 + 4.0) * 1.2 = 8.4;  T = 8 (garnet config)
#   F = 2*X*(1 - T/S) = 2*12*(1 - 8/8.4) = 24*(1 - 20/21) = 24/21 = 8/7 ~ 1.142857
#   (F comes out already on the T basis -- see redox.py's module docstring --
#   so it's used directly below, not rescaled again.)
#
#   T-basis (cation-fixed, the basis apfu are finally reported on):
#   k_T = ideal_cations / total_moles = 8 / 7.0
#   Si = 3.0 * 8/7 = 24/7 ~ 3.428571;  Fe_total = 4.0 * 8/7 = 32/7 ~ 4.571429
#   Fe2+ = Fe_total - F = 32/7 - 8/7 = 24/7 ~ 3.428571
# ---------------------------------------------------------------------------
def test_droop_hand_calculated_case(garnet_config):
    moles = {"Si": 3.0, "Fe": 4.0}
    result = redox.estimate_fe_split(moles, garnet_config, method="droop_1987")

    assert result.S == pytest.approx(8.4, abs=1e-9)
    assert result.T == 8.0
    assert result.species_3plus_apfu == pytest.approx(8.0 / 7.0, abs=1e-9)
    assert result.species_2plus_apfu == pytest.approx(24.0 / 7.0, abs=1e-9)
    assert result.apfu["Fe3"] == pytest.approx(8.0 / 7.0, abs=1e-9)
    assert result.apfu["Fe2"] == pytest.approx(24.0 / 7.0, abs=1e-9)
    assert result.apfu["Si"] == pytest.approx(24.0 / 7.0, abs=1e-9)


def test_droop_clips_negative_f_to_zero_when_s_below_t(garnet_config):
    """S < T means no charge-balance evidence for any Fe3+ -- F must floor at 0."""
    moles = {"Si": 0.3, "Fe": 0.1, "Mg": 0.05, "Ca": 0.05}
    result = redox.estimate_fe_split(moles, garnet_config, method="droop_1987")
    assert result.S < result.T
    assert result.species_3plus_apfu == 0.0
    assert result.apfu["Fe2"] == pytest.approx(result.apfu.get("Fe3", 0.0) + result.apfu["Fe2"], abs=1e-9)


def test_droop_clips_f_to_total_fe_when_formula_exceeds_it(garnet_config):
    """F is never allowed to exceed the total Fe actually present."""
    moles = {"Fe": 0.6, "Mg": 0.3, "Ca": 0.1}
    result = redox.estimate_fe_split(moles, garnet_config, method="droop_1987")
    fe_total = result.species_2plus_apfu + result.species_3plus_apfu
    assert result.species_3plus_apfu <= fe_total + 1e-9
    assert result.species_2plus_apfu >= -1e-9
