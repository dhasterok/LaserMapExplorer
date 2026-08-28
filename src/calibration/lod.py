"""Limit of detection: mean(background) + 3*SD(background), per analyte."""
from __future__ import annotations


def compute_lod(
    background_mean: dict[str, float], background_std: dict[str, float], k: float = 3.0
) -> dict[str, float]:
    """Limit of detection per analyte, ``background_mean + k * background_std``.

    Parameters
    ----------
    background_mean : dict[str, float]
        Mean background signal keyed by analyte name. Its keys define the
        set of analytes returned.
    background_std : dict[str, float]
        Standard deviation of the background signal keyed by analyte name.
        Analytes absent from this mapping are treated as having zero
        background spread.
    k : float, optional
        Multiplier applied to the background standard deviation, by default
        ``3.0`` (the conventional 3-sigma limit of detection).

    Returns
    -------
    dict[str, float]
        LOD value for every analyte in ``background_mean``, in the same
        units as the input background signal.
    """
    return {
        analyte: background_mean[analyte] + k * background_std.get(analyte, 0.0)
        for analyte in background_mean
    }
