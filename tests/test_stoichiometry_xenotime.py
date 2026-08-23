"""Characterization tests for xenotime -- no workbook reference sheet exists
for this mineral. Uses *exact* ideal-formula and coupled-substitution
compositions (oxide wt% computed directly from molar weights), matching
monazite's/zircon's precedent for a new-mineral characterization test in
this batch: see ``resources/minerals/xenotime.yaml`` for the
``ideal_oxygens=4`` derivation (Y2O3/P2O5 and ZrO2/SiO2 O-per-cation ratios
both resolving to the same target).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

XENOTIME_YAML_PATH = project_root / "resources" / "minerals" / "xenotime.yaml"

# Exact pure xenotime YPO4 (0.5 Y2O3 + 0.5 P2O5 per formula unit).
PURE_XENOTIME = {"Y2O3": 61.40236126703945, "P2O5": 38.59763873296056}
# Exact 50:50 (molar) zircon-substituted xenotime: 0.5 Y + 0.5 P
# (unsubstituted) plus 0.5 Zr + 0.5 Si (zircon substitution Zr4+ + Si4+ =
# REE3+ + P5+, the reverse of zircon.yaml's xenotime substitution).
HALF_ZIRCON_SUBSTITUTED = {"Y2O3": 30.74884910, "P2O5": 19.32878385, "ZrO2": 33.55884115, "SiO2": 16.36352590}


@pytest.fixture(scope="module")
def xenotime_config():
    return load_mineral_config(XENOTIME_YAML_PATH)


def test_pure_xenotime_reproduces_y_p_one_apfu(xenotime_config):
    result = pipeline.calculate(PURE_XENOTIME, xenotime_config, input_mode="wt_percent")
    assert result.apfu["Y"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["P"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated
    assert result.redox is None
    assert result.end_members == {}


def test_zircon_substituted_xenotime_sites(xenotime_config):
    result = pipeline.calculate(HALF_ZIRCON_SUBSTITUTED, xenotime_config, input_mode="wt_percent")
    sites = result.site_allocation.sites
    assert sites["A"].total == pytest.approx(1.0, abs=2e-3)
    assert sites["T"].total == pytest.approx(1.0, abs=2e-3)
    assert sites["A"].elements["Y"] == pytest.approx(0.5, abs=2e-3)
    assert sites["A"].elements["Zr"] == pytest.approx(0.5, abs=2e-3)
    assert sites["T"].elements["P"] == pytest.approx(0.5, abs=2e-3)
    assert sites["T"].elements["Si"] == pytest.approx(0.5, abs=2e-3)
