# tests/test_fieldlogic.py
import sys
from pathlib import Path

# Get the project root (assuming tests/ is in the root)
project_root = Path(__file__).resolve().parent.parent

# Add src/ to sys.path
sys.path.insert(0, str(project_root / 'src'))

import pytest
from app.PlotAxisSettings import axis_settings_dict
from collections import defaultdict

# sample attributes dictionary
attributes_dict = {
    "Xc": {"data_type": "coordinate"},
    "Yc": {"data_type": "coordinate"},
    "Li7": {"data_type": "Analyte"},
    "Mg24": {"data_type": "Analyte"},
    "PC1": {"data_type": "PCA score"},
    "k-means": {"data_type": "Cluster"},
}

def expected_items_for_axis(axis_settings, field_types, attributes_dict):
    if not axis_settings.enabled:
        return []

    expected = [
        name for name, meta in attributes_dict.items()
        if field_types is None or meta["data_type"] in field_types
    ]

    if axis_settings.add_none:
        expected.insert(0, "None")
    return expected

@pytest.mark.parametrize("plot_type", list(axis_settings_dict.keys()))
def test_axis_settings(plot_type):
    settings = axis_settings_dict[plot_type]
    for axis, axis_settings in settings.axes.items():
        if axis == "c":
            field_types = settings.cfield_type or settings.field_type
        else:
            field_types = settings.field_type

        expected = expected_items_for_axis(axis_settings, field_types, attributes_dict)

        # For now we just test that the logic runs correctly
        assert isinstance(expected, list)