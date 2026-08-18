"""Characterization tests for epidote -- no workbook reference sheet exists
for this mineral (Stage 3 batch); these check self-consistency and
specifically the new ``epidote_equipart`` site-allocation method (Fe2+/
Mn2+/Mg equipartitioned between M and A by bulk ratio, scaled by remaining
M-space -- see ``sites.py``'s ``_allocate_epidote_equipart``) on hand-picked
synthetic analyses, including both the "M-space-limited" and "divalent-
cations-limited" edge cases. See ``resources/minerals/epidote.yaml`` and the
Stage 3 plan.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

EPIDOTE_YAML_PATH = project_root / "resources" / "minerals" / "epidote.yaml"


@pytest.fixture(scope="module")
def epidote_config():
    return load_mineral_config(EPIDOTE_YAML_PATH)


def test_equipartition_when_m_space_is_the_limiting_factor(epidote_config):
    """Al+Fe3+ alone nearly fill M's target -- the small amount of
    remaining M-space should be split between Mn2+ and Mg in proportion to
    their bulk ratio, with the rest overflowing to A.
    """
    analysis = {"SiO2": 38.0, "Al2O3": 22.0, "FeO": 8.0, "MnO": 2.0, "MgO": 1.5, "CaO": 23.0}
    result = pipeline.calculate(analysis, epidote_config, input_mode="wt_percent", redox_method="fixed_ratio")

    m = result.site_allocation.sites["M"]
    a = result.site_allocation.sites["A"]
    assert m.total == pytest.approx(3.0, abs=1e-6)  # M-space was the binding constraint

    mn_total = result.apfu["Mn"]
    mg_total = result.apfu["Mg"]
    # Mn2+/Mg split the same fraction of their respective totals into M.
    mn_fraction_in_m = m.elements.get("Mn", 0.0) / mn_total
    mg_fraction_in_m = m.elements.get("Mg", 0.0) / mg_total
    assert mn_fraction_in_m == pytest.approx(mg_fraction_in_m, rel=1e-6)
    assert 0 < mn_fraction_in_m < 1
    # And whatever didn't fit lands in A.
    assert a.elements.get("Mn", 0.0) == pytest.approx(mn_total - m.elements.get("Mn", 0.0), rel=1e-6)
    assert a.elements.get("Mg", 0.0) == pytest.approx(mg_total - m.elements.get("Mg", 0.0), rel=1e-6)


def test_equipartition_when_divalent_cations_are_the_limiting_factor(epidote_config):
    """Low Al+Fe3+ leaves abundant M-space, but Mg is scarce -- all of it
    should fit in M (share capped at 1), leaving none for A.
    """
    analysis = {"SiO2": 40.0, "Al2O3": 10.0, "FeO": 2.0, "CaO": 24.0, "MgO": 0.2}
    result = pipeline.calculate(analysis, epidote_config, input_mode="wt_percent", redox_method="fixed_ratio")

    m = result.site_allocation.sites["M"]
    a = result.site_allocation.sites["A"]
    assert m.total < 3.0  # M-space wasn't the binding constraint here
    assert m.elements.get("Mg", 0.0) == pytest.approx(result.apfu["Mg"], rel=1e-6)  # all Mg fits in M
    assert a.elements.get("Mg", 0.0) is None or a.elements.get("Mg", 0.0) == pytest.approx(0.0, abs=1e-9)


def test_end_members_sum_and_dominant_member(epidote_config):
    analysis = {"SiO2": 38.5, "Al2O3": 24.0, "FeO": 12.0, "CaO": 23.5}
    result = pipeline.calculate(analysis, epidote_config, input_mode="wt_percent", redox_method="fixed_ratio")
    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    assert em["cr_epidote"] == pytest.approx(0.0, abs=1e-9)  # no Cr in this analysis
    assert em["epidote"] > em["clinozoisite"] > 0  # Fe3+-rich M site
