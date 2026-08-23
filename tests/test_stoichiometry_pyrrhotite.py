"""Characterization tests for pyrrhotite (Fe(1-x)S) -- no workbook
reference sheet exists for this mineral. This is the key test of the whole
anion-basis mechanism: cation-basis normalization would force the metal
site to exactly 1.0 apfu by construction, hiding any real Fe-vacancy
entirely (it would leak into an inflated S apfu instead). Anchoring on the
directly-measured S lets the metal apfu itself show the deficiency. See
``resources/minerals/pyrrhotite.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

PYRRHOTITE_YAML_PATH = project_root / "resources" / "minerals" / "pyrrhotite.yaml"

# Exact stoichiometric FeS (troilite end-member, no vacancy).
STOICHIOMETRIC_FES = {"Fe": 63.52519622, "S": 36.47480378}
# Exact Fe0.9S -- a 10% Fe-vacancy composition (x = 0.1 in Fe(1-x)S).
FE_DEFICIENT = {"Fe": 61.05095019, "S": 38.94904981}


@pytest.fixture(scope="module")
def pyrrhotite_config():
    return load_mineral_config(PYRRHOTITE_YAML_PATH)


def test_stoichiometric_fes_shows_no_vacancy(pyrrhotite_config):
    result = pipeline.calculate(STOICHIOMETRIC_FES, pyrrhotite_config, input_mode="element_wt_percent")
    assert result.basis_used == "anion"
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-3)
    assert result.end_members["vacancy_fraction"] == pytest.approx(0.0, abs=0.5)


def test_fe_deficient_composition_shows_real_vacancy_on_metal_side(pyrrhotite_config):
    """The whole point of basis: "anion" -- Fe apfu itself reads ~0.9, not
    pinned to 1.0, and vacancy_fraction reads ~10%, not 0.
    """
    result = pipeline.calculate(FE_DEFICIENT, pyrrhotite_config, input_mode="element_wt_percent")
    assert result.apfu["Fe"] == pytest.approx(0.9, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(1.0, abs=1e-6)
    assert result.end_members["vacancy_fraction"] == pytest.approx(10.0, abs=0.5)


def test_falls_back_to_cation_basis_when_s_not_measured(pyrrhotite_config):
    """Without S, the vacancy signal is lost (same as before this engine
    change) -- Fe is pinned back to exactly 1.0 under the cation-basis
    fallback, rather than raising.
    """
    result = pipeline.calculate({"Fe": 100.0}, pyrrhotite_config, input_mode="element_wt_percent")
    assert result.basis_used == "cation"
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-6)
