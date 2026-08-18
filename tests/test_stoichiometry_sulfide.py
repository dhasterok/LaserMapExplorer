"""Characterization tests for the generic sulfide config -- no workbook
reference sheet exists for this mineral family (Stage 3), and unlike every
other mineral in this library, MinPlotX's own sulfide calculator is a fully
generic, runtime-configurable tool (any cation-normalization target), not a
fixed formula -- see ``resources/minerals/sulfide.yaml``'s docstring.

Tests recover known ideal formulas (pyrite FeS2, chalcopyrite CuFeS2,
sphalerite ZnS, pentlandite (Fe,Ni)9S8) from their textbook element wt%
compositions, at the matching ``ideal_cations_override`` target -- this
doubles as end-to-end verification of two new engine pieces added
specifically for sulfides: the ``element_wt_percent`` input mode
(``normalize.to_cation_moles``) and ``normalization.excludes``
(``normalize.normalize_to_cations`` excluding S from the target sum while
still reporting/scaling it).

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry import pipeline
from src.stoichiometry.config import load_mineral_config

SULFIDE_YAML_PATH = project_root / "resources" / "minerals" / "sulfide.yaml"


@pytest.fixture(scope="module")
def sulfide_config():
    return load_mineral_config(SULFIDE_YAML_PATH)


def test_pyrite_feS2(sulfide_config):
    analysis = {"Fe": 46.55, "S": 53.45}
    result = pipeline.calculate(
        analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=1.0
    )
    assert result.redox is None  # sulfide has no redox: block
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(2.0, abs=1e-3)


def test_chalcopyrite_cuFeS2(sulfide_config):
    analysis = {"Cu": 34.63, "Fe": 30.43, "S": 34.94}
    result = pipeline.calculate(
        analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=2.0
    )
    assert result.apfu["Cu"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["Fe"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(2.0, abs=1e-3)


def test_sphalerite_znS(sulfide_config):
    analysis = {"Zn": 67.1, "S": 32.9}
    result = pipeline.calculate(
        analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=1.0
    )
    assert result.apfu["Zn"] == pytest.approx(1.0, abs=1e-3)
    assert result.apfu["S"] == pytest.approx(1.0, abs=1e-3)


def test_pentlandite_fe_ni_9_s8(sulfide_config):
    """(Fe,Ni)9S8 -- a roughly 1:1 Fe:Ni pentlandite, target=9 metal cations."""
    analysis = {"Fe": 32.0, "Ni": 34.2, "S": 33.8}
    result = pipeline.calculate(
        analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=9.0
    )
    assert result.apfu["Fe"] + result.apfu["Ni"] == pytest.approx(9.0, abs=1e-2)
    assert result.apfu["S"] == pytest.approx(8.0, rel=0.05)


def test_s_excluded_from_target_sum_but_still_reported(sulfide_config):
    """S scales with the metals (same normalization factor) but doesn't
    count toward the ideal_cations target -- the M site's total should
    therefore exceed its nominal target by roughly the S apfu.
    """
    analysis = {"Fe": 46.55, "S": 53.45}
    result = pipeline.calculate(
        analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=1.0
    )
    m = result.site_allocation.sites["M"]
    assert "S" in m.elements
    assert m.total == pytest.approx(1.0 + result.apfu["S"], rel=1e-6)


def test_ideal_cations_override_changes_the_target(sulfide_config):
    """The same composition normalized to two different targets should
    scale proportionally -- confirms the override actually takes effect.
    """
    analysis = {"Fe": 46.55, "S": 53.45}
    r1 = pipeline.calculate(analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=1.0)
    r2 = pipeline.calculate(analysis, sulfide_config, input_mode="element_wt_percent", ideal_cations_override=2.0)
    assert r2.apfu["Fe"] == pytest.approx(2.0 * r1.apfu["Fe"], rel=1e-6)
    assert r2.apfu["S"] == pytest.approx(2.0 * r1.apfu["S"], rel=1e-6)
