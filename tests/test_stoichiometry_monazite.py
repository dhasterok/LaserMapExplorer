"""Characterization test for the monazite-huttonite solid solution -- no
workbook reference sheet exists for this mineral. Uses *exact* ideal-formula
compositions (oxide wt% computed directly from molar weights, not
hand-approximated), matching apatite's/titanite's precedent for a
new-mineral characterization test in this batch: see
``resources/minerals/monazite.yaml`` for the ``ideal_oxygens=4`` derivation
(REE2O3/ThO2 O-per-cation ratios both resolving to the same target across
the solid solution).

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
# exact 50:50 (molar) monazite-huttonite mix.
MIXED_50_50 = {
    "Ce2O3": 29.34774660, "P2O5": 12.69155587,
    "ThO2": 47.21617243, "SiO2": 10.74452510,
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


def test_pure_huttonite_reproduces_th_si_one_apfu(monazite_config):
    result = pipeline.calculate(PURE_HUTTONITE, monazite_config, input_mode="wt_percent")
    assert result.apfu["Th"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["Si"] == pytest.approx(1.0, abs=1e-6)
    assert result.end_members["huttonite"] == pytest.approx(100.0, abs=1e-4)
    assert result.end_members["monazite"] == pytest.approx(0.0, abs=1e-4)


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
