# Claude Code Prompt: Migrate LaserMapExplorer to a Project-Based Data Model

## Context

LaserMapExplorer (LaME) currently opens data via three independent toolbar actions:
**Open Sample**, **Open Directory**, and **Open Project**. This is being replaced with a
single project-based model, similar in spirit to GIS applications (e.g., QGIS): a
**project** is the unit of work, and **samples** are members of a project, added
individually or by directory.

This migration is primarily a data-model and architecture change. UI updates (menus,
toolbar, dock widget) follow from it but should be treated as secondary to getting the
data model and file formats right.

Please read through this entire prompt before making changes, then propose an
implementation plan (file/module layout, new classes, migration order) before writing
code. This is a substantial architectural change — work incrementally, and check in
after each phase rather than doing everything in one pass.

---

## Data model

Two tiers of per-sample state, deliberately kept separate because they have different
scopes and lifecycles:

### Tier 1 — Calibration (sample-inherent, shared across any project)

Genuinely a fact about the measurement, not an analytical choice: instrument response,
standards used, drift correction. Computed once; any project that opens this sample
picks it up automatically from a sidecar file stored alongside the raw data.

```python
@dataclass
class SampleCalibration:
    source_hash: str            # hash/mtime of the raw file, for staleness checks
    standards_used: list[str]
    drift_correction: DriftCorrectionSpec
    calibrated_at: datetime
```

- Lives in a sidecar file next to the raw data, e.g. `core_47A.calib`.
- Raw data files themselves are never modified by LaME.
- On loading a sample into a project, check `source_hash` against the current raw
  file's hash/mtime. If it doesn't match, flag as stale in the UI rather than silently
  trusting it — don't auto-recompute or auto-discard.

### Tier 2 — Processing state + notes (project-scoped, NOT shared)

Filters, masks, computed columns, cluster/classification definitions, and notes are
analytical choices specific to a given project's questions. They are bundled together
because notes are commentary on these specific choices and aren't meaningful decoupled
from them. This tier is owned by the project, not the sample.

```python
@dataclass
class SampleProcessingState:
    workflow_ref: str | None            # path/UUID of the .lame_workflow used, if any
    applied_filters: list[FilterSpec]
    masks: list[MaskSpec]
    computed_fields: list[ComputedFieldSpec]
    notes: str                          # free-text interpretation, project-scoped
    processing_log: list[ProcessingLogEntry]  # auto-generated, timestamped, factual
```

- Keep `processing_log` (mechanical, auto-generated record of what operations were
  applied) conceptually distinct from `notes` (human interpretation) even though they
  live in the same object — this distinction is cheap now and will matter if/when
  sample export is built later.
