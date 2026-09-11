"""Tests for AttributeDataFrame.sort_columns' reordering.

Regression coverage for a crash where sorting mixed-dtype columns raised
``TypeError: Invalid value '<series>' for dtype 'int64'``. sort_columns used
to write *values* into the existing column slots positionally
(``self[:] = self.reindex(columns=new_order)``, then rename ``self.columns``),
so a column landing on a slot of a different dtype hit pandas'
LossySetitemError.

That is a real data shape, not a contrived one: a CPS channel whose float32
values sit around 1e9 is written to .lame.csv with no decimal point and
reads back as int64, while every other analyte is float64. Sorting analytes
alphabetically then moved a float column onto the int column's slot and
aborted -- taking down whatever UI action had called ``get_field_list``.

Pure pandas -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data.ExtendedDF import AttributeDataFrame


def _df():
    """Columns deliberately out of alphabetical order, with the int64 one
    first so sorting must move a float column onto its slot."""
    frame = AttributeDataFrame(pd.DataFrame({
        "Xc": [0.0, 1.0, 2.0],
        "Zr90": pd.Series([1209970176, 1194316288, 1500000000], dtype="int64"),
        "Al27": [1.5, 2.5, 3.5],
        "Ce140": [10.25, 11.25, 12.25],
    }))
    for col, dtype in (("Xc", "coordinate"), ("Zr90", "Analyte"),
                        ("Al27", "Analyte"), ("Ce140", "Analyte")):
        frame.set_attribute(col, "data_type", dtype)
    return frame


def test_sort_columns_across_mixed_dtypes():
    df = _df()
    original = df.copy()

    df.sort_columns(["Al27", "Ce140", "Zr90"])

    # Non-sorted columns hold their slots; the sorted names fill the rest.
    assert list(df.columns) == ["Xc", "Al27", "Ce140", "Zr90"]
    # Every column keeps its own values and its own dtype -- no coercion.
    for col in original.columns:
        pd.testing.assert_series_equal(df[col], original[col], check_names=False)
    assert df["Zr90"].dtype == "int64"


def test_sort_columns_preserves_attributes():
    df = _df()
    df.sort_columns(["Al27", "Ce140", "Zr90"])
    assert [df.get_attribute(c, "data_type") for c in df.columns] == [
        "coordinate", "Analyte", "Analyte", "Analyte",
    ]
    # column_attributes is rebuilt in the new order, and loses nothing.
    assert list(df.column_attributes) == ["Xc", "Al27", "Ce140", "Zr90"]


def test_sort_columns_is_in_place_and_returns_self():
    df = _df()
    returned = df.sort_columns(["Al27", "Ce140", "Zr90"])
    assert returned is df
    assert list(df.columns) == ["Xc", "Al27", "Ce140", "Zr90"]


def test_sort_columns_all_float_still_reorders():
    """The path that already worked before -- pinned so the dtype fix didn't
    change ordinary reordering."""
    df = AttributeDataFrame(pd.DataFrame({
        "Xc": [0.0], "Zr90": [3.0], "Al27": [1.0], "Ce140": [2.0],
    }))
    df.sort_columns(["Al27", "Ce140", "Zr90"])
    assert list(df.columns) == ["Xc", "Al27", "Ce140", "Zr90"]
    assert df["Al27"].iloc[0] == 1.0 and df["Zr90"].iloc[0] == 3.0


def test_sort_columns_noop_when_already_ordered():
    df = _df()
    df.sort_columns(["Zr90", "Al27", "Ce140"])  # already the current order
    assert list(df.columns) == ["Xc", "Zr90", "Al27", "Ce140"]
    assert df["Zr90"].dtype == "int64"
