"""Characterization test for amphibole -- no workbook reference sheet
exists for this mineral, and no charge-balance Fe3+ estimator is
implemented either (see ``resources/minerals/amphibole.yaml``'s comment).
A self-consistency check on a hand-picked tremolite-leaning synthetic
analysis rather than a cross-check against an authoritative external
value.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

AMPHIBOLE_YAML_PATH = project_root / "resources" / "minerals" / "amphibole.yaml"

# Tremolite-leaning: high Si, Ca~2, Mg >> Fe2+, minor Al/Na.
ANALYSIS = {"SiO2": 58.0, "Al2O3": 1.0, "MgO": 24.0, "FeO": 2.0, "CaO": 13.0, "Na2O": 0.3}


@pytest.fixture(scope="module")
def amphibole_config():
    return load_mineral_config(AMPHIBOLE_YAML_PATH)


@pytest.fixture(scope="module")
def result(amphibole_config):
    return pipeline.calculate(ANALYSIS, amphibole_config, input_mode="wt_percent")


def test_sites_close_to_target_on_23_oxygen_basis(result):
    assert not result.site_allocation.unallocated
    sites = result.site_allocation.sites
    assert sites["T"].total == pytest.approx(8.0, abs=0.05)
    assert sites["C"].total == pytest.approx(5.0, abs=0.05)
    assert sites["B"].total == pytest.approx(2.0, abs=0.1)
    assert sites["A"].total < 0.5  # low Na/K -> mostly filled by B, little spills to A


def test_default_all_ferrous_no_charge_balance(result):
    assert result.redox.method == "fixed_ratio"
    assert result.apfu["Fe3"] == pytest.approx(0.0, abs=1e-9)


def test_low_tschermak_high_mg_number(result):
    # Near the tremolite-actinolite-ferro-actinolite quadrilateral (low Al),
    # and Mg strongly dominates Fe2+.
    em = result.end_members
    assert em["mg_number"] > 90.0
    assert em["tschermak_fraction"] < 15.0
