"""Tests for AttributeDataFrame.set_attribute's columns/values dispatch.

Regression coverage for a bug where a single column's attribute couldn't be
set to a list-shaped value (e.g. category_labels/category_colors on a
discrete field) -- set_attribute treated any list-typed `values` as "one
value per column," which crashed comparing len(a_single_column_name_string)
against len(values) whenever `columns` was a scalar string.

Pure pandas -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data.ExtendedDF import AttributeDataFrame


@pytest.fixture
def df():
    return AttributeDataFrame(pd.DataFrame({"Temperature": [22, 23, 21], "Pressure": [101, 102, 100]}))


def test_single_column_scalar_value(df):
    df.set_attribute("Temperature", "units", "Celsius")
    assert df.get_attribute("Temperature", "units") == "Celsius"


def test_single_column_list_valued_attribute(df):
    """The exact regression case: one column, one attribute, whose value is
    itself a list (e.g. the category labels for a discrete field) -- must be
    stored as that single value, not distributed across columns.
    """
    labels = ["monazite", "huttonite"]
    df.set_attribute("Temperature", "category_labels", labels)
    assert df.get_attribute("Temperature", "category_labels") == labels


def test_multiple_columns_single_value_broadcasts(df):
    df.set_attribute(["Temperature", "Pressure"], "source", "Sensor")
    assert df.get_attribute("Temperature", "source") == "Sensor"
    assert df.get_attribute("Pressure", "source") == "Sensor"


def test_multiple_columns_list_of_values_distributes_one_to_one(df):
    df.set_attribute(["Temperature", "Pressure"], "units", ["Celsius", "Pascal"])
    assert df.get_attribute("Temperature", "units") == "Celsius"
    assert df.get_attribute("Pressure", "units") == "Pascal"


def test_multiple_columns_mismatched_list_length_raises(df):
    with pytest.raises(ValueError):
        df.set_attribute(["Temperature", "Pressure"], "units", ["Celsius"])
