"""Filename-parsing tests for the Map Import dialog.

``MapImporter.parse_filenames`` guesses each export file's field type,
analyte(s), and units from its filename alone. It has accreted special
cases over time (element "total" channels, StdCorr duplicates,
reaction-cell product masses), several of which have quietly broken each
other -- these pin the ones that matter against real Iolite/XMapTools-style
export names.

Headless (QT_QPA_PLATFORM=offscreen), following the convention in
tests/test_calibration_gui.py.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.importers.MapImporter import MapImporter


class _StubProjectManager:
    def add_samples(self, paths):
        return []


class _StubHost(QWidget):
    """The only thing MapImporter uses its parent for."""

    def __init__(self):
        super().__init__()
        self.project_manager = _StubProjectManager()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def importer(qtbot, app):
    host = _StubHost()
    qtbot.addWidget(host)
    dialog = MapImporter(parent=host)
    qtbot.addWidget(dialog)
    dialog.comboBoxDataType.setCurrentText("LA-ICP-MS")
    return dialog


def parse_one(importer, sample_id, filename):
    """``(fieldtype, analyte1, analyte2, unit)`` for a single filename."""
    valid, _ext, _filetype, fieldtype, a1, a2, unit = importer.parse_filenames(
        sample_id, [filename]
    )[0]
    assert valid, f"{filename!r} was rejected outright"
    return fieldtype, a1, a2, unit


@pytest.mark.parametrize("filename, expected", [
    ("AH5C_1 Al27_CPS matrix.xlsx", ("Analyte", "Al27", None, "cps")),
    ("AH5C_1 Hf178_CPS matrix.xlsx", ("Analyte", "Hf178", None, "cps")),
    ("AH5C_1 Y89_CPS matrix.xlsx", ("Analyte", "Y89", None, "cps")),
])
def test_plain_isotope_channels(importer, filename, expected):
    assert parse_one(importer, "ah5c_1", filename) == expected


@pytest.mark.parametrize("filename, expected", [
    # Same element, two masses -- the mass is named once with its element
    # and once bare.
    ("AH5C_1 StdCorr_Hf176_177 matrix.xlsx", ("Ratio", "Hf176", "Hf177", None)),
    ("AH5C_1 StdCorr_Hf177_176 matrix.xlsx", ("Ratio", "Hf177", "Hf176", None)),
    # Two elements, two different masses.
    ("AH5C_1 StdCorr_Lu176_Hf177 matrix.xlsx", ("Ratio", "Lu176", "Hf177", None)),
    # Two elements sharing one mass number. Regression: the mass-value
    # search consumed "176" for Lu and then refused it for Hf, silently
    # degrading this to a bare Lu176 *analyte* and dropping the
    # denominator -- the column imported as "Lu176", not "Lu176 / Hf176".
    ("AH5C_1 StdCorr_Lu176_Hf176 matrix.xlsx", ("Ratio", "Lu176", "Hf176", None)),
])
def test_ratio_channels(importer, filename, expected):
    assert parse_one(importer, "ah5c_1", filename) == expected


def test_reaction_cell_product_mass_keeps_its_label(importer):
    """A reaction/collision-cell method reports the product m/z: Lu175
    measured as a reaction product at m/z 257 (written "Lu175 -> 257" in the
    raw instrument file) exports here as "Lu257". 257 is not an isotope of
    Lu, so the element/mass check rejected it and the column imported with
    an empty name."""
    assert parse_one(importer, "ah5c_1", "AH5C_1 Lu257_CPS matrix.xlsx") == (
        "Analyte", "Lu257", None, "cps",
    )


def test_total_beam_is_a_named_special_field(importer):
    """TotalBeam is the ion beam summed over every mass, not an isotope.
    Regression: the "total" qualifier strip (added for "PbTotal") also fired
    mid-word here, leaving "beam", which matched nothing -- so the column
    imported unnamed *and* typed as an analyte."""
    assert parse_one(importer, "ah5c_1", "AH5C_1 TotalBeam_CPS matrix.xlsx") == (
        "Special", "TotalBeam", None, "cps",
    )


@pytest.mark.parametrize("filename", [
    "SAMP PbTotal_CPS matrix.xlsx",
    "SAMP Pb_total_CPS matrix.xlsx",
    "SAMP Pb total_CPS matrix.xlsx",
])
def test_element_total_channels_still_strip_the_qualifier(importer, filename):
    """The case the "total" strip exists for: an element total with no
    isotope mass. Must keep working now that the strip is anchored."""
    fieldtype, a1, a2, _unit = parse_one(importer, "samp", filename)
    assert (fieldtype, a1, a2) == ("Analyte", "Pb", None)


def test_real_export_folder_leaves_no_unnamed_channel(importer):
    """Every file in a real quadrupole export must resolve to a usable
    column title -- an empty Analyte 1 becomes an empty CSV header."""
    files = [
        "AH5C_1 Al27_CPS matrix.xlsx", "AH5C_1 Ca43_CPS matrix.xlsx",
        "AH5C_1 Ce140_CPS matrix.xlsx", "AH5C_1 Cr53_CPS matrix.xlsx",
        "AH5C_1 Fe57_CPS matrix.xlsx", "AH5C_1 Hf176_CPS matrix.xlsx",
        "AH5C_1 Hf178_CPS matrix.xlsx", "AH5C_1 La139_CPS matrix.xlsx",
        "AH5C_1 Lu175_CPS matrix.xlsx", "AH5C_1 Lu257_CPS matrix.xlsx",
        "AH5C_1 Mn55_CPS matrix.xlsx", "AH5C_1 Nd146_CPS matrix.xlsx",
        "AH5C_1 Sm147_CPS matrix.xlsx", "AH5C_1 Sr88_CPS matrix.xlsx",
        "AH5C_1 StdCorr_Hf176_177 matrix.xlsx", "AH5C_1 StdCorr_Hf177_176 matrix.xlsx",
        "AH5C_1 StdCorr_Lu176_Hf176 matrix.xlsx", "AH5C_1 StdCorr_Lu176_Hf177 matrix.xlsx",
        "AH5C_1 Ti47_CPS matrix.xlsx", "AH5C_1 TotalBeam_CPS matrix.xlsx",
        "AH5C_1 Y89_CPS matrix.xlsx", "AH5C_1 Zr90_CPS matrix.xlsx",
    ]
    results = importer.parse_filenames("ah5c_1", files)
    assert len(results) == len(files)

    names = []
    for filename, (valid, _ext, _ft, fieldtype, a1, a2, _u) in zip(files, results):
        assert valid, filename
        assert a1, f"{filename} produced no column name"
        assert fieldtype in ("Analyte", "Ratio", "Special"), filename
        names.append(f"{a1} / {a2}" if a2 else a1)

    # The same names the importer writes as CSV headers -- all distinct, so
    # no column silently overwrites another on concat.
    assert len(set(names)) == len(names)
    assert "Lu176 / Hf176" in names
    assert "TotalBeam" in names
    assert "Lu257" in names


def test_raw_line_files_still_read_as_line_numbers(importer):
    """The product-mass fallback matches an element symbol followed by any
    number, which would also swallow a raw per-line filename and pre-empt
    line-number detection -- it is restricted to matrix files for that
    reason. These have no "matrix" in the name, so they must stay lines."""
    files = ["NIST610 - 8.csv", "NIST610 - 12.csv"]
    results = importer.parse_filenames("nist610", files)
    for filename, (valid, _ext, filetype, _ft, first, second, _u) in zip(files, results):
        assert valid, filename
        assert filetype == "line", filename
        assert second is None
    assert [r[4] for r in results] == ["8", "12"]
