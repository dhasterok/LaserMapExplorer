"""Characterization tests for serpentine -- no workbook reference sheet
exists for this mineral (Stage 3 batch); these check self-consistency and
specifically the new ``tetra_fe3_ratio`` site-allocation method (a fixed-
fraction T/M split for Fe3+, distinct from capped-spillover and
equipartition -- see ``sites.py``'s ``_allocate_tetra_fe3_ratio``) on
hand-picked synthetic analyses. See ``resources/minerals/serpentine.yaml``
and the Stage 3 plan.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest
import yaml

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config, parse_mineral_config

SERPENTINE_YAML_PATH = project_root / "resources" / "minerals" / "serpentine.yaml"


@pytest.fixture(scope="module")
def serpentine_config():
    return load_mineral_config(SERPENTINE_YAML_PATH)


def test_default_config_routes_no_fe3_to_t(serpentine_config):
    """serpentine.yaml's default tetra_fe3_ratio=0.0 -- even with measured
    Fe3+, none of it should land in T.
    """
    analysis = {"SiO2": 40.0, "FeO": 8.0, "MgO": 38.0}
    result = pipeline.calculate(analysis, serpentine_config, input_mode="wt_percent", redox_method="fixed_ratio")
    assert not result.site_allocation.unallocated
    assert "Fe3" not in result.site_allocation.sites["T"].elements
    assert result.end_members == {}  # no end-member scheme for serpentine


def test_nonzero_tetra_fe3_ratio_splits_fe3_by_fixed_fraction():
    """With both fixed_ratio (Fe2+/Fe3+ split) and tetra_fe3_ratio (T/M
    split of that Fe3+) set to 0.5, exactly half of total Fe3+ should land
    in T regardless of T's remaining space -- confirming this is a fixed
    fraction, not a capped-fill.
    """
    with SERPENTINE_YAML_PATH.open() as f:
        raw = yaml.safe_load(f)
    raw["redox"]["fixed_ratio"] = 0.5
    raw["site_allocation"]["tetra_fe3_ratio"] = 0.5
    config = parse_mineral_config(raw)

    analysis = {"SiO2": 40.0, "FeO": 8.0, "MgO": 38.0}
    result = pipeline.calculate(analysis, config, input_mode="wt_percent", redox_method="fixed_ratio")

    fe3_total = result.redox.species_3plus_apfu
    t_fe3 = result.site_allocation.sites["T"].elements.get("Fe3", 0.0)
    m_fe3 = result.site_allocation.sites["M"].elements.get("Fe3", 0.0)
    assert t_fe3 == pytest.approx(0.5 * fe3_total, rel=1e-6)
    assert m_fe3 == pytest.approx(0.5 * fe3_total, rel=1e-6)
    assert t_fe3 + m_fe3 == pytest.approx(fe3_total, rel=1e-9)
    assert not result.site_allocation.unallocated
