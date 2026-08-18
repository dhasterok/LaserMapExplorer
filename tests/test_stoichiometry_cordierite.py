"""Characterization tests for cordierite -- no workbook reference sheet
exists for this mineral (Stage 3 batch, unlike Stages 1-2's garnet/olivine/
plagioclase/pyroxene/spinel), so these are self-consistency checks on a
hand-picked synthetic analysis rather than cross-checks against an
authoritative external value. See ``resources/minerals/cordierite.yaml``
and the Stage 3 plan for the porting rationale (oxygen-basis reporting,
fixed_ratio Fe redox, no OH/volatile tracking).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

CORDIERITE_YAML_PATH = project_root / "resources" / "minerals" / "cordierite.yaml"

ANALYSIS = {"SiO2": 49.0, "Al2O3": 33.0, "FeO": 5.0, "MgO": 10.0, "CaO": 0.1}


@pytest.fixture(scope="module")
def cordierite_config():
    return load_mineral_config(CORDIERITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(cordierite_config):
    return pipeline.calculate(ANALYSIS, cordierite_config, input_mode="wt_percent", redox_method="fixed_ratio")


def test_t1_site_capped_at_target_al_spills_to_t2(result):
    sites = result.site_allocation.sites
    assert not result.site_allocation.unallocated
    assert sites["T1"].total == pytest.approx(6.0, abs=1e-6)
    assert sites["T1"].elements["Si"] == pytest.approx(result.apfu["Si"], rel=1e-6)
    # T2 is Al's last site -- uncapped, absorbs whatever Al didn't fit in T1.
    assert sites["T2"].elements["Al"] == pytest.approx(result.apfu["Al"] - sites["T1"].elements.get("Al", 0.0), rel=1e-6)


def test_fixed_ratio_default_assumes_all_fe_ferric(result):
    """cordierite.yaml's default fixed_ratio=1.0 (MinPlotX's own default) --
    with no Fe2O3 in the input, all measured Fe should end up as Fe3+.
    """
    assert result.redox.species_2plus_apfu == pytest.approx(0.0, abs=1e-9)
    assert result.redox.species_3plus_apfu > 0
    assert result.apfu["Fe2"] == pytest.approx(0.0, abs=1e-9)


def test_end_member_xmg_reflects_fe_free_b_site(result):
    # With Fe2+ = 0, the B site is pure Mg -- mg_number must be exactly 100.
    assert result.end_members["mg_number"] == pytest.approx(100.0, abs=1e-6)
