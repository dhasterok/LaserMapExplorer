"""Characterization test for sapphirine -- no workbook reference sheet
exists for this mineral, and no single polytype-exact ideal formula either
(see ``resources/minerals/sapphirine.yaml``'s comment on the 7:9:3 vs 2:2:1
polytype ambiguity). A self-consistency check on a hand-picked synthetic
Mg-rich analysis rather than a cross-check against an authoritative
external value.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

SAPPHIRINE_YAML_PATH = project_root / "resources" / "minerals" / "sapphirine.yaml"

ANALYSIS = {"SiO2": 13.5, "Al2O3": 63.5, "MgO": 20.0, "FeO": 3.0}


@pytest.fixture(scope="module")
def sapphirine_config():
    return load_mineral_config(SAPPHIRINE_YAML_PATH)


@pytest.fixture(scope="module")
def result(sapphirine_config):
    return pipeline.calculate(ANALYSIS, sapphirine_config, input_mode="wt_percent")


def test_sites_fill_to_target(result):
    assert not result.site_allocation.unallocated
    sites = result.site_allocation.sites
    assert sites["T"].total == pytest.approx(2.0, abs=1e-6)  # T is Si+Al, capped at target
    assert sites["M"].total == pytest.approx(12.0, abs=1e-6)
    assert sites["T"].elements["Si"] == pytest.approx(1.57, abs=0.05)


def test_mg_number_reflects_mg_rich_composition(result):
    # Mg strongly dominates Fe2+ in this analysis -> high mg_number.
    assert result.end_members["mg_number"] > 90.0
