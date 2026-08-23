"""Cosine-distance mineral classification (design spec
``plans/mineral_classification_calibration_spec.md`` Sec 3.2-3.5).

Cosine similarity is restricted to each candidate's element overlap with
the sample (eq. 1) -- LA-ICP-MS analyses aren't closed compositions, and
different reference minerals cover different element sets, so a raw dot
product over all columns (zero-filling gaps) would bias the score toward
whichever reference happens to share the most measured elements, not the
best compositional match.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from src.classification.reference import MineralReference


@dataclass(frozen=True)
class PixelClassification:
    label: str | None       # winning mineral_name, or None if unclassified (below tau_min or no candidate scored)
    score: float | None      # winning cosine similarity
    gap: float | None         # group-aware ambiguity gap (Sec 3.5), None only when nothing scored at all
    ambiguous: bool            # gap < g_min -- flagged, but label/score are still reported (Sec 3.4)


def cosine_similarity(sample: dict[str, float], reference: dict[str, float], n_min: int = 3) -> float | None:
    """Eq. (1): dot product restricted to the key intersection.

    Returns ``None`` (not a low score) when the overlap is smaller than
    ``n_min`` -- excluded from the candidate set entirely, per spec
    Sec 3.2, rather than scored as a poor match that could still win by
    default if every other candidate is also excluded.
    """
    common = sample.keys() & reference.keys()
    if len(common) < n_min:
        return None
    numerator = sum(sample[k] * reference[k] for k in common)
    norm_sample = math.sqrt(sum(sample[k] ** 2 for k in common))
    norm_reference = math.sqrt(sum(reference[k] ** 2 for k in common))
    if norm_sample == 0 or norm_reference == 0:
        return None
    return numerator / (norm_sample * norm_reference)


def classify_pixel(
    sample: dict[str, float],
    references: list[MineralReference],
    tau_min: float = 0.95,
    g_min: float = 0.02,
    n_min: int = 3,
) -> PixelClassification:
    """Eq. (2)-(3): best-match assignment plus the group-aware ambiguity gap.

    The gap (eq. 3) is computed **after** grouping same-``group_yaml``
    references (spec Sec 3.5): it's the winning score minus the best score
    among references in a *different* group, not simply top-1-minus-top-2.
    An intermediate-composition plagioclase legitimately scoring close to
    both anorthite and albite (same group_yaml) is expected -- solid
    solutions are compositional segments, not ambiguity -- so that
    within-group closeness must not trip the ambiguous flag; only a
    close *cross-group* runner-up (a genuine boundary/mixed-phase pixel)
    should.
    """
    scored = []
    for ref in references:
        s = cosine_similarity(sample, ref.composition, n_min=n_min)
        if s is not None:
            scored.append((ref, s))

    if not scored:
        return PixelClassification(label=None, score=None, gap=None, ambiguous=False)

    scored.sort(key=lambda pair: pair[1], reverse=True)
    best_ref, best_score = scored[0]

    other_group = [s for ref, s in scored if ref.group_yaml != best_ref.group_yaml]
    gap = best_score - other_group[0] if other_group else best_score

    if best_score < tau_min:
        return PixelClassification(label=None, score=best_score, gap=gap, ambiguous=False)

    return PixelClassification(label=best_ref.mineral_name, score=best_score, gap=gap, ambiguous=gap < g_min)


def classify_batch(
    data: pd.DataFrame,
    references: list[MineralReference],
    element_columns: dict[str, str],
    tau_min: float = 0.95,
    g_min: float = 0.02,
    n_min: int = 3,
) -> pd.DataFrame:
    """Per-row wrapper over :func:`classify_pixel`.

    ``element_columns`` maps a reference element symbol (e.g. ``"Ca"``) to
    the actual column name in ``data`` (e.g. ``"Ca43"``) -- see
    ``dock.py``'s column-resolution helper, the same problem
    ``src/stoichiometry/dock.py``'s ``_resolve_ppm_columns`` solves for
    mineral configs.

    Returns a DataFrame (same index as ``data``) with columns ``label``,
    ``score``, ``gap``, ``ambiguous`` -- row-by-row Python loop, same
    "simplicity over micro-optimization for desktop-map-sized data"
    precedent as ``src/stoichiometry/dock.py``'s per-pixel
    ``pipeline.calculate`` loop.
    """
    rows = []
    for _, row in data.iterrows():
        sample = {
            el: float(row[col]) for el, col in element_columns.items()
            if col in row.index and pd.notna(row[col])
        }
        result = classify_pixel(sample, references, tau_min=tau_min, g_min=g_min, n_min=n_min)
        rows.append({"label": result.label, "score": result.score, "gap": result.gap, "ambiguous": result.ambiguous})
    return pd.DataFrame(rows, index=data.index)
