"""Limit of detection: mean(background) + 3*SD(background), per analyte."""
from __future__ import annotations


def compute_lod(
    background_mean: dict[str, float], background_std: dict[str, float], k: float = 3.0
) -> dict[str, float]:
    """LOD per analyte = ``background_mean + k * background_std`` (k=3 by default)."""
    return {
        analyte: background_mean[analyte] + k * background_std.get(analyte, 0.0)
        for analyte in background_mean
    }
