"""Characterization test for carbonate -- no workbook reference
sheet exists for this mineral (see ``resources/minerals/
carbonate.yaml``). A self-consistency check on hand-picked synthetic
analyses (near-ideal dolomite and near-pure calcite) rather than a
cross-check against an authoritative external value.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

CARBONATE_YAML_PATH = project_root / "resources" / "minerals" / "carbonate.yaml"

DOLOMITE_ANALYSIS = {"CaO": 30.4, "MgO": 21.7, "FeO": 0.5}
CALCITE_ANALYSIS = {"CaO": 55.0, "MgO": 0.5, "FeO": 0.3, "MnO": 0.2}


@pytest.fixture(scope="module")
def carbonate_config():
    return load_mineral_config(CARBONATE_YAML_PATH)


def test_dolomite_composition_splits_ca_mg_evenly(carbonate_config):
    r = pipeline.calculate(DOLOMITE_ANALYSIS, carbonate_config, input_mode="wt_percent")
    assert r.redox is None  # no redox: block -- Fe is plain, unsplit
    assert not r.site_allocation.unallocated
    m = r.site_allocation.sites["M"]
    assert m.total == pytest.approx(1.0, abs=1e-9)  # single site, cation-basis normalized to 1
    assert m.elements["Ca"] == pytest.approx(m.elements["Mg"], abs=0.02)
    em = r.end_members
    assert em["calcite"] == pytest.approx(em["magnesite"], abs=2.0)
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)


def test_calcite_composition_is_calcite_dominant(carbonate_config):
    r = pipeline.calculate(CALCITE_ANALYSIS, carbonate_config, input_mode="wt_percent")
    assert r.end_members["calcite"] > 90.0
