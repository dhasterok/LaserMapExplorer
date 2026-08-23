"""Unit tests for src/deconvolution/config.py's YAML defaults loader.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.config import (
    DeconvolutionConfigError, DeconvolutionSettings, load_default_deconvolution_settings,
)


def _write(tmp_path, content: dict) -> Path:
    p = tmp_path / "defaults.yaml"
    p.write_text(yaml.safe_dump(content))
    return p


def test_load_real_defaults_yaml_is_all_off():
    settings = load_default_deconvolution_settings("resources/calibration/defaults.yaml")
    assert settings == DeconvolutionSettings()


def test_missing_deconvolution_section_returns_defaults(tmp_path):
    path = _write(tmp_path, {"drift_order": 1})
    settings = load_default_deconvolution_settings(path)
    assert settings == DeconvolutionSettings()


def test_loads_configured_values(tmp_path):
    path = _write(tmp_path, {
        "deconvolution": {
            "apply_shift": True,
            "apply_washout": True,
            "washout_tau_s": {"Si29": 2.5, "Ca43": 1.1},
        }
    })
    settings = load_default_deconvolution_settings(path)
    assert settings.apply_shift is True
    assert settings.apply_washout is True
    assert settings.washout_tau_s == {"Si29": 2.5, "Ca43": 1.1}


def test_rejects_non_mapping_washout_tau_s(tmp_path):
    path = _write(tmp_path, {"deconvolution": {"washout_tau_s": [1, 2, 3]}})
    with pytest.raises(DeconvolutionConfigError):
        load_default_deconvolution_settings(path)


def test_rejects_nonpositive_tau(tmp_path):
    path = _write(tmp_path, {"deconvolution": {"washout_tau_s": {"Si29": -1.0}}})
    with pytest.raises(DeconvolutionConfigError):
        load_default_deconvolution_settings(path)


def test_rejects_malformed_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("deconvolution: [unterminated")
    with pytest.raises(DeconvolutionConfigError):
        load_default_deconvolution_settings(path)
