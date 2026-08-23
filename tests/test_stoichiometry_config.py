"""Config loading/validation tests for src/stoichiometry/config.py.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest
import yaml

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.stoichiometry.config import (
    MineralConfigError,
    load_mineral_config,
    parse_mineral_config,
)

GARNET_YAML_PATH = project_root / "resources" / "minerals" / "garnet.yaml"


def base_garnet_dict():
    """A valid, minimal garnet-shaped config dict, for mutating in tests."""
    return {
        "mineral": "garnet",
        "abbreviation": "Grt",
        "formula": "X3Y2Z3O12",
        "normalization": {"basis": "oxygen", "ideal_oxygens": 12, "ideal_cations": 8},
        "sites": {
            "Z": {"target": 3.0, "elements": ["Si", "Al", "Fe3"], "priority": ["Si", "Al", "Fe3"]},
            "Y": {"target": 2.0, "elements": ["Al", "Fe3"], "priority": ["Al", "Fe3"]},
            "X": {"target": 3.0, "elements": ["Ca", "Mg", "Fe2"], "priority": ["Ca", "Mg", "Fe2"]},
        },
        "redox": {"elements": ["Fe"], "methods": ["all_2plus", "all_3plus", "droop_1987"], "default_method": "droop_1987"},
        "trace_elements": {"structural": [], "excluded": ["Zr"]},
        "end_members": {"method": "locock_2008", "members": ["pyrope", "almandine"]},
        "qc_checks": ["hydrogarnet_substitution"],
    }


def test_real_garnet_yaml_loads_and_validates():
    config = load_mineral_config(GARNET_YAML_PATH)
    assert config.mineral == "garnet"
    assert config.site_order == ["Z", "Y", "X"]
    assert config.ideal_oxygens == 12
    assert config.ideal_cations == 8
    assert config.redox.default_method == "droop_1987"
    assert config.end_members.method == "locock_2008"
    assert "hydrogarnet_substitution" in config.qc_checks


def test_missing_sites_raises():
    d = base_garnet_dict()
    del d["sites"]
    with pytest.raises(MineralConfigError, match="sites"):
        parse_mineral_config(d)


def test_empty_sites_raises():
    d = base_garnet_dict()
    d["sites"] = {}
    with pytest.raises(MineralConfigError, match="sites"):
        parse_mineral_config(d)


def test_priority_elements_mismatch_raises():
    """An element in 'priority' that isn't in 'elements' (or vice versa) --
    i.e. an element inconsistently assigned within a site -- must raise.
    """
    d = base_garnet_dict()
    d["sites"]["Z"]["priority"] = ["Si", "Al", "Cr"]  # 'Cr' not in Z's 'elements'
    with pytest.raises(MineralConfigError, match="priority"):
        parse_mineral_config(d)


def test_redox_element_with_no_matching_site_species_raises():
    """A redox-sensitive element must have a matching '<el>2'/'<el>3' (or
    itself) somewhere in the site definitions, or it would be estimated but
    never allocated to any site.
    """
    d = base_garnet_dict()
    d["redox"]["elements"] = ["Mn"]  # 'Mn2'/'Mn3'/'Mn' not in any site's elements
    with pytest.raises(MineralConfigError, match="Mn"):
        parse_mineral_config(d)


def test_unknown_redox_method_raises():
    d = base_garnet_dict()
    d["redox"]["methods"] = ["all_2plus", "made_up_method"]
    with pytest.raises(MineralConfigError, match="made_up_method"):
        parse_mineral_config(d)


def test_default_method_not_in_methods_raises():
    d = base_garnet_dict()
    d["redox"]["default_method"] = "all_3plus"
    d["redox"]["methods"] = ["all_2plus", "droop_1987"]  # all_3plus not enabled
    with pytest.raises(MineralConfigError, match="default_method"):
        parse_mineral_config(d)


def test_unknown_end_member_method_raises():
    d = base_garnet_dict()
    d["end_members"]["method"] = "made_up_2099"
    with pytest.raises(MineralConfigError, match="made_up_2099"):
        parse_mineral_config(d)


def test_malformed_yaml_raises_clear_error(tmp_path):
    bad_file = tmp_path / "broken.yaml"
    bad_file.write_text("mineral: garnet\nsites: [this is not: valid: yaml structure\n")
    with pytest.raises(MineralConfigError):
        load_mineral_config(bad_file)


def test_empty_yaml_file_raises(tmp_path):
    empty_file = tmp_path / "empty.yaml"
    empty_file.write_text("")
    with pytest.raises(MineralConfigError, match="empty"):
        load_mineral_config(empty_file)


def test_non_mapping_root_raises():
    with pytest.raises(MineralConfigError, match="mapping"):
        parse_mineral_config(["not", "a", "mapping"])


def test_missing_abbreviation_raises():
    d = base_garnet_dict()
    del d["abbreviation"]
    with pytest.raises(MineralConfigError, match="abbreviation"):
        parse_mineral_config(d)


def test_malformed_abbreviation_raises():
    """Must be a plain letters/digits string starting with a letter -- it
    becomes an output column-name prefix (e.g. 'Grt_apfu_X'), so spaces/
    punctuation would break column naming.
    """
    d = base_garnet_dict()
    d["abbreviation"] = "Grt 1"
    with pytest.raises(MineralConfigError, match="abbreviation"):
        parse_mineral_config(d)


def test_anion_basis_parses(tmp_path):
    """basis: 'anion' (sulfide's anion-anchored normalization -- see
    normalize.normalize_to_measured_anion) is a valid basis, alongside
    'oxygen'/'cation'.
    """
    d = base_garnet_dict()
    d["normalization"]["basis"] = "anion"
    d["normalization"]["excludes"] = ["S"]
    config = parse_mineral_config(d)
    assert config.basis == "anion"


def test_unknown_basis_raises():
    d = base_garnet_dict()
    d["normalization"]["basis"] = "made_up_basis"
    with pytest.raises(MineralConfigError, match="basis"):
        parse_mineral_config(d)
