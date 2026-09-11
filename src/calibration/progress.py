"""Lightweight, UI-agnostic progress reporting for the calibration pipeline.

Mirrors this codebase's backend/UI separation elsewhere (e.g.
``src/deconvolution/*.py``): no Qt imports here, so ``pipeline.py`` and
``src/classification/cosine.py`` stay independently testable/importable
without a running ``QApplication``. Every instrumented function takes an
optional ``progress_callback: ProgressCallback | None = None`` and calls it
directly wherever it has something worth reporting; ``None`` (the default
for every existing caller) is a complete no-op, so adding this parameter
changes nothing for code that doesn't pass it.

``src/calibration/dock_widgets.py`` is the only consumer that turns these
events into UI: ``_PipelineWorker`` re-exposes ``progress_callback`` as a Qt
signal (``worker.progress.emit``) so a ``ProgressEvent`` built on the worker
thread can safely update the main-thread status bar via a normal queued
signal/slot connection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Stage keys used across the pipeline, in the order a full Stage-1 run
# through them: "reading" (parsing raw files) -> "background" (per-file
# background window detection/correction) -> "drift" (session background
# drift fit) -> "calibration" (per-standard fit) -> "sample" (per-sample
# calibrated-grid assembly). "deconvolution"/"classification" are Stage
# 2/3, reported the same way but never interleaved with Stage 1's.
STAGE_READING = "reading"
STAGE_BACKGROUND = "background"
STAGE_DRIFT = "drift"
STAGE_CALIBRATION = "calibration"
STAGE_SAMPLE = "sample"
STAGE_DECONVOLUTION = "deconvolution"
STAGE_CLASSIFICATION = "classification"


@dataclass
class ProgressEvent:
    """One progress update.

    Attributes
    ----------
    stage : str
        One of the ``STAGE_*`` constants above.
    message : str
        Human-readable status text, ready to show as-is.
    current : int
        Progress-bar value for this stage.
    total : int
        Progress-bar maximum for this stage; ``0`` means indeterminate
        (unknown/not worth computing a total -- e.g. a single one-shot fit)
        and should drive a busy/marquee indicator, not a stalled 0/0 bar.
    sample_current, sample_total, sample_label : int, int, str
        Only meaningful for ``stage == STAGE_READING``: which sample
        (1-based) is currently being read, how many samples there are in
        total, and its label -- the "how many samples have been read"
        counter is separate from ``current``/``total``, which track
        progress *within* that one sample's line files.
    """

    stage: str
    message: str
    current: int
    total: int
    sample_current: int = 0
    sample_total: int = 0
    sample_label: str = ""


ProgressCallback = Callable[[ProgressEvent], None]
