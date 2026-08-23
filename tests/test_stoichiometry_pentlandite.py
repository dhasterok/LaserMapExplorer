"""Characterization tests for pentlandite ((Fe,Ni,Co)9S8) -- no workbook
reference sheet exists for this mineral. Verifies the anion-basis engine
(anchored on S at 8.0) reproduces the ideal 9:8 metal:S ratio, the
pentlandite_ratio end-member, and that a non-ideal analysis correctly shows
a metal total that deviates from 9 (rather than being forced to it), since
the metal side floats under basis: "anion". See
``resources/minerals/pentlandite.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

PENTLANDITE_YAML_PATH = project_root / "resources" / "minerals" / "pentlandite.yaml"

# Exact pure pentlandite (Fe4.5Ni4.5)S8 (1:1 Fe:Ni, 9 metal : 8 S).
PURE_PENTLANDITE = {"Fe": 32.55454938, "Ni": 34.21500919, "S": 33.23044143}
# Exact pure cobalt-pentlandite Co9S8.
COBALT_PENTLANDITE = {"Co": 67.40197150339873, "S": 32.59802849660128}
# Roughly 1:1 Fe:Ni but not perfectly ideal pentlandite stoichiometry (a
# realistic EPMA-style analysis) -- used to confirm the metal total is
# allowed to float away from 9.0 rather than being forced there.
NEAR_IDEAL_PENTLANDITE = {"Fe": 32.0, "Ni": 34.2, "S": 33.8}


@pytest.fixture(scope="module")
def pentlandite_config():
    return load_mineral_config(PENTLANDITE_YAML_PATH)


def test_pure_pentlandite_reproduces_9_8_ratio(pentlandite_config):
    result = pipeline.calculate(PURE_PENTLANDITE, pentlandite_config, input_mode="element_wt_percent")
    assert result.basis_used == "anion"
    assert result.apfu["Fe"] + result.apfu["Ni"] == pytest.approx(9.0, abs=1e-2)
    assert result.apfu["S"] == pytest.approx(8.0, abs=1e-6)
    assert result.end_members["pentlandite"] > 99.0
    assert result.end_members["cobalt_pentlandite"] == pytest.approx(0.0, abs=1e-6)


def test_cobalt_pentlandite_end_member_dominant(pentlandite_config):
    result = pipeline.calculate(COBALT_PENTLANDITE, pentlandite_config, input_mode="element_wt_percent")
    assert result.apfu["Co"] == pytest.approx(9.0, abs=1e-3)
    assert result.end_members["cobalt_pentlandite"] > 99.0


def test_non_ideal_composition_metal_total_floats(pentlandite_config):
    """Anion-basis normalization (anchored on S) does not force the metal
    total to exactly 9.0 the way cation-basis would -- a real, slightly
    non-ideal composition should show that directly in the M-site total.
    """
    result = pipeline.calculate(NEAR_IDEAL_PENTLANDITE, pentlandite_config, input_mode="element_wt_percent")
    m_total = result.site_allocation.sites["M"].total
    assert m_total != pytest.approx(9.0, abs=1e-6)
    assert result.apfu["S"] == pytest.approx(8.0, abs=1e-6)
