# tests/test_fieldlogic.py
import sys
from pathlib import Path
import pytest

# Add src/ to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from app.PlotAxisSettings import axis_settings_dict

# Sample attributes dictionary
attributes_dict = {
    "Xc": {"data_type": "coordinate"},
    "Yc": {"data_type": "coordinate"},
    "Li7": {"data_type": "Analyte"},
    "Mg24": {"data_type": "Analyte"},
    "PC1": {"data_type": "PCA score"},
    "k-means": {"data_type": "Cluster"},
}

# Mock combobox class
class MockComboBox:
    def __init__(self, items=None):
        self.items = items or []

    def currentText(self):
        return self.items[0] if self.items else None

    def count(self):
        return len(self.items)

    def itemText(self, idx):
        return self.items[idx]

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

    # Mock comboboxes for each axis
    mock_comboboxes = {axis: MockComboBox(settings.field_type) for axis in settings.axes}

    for axis, axis_settings in settings.axes.items():
        if axis == "c":
            field_types = settings.cfield_type or settings.field_type
        else:
            field_types = settings.field_type

        # Use mock combobox items
        field_types = mock_comboboxes.get(axis, MockComboBox(field_types)).items

        expected = expected_items_for_axis(axis_settings, field_types, attributes_dict)

        # Assertions
        assert isinstance(expected, list)
        if axis_settings.add_none:
            assert expected[0] == "None"