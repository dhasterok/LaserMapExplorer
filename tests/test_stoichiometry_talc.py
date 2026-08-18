"""Characterization test for talc -- no workbook reference sheet exists for
this mineral (Stage 3 batch); a self-consistency check on a hand-picked
synthetic analysis. Shares its site-allocation code
(``tetra_fe3_ratio``) with serpentine, exercised more thoroughly in
``test_stoichiometry_serpentine.py``; this file focuses on talc's own
differences (extra Na/K in M, different site targets). See
``resources/minerals/talc.yaml`` and the Stage 3 plan.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

TALC_YAML_PATH = project_root / "resources" / "minerals" / "talc.yaml"

ANALYSIS = {"SiO2": 63.0, "MgO": 31.5, "FeO": 1.0}


@pytest.fixture(scope="module")
def talc_config():
    return load_mineral_config(TALC_YAML_PATH)


@pytest.fixture(scope="module")
def result(talc_config):
    return pipeline.calculate(ANALYSIS, talc_config, input_mode="wt_percent", redox_method="fixed_ratio")


def test_near_ideal_talc_hits_site_targets(result):
    sites = result.site_allocation.sites
    assert not result.site_allocation.unallocated
    assert sites["T"].elements["Si"] == pytest.approx(4.0, abs=0.05)
    assert sites["M"].total == pytest.approx(3.0, abs=0.05)
    assert result.end_members == {}  # no end-member scheme for talc


def test_na_k_in_m_site_when_present():
    from src.stoichiometry.config import parse_mineral_config
    import yaml
    with TALC_YAML_PATH.open() as f:
        raw = yaml.safe_load(f)
    config = parse_mineral_config(raw)
    analysis = dict(ANALYSIS, Na2O=0.3, K2O=0.1)
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="fixed_ratio")
    m = result.site_allocation.sites["M"]
    assert m.elements.get("Na", 0.0) > 0
    assert m.elements.get("K", 0.0) > 0
    assert not result.site_allocation.unallocated
