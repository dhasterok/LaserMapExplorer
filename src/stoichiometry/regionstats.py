"""Per-region (ROI/cluster) summary statistics for computed quantities.

No generic "mean/median/std per region" mechanism exists elsewhere in the
app -- ``SampleObj.cluster_percentages``/``roi_percentages`` only compute
area fractions. This is a small, new, deliberately generic adapter (not
stoichiometry-specific beyond its default use here) so it could be reused
for other per-region summaries later without duplicating this groupby.
"""
from __future__ import annotations

import pandas as pd


def region_stats(
    processed: pd.DataFrame,
    mask,
    region_column: str,
    value_columns: list[str],
    exclude_ids: list | None = None,
) -> pd.DataFrame:
    """Mean/median/std/count of ``value_columns``, grouped by ``region_column``.

    Parameters
    ----------
    processed : pandas.DataFrame
        ``SampleObj.processed`` (or any frame with the same columns).
    mask : array-like of bool
        Rows to include (e.g. ``SampleObj.mask``).
    region_column : str
        Column holding integer region ids -- ``'ROI'`` or the active
        clustering method's column name (both already exist as ``processed``
        columns via the app's existing ROI/cluster machinery).
    value_columns : list[str]
        Columns to summarize.
    exclude_ids : list, optional
        Region ids to drop before aggregating (e.g. ``[0]`` for ROI's
        "unassigned" placeholder, or ``[99]`` for the cluster "mask" placeholder).

    Returns
    -------
    pandas.DataFrame
        One row per region id, columns ``region_column`` plus
        ``f'{value_column}_{stat}'`` for stat in mean/median/std/count.
    """
    df = processed.loc[mask, [region_column] + list(value_columns)]

    if exclude_ids:
        df = df[~df[region_column].isin(exclude_ids)]

    grouped = df.groupby(region_column)[value_columns].agg(["mean", "median", "std", "count"])
    grouped.columns = [f"{col}_{stat}" for col, stat in grouped.columns]
    return grouped.reset_index()
