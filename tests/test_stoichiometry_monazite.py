"""Characterization test for the monazite-huttonite-cheralite solid
solution -- no workbook reference sheet exists for this mineral. Uses
*exact* ideal-formula compositions (oxide wt% computed directly from molar
weights, not hand-approximated), matching apatite's/titanite's precedent
for a new-mineral characterization test in this batch: see
``resources/minerals/monazite.yaml`` for the ``ideal_oxygens=4`` derivation
(REE2O3/ThO2/CaO O-per-cation ratios all resolving to the same target
across the solid solution).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

MONAZITE_YAML_PATH = project_root / "resources" / "minerals" / "monazite.yaml"

# Exact ideal end-members (oxide wt% derived from molar weights):
# pure monazite CePO4 (0.5 Ce2O3 + 0.5 P2O5 per formula unit).
PURE_MONAZITE = {"Ce2O3": 69.81026058, "P2O5": 30.18973942}
# pure huttonite ThSiO4 (1 ThO2 + 1 SiO2 per formula unit).
PURE_HUTTONITE = {"ThO2": 81.46239511, "SiO2": 18.53760489}
# pure cheralite Ca0.5Th0.5PO4 (0.5 CaO + 0.5 ThO2 + 0.5 P2O5 per formula unit).
PURE_CHERALITE = {"CaO": 12.13642115, "ThO2": 57.14356466, "P2O5": 30.72001419}
# exact 50:50 (molar) monazite-huttonite mix.
MIXED_50_50 = {
    "Ce2O3": 29.34774660, "P2O5": 12.69155587,
    "ThO2": 47.21617243, "SiO2": 10.74452510,
}
# exact 50:50 (molar) monazite-cheralite mix (no Si/huttonite at all).
MONAZITE_CHERALITE_50_50 = {
    "Ce2O3": 35.20901117, "P2O5": 30.45256854,
    "ThO2": 28.323039, "CaO": 6.01538129,
}
# exact equal (1:1:1) molar thirds of monazite:huttonite:cheralite.
THIRDS = {
    "Ce2O3": 20.76780892, "P2O5": 17.96225181,
    "ThO2": 50.11848748, "SiO2": 7.6033178, "CaO": 3.54813399,
}


@pytest.fixture(scope="module")
def monazite_config():
    return load_mineral_config(MONAZITE_YAML_PATH)


def test_pure_monazite_reproduces_ce_p_one_apfu(monazite_config):
    result = pipeline.calculate(PURE_MONAZITE, monazite_config, input_mode="wt_percent")
    assert result.apfu["Ce"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["P"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated
    assert result.end_members["monazite"] == pytest.approx(100.0, abs=1e-4)
    assert result.end_members["huttonite"] == pytest.approx(0.0, abs=1e-4)
    assert result.end_members["cheralite"] == pytest.approx(0.0, abs=1e-4)


def test_pure_huttonite_reproduces_th_si_one_apfu(monazite_config):
    result = pipeline.calculate(PURE_HUTTONITE, monazite_config, input_mode="wt_percent")
    assert result.apfu["Th"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["Si"] == pytest.approx(1.0, abs=1e-6)
    assert result.end_members["huttonite"] == pytest.approx(100.0, abs=1e-4)
    assert result.end_members["monazite"] == pytest.approx(0.0, abs=1e-4)
    assert result.end_members["cheralite"] == pytest.approx(0.0, abs=1e-4)


def test_pure_cheralite_reproduces_ca_th_p_apfu(monazite_config):
    result = pipeline.calculate(PURE_CHERALITE, monazite_config, input_mode="wt_percent")
    assert result.apfu["Ca"] == pytest.approx(0.5, abs=1e-6)
    assert result.apfu["Th"] == pytest.approx(0.5, abs=1e-6)
    assert result.apfu["P"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated
    assert result.end_members["cheralite"] == pytest.approx(100.0, abs=1e-4)
    assert result.end_members["monazite"] == pytest.approx(0.0, abs=1e-4)
    assert result.end_members["huttonite"] == pytest.approx(0.0, abs=1e-4)


def test_no_redox_and_sites_populated(monazite_config):
    result = pipeline.calculate(MIXED_50_50, monazite_config, input_mode="wt_percent")
    assert result.redox is None
    sites = result.site_allocation.sites
    assert sites["A"].total == pytest.approx(1.0, abs=1e-6)
    assert sites["T"].total == pytest.approx(1.0, abs=1e-6)


def test_mixed_50_50_end_members(monazite_config):
    result = pipeline.calculate(MIXED_50_50, monazite_config, input_mode="wt_percent")
    sites = result.site_allocation.sites
    assert sites["A"].elements["Ce"] == pytest.approx(0.5, abs=1e-6)
    assert sites["A"].elements["Th"] == pytest.approx(0.5, abs=1e-6)
    assert sites["T"].elements["P"] == pytest.approx(0.5, abs=1e-6)
    assert sites["T"].elements["Si"] == pytest.approx(0.5, abs=1e-6)
    assert result.end_members["monazite"] == pytest.approx(50.0, abs=1e-4)
    assert result.end_members["huttonite"] == pytest.approx(50.0, abs=1e-4)
    assert result.end_members["cheralite"] == pytest.approx(0.0, abs=1e-4)


def test_monazite_cheralite_mix_no_huttonite(monazite_config):
    """Ca-Th pairing (cheralite) with zero Si present -- huttonite must stay
    exactly 0 even though Th is present, since none of it is Si-paired."""
    result = pipeline.calculate(MONAZITE_CHERALITE_50_50, monazite_config, input_mode="wt_percent")
    sites = result.site_allocation.sites
    assert sites["A"].elements["Ce"] == pytest.approx(0.5, abs=1e-6)
    assert sites["A"].elements["Ca"] == pytest.approx(0.25, abs=1e-6)
    assert sites["A"].elements["Th"] == pytest.approx(0.25, abs=1e-6)
    assert result.end_members["monazite"] == pytest.approx(50.0, abs=1e-4)
    assert result.end_members["cheralite"] == pytest.approx(50.0, abs=1e-4)
    assert result.end_members["huttonite"] == pytest.approx(0.0, abs=1e-4)


def test_three_way_mix_sums_to_100(monazite_config):
    """Equal molar thirds of monazite:huttonite:cheralite -- all three
    end-members split the A site's Th between Si-pairing (huttonite) and
    Ca-pairing (cheralite) correctly, and still conserve the total (no apfu
    silently dropped or double-counted)."""
    result = pipeline.calculate(THIRDS, monazite_config, input_mode="wt_percent")
    em = result.end_members
    assert em["monazite"] == pytest.approx(100.0 / 3.0, abs=1e-2)
    assert em["huttonite"] == pytest.approx(100.0 / 3.0, abs=1e-2)
    assert em["cheralite"] == pytest.approx(100.0 / 3.0, abs=1e-2)
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)


def test_excess_thorium_without_calcium_falls_back_to_monazite(monazite_config):
    """Th present with no Si and no Ca to pair with either substitution --
    matches the pre-cheralite fallback behavior (all uncoupled Th lumped
    into the generic 'monazite' bucket, not silently dropped)."""
    analysis = {"ThO2": 50.0, "P2O5": 50.0}
    result = pipeline.calculate(analysis, monazite_config, input_mode="wt_percent")
    em = result.end_members
    assert em["monazite"] == pytest.approx(100.0, abs=1e-6)
    assert em["huttonite"] == pytest.approx(0.0, abs=1e-6)
    assert em["cheralite"] == pytest.approx(0.0, abs=1e-6)


def test_excess_calcium_without_thorium_falls_back_to_monazite(monazite_config):
    """Ca present with no Th to pair with -- uncoupled Ca must not
    spuriously produce a nonzero cheralite fraction."""
    analysis = {"CaO": 50.0, "P2O5": 50.0}
    result = pipeline.calculate(analysis, monazite_config, input_mode="wt_percent")
    em = result.end_members
    assert em["cheralite"] == pytest.approx(0.0, abs=1e-6)
    assert em["monazite"] == pytest.approx(100.0, abs=1e-6)


def test_partial_pairing_conserves_total(monazite_config):
    """Th in excess of available Ca (only some of the A-site Th can be
    cheralite-paired) -- the leftover, unpaired Th still falls into
    'monazite' rather than vanishing, and the three fractions still sum to
    exactly 100."""
    analysis = {"ThO2": 40.0, "CaO": 10.0, "P2O5": 50.0}
    result = pipeline.calculate(analysis, monazite_config, input_mode="wt_percent")
    em = result.end_members
    assert em["cheralite"] > 0
    assert em["monazite"] > 0
    assert em["huttonite"] == pytest.approx(0.0, abs=1e-6)
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
