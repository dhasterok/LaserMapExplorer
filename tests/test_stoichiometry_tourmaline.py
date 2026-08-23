"""Characterization tests for tourmaline -- no workbook reference sheet
exists for this mineral. Uses *exact* ideal-formula compositions (oxide
wt% computed directly from molar weights), matching monazite's/ilmenite's
precedent for a new-mineral characterization test in this batch. See
``resources/minerals/tourmaline.yaml`` for the ``ideal_oxygens=29``
derivation (numerically verified across dravite and elbaite, i.e. across a
Y-site substitution).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

TOURMALINE_YAML_PATH = project_root / "resources" / "minerals" / "tourmaline.yaml"

# Exact end-member dravite NaMg3Al6Si6B3O27(OH)4 (Na=1, Mg=3, Al=6, Si=6, B=3
# per formula unit; OH not tracked, see the YAML's module comment).
DRAVITE = {
    "Na2O": 3.3584816553149737, "MgO": 13.103959942531498, "Al2O3": 33.15013973953589,
    "SiO2": 39.069791902375194, "B2O3": 11.317626760242446,
}
# Exact end-member schorl NaFe3Al6Si6B3O27(OH)4 (Na=1, Fe2+=3, Al=6, Si=6, B=3).
SCHORL = {
    "Na2O": 3.046119296802685, "FeO": 21.185901368286753, "Al2O3": 30.06694414796067,
    "SiO2": 35.43602712480171, "B2O3": 10.265008062148182,
}
# Exact end-member elbaite Na(Li1.5Al1.5)Al6Si6B3O27(OH)4 (Na=1, Li=1.5,
# Al=7.5, Si=6, B=3) -- the Y-site Li+Al-for-Mg/Fe2+ substitution.
ELBAITE = {
    "Na2O": 3.440631162, "Li2O": 2.488205148, "Al2O3": 42.451253090,
    "SiO2": 40.025451168, "B2O3": 11.594459432,
}


@pytest.fixture(scope="module")
def tourmaline_config():
    return load_mineral_config(TOURMALINE_YAML_PATH)


def test_dravite_reproduces_ideal_apfu_and_mg_number(tourmaline_config):
    result = pipeline.calculate(DRAVITE, tourmaline_config, input_mode="wt_percent")
    assert result.apfu["Na"] == pytest.approx(1.0, abs=1e-4)
    assert result.apfu["Mg"] == pytest.approx(3.0, abs=1e-4)
    assert result.apfu["Al"] == pytest.approx(6.0, abs=1e-4)
    assert result.apfu["Si"] == pytest.approx(6.0, abs=1e-4)
    assert result.apfu["B"] == pytest.approx(3.0, abs=1e-4)
    assert not result.site_allocation.unallocated
    assert result.end_members["mg_number"] == pytest.approx(100.0, abs=1e-3)


def test_schorl_reproduces_ideal_apfu_and_mg_number(tourmaline_config):
    result = pipeline.calculate(SCHORL, tourmaline_config, input_mode="wt_percent")
    assert result.apfu["Na"] == pytest.approx(1.0, abs=1e-4)
    assert result.apfu["Fe2"] == pytest.approx(3.0, abs=1e-4)
    assert result.apfu["Al"] == pytest.approx(6.0, abs=1e-4)
    assert result.apfu["Si"] == pytest.approx(6.0, abs=1e-4)
    assert result.apfu["B"] == pytest.approx(3.0, abs=1e-4)
    assert not result.site_allocation.unallocated
    assert result.end_members["mg_number"] == pytest.approx(0.0, abs=1e-3)


def test_elbaite_y_site_li_al_substitution(tourmaline_config):
    result = pipeline.calculate(ELBAITE, tourmaline_config, input_mode="wt_percent")
    sites = result.site_allocation.sites
    assert result.apfu["Li"] == pytest.approx(1.5, abs=1e-3)
    assert result.apfu["Al"] == pytest.approx(7.5, abs=1e-3)
    assert sites["T"].total == pytest.approx(6.0, abs=1e-3)
    assert sites["Z"].total == pytest.approx(6.0, abs=1e-3)
    assert sites["Y"].elements["Li"] == pytest.approx(1.5, abs=1e-3)
    assert sites["Y"].elements["Al"] == pytest.approx(1.5, abs=1e-3)
    assert not result.site_allocation.unallocated


def test_fixed_ratio_default_keeps_fe_all_ferrous(tourmaline_config):
    result = pipeline.calculate(SCHORL, tourmaline_config, input_mode="wt_percent", redox_method="fixed_ratio")
    assert result.redox.species_3plus_apfu == pytest.approx(0.0, abs=1e-6)
    assert result.redox.species_2plus_apfu == pytest.approx(3.0, abs=1e-4)
