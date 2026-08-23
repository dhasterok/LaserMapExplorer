"""Characterization tests for orthopyroxene -- no workbook reference sheet
exists for this mineral. Uses exact end-member element compositions (oxide
wt% computed from molar weights) to verify the shared pyroxene_quad engine
reproduces ideal apfu, and that the dedicated 2-member
``orthopyroxene_ratio`` end-member scheme (enstatite/ferrosilite only, no
wollastonite) works as intended. See ``resources/minerals/orthopyroxene.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

ORTHOPYROXENE_YAML_PATH = project_root / "resources" / "minerals" / "orthopyroxene.yaml"

# Exact pure enstatite Mg2Si2O6 (2 MgO + 2 SiO2 per formula unit).
PURE_ENSTATITE = {"MgO": 40.148343389246, "SiO2": 59.851656610754}
# Exact pure ferrosilite Fe2Si2O6 (2 FeO + 2 SiO2 per formula unit).
PURE_FERROSILITE = {"FeO": 54.45699078365814, "SiO2": 45.543009216341865}


@pytest.fixture(scope="module")
def orthopyroxene_config():
    return load_mineral_config(ORTHOPYROXENE_YAML_PATH)


def test_pure_enstatite_reproduces_mg_si_two_apfu(orthopyroxene_config):
    result = pipeline.calculate(PURE_ENSTATITE, orthopyroxene_config, input_mode="wt_percent")
    assert result.apfu["Mg"] == pytest.approx(2.0, abs=1e-3)
    assert result.apfu["Si"] == pytest.approx(2.0, abs=1e-3)
    assert not result.site_allocation.unallocated
    assert result.end_members["enstatite"] == pytest.approx(100.0, abs=1e-4)
    assert result.end_members["ferrosilite"] == pytest.approx(0.0, abs=1e-4)


def test_pure_ferrosilite_reproduces_fe_si_two_apfu(orthopyroxene_config):
    result = pipeline.calculate(PURE_FERROSILITE, orthopyroxene_config, input_mode="wt_percent")
    assert result.apfu["Fe2"] == pytest.approx(2.0, abs=1e-3)
    assert result.apfu["Si"] == pytest.approx(2.0, abs=1e-3)
    assert result.end_members["ferrosilite"] == pytest.approx(100.0, abs=1e-4)
    assert result.end_members["enstatite"] == pytest.approx(0.0, abs=1e-4)


def test_end_members_have_no_wollastonite_member(orthopyroxene_config):
    """Unlike clinopyroxene.yaml/pyroxene.yaml's 3-member ternary,
    orthopyroxene only reports enstatite/ferrosilite -- Wo isn't a
    meaningful axis for this branch.
    """
    assert set(orthopyroxene_config.end_members.members) == {"enstatite", "ferrosilite"}


def test_mixed_composition_sums_to_100(orthopyroxene_config):
    analysis = {"SiO2": 55.0, "MgO": 32.0, "FeO": 12.0, "Al2O3": 1.0}
    result = pipeline.calculate(analysis, orthopyroxene_config, input_mode="wt_percent", redox_method="droop_1987")
    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    assert em["enstatite"] > em["ferrosilite"] > 0
