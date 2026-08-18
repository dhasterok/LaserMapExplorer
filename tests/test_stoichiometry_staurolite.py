"""Characterization test for staurolite -- no workbook reference sheet
exists for this mineral (Stage 3, OH-bearing batch). Uses an *exact*
ideal-formula composition (Fe4Al18Si8, oxide wt% computed directly from
molar weights) with a tight tolerance -- an earlier, loosely-toleranced
version of this test (``abs=1.5`` on a target of 30) failed to catch a real
~2% normalization bug (the same ``ideal_oxygens`` derivation mistake as
apatite; see ``resources/minerals/staurolite.yaml``'s comment).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

STAUROLITE_YAML_PATH = project_root / "resources" / "minerals" / "staurolite.yaml"

# Exact ideal Fe4Al18Si8 (8 SiO2 + 9 Al2O3 + 4 FeO by mole).
ANALYSIS = {"SiO2": 28.514765584977894, "Al2O3": 54.43730155574451, "FeO": 17.047932859277594}


@pytest.fixture(scope="module")
def staurolite_config():
    return load_mineral_config(STAUROLITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(staurolite_config):
    return pipeline.calculate(ANALYSIS, staurolite_config, input_mode="wt_percent", redox_method="fixed_ratio")


def test_ideal_formula_reproduces_exact_cation_ratios(result):
    assert result.apfu["Si"] == pytest.approx(8.0, abs=1e-6)
    assert result.apfu["Al"] == pytest.approx(18.0, abs=1e-6)
    fe_total = result.apfu["Fe2"] + result.apfu["Fe3"]
    assert fe_total == pytest.approx(4.0, abs=1e-6)
    assert not result.site_allocation.unallocated


def test_default_fixed_ratio_matches_minplotx_default(result):
    """staurolite.yaml's default fixed_ratio=0.035 (MinPlotX's own default) --
    a small but nonzero Fe3+ fraction.
    """
    fe_total = result.apfu["Fe2"] + result.apfu["Fe3"]
    assert result.redox.species_3plus_apfu == pytest.approx(0.035 * fe_total, rel=1e-6)
