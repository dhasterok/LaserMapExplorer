"""Unit tests for src/classification/presets.py.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.classification.presets import load_presets, save_preset


def test_load_presets_missing_file_returns_empty_dict(tmp_path):
    assert load_presets(tmp_path / "does_not_exist.csv") == {}


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "presets.csv"
    save_preset(path, "Carbonates", ["Calcite", "Dolomite", "Magnesite"])
    presets = load_presets(path)
    assert presets == {"Carbonates": ["Calcite", "Dolomite", "Magnesite"]}


def test_saving_a_second_preset_preserves_the_first(tmp_path):
    path = tmp_path / "presets.csv"
    save_preset(path, "Carbonates", ["Calcite", "Dolomite"])
    save_preset(path, "Feldspars", ["Anorthite", "Albite"])
    presets = load_presets(path)
    assert presets == {
        "Carbonates": ["Calcite", "Dolomite"],
        "Feldspars": ["Anorthite", "Albite"],
    }


def test_saving_same_name_again_overwrites_it(tmp_path):
    path = tmp_path / "presets.csv"
    save_preset(path, "Carbonates", ["Calcite"])
    save_preset(path, "Carbonates", ["Dolomite", "Magnesite"])
    presets = load_presets(path)
    assert presets == {"Carbonates": ["Dolomite", "Magnesite"]}
