"""Pure-Python data model and JSON (de)serialization for LaME projects.

A project is a **manifest** -- relative paths to sample data plus per-sample
processing state -- not an archive: raw sample data is never duplicated or
modified by LaME. This mirrors ``src/workflow/WorkflowFile.py``'s style
deliberately (plain dataclasses/functions, no Qt) so it's testable without a
``QApplication``, and so a project's relationship to workflow files (see
``Project.workflow_refs``) is symmetric with how workflow files already
reference their own on-disk state.

Two tiers of per-sample state, kept separate because they have different
scopes and lifecycles:

- Tier 1 -- :class:`SampleCalibration`: a fact about the measurement, shared
  across any project that opens the sample. Lives in a ``<id>.calib.json``
  sidecar next to the sample's ``.lame.csv`` file, kept separate from the
  existing ``.lmdf.json`` import-metadata sidecar (``SampleObj.reset_data``,
  ``src/data/DataHandling.py``) since the two have different lifecycles.
- Tier 2 -- :class:`SampleProcessingState`: filters, masks, computed fields,
  and a processing log -- analytical choices specific to one project, owned
  by the project via :class:`ProjectSampleEntry`, never shared/forked across
  projects. Notes are deliberately NOT stored here: they stay as the existing
  per-sample ``.rst`` file (see ``siesta.reSTNotes``), just relocated under
  the project directory -- folding free text into this JSON manifest would
  lose the existing rich-text editor's file-based autosave/image-path
  handling for no benefit.
"""
import base64
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_FORMAT_VERSION = 1
UNTITLED_PROJECT_NAME = "Untitled Project"


# ---------------------------------------------------------------------------
# Tier 1 -- calibration (sample-inherent, shared across any project)
# ---------------------------------------------------------------------------

@dataclass
class SampleCalibration:
    """A fact about a measurement, not an analytical choice.

    Deliberately schema-open: what "calibration" means varies by instrument
    and workflow (LA-ICP-MS standards/drift correction vs. data that arrives
    already fully processed by outside software, e.g. XRF images, which may
    carry a much thinner provenance-only record). Only ``source_hash`` and
    ``calibrated_at`` are fixed, since the staleness check and "calibrated on
    <date>" display are all this migration's read side actually needs.
    Everything instrument/method-specific goes in ``payload``.

    Parameters
    ----------
    source_hash : str
        Fingerprint of the raw sample file at calibration time, from
        `compute_source_hash`. Compared against the file's current
        fingerprint to detect staleness.
    calibrated_at : datetime
        When this calibration was computed.
    method : str, optional
        Free-form tag naming the calibration approach (e.g.
        ``'LA-ICP-MS standards+drift'``, ``'XRF (pre-processed externally)'``)
        -- not an enum, so a new method needs no schema change.
    payload : dict, optional
        Method-specific content; shape is not fixed here.
    """
    source_hash: str
    calibrated_at: datetime
    method: Optional[str] = None
    payload: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'source_hash': self.source_hash,
            'calibrated_at': self.calibrated_at.isoformat(),
            'method': self.method,
            'payload': self.payload,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            source_hash=d['source_hash'],
            calibrated_at=datetime.fromisoformat(d['calibrated_at']),
            method=d.get('method'),
            payload=d.get('payload', {}),
        )


def compute_source_hash(raw_path):
    """Cheap staleness fingerprint for a sample file: mtime + size, not content.

    A full-file hash is deliberately avoided -- laser-map ``.lame.csv`` files
    can be large, and re-hashing one on every sample load would be a real
    cost for no benefit here; mtime+size is enough to catch "the file
    changed" without reading it.

    Parameters
    ----------
    raw_path : str or Path

    Returns
    -------
    str
        ``"<mtime>:<size>"``.
    """
    st = Path(raw_path).stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def is_calibration_stale(calibration, raw_path):
    """True if `raw_path`'s current fingerprint no longer matches `calibration`.

    Parameters
    ----------
    calibration : SampleCalibration or None
        ``None`` means "no calibration exists" -- not stale, just absent;
        callers should distinguish "no calibration" from "stale calibration"
        using ``calibration is None`` rather than relying on this returning
        `True` for that case.
    raw_path : str or Path

    Returns
    -------
    bool
    """
    if calibration is None:
        return False
    return compute_source_hash(raw_path) != calibration.source_hash


