"""Unit tests for src/classification/reference.py.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.classification.reference import (
    ReferenceLibraryError, load_reference_library,
)


def test_loads_real_library():
    refs = load_reference_library()
    names = {r.mineral_name for r in refs}
    assert len(refs) >= 100
    assert "Anorthite" in names
    assert "Quartz" in names
    assert "Kaolinite" in names


def test_ahrensite_not_found_row_is_skipped():
    refs = load_reference_library()
    assert "Ahrensite" not in {r.mineral_name for r in refs}


def test_smectite_group_row_is_skipped_but_its_members_are_present():
    """'Smectite' itself has no webmineral.com page (it's a group name, a
    redirect-only page with no composition data) -- excluded like Ahrensite.
    Its actual member species (Montmorillonite, Nontronite) are present."""
    names = {r.mineral_name for r in load_reference_library()}
    assert "Smectite" not in names
    assert "Montmorillonite" in names
    assert "Nontronite" in names


def test_clay_minerals_share_expected_groups():
    refs = {r.mineral_name: r for r in load_reference_library()}
    assert refs["Montmorillonite"].group_yaml == refs["Nontronite"].group_yaml == "smectite"
    assert refs["Kaolinite"].group_yaml == "kaolinite"
    assert refs["Illite"].group_yaml == "illite"
    assert refs["Vermiculite"].group_yaml == "vermiculite"


def test_quartz_composition_matches_known_values():
    refs = load_reference_library()
    quartz = next(r for r in refs if r.mineral_name == "Quartz")
    assert quartz.composition["Si"] == pytest.approx(46.74, abs=0.1)
    assert quartz.composition["O"] == pytest.approx(53.26, abs=0.1)
    assert quartz.group_yaml == "quartz"


def test_anorthite_composition_matches_known_values():
    refs = load_reference_library()
    anorthite = next(r for r in refs if r.mineral_name == "Anorthite")
    # From the earlier direct WebFetch check of webmineral.com/data/Anorthite.shtml:
    # Na 0.41% Ca 13.72% Al 18.97% Si 20.75% O 46.14%.
    assert anorthite.composition["Si"] == pytest.approx(20.75, abs=0.1)
    assert anorthite.composition["Ca"] == pytest.approx(13.72, abs=0.1)
    assert anorthite.composition["Al"] == pytest.approx(18.97, abs=0.1)
    assert anorthite.composition["O"] == pytest.approx(46.14, abs=0.1)
    assert anorthite.group_yaml == "feldspar"


def test_every_reference_has_nonempty_composition():
    refs = load_reference_library()
    assert all(r.composition for r in refs)


def test_no_duplicate_mineral_names():
    """Regression test: Enstatite/Ferrosilite/Wollastonite and Hematite were
    each duplicated 2-3x under different group_yaml tags in an earlier
    version of the CSV (a mistaken attempt at a stoichiometry-config lookup
    that was never actually used -- stoichiometry reads
    resources/minerals/*.yaml directly, never this CSV). Each mineral name
    should appear exactly once."""
    names = [r.mineral_name for r in load_reference_library()]
    assert len(names) == len(set(names)), f"duplicates: {sorted(n for n in set(names) if names.count(n) > 1)}"


def test_every_reference_has_a_mineral_class():
    refs = load_reference_library()
    assert all(r.mineral_class for r in refs)


def test_mineral_class_matches_known_values():
    refs = {r.mineral_name: r for r in load_reference_library()}
    assert refs["Anorthite"].mineral_class == "Feldspar"
    assert refs["Quartz"].mineral_class == "Quartz/Silica"
    assert refs["Kaolinite"].mineral_class == "Clay"
    assert refs["Montmorillonite"].mineral_class == "Clay"
    assert refs["Calcite"].mineral_class == "Carbonate"
    assert refs["Pyrite"].mineral_class == "Sulfide"


def test_missing_file_raises():
    with pytest.raises(ReferenceLibraryError):
        load_reference_library("resources/minerals/does_not_exist.csv")
