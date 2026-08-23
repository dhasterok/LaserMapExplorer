"""Unit tests for src/classification/cosine.py.

Pure Python/pandas -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.classification.cosine import classify_batch, classify_pixel, cosine_similarity
from src.classification.reference import MineralReference


def _ref(name, group, **composition):
    return MineralReference(
        mineral_name=name, group_yaml=group, mineral_class="Test", end_member_key=name.lower(),
        formula="", composition=composition,
    )


ANORTHITE = _ref("Anorthite", "feldspar", Ca=13.72, Al=18.97, Si=20.75, O=46.14)
ALBITE = _ref("Albite", "feldspar", Na=8.6, Al=10.3, Si=32.1, O=48.9)
QUARTZ = _ref("Quartz", "quartz", Si=46.7, O=53.3)
PYRITE = _ref("Pyrite", "pyrite", Fe=46.55, S=53.45)
# Same 4-element set as ANORTHITE (Ca, Al, Si, O) but different ratios and a
# different group -- lets a mix of the two stay fully scorable against both
# (n_min=3) without the overlap itself being the thing that excludes one
# side, which a quartz/anorthite mix (only 2 shared elements) would do.
GARNET_LIKE = _ref("Pyrope", "garnet", Ca=5.0, Al=13.0, Si=18.0, O=45.0)


# ------------------------------------------------------------------
# cosine_similarity
# ------------------------------------------------------------------

def test_cosine_similarity_identical_vectors_is_one():
    s = cosine_similarity(ANORTHITE.composition, ANORTHITE.composition)
    assert s == pytest.approx(1.0)


def test_cosine_similarity_is_scale_invariant():
    scaled = {k: v * 10000 for k, v in ANORTHITE.composition.items()}  # e.g. wt% -> ppm-like scale
    s = cosine_similarity(scaled, ANORTHITE.composition)
    assert s == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_below_n_min_returns_none():
    # Only 2 elements overlap (Fe, S both absent from anorthite) -- below default n_min=3
    sample = {"Fe": 46.55, "S": 53.45}
    assert cosine_similarity(sample, ANORTHITE.composition, n_min=3) is None


def test_cosine_similarity_excludes_nonoverlapping_elements():
    # Quartz-like sample plus an element quartz doesn't have -- shouldn't
    # be dragged down by zero-filling that element.
    sample = {"Si": 46.7, "O": 53.3, "Zr": 500.0}
    s = cosine_similarity(sample, QUARTZ.composition, n_min=2)
    assert s == pytest.approx(1.0)


# ------------------------------------------------------------------
# classify_pixel
# ------------------------------------------------------------------

def test_classify_pixel_pure_endmember_scores_near_one():
    result = classify_pixel(dict(ANORTHITE.composition), [ANORTHITE, ALBITE, QUARTZ, PYRITE])
    assert result.label == "Anorthite"
    assert result.score == pytest.approx(1.0, abs=1e-9)
    assert result.ambiguous is False


def test_classify_pixel_below_threshold_is_unclassified():
    # Quartz-like sample plus a trace Al so it clears n_min=3 against the
    # feldspar references. Si/O-dominated silicate compositions still score
    # fairly high on cosine similarity against each other even when the
    # actual mineral differs (a known, expected limitation of composition-
    # only matching -- see the classification spec's discussion of this) --
    # tau_min=0.99 is set high enough that this still counts as "below
    # threshold" without pretending the raw score is near zero.
    sample = {"Si": 46.7, "O": 53.3, "Al": 0.05}
    result = classify_pixel(sample, [ANORTHITE, ALBITE, PYRITE], tau_min=0.99)
    assert result.label is None
    assert result.score is not None and result.score < 0.99


def test_classify_pixel_intermediate_plagioclase_not_flagged_ambiguous():
    """An50-like mix of anorthite+albite (same group_yaml) should score
    close to both -- small in-group gap -- but must NOT be flagged
    ambiguous, since that's an expected solid-solution position, not a
    mixed/boundary pixel (spec Sec 3.5)."""
    an50 = {k: (ANORTHITE.composition.get(k, 0) + ALBITE.composition.get(k, 0)) / 2
            for k in set(ANORTHITE.composition) | set(ALBITE.composition)}
    result = classify_pixel(an50, [ANORTHITE, ALBITE, QUARTZ, PYRITE], tau_min=0.8, g_min=0.02)
    assert result.label in ("Anorthite", "Albite")
    assert result.ambiguous is False
    # The gap should be large relative to quartz/pyrite (different groups),
    # even though it's a genuine 50/50 mix within the feldspar group.
    assert result.gap > 0.02


def test_classify_pixel_cross_group_mix_flagged_ambiguous():
    """A 50/50 mix of two *different-group* references sharing the same
    element set (e.g. a genuine feldspar/garnet boundary pixel) should
    score close to both, with a small cross-group gap -- this IS the case
    the ambiguous flag exists to catch."""
    mix = {k: (ANORTHITE.composition[k] + GARNET_LIKE.composition[k]) / 2 for k in ANORTHITE.composition}
    result = classify_pixel(mix, [ANORTHITE, ALBITE, GARNET_LIKE, PYRITE], tau_min=0.5, g_min=0.05)
    assert result.ambiguous is True
    assert result.gap < 0.05


def test_classify_pixel_no_candidates_scored_returns_all_none():
    result = classify_pixel({"Xx": 1.0}, [ANORTHITE, ALBITE])
    assert result.label is None
    assert result.score is None
    assert result.gap is None
    assert result.ambiguous is False


# ------------------------------------------------------------------
# classify_batch
# ------------------------------------------------------------------

def test_classify_batch_aligns_to_dataframe_index():
    data = pd.DataFrame({
        "Ca43": [13.72, 0.0],
        "Al27": [18.97, 10.3],
        "Si29": [20.75, 32.1],
        "O16": [46.14, 48.9],
        "Na23": [0.0, 8.6],
    }, index=[10, 20])
    element_columns = {"Ca": "Ca43", "Al": "Al27", "Si": "Si29", "O": "O16", "Na": "Na23"}
    result = classify_batch(data, [ANORTHITE, ALBITE], element_columns, tau_min=0.9)
    assert list(result.index) == [10, 20]
    assert result.loc[10, "label"] == "Anorthite"
    assert result.loc[20, "label"] == "Albite"


def test_classify_batch_skips_missing_values():
    import numpy as np
    data = pd.DataFrame({"Ca43": [13.72, np.nan], "Al27": [18.97, 10.3], "Si29": [20.75, 32.1], "O16": [46.14, 48.9]})
    element_columns = {"Ca": "Ca43", "Al": "Al27", "Si": "Si29", "O": "O16"}
    result = classify_batch(data, [ANORTHITE, ALBITE], element_columns, tau_min=0.9, n_min=3)
    assert result.loc[0, "label"] == "Anorthite"
