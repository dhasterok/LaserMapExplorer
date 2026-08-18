"""Reference-material YAML schema, loader, validator, and writer tests.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest
import yaml

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.reflib import (
    ReferenceLibraryError,
    load_reference_library,
    load_reference_material,
    parse_reference_material,
    resolve_elemental_value,
    save_reference_material,
)

SEED_DIR = project_root / "resources" / "calibration" / "reference_materials"


def test_load_seed_nist610_yaml_has_real_georem_values():
    # Populated from resources/calibration/reference_materials/georem.xlsx via
    # scripts/build_reference_library_from_georem.py (Jochum et al. 2011
    # GeoReM preferred values) -- these are well-known published NIST610
    # concentrations, checked here against generous literature ranges so the
    # test isn't brittle to re-running the converter against an updated
    # georem.xlsx.
    material = load_reference_material(SEED_DIR / "NIST610.yaml")
    assert material.standard == "NIST610"
    assert "Al27" in material.analytes
    assert material.analytes["Al27"].element == "Al"
    assert 9000 < material.value("Al27") < 12000          # Al2O3 wt% converted to ppm
    assert material.uncertainty_1sd("Al27") is not None
    assert 400 < material.value("Mg24") < 460              # reported directly in µg/g (=ppm)
    assert 400 < material.value("Sr88") < 550
    assert material.analytes["Al27"].mass == 27


def test_load_reference_library_skips_underscore_prefixed_files():
    library = load_reference_library(SEED_DIR)
    assert "NIST610" in library
    # _template.yaml's placeholder 'standard: STANDARD_NAME' must never load.
    assert "STANDARD_NAME" not in library


def test_null_value_is_a_legitimate_placeholder_state():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": None}},
    }
    material = parse_reference_material(raw)
    assert material.value("Al27") is None
    assert material.uncertainty_1sd("Al27") is None


def test_populated_value_requires_valid_uncertainty_type():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 10.0}},
    }
    with pytest.raises(ReferenceLibraryError):
        parse_reference_material(raw)


def test_populated_value_with_unknown_uncertainty_type_raises():
    raw = {
        "standard": "TESTSTD",
        "analytes": {
            "Al27": {
                "element": "Al", "mass": 27, "value": 500.0, "uncertainty": 10.0,
                "uncertainty_type": "not_a_real_type",
            }
        },
    }
    with pytest.raises(ReferenceLibraryError):
        parse_reference_material(raw)


def test_uncertainty_1sd_conversion():
    raw = {
        "standard": "TESTSTD",
        "analytes": {
            "Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 10.0, "uncertainty_type": "2SD"},
            "Ca43": {"element": "Ca", "mass": 43, "value": 300.0, "uncertainty": 9.8, "uncertainty_type": "95CI"},
        },
    }
    material = parse_reference_material(raw)
    assert material.uncertainty_1sd("Al27") == pytest.approx(5.0)
    assert material.uncertainty_1sd("Ca43") == pytest.approx(9.8 / 1.959963984540054)


def test_missing_analytes_key_raises():
    with pytest.raises(ReferenceLibraryError):
        parse_reference_material({"standard": "TESTSTD"})


def test_resolve_elemental_value_direct_key_matches_value_exactly():
    # Regression pin: a directly-keyed isotope (e.g. U238) must resolve to
    # the exact same entry/value as before resolve_elemental_value existed.
    raw = {
        "standard": "TESTSTD",
        "analytes": {"U238": {"element": "U", "mass": 238, "value": 461.5, "uncertainty": 1.0, "uncertainty_type": "95CI"}},
    }
    material = parse_reference_material(raw)
    entry = resolve_elemental_value(material, "U238")
    assert entry is not None
    assert entry.value == pytest.approx(461.5)
    assert entry is material.analytes["U238"]


def test_resolve_elemental_value_falls_back_to_sibling_isotope():
    # GeoREM only reports one row per element -- U235 has no key of its
    # own, but should resolve to U238's (elemental total) entry unscaled.
    raw = {
        "standard": "TESTSTD",
        "analytes": {"U238": {"element": "U", "mass": 238, "value": 461.5, "uncertainty": 1.0, "uncertainty_type": "95CI"}},
    }
    material = parse_reference_material(raw)
    entry = resolve_elemental_value(material, "U235")
    assert entry is not None
    assert entry.value == pytest.approx(461.5)  # unscaled -- no abundance math
    assert entry is material.analytes["U238"]


def test_resolve_elemental_value_no_element_match_returns_none():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    }
    material = parse_reference_material(raw)
    assert resolve_elemental_value(material, "U235") is None


def test_isotope_ratios_defaults_to_empty_for_concentration_only_material():
    # Every existing concentration-only YAML file has no 'isotope_ratios'
    # key -- must keep loading unchanged.
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    }
    material = parse_reference_material(raw)
    assert material.isotope_ratios == {}


def test_isotope_ratio_round_trips_through_parse_and_save(tmp_path):
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/Pb204": {
                "numerator_element": "Pb", "numerator_mass": 206,
                "denominator_element": "Pb", "denominator_mass": 204,
                "value": 17.047, "uncertainty": 0.0018, "uncertainty_type": "2SD",
                "source": "Woodhead & Hergt, 2007",
            },
        },
    }
    material = parse_reference_material(raw)
    entry = material.isotope_ratios["Pb206/Pb204"]
    assert entry.numerator == "Pb206"
    assert entry.denominator == "Pb204"
    assert entry.value == pytest.approx(17.047)
    assert entry.uncertainty_1sd() == pytest.approx(0.0009)

    path = tmp_path / "roundtrip.yaml"
    save_reference_material(material, path)
    reloaded = load_reference_material(path)
    assert reloaded.isotope_ratios["Pb206/Pb204"].value == pytest.approx(17.047)


def test_isotope_ratio_missing_uncertainty_type_is_none_and_warns():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/Pb204": {
                "numerator_element": "Pb", "numerator_mass": 206,
                "denominator_element": "Pb", "denominator_mass": 204,
                "value": 17.094, "uncertainty": 0.0026,   # no uncertainty_type -- matches real NIST612 GeoREM data
            },
        },
    }
    with pytest.warns(UserWarning, match="no uncertainty_type"):
        material = parse_reference_material(raw)
    entry = material.isotope_ratios["Pb206/Pb204"]
    assert entry.uncertainty_type is None
    assert entry.uncertainty_1sd() is None  # can't interpret an uncertainty with no known type


def test_ratio_accessor_tries_flipped_key_when_exact_key_absent():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb208/Pb206": {
                "numerator_element": "Pb", "numerator_mass": 208,
                "denominator_element": "Pb", "denominator_mass": 206,
                "value": 2.064, "uncertainty": 0.001, "uncertainty_type": "1SD", "source": "BCR-2",
            },
        },
    }
    material = parse_reference_material(raw)
    # exact key present
    direct = material.ratio("Pb208", "Pb206")
    assert direct is not None and direct.value == pytest.approx(2.064)
    # flipped key: only "Pb208/Pb206" exists, not "Pb206/Pb208"
    flipped = material.ratio("Pb206", "Pb208")
    assert flipped is not None
    assert flipped.value == pytest.approx(1.0 / 2.064)
    assert flipped.numerator == "Pb206"
    assert flipped.denominator == "Pb208"


def test_ratio_accessor_returns_none_when_neither_direction_exists():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    }
    material = parse_reference_material(raw)
    assert material.ratio("Pb206", "Pb204") is None


def test_resolve_elemental_value_unparseable_analyte_name_returns_none():
    raw = {
        "standard": "TESTSTD",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    }
    material = parse_reference_material(raw)
    assert resolve_elemental_value(material, "not_an_analyte") is None


def test_save_reference_material_round_trips(tmp_path):
    raw = {
        "standard": "TESTSTD",
        "description": "A test standard",
        "source": "unit test",
        "analytes": {
            "Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"},
        },
    }
    material = parse_reference_material(raw)
    out_path = tmp_path / "TESTSTD.yaml"
    save_reference_material(material, out_path)

    reloaded = load_reference_material(out_path)
    assert reloaded.standard == "TESTSTD"
    assert reloaded.value("Al27") == pytest.approx(500.0)
    assert reloaded.analytes["Al27"].uncertainty_type == "1SD"


def test_load_reference_material_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    with pytest.raises(ReferenceLibraryError):
        load_reference_material(path)
