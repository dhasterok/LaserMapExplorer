"""Characterization tests for spinel-magnetite's tiered end-member scheme
(``endmembers.py``'s ``_spinel_xmg``) -- Tier 1 (always on), Tier 2
(Mn/Zn auto-trigger), Tier 3 (V auto-trigger), the ``other`` residual, and
the four lead ratios (Cr#, Mg#, Fe3+/sum(R3+), X_usp). No workbook
reference exists for these synthetic compositions (see
``test_stoichiometry_spinel_magnetite_workbook_reference.py`` for the one
composition that is cross-checked against real EPMA data) -- these are
self-consistency and design-intent checks.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

SPINEL_MAGNETITE_YAML_PATH = project_root / "resources" / "minerals" / "spinel-magnetite.yaml"


@pytest.fixture(scope="module")
def config():
    return load_mineral_config(SPINEL_MAGNETITE_YAML_PATH)


def _members_sum(result, config):
    return sum(result.end_members[m] for m in config.end_members.members)


def test_tier2_manganese_triggers_above_threshold(config):
    """Mn-rich (galaxite-dominant): Al x Mn should be named and non-zero,
    and the tiered members should still sum to 100."""
    analysis = {"MnO": 8.0, "Al2O3": 55.0, "MgO": 10.0, "FeO": 5.0}
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="all_2plus")
    em = result.end_members
    assert em["galaxite"] > 0
    assert _members_sum(result, config) == pytest.approx(100.0, abs=1e-6)


def test_tier2_manganese_stays_off_below_threshold(config):
    """Trace Mn (well under the ~2% apfu-fraction trigger) should not get
    a named cell -- its share folds into `other` instead."""
    analysis = {"MnO": 0.3, "Al2O3": 55.0, "MgO": 20.0, "FeO": 5.0}
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="all_2plus")
    em = result.end_members
    assert em["galaxite"] == pytest.approx(0.0, abs=1e-9)
    assert em["manganochromite"] == pytest.approx(0.0, abs=1e-9)
    assert em["jacobsite"] == pytest.approx(0.0, abs=1e-9)
    assert em["other"] > 0  # trace Mn's share still shows up somewhere


def test_tier3_vanadium_triggers_and_zincochromite_is_never_named(config):
    """V-rich (coulsonite/magnesiocoulsonite-dominant) -- and even with Zn
    also present, there is no 'zincochromite'-style cell (Zn only ever
    pairs with Al/Fe3+ -- see spinel-magnetite.yaml's end_members comment)."""
    analysis = {"V2O3": 20.0, "FeO": 40.0, "Fe2O3": 10.0, "MgO": 5.0, "ZnO": 3.0}
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="all_2plus")
    em = result.end_members
    assert em["coulsonite"] > 0
    assert em["magnesiocoulsonite"] > 0
    assert "zincochromite" not in em
    assert _members_sum(result, config) == pytest.approx(100.0, abs=1e-6)


def test_dropped_nickel_cobalt_fold_into_other_and_flag_qc(config):
    """Ni/Co-rich composition: no Ni/Co-bearing member exists in this
    scheme at all (see spinel-magnetite.yaml's comment) -- their real,
    still-allocated site occupancy shows up entirely as `other`, and the
    spinel_other_fraction QC check flags it above its 5% default threshold."""
    analysis = {"NiO": 30.0, "Al2O3": 40.0, "MgO": 20.0, "FeO": 5.0}
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="all_2plus")
    assert not result.site_allocation.unallocated  # Ni is still a real, allocated site occupant
    assert _members_sum(result, config) == pytest.approx(100.0, abs=1e-6)
    assert result.end_members["other"] > 5.0
    qc = result.qc["spinel_other_fraction"]
    assert qc["flag"] is True
    assert qc["other_fraction_pct"] == pytest.approx(result.end_members["other"], abs=1e-9)


def test_silicon_never_gets_a_named_cell_or_inflates_other(config):
    """Si plays no axis role at all in this scheme (ringwoodite/ahrensite
    belong in a separate silicate-spinel phase -- see spinel-magnetite.yaml's
    comment) -- a Si-contaminated analysis's `other` stays exactly what it
    would be without the contamination (here, 0 -- this magnetite-dominant
    composition has no Ni/Co/untriggered-Mn/Zn to fall into `other` either
    way), even though the overall cation proportions do shift slightly from
    the added Si diluting the fixed-ideal_cations normalization -- that
    shift is inherent to normalization/site-allocation (unchanged by this
    rewrite), not something Si does specially here.
    """
    base = {"FeO": 31.0, "Fe2O3": 67.0, "TiO2": 0.5, "Al2O3": 0.5}
    contaminated = dict(base, SiO2=5.0)
    r_base = pipeline.calculate(base, config, input_mode="wt_percent")
    r_contam = pipeline.calculate(contaminated, config, input_mode="wt_percent")
    assert r_base.end_members["other"] == pytest.approx(0.0, abs=1e-9)
    assert r_contam.end_members["other"] == pytest.approx(0.0, abs=1e-9)
    assert _members_sum(r_contam, config) == pytest.approx(100.0, abs=1e-6)


def test_lead_ratios_match_hand_computed_values(config):
    """Cr#, Mg#, Fe3+/sum(R3+), X_usp on a known, mixed composition --
    hand-computed from the same apfu the site-allocation layer already
    reports (cross-checked, not just internally self-consistent)."""
    analysis = {"Cr2O3": 20.0, "Al2O3": 20.0, "FeO": 15.0, "MgO": 15.0, "Fe2O3": 20.0, "TiO2": 2.0}
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="all_2plus")
    apfu = result.apfu
    d = result.site_allocation.sites["D"]
    a = result.site_allocation.sites["A"]

    cr_d, al_d, fe3_d, v_d = d.elements.get("Cr", 0.0), d.elements.get("Al", 0.0), d.elements.get("Fe3", 0.0), d.elements.get("V", 0.0)
    mg_bulk = apfu.get("Mg", 0.0)
    fe2_bulk = apfu.get("Fe2", 0.0)
    ti_a = a.elements.get("Ti", 0.0)

    expected_cr_number = 100.0 * cr_d / (cr_d + al_d)
    expected_mg_number = 100.0 * mg_bulk / (mg_bulk + fe2_bulk)
    expected_fe3_over_r3 = 100.0 * fe3_d / (al_d + cr_d + fe3_d + v_d)
    expected_x_usp = 100.0 * ti_a / (ti_a + fe3_d)

    em = result.end_members
    assert em["cr_number"] == pytest.approx(expected_cr_number, rel=1e-6)
    assert em["mg_number"] == pytest.approx(expected_mg_number, rel=1e-6)
    assert em["fe3_over_r3"] == pytest.approx(expected_fe3_over_r3, rel=1e-6)
    assert em["x_usp"] == pytest.approx(expected_x_usp, rel=1e-6)
    # Ratios are excluded from the sum-to-100 members contract.
    assert set(config.end_members.ratios) == {"cr_number", "mg_number", "fe3_over_r3", "x_usp"}
    assert all(r not in config.end_members.members for r in config.end_members.ratios)
