"""Characterization test for glaucophane -- no workbook reference sheet
exists for this mineral, and no charge-balance Fe3+ estimator is
implemented either (see ``resources/minerals/glaucophane.yaml``'s
comment). A self-consistency check on a hand-picked Na-amphibole synthetic
analysis rather than a cross-check against an authoritative external
value.

Pure Python -- no PyQt/QApplication needed.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

GLAUCOPHANE_YAML_PATH = project_root / "resources" / "minerals" / "glaucophane.yaml"

# Na-amphibole: Na dominant in B, Mg > Fe2+, Al-dominant C (no Fe3+ input).
ANALYSIS = {"SiO2": 58.0, "Al2O3": 11.0, "MgO": 12.0, "FeO": 7.0, "Na2O": 7.0, "CaO": 1.0}


@pytest.fixture(scope="module")
def glaucophane_config():
    return load_mineral_config(GLAUCOPHANE_YAML_PATH)


@pytest.fixture(scope="module")
def result(glaucophane_config):
    return pipeline.calculate(ANALYSIS, glaucophane_config, input_mode="wt_percent")


def test_b_site_na_dominant(result):
    assert not result.site_allocation.unallocated
    b = result.site_allocation.sites["B"]
    assert b.total == pytest.approx(2.0, abs=0.05)
    assert b.elements["Na"] > b.elements.get("Ca", 0.0)


def test_no_fe3_without_a_fixed_ratio(result):
    assert result.apfu["Fe3"] == pytest.approx(0.0, abs=1e-9)
    assert result.end_members["fe3_c_fraction"] == pytest.approx(0.0, abs=1e-9)


def test_fixed_ratio_moves_fe3_c_fraction(glaucophane_config):
    """Supplying a nonzero Fe3+ ratio (config.redox.fixed_ratio isn't a
    per-call override -- see redox.py -- so this rebuilds the config with a
    different value) should shift the C-site Fe3+/(Al+Fe3+) diagnostic
    toward the riebeckite side, exercising the path the default (all-
    ferrous) analysis can't reach.
    """
    riebeckite_leaning_config = dataclasses.replace(
        glaucophane_config,
        redox=dataclasses.replace(glaucophane_config.redox, fixed_ratio=0.5),
    )
    r = pipeline.calculate(ANALYSIS, riebeckite_leaning_config, input_mode="wt_percent")
    assert r.apfu["Fe3"] > 0.0
    assert r.end_members["fe3_c_fraction"] > 0.0
