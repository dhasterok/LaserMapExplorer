"""Characterization tests for chloritoid -- no workbook reference sheet
exists for this mineral (Stage 3 batch); these check self-consistency and
the reused ``droop_1987`` Fe3+ formula plus the T-site "no spillover
recipient" case on hand-picked synthetic analyses. See
``resources/minerals/chloritoid.yaml`` and the Stage 3 plan.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

CHLORITOID_YAML_PATH = project_root / "resources" / "minerals" / "chloritoid.yaml"

ANALYSIS = {"SiO2": 24.5, "Al2O3": 40.5, "FeO": 27.0, "MnO": 0.5, "MgO": 2.0}


@pytest.fixture(scope="module")
def chloritoid_config():
    return load_mineral_config(CHLORITOID_YAML_PATH)


@pytest.fixture(scope="module")
def result(chloritoid_config):
    return pipeline.calculate(ANALYSIS, chloritoid_config, input_mode="wt_percent", redox_method="droop_1987")


def test_al_spills_l2_to_l1_capped_then_uncapped(result):
    sites = result.site_allocation.sites
    assert not result.site_allocation.unallocated
    assert sites["L2"].total == pytest.approx(3.0, abs=1e-6)
    assert sites["L2"].elements["Al"] == pytest.approx(3.0, abs=1e-6)
    # L1 is Al's last site -- uncapped, takes the remainder.
    assert sites["L1"].elements["Al"] == pytest.approx(result.apfu["Al"] - 3.0, rel=1e-6)


def test_si_left_uncapped_not_truncated(result):
    """Si has no later site claiming it, so this codebase's generic engine
    reports it uncapped (matching this package's "never silently discard"
    rule) rather than replicating MinPlotX's hard truncation at target=2.
    """
    sites = result.site_allocation.sites
    assert sites["T"].elements["Si"] == pytest.approx(result.apfu["Si"], rel=1e-9)


def test_droop_recovers_some_fe3_for_al_rich_composition(result):
    assert result.redox.S > result.redox.T
    assert result.redox.species_3plus_apfu > 0
    assert result.end_members["mg_number"] == pytest.approx(
        100.0 * result.apfu["Mg"] / (result.apfu["Mg"] + result.apfu["Fe2"]), rel=1e-6
    )
