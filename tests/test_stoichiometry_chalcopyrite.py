"""Characterization tests for chalcopyrite (CuFeS2) -- no workbook
reference sheet exists for this mineral. Verifies the anion-basis engine
(anchored on S at 2.0) reproduces ideal apfu, has no end_members (single
near-pure phase, see the YAML's comment), and falls back to cation-basis
when S isn't measured. See ``resources/minerals/chalcopyrite.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

CHALCOPYRITE_YAML_PATH = project_root / "resources" / "minerals" / "chalcopyrite.yaml"

# Textbook chalcopyrite CuFeS2 (also used by test_stoichiometry_sulfide.py's generic-config test).
CHALCOPYRITE = {"Cu": 34.63, "Fe": 30.43, "S": 34.94}


@pytest.fixture(scope="module")
def chalcopyrite_config():
    return load_mineral_config(CHALCOPYRITE_YAML_PATH)


def test_pure_chalcopyrite_anchors_on_measured_s(chalcopyrite_config):
    result = pipeline.calculate(CHALCOPYRITE, chalcopyrite_config, input_mode="element_wt_percent")
    assert result.basis_used == "anion"
    assert result.apfu["Cu"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(2.0, abs=1e-6)
    assert result.end_members == {}


def test_falls_back_to_cation_basis_when_s_not_measured(chalcopyrite_config):
    result = pipeline.calculate({"Cu": 34.63, "Fe": 30.43}, chalcopyrite_config, input_mode="element_wt_percent")
    assert result.basis_used == "cation"
    assert result.apfu["Cu"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-3)
