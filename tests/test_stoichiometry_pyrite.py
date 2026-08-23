"""Characterization tests for the pyrite group (pyrite/cattierite/vaesite)
-- no workbook reference sheet exists for this mineral. Uses exact
end-member and mixed element wt% compositions to verify the anion-basis
engine reproduces ideal apfu and the pyrite_group_ratio end-members. See
``resources/minerals/pyrite.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

PYRITE_YAML_PATH = project_root / "resources" / "minerals" / "pyrite.yaml"

# Textbook pyrite FeS2 (also used by test_stoichiometry_sulfide.py's generic-config test).
PYRITE = {"Fe": 46.55, "S": 53.45}
# A 50:25:25 (molar) pyrite:cattierite:vaesite mix, oxide-wt%-style computed
# from CoS2/NiS2/FeS2 molar weights.
MIXED_SERIES = {
    "Fe": 46.55 * 0.5, "Co": 47.88856245768688 * 0.25, "Ni": 47.78682238075155 * 0.25,
    "S": 53.45 * 0.5 + 52.11143754231312 * 0.25 + 52.213177619248455 * 0.25,
}


@pytest.fixture(scope="module")
def pyrite_config():
    return load_mineral_config(PYRITE_YAML_PATH)


def test_pure_pyrite_anchors_on_measured_s(pyrite_config):
    result = pipeline.calculate(PYRITE, pyrite_config, input_mode="element_wt_percent")
    assert result.basis_used == "anion"
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(2.0, abs=1e-6)
    assert result.end_members["pyrite"] > 99.0


def test_mixed_series_end_members_track_fe_co_ni_ratio(pyrite_config):
    result = pipeline.calculate(MIXED_SERIES, pyrite_config, input_mode="element_wt_percent")
    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    assert em["pyrite"] == pytest.approx(50.0, abs=2.0)
    assert em["cattierite"] == pytest.approx(25.0, abs=2.0)
    assert em["vaesite"] == pytest.approx(25.0, abs=2.0)
