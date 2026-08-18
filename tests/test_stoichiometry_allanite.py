"""Characterization tests for allanite -- no workbook reference sheet exists
for this mineral (Stage 3, OH-bearing batch). Uses an *exact* ideal-formula
composition (Ca1Ce1Fe1Al2Si3, oxide wt% computed directly from molar
weights) with a tight tolerance on the cation ratios -- this is the check
that would have caught the ``ideal_oxygens`` derivation mistake found
elsewhere in this batch (apatite/staurolite/mica; see
``resources/minerals/apatite.yaml``'s comment for the general derivation).
Allanite's own target happened to already be correct (matches epidote's,
both epidote-group minerals), confirmed here rather than assumed.

See also ``sites.py``'s ``_allocate_equipart`` docstring -- allanite reuses
the same generic T/M/A equipartition method as epidote, just with a much
larger A-site element list (individual REE + Pb/U/Th).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

ALLANITE_YAML_PATH = project_root / "resources" / "minerals" / "allanite.yaml"

# Exact ideal Ca1 Ce1 Fe1(2+) Al2 Si3 (3 SiO2 + 1 Al2O3 + 1 CaO + 0.5 Ce2O3 + 1 FeO).
IDEAL_ANALYSIS = {
    "SiO2": 31.389214083654487, "Al2O3": 17.75552214845719, "CaO": 9.765310371454364,
    "Ce2O3": 28.57897991244726, "FeO": 12.5109734839867,
}
# Same composition but with Mg added (to exercise the M/A Mg equipartition,
# not present in the pure-ideal-formula case above).
ANALYSIS_WITH_MG = dict(IDEAL_ANALYSIS, MgO=1.0)


@pytest.fixture(scope="module")
def allanite_config():
    return load_mineral_config(ALLANITE_YAML_PATH)


def test_ideal_formula_reproduces_exact_cation_ratios(allanite_config):
    result = pipeline.calculate(
        IDEAL_ANALYSIS, allanite_config, input_mode="wt_percent", redox_method="fixed_ratio"
    )
    assert result.apfu["Si"] == pytest.approx(3.0, abs=1e-6)
    assert result.apfu["Al"] == pytest.approx(2.0, abs=1e-6)
    assert result.apfu["Ca"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["Ce"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated


def test_ree_all_land_in_a_site_unconditionally(allanite_config):
    result = pipeline.calculate(
        ANALYSIS_WITH_MG, allanite_config, input_mode="wt_percent", redox_method="fixed_ratio"
    )
    a = result.site_allocation.sites["A"]
    assert a.elements["Ce"] == pytest.approx(result.apfu["Ce"], rel=1e-6)


def test_default_fixed_ratio_assumes_all_fe_ferric(allanite_config):
    result = pipeline.calculate(
        ANALYSIS_WITH_MG, allanite_config, input_mode="wt_percent", redox_method="fixed_ratio"
    )
    assert result.redox.species_2plus_apfu == pytest.approx(0.0, abs=1e-9)
    assert result.redox.species_3plus_apfu > 0


def test_mg_equipartition_between_m_and_a(allanite_config):
    """Mg is shared between M and A (both list it); the M-site portion
    should exactly fill M's remaining space after Al+Fe3+, with the
    remainder landing in A.
    """
    result = pipeline.calculate(
        ANALYSIS_WITH_MG, allanite_config, input_mode="wt_percent", redox_method="fixed_ratio"
    )
    m = result.site_allocation.sites["M"]
    a = result.site_allocation.sites["A"]
    assert m.total == pytest.approx(3.0, abs=1e-6)  # M-space was the limiting factor here
    assert m.elements["Mg"] + a.elements["Mg"] == pytest.approx(result.apfu["Mg"], rel=1e-6)
    assert m.elements["Mg"] > 0 and a.elements["Mg"] > 0


def test_no_end_members(allanite_config):
    result = pipeline.calculate(
        IDEAL_ANALYSIS, allanite_config, input_mode="wt_percent", redox_method="fixed_ratio"
    )
    assert result.end_members == {}
