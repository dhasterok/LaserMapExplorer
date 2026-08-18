"""Characterization test for lawsonite -- no workbook reference sheet exists
for this mineral (Stage 3 batch); a self-consistency check on a near-ideal
synthetic composition rather than a cross-check against an authoritative
external value. See ``resources/minerals/lawsonite.yaml`` and the Stage 3
plan (sequential capped-fill M-site, product-of-fractions end-member).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

LAWSONITE_YAML_PATH = project_root / "resources" / "minerals" / "lawsonite.yaml"

ANALYSIS = {"SiO2": 38.2, "Al2O3": 31.8, "FeO": 0.5, "MgO": 0.1, "CaO": 17.3}


@pytest.fixture(scope="module")
def lawsonite_config():
    return load_mineral_config(LAWSONITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(lawsonite_config):
    return pipeline.calculate(ANALYSIS, lawsonite_config, input_mode="wt_percent", redox_method="fixed_ratio")


def test_near_ideal_composition_hits_targets(result):
    sites = result.site_allocation.sites
    assert not result.site_allocation.unallocated
    assert sites["T"].elements["Si"] == pytest.approx(2.0, abs=0.05)
    assert sites["M"].total == pytest.approx(2.0, abs=1e-6)
    assert sites["A"].elements["Ca"] == pytest.approx(0.98, abs=0.05)


def test_mg_fe2_sequential_priority_fill_in_m(result):
    """Mg is listed before Fe2+ in M's priority list -- for this
    Mg-poor/Fe-bearing composition, Mg should be fully absorbed into M
    (space permitting) before Fe2+ gets any of the remaining M-space.
    """
    m = result.site_allocation.sites["M"]
    assert m.elements.get("Mg", 0.0) == pytest.approx(result.apfu["Mg"], rel=1e-6)  # all Mg fits


def test_end_member_matches_product_of_site_fractions(result):
    m = result.site_allocation.sites["M"]
    a = result.site_allocation.sites["A"]
    expected = 100.0 * (m.elements["Al"] / m.total) * (a.elements["Ca"] / a.total)
    assert result.end_members["lawsonite"] == pytest.approx(expected, rel=1e-6)
    assert result.end_members["lawsonite"] > 90  # near-ideal composition
