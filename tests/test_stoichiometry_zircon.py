"""Characterization tests for zircon -- no workbook reference sheet exists
for this mineral. Uses *exact* ideal-formula and coupled-substitution
compositions (oxide wt% computed directly from molar weights), matching
monazite's precedent for a new-mineral characterization test in this batch:
see ``resources/minerals/zircon.yaml`` for the ``ideal_oxygens=4``
derivation (ZrO2/SiO2 and REE2O3/P2O5 O-per-cation ratios both resolving to
the same target).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

ZIRCON_YAML_PATH = project_root / "resources" / "minerals" / "zircon.yaml"

# Exact pure zircon ZrSiO4 (1 ZrO2 + 1 SiO2 per formula unit).
PURE_ZIRCON = {"ZrO2": 67.22205522863, "SiO2": 32.77794477137002}
# Exact 50:50 (molar) xenotime-substituted zircon: 0.5 Zr + 0.5 Si
# (unsubstituted) plus 0.5 Y + 0.5 P (xenotime substitution REE3+ + P5+ =
# Zr4+ + Si4+, using Y as the REE proxy).
HALF_XENOTIME_SUBSTITUTED = {"ZrO2": 33.55884115, "SiO2": 16.36352590, "Y2O3": 30.74884910, "P2O5": 19.32878385}


@pytest.fixture(scope="module")
def zircon_config():
    return load_mineral_config(ZIRCON_YAML_PATH)


def test_pure_zircon_reproduces_zr_si_one_apfu(zircon_config):
    result = pipeline.calculate(PURE_ZIRCON, zircon_config, input_mode="wt_percent")
    assert result.apfu["Zr"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["Si"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated
    assert result.redox is None
    assert result.end_members == {}


def test_xenotime_substituted_zircon_sites(zircon_config):
    result = pipeline.calculate(HALF_XENOTIME_SUBSTITUTED, zircon_config, input_mode="wt_percent")
    sites = result.site_allocation.sites
    assert sites["A"].total == pytest.approx(1.0, abs=2e-3)
    assert sites["T"].total == pytest.approx(1.0, abs=2e-3)
    assert sites["A"].elements["Zr"] == pytest.approx(0.5, abs=2e-3)
    assert sites["A"].elements["Y"] == pytest.approx(0.5, abs=2e-3)
    assert sites["T"].elements["Si"] == pytest.approx(0.5, abs=2e-3)
    assert sites["T"].elements["P"] == pytest.approx(0.5, abs=2e-3)
