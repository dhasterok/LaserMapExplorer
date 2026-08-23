"""Characterization tests for the monosulfide group (sphalerite/galena/
alabandite/greenockite/troilite) -- no workbook reference sheet exists for
this mineral. Uses exact end-member element wt% compositions (computed
from molar weights) to verify the anion-basis (basis: "anion") engine
reproduces ideal apfu and the monosulfide_ratio end-members, plus a
fallback test confirming graceful degradation to cation-basis when S isn't
measured. See ``resources/minerals/monosulfide.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

MONOSULFIDE_YAML_PATH = project_root / "resources" / "minerals" / "monosulfide.yaml"

# Textbook sphalerite ZnS (also used by test_stoichiometry_sulfide.py's generic-config test).
SPHALERITE = {"Zn": 67.1, "S": 32.9}
# Exact galena PbS (from molar weights).
GALENA = {"Pb": 86.59854136626753, "S": 13.401458633732473}


@pytest.fixture(scope="module")
def monosulfide_config():
    return load_mineral_config(MONOSULFIDE_YAML_PATH)


def test_sphalerite_anchors_on_measured_s(monosulfide_config):
    result = pipeline.calculate(SPHALERITE, monosulfide_config, input_mode="element_wt_percent")
    assert result.basis_used == "anion"
    assert result.apfu["Zn"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(1.0, abs=1e-6)
    assert result.end_members["sphalerite"] > 99.0
    assert result.end_members["galena"] == pytest.approx(0.0, abs=1e-6)


def test_galena_end_member_dominant(monosulfide_config):
    result = pipeline.calculate(GALENA, monosulfide_config, input_mode="element_wt_percent")
    assert result.apfu["Pb"] == pytest.approx(1.0, abs=1e-3)
    assert result.end_members["galena"] > 99.0
    assert sum(result.end_members.values()) == pytest.approx(100.0, abs=1e-6)


def test_falls_back_to_cation_basis_when_s_not_measured(monosulfide_config):
    """S absent entirely (not below-LOD, just never collected) -- should
    fall back to cation-basis (metal pinned to 1.0 apfu, same as before
    this engine change) rather than raising.
    """
    result = pipeline.calculate({"Zn": 100.0}, monosulfide_config, input_mode="element_wt_percent")
    assert result.basis_used == "cation"
    assert result.apfu["Zn"] == pytest.approx(1.0, abs=1e-6)
