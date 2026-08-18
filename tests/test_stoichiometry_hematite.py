"""Characterization test for hematite -- no workbook reference sheet exists
for this mineral (see ``resources/minerals/hematite.yaml``). A
self-consistency check on a hand-picked near-pure Fe2O3 analysis rather
than a cross-check against an authoritative external value.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

HEMATITE_YAML_PATH = project_root / "resources" / "minerals" / "hematite.yaml"

ANALYSIS = {"Fe2O3": 98.0, "Al2O3": 1.0, "TiO2": 0.5}


@pytest.fixture(scope="module")
def hematite_config():
    return load_mineral_config(HEMATITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(hematite_config):
    return pipeline.calculate(ANALYSIS, hematite_config, input_mode="wt_percent")


def test_default_all_ferric(result):
    assert result.redox.method == "all_3plus"
    assert result.redox.species_2plus_apfu == pytest.approx(0.0, abs=1e-9)


def test_close_to_stoichiometric_hematite(result):
    assert not result.site_allocation.unallocated
    m = result.site_allocation.sites["M"]
    assert m.total == pytest.approx(2.0, abs=1e-9)  # single site, cation-basis normalized
    assert m.elements["Fe3"] == pytest.approx(1.96, abs=0.05)


def test_all_2plus_still_allocates(hematite_config):
    """M's element list includes Fe2 (not just Fe3), so choosing all_2plus
    doesn't strand the whole analysis in 'unallocated'.
    """
    r = pipeline.calculate(ANALYSIS, hematite_config, input_mode="wt_percent", redox_method="all_2plus")
    assert not r.site_allocation.unallocated
    assert r.site_allocation.sites["M"].elements["Fe2"] == pytest.approx(1.96, abs=0.05)
