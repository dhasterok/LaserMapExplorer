"""Characterization test for a magnetite-dominant composition, run through
the shared ``resources/minerals/spinel-magnetite.yaml`` config (see that
file's comment -- magnetite is the Fe3+-dominant member of the same
spinel_xmg solid solution, not a separate calculation); no workbook
reference sheet exists for this specific composition (the workbook
reference test uses an Al-rich spinel instead -- see
``test_stoichiometry_spinel_magnetite_workbook_reference.py``). A
self-consistency check on a hand-picked near-pure Fe3O4 analysis rather
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

SPINEL_MAGNETITE_YAML_PATH = project_root / "resources" / "minerals" / "spinel-magnetite.yaml"

ANALYSIS = {"FeO": 31.0, "Fe2O3": 67.0, "TiO2": 0.5, "Al2O3": 0.5}


@pytest.fixture(scope="module")
def magnetite_config():
    return load_mineral_config(SPINEL_MAGNETITE_YAML_PATH)


@pytest.fixture(scope="module")
def result(magnetite_config):
    return pipeline.calculate(ANALYSIS, magnetite_config, input_mode="wt_percent")


def test_sites_close_to_target(result):
    assert not result.site_allocation.unallocated
    sites = result.site_allocation.sites
    assert sites["D"].total == pytest.approx(2.0, abs=0.05)
    assert sites["A"].total == pytest.approx(1.0, abs=0.05)


def test_end_members_sum_to_100_and_magnetite_dominant(result, magnetite_config):
    """Only the tiered `members` (not the separate `ratios`, mixed into the
    same dict -- see config.py's EndMemberConfig.ratios docstring) sum to
    100."""
    em = result.end_members
    members_sum = sum(em[m] for m in magnetite_config.end_members.members)
    assert members_sum == pytest.approx(100.0, abs=1e-6)
    assert em["magnetite"] > 90.0
