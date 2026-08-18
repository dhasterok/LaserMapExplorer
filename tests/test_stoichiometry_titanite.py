"""Characterization test for titanite -- no workbook reference sheet exists
for this mineral (Stage 3 batch); a self-consistency check on a hand-picked
synthetic analysis rather than a cross-check against an authoritative
external value. See ``resources/minerals/titanite.yaml`` and the Stage 3
plan (no Fe-redox split, plain 'Fe' cation, whole-analysis cation-basis
normalization as a simplification of MinPlotX's T+Oct-only normalizer).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

TITANITE_YAML_PATH = project_root / "resources" / "minerals" / "titanite.yaml"

ANALYSIS = {"SiO2": 30.6, "TiO2": 38.0, "Al2O3": 2.0, "FeO": 1.0, "CaO": 28.6}


@pytest.fixture(scope="module")
def titanite_config():
    return load_mineral_config(TITANITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(titanite_config):
    return pipeline.calculate(ANALYSIS, titanite_config, input_mode="wt_percent")


def test_close_to_stoichiometric_titanite(result):
    """This analysis is near-ideal CaTiSiO5, so Si/Ti/Ca should each land
    near 1 apfu and each site near its target.
    """
    assert result.redox is None  # no redox: block -- Fe is plain, unsplit
    assert not result.site_allocation.unallocated
    sites = result.site_allocation.sites
    assert sites["T"].total == pytest.approx(1.0, abs=0.05)
    assert sites["Dec"].total == pytest.approx(1.0, abs=0.05)
    assert sites["T"].elements["Si"] == pytest.approx(0.99, abs=0.05)
    assert sites["Dec"].elements["Ca"] == pytest.approx(0.99, abs=0.05)


def test_titanite_end_member_dominant(result):
    # Ti dominates the octahedral site (minor Al/Fe substitution) -> high XTtn.
    assert result.end_members["titanite_ss"] > 85.0
