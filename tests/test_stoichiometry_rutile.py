"""Characterization tests for rutile -- no workbook reference sheet exists
for this mineral (Stage 3-style batch entry). Uses *exact* ideal-formula
compositions (oxide wt% computed directly from molar weights) plus a
trace-substituent case, matching ilmenite's/monazite's precedent for a
new-mineral characterization test in this batch. See
``resources/minerals/rutile.yaml``.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

RUTILE_YAML_PATH = project_root / "resources" / "minerals" / "rutile.yaml"


@pytest.fixture(scope="module")
def rutile_config():
    return load_mineral_config(RUTILE_YAML_PATH)


def test_pure_rutile_reproduces_one_ti_apfu(rutile_config):
    result = pipeline.calculate({"TiO2": 100.0}, rutile_config, input_mode="wt_percent")
    assert result.apfu["Ti"] == pytest.approx(1.0, abs=1e-6)
    assert result.site_allocation.sites["M"].total == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated
    assert result.redox is None


def test_trace_substituted_rutile_fills_m_site_fully(rutile_config):
    """Nb/Fe/Zr trace substituents (Zr-in-rutile thermometry, Nb-Ta
    geochemistry) should all land in the single M site alongside Ti, with
    nothing left unallocated -- the single-site engine takes every listed
    element unconditionally (see sites.py's has_later_site rule: none of
    these elements has a second eligible site).
    """
    analysis = {"TiO2": 90.0, "Nb2O5": 5.0, "FeO": 3.0, "ZrO2": 2.0}
    result = pipeline.calculate(analysis, rutile_config, input_mode="wt_percent")
    m = result.site_allocation.sites["M"]
    assert m.total == pytest.approx(1.0, abs=1e-6)
    assert set(m.elements) == {"Ti", "Nb", "Fe", "Zr"}
    assert not result.site_allocation.unallocated
    assert result.end_members == {}
