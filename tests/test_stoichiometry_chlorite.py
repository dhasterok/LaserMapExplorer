"""Characterization tests for chlorite -- no workbook reference sheet exists
for this mineral (Stage 3, OH-bearing batch). Uses an *exact* ideal-formula
composition (clinochlore, Mg5Al2Si3O10(OH)8, oxide wt% computed directly
from molar weights) with a tight tolerance on the cation total -- this is
the specific check that would have caught the ``ideal_oxygens`` derivation
mistake found in apatite/staurolite/mica in this same batch (naively
subtracting OH's oxygen from the crystallographic total, rather than
matching this engine's own O-per-cation accounting method -- see
``resources/minerals/apatite.yaml``'s comment for the general derivation).
Chlorite's own target happened to already be correct (sourced directly from
MinPlotX's own reported anhydrous value, which independently uses the same
accounting convention), confirmed here rather than assumed.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

CHLORITE_YAML_PATH = project_root / "resources" / "minerals" / "chlorite.yaml"

# Exact ideal clinochlore, Mg5Al2Si3O10(OH)8 (3 SiO2 + 1 Al2O3 + 5 MgO by mole).
IDEAL_ANALYSIS = {"SiO2": 37.262646148021034, "Al2O3": 21.077868889232214, "MgO": 41.65948496274676}
ANALYSIS_WITH_FE = dict(IDEAL_ANALYSIS, FeO=1.0)


@pytest.fixture(scope="module")
def chlorite_config():
    return load_mineral_config(CHLORITE_YAML_PATH)


def test_ideal_formula_reproduces_exact_cation_ratios(chlorite_config):
    result = pipeline.calculate(IDEAL_ANALYSIS, chlorite_config, input_mode="wt_percent", redox_method="fixed_ratio")
    assert result.apfu["Si"] == pytest.approx(3.0, abs=1e-6)
    assert result.apfu["Al"] == pytest.approx(2.0, abs=1e-6)
    assert result.apfu["Mg"] == pytest.approx(5.0, abs=1e-6)
    assert not result.site_allocation.unallocated


def test_al_splits_between_t_and_m(chlorite_config):
    result = pipeline.calculate(IDEAL_ANALYSIS, chlorite_config, input_mode="wt_percent", redox_method="fixed_ratio")
    sites = result.site_allocation.sites
    assert sites["T"].total == pytest.approx(4.0, abs=1e-6)
    assert sites["T"].elements["Al"] == pytest.approx(1.0, abs=1e-6)  # fills T's remaining space after Si=3
    assert sites["M"].elements["Al"] == pytest.approx(1.0, abs=1e-6)  # the other Al, ideal clinochlore has 1+1


def test_default_fixed_ratio_assumes_all_fe_ferrous(chlorite_config):
    result = pipeline.calculate(ANALYSIS_WITH_FE, chlorite_config, input_mode="wt_percent", redox_method="fixed_ratio")
    assert result.redox.species_3plus_apfu == pytest.approx(0.0, abs=1e-9)
    assert result.apfu["Fe2"] > 0


def test_xmg_end_member(chlorite_config):
    result = pipeline.calculate(ANALYSIS_WITH_FE, chlorite_config, input_mode="wt_percent", redox_method="fixed_ratio")
    mg, fe2 = result.apfu["Mg"], result.apfu["Fe2"]
    assert result.end_members["mg_number"] == pytest.approx(100.0 * mg / (mg + fe2), rel=1e-6)
