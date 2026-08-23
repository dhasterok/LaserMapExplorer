"""Characterization test for an orthoclase-dominant composition, run
through the shared ``resources/minerals/feldspar.yaml`` config (see that
file's comment -- alkali feldspar and plagioclase use the same generic
engine, not a separate calculation); no workbook reference sheet exists for
this specific composition (the workbook reference test uses a labradorite
instead -- see ``test_stoichiometry_feldspar_workbook_reference.py``). A
self-consistency check on a hand-picked synthetic analysis rather than a
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

FELDSPAR_YAML_PATH = project_root / "resources" / "minerals" / "feldspar.yaml"

# Near-ideal orthoclase (KAlSi3O8) with a small albite component.
ANALYSIS = {"SiO2": 64.7, "Al2O3": 18.4, "CaO": 0.0, "Na2O": 0.5, "K2O": 16.0}


@pytest.fixture(scope="module")
def kfeldspar_config():
    return load_mineral_config(FELDSPAR_YAML_PATH)


@pytest.fixture(scope="module")
def result(kfeldspar_config):
    return pipeline.calculate(ANALYSIS, kfeldspar_config, input_mode="wt_percent")


def test_close_to_stoichiometric_orthoclase(result):
    assert not result.site_allocation.unallocated
    sites = result.site_allocation.sites
    assert sites["T"].total == pytest.approx(4.0, abs=0.05)
    assert sites["A"].total == pytest.approx(1.0, abs=0.05)
    assert sites["T"].elements["Si"] == pytest.approx(3.0, abs=0.05)
    assert sites["A"].elements["K"] == pytest.approx(0.95, abs=0.05)


def test_end_members_orthoclase_dominant(result):
    em = result.end_members
    assert em["orthoclase"] > 90.0
    assert em["albite"] > 0.0
    assert em["anorthite"] == pytest.approx(0.0, abs=1e-6)
    assert em["anorthite"] + em["albite"] + em["orthoclase"] == pytest.approx(100.0, abs=1e-6)
