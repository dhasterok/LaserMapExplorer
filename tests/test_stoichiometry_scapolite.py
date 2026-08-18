"""Characterization test for scapolite -- no workbook reference sheet exists
for this mineral (Stage 3 batch); a self-consistency check on a hand-picked
synthetic analysis rather than a cross-check against an authoritative
external value. See ``resources/minerals/scapolite.yaml`` and the Stage 3
plan (single site, no Fe-redox, ideal_oxygens=27 matching MinPlotX's
"CO2 measured" branch).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

SCAPOLITE_YAML_PATH = project_root / "resources" / "minerals" / "scapolite.yaml"

ANALYSIS = {"SiO2": 45.0, "Al2O3": 25.0, "CaO": 17.0, "Na2O": 6.0, "K2O": 0.5}


@pytest.fixture(scope="module")
def scapolite_config():
    return load_mineral_config(SCAPOLITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(scapolite_config):
    return pipeline.calculate(ANALYSIS, scapolite_config, input_mode="wt_percent")


def test_single_site_absorbs_everything_unconditionally(result):
    assert result.redox is None  # no redox: block -- Fe (absent here) would be plain, unsplit
    assert not result.site_allocation.unallocated
    m = result.site_allocation.sites["M"]
    assert m.elements == pytest.approx(result.apfu, abs=1e-9)


def test_end_members_reflect_ca_rich_composition(result):
    em = result.end_members
    # eq_anorthite = (Al-3)/3, meionite_divalent = (Ca+Mg+Sr+Ba+Mn+Fe)/4 -- both
    # positive and sane in magnitude for a Ca/Al-rich, meionite-leaning composition.
    assert em["eq_anorthite"] > 0
    assert em["meionite_divalent"] > 0