- Do NOT build shared/fork reuse logic for this tier. No "used by N other projects"
  tracking, no reuse-vs-fork prompts. Each project owns its own processing state for a
  sample outright. (This is an intentional simplification — see "Explicitly out of
  scope" below.)

### Project file

```python
@dataclass
class ProjectSampleEntry:
    sample_path: Path                       # → raw data; drives dock widget link status
    calibration: SampleCalibration | None   # auto-loaded from sidecar if present
    processing: SampleProcessingState       # owned by this project

@dataclass
class Project:
    name: str
    samples: dict[str, ProjectSampleEntry]  # keyed by sample id
    workflow_refs: list[Path]               # linked workflow files (see below)
    dock_layout: bytes | None               # optional: saveState() blob
    dirty: bool = False                     # tracks unsaved changes for close prompt
```

**File format**: use a manifest-with-references design, not a monolithic archive.
Store relative paths to raw sample data plus the processing state above. Reasons:
projects stay small and fast to save/load; raw data stays canonical and untouched
(provenance); relative paths survive moving a project directory between machines.
JSON or SQLite are both reasonable for the manifest — pick based on whether you expect
to query across many samples (SQLite) or mostly load-the-whole-thing (JSON). Since
there's no backward-compatibility burden yet (pre-release, testing only), don't
over-engineer versioning — a simple `format_version` field is enough for now.

### Untitled / implicit project

To avoid forcing "New Project → name it → choose location" before a user can look at
data:

- If a user adds a sample/directory with no project open, silently create an in-memory
  "Untitled Project." Everything works immediately; nothing is written to disk until
  the user saves, at which point they're prompted for a location/name.
- This means "Open Directory" and "Open Sample" as *concepts* survive as the entry
  point into an untitled project, even though there's only one underlying code path.
  You can keep a menu action labeled "Add Samples..." that does this regardless of
  whether a project is currently open.

### Workflows

Workflow files are project-linked but stored and saved **separately** so they can be
reused across projects (e.g., a "HPE correction" workflow used by multiple studies).
The project stores references (paths) to workflow files, not the workflow content
itself. Same is true for other files generated by LaME that should be reusable
independent of a project (check with me on the exact list if it's not obvious from
the existing codebase — colormap presets, cluster definitions, etc. may fall in this
category too).

---

## UI changes

### Menu / toolbar restructuring

Replace the three open actions with:

```
File:  New Project
       Open Project...          (+ Recent Projects submenu)
       Add Samples...           ← file(s) or directory; always enabled,
                                    spawns an untitled project if none open
       ─────────
       Save Project
       Save Project As...
       ─────────
       Close Project
```

- `Add Samples...` should accept both individual files and directories in one dialog
  action (or a split-button if that's cleaner given the existing `QToolButton`
  patterns elsewhere in the app).
- Tool-specific dock widgets keep their existing toolbars — this migration does not
  change per-tool toolbar ownership.

### Close-project prompt

On close (and on app exit), check `project.dirty`. If true, prompt Save / Discard /
Cancel before proceeding. Consider only setting `dirty = True` for meaningful state
changes (samples added, processing changed, notes edited) rather than incidental UI
state, so users aren't prompted to save trivial untitled sessions where nothing of
substance happened — use judgment here, but err toward NOT nagging the user for a
session where they just looked at data without modifying anything.

### Project Files dock widget (new)

A new `QDockWidget` showing the samples in the current project as a tree, with status
indicators per sample:

- **Link status**: raw file found / moved / missing. If missing, offer a "Locate..."
  action that lets the user pick the new path and updates `sample_path` in the project
  (don't silently break — this was the original motivating requirement).
- **Processing status**: unprocessed / processed / stale (calibration `source_hash`
  mismatch against the current raw file).
- **Notes indicator**: whether project notes exist for this sample.

Example tree shape:

```
▾ core_47A                          [✓ linked]
    calibration: ✓ (2026-06-14)
    processing: 3 filters, 1 mask   [notes: 2 paragraphs]
▾ core_52B                          [⚠ moved — click to relocate]
    calibration: none
    processing: none
```

Keep this dock widget's own toolbar (if any) consistent in styling with the other
tool dock widgets already in the app, per existing conventions.

---

## Explicitly out of scope for this migration

Do not build these now — flag if you find yourself needing to for the core model to
work, but the intent is to defer them:

- **Sample export/import between projects.** Later, this is expected to be "serialize
  a `SampleProcessingState` (+ optionally `SampleCalibration`) to a standalone file"
  and "read one in as the starting processing state for a new project entry." Don't
  build the dialog, merge logic, or conflict handling now.
- **Shared/fork reuse tracking for Tier 2 processing state.** Each project owns its
  processing state outright; no cross-project sharing bookkeeping.
- **Backward-compatibility / project file versioning migrations.** No one is using
  this in production yet — a simple format version tag is sufficient.
- **Ribbon-style / stacked toolbar layout.** Separate piece of work, not part of this
  migration.

---

## Suggested implementation order

1. Define the dataclasses above (`SampleCalibration`, `SampleProcessingState`,
   `ProjectSampleEntry`, `Project`) and the manifest serialization format.
2. Implement `Project` load/save, including the untitled-project flow and the
   relative-path resolution + "locate missing sample" handling.
3. Wire calibration sidecar read (`.calib` next to raw data) with staleness check.
4. Replace the three existing open actions with the new File menu structure and the
   `Add Samples...` flow.
5. Build the Project Files dock widget against the `Project` model from steps 1–2.
6. Add the close/exit dirty-check prompt.
7. Migrate workflow linking (project stores references, workflow files remain
   separately saved/loadable).

Please confirm this plan against the current codebase structure (I'd expect this
touches `MainWindow`, whatever currently handles Open Sample/Directory/Project, and
introduces new modules for `Project`/`SampleCalibration`/`SampleProcessingState`)
before starting, and flag anywhere the existing architecture makes a step here more
involved than described.
