"""Characterization tests for titanohematite (the FeTiO3-Fe2O3 ilmenite-
hematite solid-solution series) -- no workbook reference sheet exists for
this mineral (Stage 3 batch); these check self-consistency and the reused
``droop_1987`` Fe3+ formula on hand-picked synthetic analyses rather than
cross-checking against an authoritative external value. See
``resources/minerals/titanohematite.yaml`` and the Stage 3 plan.

There is no standalone hematite config -- a near-pure Fe2O3 analysis is
covered here (test_hematite_rich_composition_dominant_end_member) since
hematite is an end-member of this series, not a separate mineral.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

TITANOHEMATITE_YAML_PATH = project_root / "resources" / "minerals" / "titanohematite.yaml"


@pytest.fixture(scope="module")
def titanohematite_config():
    return load_mineral_config(TITANOHEMATITE_YAML_PATH)


def test_stoichiometric_ilmenite_has_no_fe3(titanohematite_config):
    """A textbook-stoichiometric FeTiO3 analysis (S == T exactly) should give
    zero Fe3+ under droop_1987 -- no charge-balance evidence for any.
    """
    analysis = {"TiO2": 52.65, "FeO": 47.35}  # 1:1 Ti:Fe, no other cations
    result = pipeline.calculate(analysis, titanohematite_config, input_mode="wt_percent", redox_method="droop_1987")
    assert result.redox.species_3plus_apfu == pytest.approx(0.0, abs=1e-3)
    assert result.site_allocation.sites["M"].total == pytest.approx(2.0, abs=1e-6)
    assert not result.site_allocation.unallocated


def test_fe_rich_ilmenite_recovers_some_fe3(titanohematite_config):
    """Excess Fe relative to Ti (S > T under the all-Fe2+ assumption) should
    show up as a nonzero Fe3+ split, same mechanism as garnet's droop_1987.
    """
    analysis = {"TiO2": 47.0, "FeO": 45.0, "MnO": 5.0, "MgO": 1.0}
    result = pipeline.calculate(analysis, titanohematite_config, input_mode="wt_percent", redox_method="droop_1987")
    assert result.redox.S > result.redox.T
    assert result.redox.species_3plus_apfu > 0
    assert not result.site_allocation.unallocated

    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    assert em["ilmenite"] > em["hematite"] > em["pyrophanite"] > em["geikielite"] > 0  # Fe2+-dominant


def test_hematite_rich_composition_dominant_end_member(titanohematite_config):
    """A near-pure Fe2O3 analysis (formerly its own hematite.yaml config,
    now folded into this series -- see this module's docstring) should
    still allocate cleanly and come out hematite-dominant, with all_3plus
    (the sensible default for a corundum-structure sesquioxide, same
    reasoning the old standalone config used) recovering essentially all Fe
    as Fe3+.
    """
    analysis = {"Fe2O3": 98.0, "Al2O3": 1.0, "TiO2": 0.5}
    result = pipeline.calculate(analysis, titanohematite_config, input_mode="wt_percent", redox_method="all_3plus")
    assert not result.site_allocation.unallocated
    assert result.redox.species_2plus_apfu == pytest.approx(0.0, abs=1e-9)

    em = result.end_members
    assert sum(em.values()) == pytest.approx(100.0, abs=1e-6)
    assert em["hematite"] == max(em.values())
