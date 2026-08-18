"""Characterization test for apatite -- no workbook reference sheet exists
for this mineral (Stage 3, OH-bearing batch). Uses an *exact* ideal-formula
composition (Ca5(PO4)3, oxide wt% computed directly from molar weights, not
hand-approximated) with a tight tolerance -- an earlier, loosely-toleranced
version of this test (``abs=0.7`` on a target of 8) failed to catch a real
~4% normalization bug (``ideal_oxygens`` was derived by naively subtracting
OH's oxygen from the crystallographic total, rather than matching this
engine's own O-per-cation accounting method; see
``resources/minerals/apatite.yaml``'s comment for the derivation). This
composition is deliberately exact so the same class of bug can't hide
behind a wide tolerance again.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

APATITE_YAML_PATH = project_root / "resources" / "minerals" / "apatite.yaml"

# Exact ideal Ca5(PO4)3 (5 CaO + 1.5 P2O5 by mole), plus trace REE (not part
# of the ideal formula, included to confirm trace cations still parse
# correctly alongside an exact major-element composition).
IDEAL_ANALYSIS = {"CaO": 56.83860695121444, "P2O5": 43.16139304878556}
ANALYSIS_WITH_TRACE = dict(IDEAL_ANALYSIS, Ce2O3=0.3, La2O3=0.15)


@pytest.fixture(scope="module")
def apatite_config():
    return load_mineral_config(APATITE_YAML_PATH)


def test_ideal_formula_reproduces_exact_ca5p3(apatite_config):
    result = pipeline.calculate(IDEAL_ANALYSIS, apatite_config, input_mode="wt_percent")
    assert result.apfu["Ca"] == pytest.approx(5.0, abs=1e-6)
    assert result.apfu["P"] == pytest.approx(3.0, abs=1e-6)
    assert not result.site_allocation.unallocated


def test_no_redox_and_no_end_members(apatite_config):
    result = pipeline.calculate(ANALYSIS_WITH_TRACE, apatite_config, input_mode="wt_percent")
    assert result.redox is None
    assert result.end_members == {}


def test_trace_ree_recovered_alongside_exact_major_elements(apatite_config):
    result = pipeline.calculate(ANALYSIS_WITH_TRACE, apatite_config, input_mode="wt_percent")
    # Adding ~0.45 wt% of REE oxides correctly dilutes Ca/P slightly below
    # exactly 5/3 (the O-basis sum now includes the REE contribution too) --
    # a looser tolerance here than the exact-formula test, matching that
    # expected small dilution rather than a tight formula check.
    assert result.apfu["Ca"] == pytest.approx(5.0, rel=0.02)
    assert result.apfu["P"] == pytest.approx(3.0, rel=0.02)
    assert result.apfu["Ce"] > result.apfu["La"] > 0
