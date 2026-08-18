"""Characterization tests for mica -- no workbook reference sheet exists for
this mineral (Stage 3, OH-bearing batch). Uses *exact* ideal-formula
compositions (muscovite and phlogopite, oxide wt% computed directly from
molar weights) to validate both the site allocation (reused
``tetra_fe3_ratio`` method, extended to support mica's third, independent
interlayer site -- see ``sites.py``'s docstring) and the cascading
di/trioctahedral end-member classification (``endmembers.py``'s
``_mica_cascade``).

An earlier version of ``ideal_oxygens`` (10, "framework O minus OH") badly
under-filled the M site for both end-members (M totaled ~1.48 for ideal
muscovite instead of 2, misclassifying it as ~57% al-celadonite); this is
the same class of mistake found in apatite/staurolite in this batch -- see
``resources/minerals/mica.yaml``'s comment for the correct derivation
(matching this engine's own O-per-cation accounting for the ideal formula,
not the crystallographic anhydrous O count).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

MICA_YAML_PATH = project_root / "resources" / "minerals" / "mica.yaml"

# Exact ideal muscovite KAl2(Si3Al)O10(OH)2 (3 SiO2 + 1.5 Al2O3 + 0.5 K2O).
MUSCOVITE_ANALYSIS = {"SiO2": 47.398449960410744, "Al2O3": 40.216882740281314, "K2O": 12.384667299307946}
# Exact ideal phlogopite KMg3(Si3Al)O10(OH)2 (3 SiO2 + 0.5 Al2O3 + 3 MgO + 0.5 K2O).
PHLOGOPITE_ANALYSIS = {
    "SiO2": 45.14847224589073, "Al2O3": 12.769269991827514, "MgO": 30.285483641937716, "K2O": 11.796774120344038,
}


@pytest.fixture(scope="module")
def mica_config():
    return load_mineral_config(MICA_YAML_PATH)


def test_ideal_muscovite_reproduces_exact_apfu_and_is_pure_muscovite(mica_config):
    result = pipeline.calculate(MUSCOVITE_ANALYSIS, mica_config, input_mode="wt_percent", redox_method="fixed_ratio")
    assert result.apfu["Si"] == pytest.approx(3.0, abs=1e-6)
    assert result.apfu["Al"] == pytest.approx(3.0, abs=1e-6)
    assert result.apfu["K"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated

    sites = result.site_allocation.sites
    assert sites["T"].total == pytest.approx(4.0, abs=1e-6)
    assert sites["M"].total == pytest.approx(2.0, abs=1e-6)  # fully dioctahedral
    assert sites["I"].total == pytest.approx(1.0, abs=1e-6)

    em = result.end_members
    assert em["muscovite"] == pytest.approx(100.0, abs=1e-3)
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)


def test_ideal_phlogopite_reproduces_exact_apfu_and_is_pure_phlogopite(mica_config):
    result = pipeline.calculate(PHLOGOPITE_ANALYSIS, mica_config, input_mode="wt_percent", redox_method="fixed_ratio")
    assert result.apfu["Si"] == pytest.approx(3.0, abs=1e-6)
    assert result.apfu["Al"] == pytest.approx(1.0, abs=1e-6)
    assert result.apfu["Mg"] == pytest.approx(3.0, abs=1e-6)
    assert result.apfu["K"] == pytest.approx(1.0, abs=1e-6)
    assert not result.site_allocation.unallocated

    sites = result.site_allocation.sites
    assert sites["M"].total == pytest.approx(3.0, abs=1e-6)  # fully trioctahedral

    em = result.end_members
    assert em["phlogopite"] == pytest.approx(100.0, abs=1e-3)
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)


def test_fe_bearing_dioctahedral_mica_shows_celadonite_component(mica_config):
    """A muscovite-like composition with some Fe2+/Fe3+ substituting for Al
    in M should show up as celadonite/al-celadonite, not purely muscovite.
    """
    analysis = dict(MUSCOVITE_ANALYSIS)
    analysis["Al2O3"] -= 3.0
    analysis["FeO"] = 3.0
    config_with_fe3 = mica_config
    result = pipeline.calculate(analysis, config_with_fe3, input_mode="wt_percent", redox_method="fixed_ratio")
    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    assert em["muscovite"] < 100.0
    assert em["al_celadonite"] > 0 or em["celadonite"] > 0


def test_interlayer_site_independent_of_t_and_m(mica_config):
    """The interlayer (I) site is a trailing, fully-independent site (per
    _allocate_tetra_fe3_ratio's generalization) -- confirm it holds exactly
    the K apfu and doesn't interact with T/M's Al/Fe3+ spillover.
    """
    result = pipeline.calculate(MUSCOVITE_ANALYSIS, mica_config, input_mode="wt_percent", redox_method="fixed_ratio")
    i_site = result.site_allocation.sites["I"]
    assert i_site.elements == {"K": pytest.approx(result.apfu["K"], rel=1e-6)}