def calibration_sidecar_path(sample_path):
    """Path to the ``.calib.json`` sidecar for a ``<id>.lame.csv`` sample file.

    Mirrors the existing ``.lmdf.json`` import-metadata sidecar naming
    convention (``SampleObj.reset_data``, ``src/data/DataHandling.py``) --
    ``'.lame.'`` -> ``'.calib.'``, ``'.csv'`` -> ``'.json'`` -- so calibration
    sidecars sit predictably next to both the sample data and its import
    metadata.
    """
    sample_path = Path(sample_path)
    return Path(str(sample_path).replace('.lame.', '.calib.').replace('.csv', '.json'))


def load_calibration_sidecar(sample_path):
    """Load the `.calib.json` sidecar for `sample_path`, if present.

    Tolerant like `WorkflowFile.load_workflow_file`, but returns `None`
    rather than an empty-but-valid payload -- "no calibration yet" is a
    normal, expected state here, not something to backfill defaults for.

    Returns
    -------
    SampleCalibration or None
    """
    path = calibration_sidecar_path(sample_path)
    if not path.exists():
        return None
    with open(path, 'r') as f:
        return SampleCalibration.from_dict(json.load(f))


def save_calibration_sidecar(sample_path, calibration):
    """Write `calibration` to the `.calib.json` sidecar next to `sample_path`."""
    path = calibration_sidecar_path(sample_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(calibration.to_dict(), f, indent=2)


# ---------------------------------------------------------------------------
# Tier 2 -- processing state (project-scoped, not shared)
# ---------------------------------------------------------------------------

@dataclass
class FilterSpec:
    """One row of `SampleObj.filter_df` (`src/data/DataHandling.py`), serialized."""
    use: bool
    field_type: str
    field: str
    norm: str
    min: float
    max: float
    operator: str
    persistent: bool


@dataclass
class MaskSpec:
    """One named mask contributing to `SampleObj.mask` (crop/polygon/cluster).

    Polygon *geometry* is not duplicated here -- it already round-trips
    through `PolygonManager.save_polygons`/`load_polygons`
    (`src/data/Polygon.py`) as ``.poly`` files alongside this manifest.
    `MaskSpec` records which mask kinds are active and any parameters needed
    to reproduce non-polygon masks (e.g. a crop bounding box, or which
    cluster method/labels a cluster mask came from).
    """
    kind: str
    enabled: bool = True
    params: dict = field(default_factory=dict)


@dataclass
class ComputedFieldSpec:
    """A Calculator-defined field (`src/common/Calculator.py`), recorded so it
    can be recomputed on load rather than requiring raw values to be stored.
    """
    field: str
    formula: str


@dataclass
class ProcessingLogEntry:
    """An auto-generated, factual record of one processing operation --
    distinct from notes' human interpretation, even though both describe the
    same underlying choices.
    """
    timestamp: str
    action: str
    details: dict = field(default_factory=dict)


@dataclass
class SampleProcessingState:
    workflow_ref: Optional[str] = None
    applied_filters: list = field(default_factory=list)
    masks: list = field(default_factory=list)
    computed_fields: list = field(default_factory=list)
    processing_log: list = field(default_factory=list)


def _processing_state_to_dict(state):
    return {
        'workflow_ref': state.workflow_ref,
        'applied_filters': [asdict(f) for f in state.applied_filters],
        'masks': [asdict(m) for m in state.masks],
        'computed_fields': [asdict(c) for c in state.computed_fields],
        'processing_log': [asdict(p) for p in state.processing_log],
    }


def _processing_state_from_dict(d):
    return SampleProcessingState(
        workflow_ref=d.get('workflow_ref'),
        applied_filters=[FilterSpec(**f) for f in d.get('applied_filters', [])],
        masks=[MaskSpec(**m) for m in d.get('masks', [])],
        computed_fields=[ComputedFieldSpec(**c) for c in d.get('computed_fields', [])],
        processing_log=[ProcessingLogEntry(**p) for p in d.get('processing_log', [])],
    )


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

@dataclass
class ProjectSampleEntry:
    sample_path: Path
    calibration: Optional[SampleCalibration] = None
    processing: SampleProcessingState = field(default_factory=SampleProcessingState)


@dataclass
class Project:
    name: str
    samples: dict = field(default_factory=dict)          # dict[str, ProjectSampleEntry]
    workflow_refs: list = field(default_factory=list)    # list[Path]
    dock_layout: Optional[bytes] = None
    dirty: bool = False
    # Not part of the spec's dataclass sketch, and not written into the JSON
    # payload itself (it's where the manifest came from, not its content) --
    # added so `ProjectManager` can distinguish "Save" (write back here) from
    # "Save As" (prompt for a new location) without tracking it separately.
    manifest_path: Optional[Path] = None


def new_project(name=None):
    """Create a new, empty, in-memory project. Nothing is written to disk."""
    return Project(name=name or UNTITLED_PROJECT_NAME)


def _to_relative(path, base_dir):
    """`path` relative to `base_dir`, falling back to an absolute string if
    they don't share a common root (e.g. different drives on Windows).
    """
    try:
        return os.path.relpath(path, base_dir)
    except ValueError:
        return str(path)


def _to_absolute(rel_or_abs, base_dir):
    p = Path(rel_or_abs)
    return p if p.is_absolute() else (base_dir / p).resolve()


def save_project(project, manifest_path):
    """Write `project` to `manifest_path` as JSON, creating parent directories
    as needed.

    Sample and workflow-file paths are stored relative to `manifest_path`'s
    own directory, so the project directory can be moved -- even to another
    machine -- without breaking the links, per the "manifest with
    references, not an archive" design. Sets `project.dirty = False` and
    `project.manifest_path = manifest_path` on success.

    Parameters
    ----------
    project : Project
    manifest_path : str or Path
    """
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    # Resolve (not just absolute-ify) before computing relative paths: on
    # macOS /tmp and /var are symlinks, and tempfile.mkdtemp() (among other
    # things) returns the unresolved form. If save and load ever disagree on
    # how many directory levels a manifest's own path actually has -- one
    # side resolving a symlink, the other not -- the '..' count baked into
    # a relative path here would be wrong when resolved back on the other
    # side. Resolving both ends the same way keeps them consistent.
    base_dir = manifest_path.resolve().parent

    samples = {}
    for sample_id, entry in project.samples.items():
        samples[sample_id] = {
            'sample_path': _to_relative(Path(entry.sample_path).resolve(), base_dir),
            'calibration': entry.calibration.to_dict() if entry.calibration else None,
            'processing': _processing_state_to_dict(entry.processing),
        }

    payload = {
        'format_version': PROJECT_FORMAT_VERSION,
        'name': project.name,
        'samples': samples,
        'workflow_refs': [_to_relative(Path(p).resolve(), base_dir) for p in project.workflow_refs],
        'dock_layout': (
            base64.b64encode(project.dock_layout).decode('ascii')
            if project.dock_layout else None
        ),
    }
    with open(manifest_path, 'w') as f:
        json.dump(payload, f, indent=2)

    project.dirty = False
    project.manifest_path = manifest_path


def load_project(manifest_path):
    """Load a project manifest from disk.

    Parameters
    ----------
    manifest_path : str or Path

    Returns
    -------
    Project
    """
    manifest_path = Path(manifest_path)
    base_dir = manifest_path.resolve().parent
    with open(manifest_path, 'r') as f:
        payload = json.load(f)

    samples = {}
    for sample_id, d in payload.get('samples', {}).items():
        samples[sample_id] = ProjectSampleEntry(
            sample_path=_to_absolute(d['sample_path'], base_dir),
            calibration=(
                SampleCalibration.from_dict(d['calibration'])
                if d.get('calibration') else None
            ),
            processing=_processing_state_from_dict(d.get('processing', {})),
        )

    dock_layout = None
    if payload.get('dock_layout'):
        dock_layout = base64.b64decode(payload['dock_layout'])

    return Project(
        name=payload.get('name', UNTITLED_PROJECT_NAME),
        samples=samples,
        workflow_refs=[_to_absolute(p, base_dir) for p in payload.get('workflow_refs', [])],
        dock_layout=dock_layout,
        dirty=False,
        manifest_path=manifest_path,
    )
