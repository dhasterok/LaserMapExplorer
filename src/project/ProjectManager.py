"""Qt-aware glue layer owning the live `Project` for the running session.

`ProjectManager` is to `Project` what `AppData` is to live sample state: it
owns the one current `Project` instance, mediates all load/save/dirty-
tracking, and is the single underlying code path `Add Samples...` (and,
later, the import wizards) call to get files/directories into the current
project.

`AppData.sample_list`/`csv_files`/`selected_directory` remain the actual
trigger mechanism for `SampleObj` construction (via `change_sample()` ->
`LameIO.initialize_sample_object()`) -- rewriting that cascade is out of
proportion to this migration, so `Project.samples` (durable, manifest source
of truth) and `AppData.sample_list` (derived, session-local UI-trigger
state) stay two separate layers that this class keeps in sync, rather than
being collapsed into one.

`close_project()` is also what `MainWindow.closeEvent()` delegates to for the
app-exit unsaved-changes prompt -- there's one dirty-check implementation,
not two.
"""
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from lame_core.config import BASEDIR
from src.app.Status import StatusMessageManager
from src.control.Logger import auto_log_methods
from src.project.ProjectModel import (
    Project, ProjectSampleEntry,
    new_project as _new_untitled_project,
    save_project as _save_project_file,
    load_project as _load_project_file,
)

PROJECT_FILE_SUFFIX = '.lame_project.json'
RECENT_PROJECTS_KEY = 'recent_projects'
MAX_RECENT_PROJECTS = 10

#: QSettings key for the autosave period, in minutes. Exposed as
#: `ProjectManager.autosave_interval_minutes` and clamped to
#: [`MIN_AUTOSAVE_MINUTES`, `MAX_AUTOSAVE_MINUTES`]; a future preferences
#: dialog only has to write this key.
AUTOSAVE_INTERVAL_KEY = 'project/autosave_interval_minutes'
DEFAULT_AUTOSAVE_MINUTES = 10
MIN_AUTOSAVE_MINUTES = 5
MAX_AUTOSAVE_MINUTES = 30

#: Name of the per-sample JSON written by the import tool (see
#: `ProjectManager.save_import_settings`).
IMPORT_SETTINGS_FILENAME = 'import_settings.json'

#: Parent of every untitled project's scratch directory, under the system
#: temp dir.
SCRATCH_ROOT_NAME = 'LaME-untitled'


def _project_dir_for_manifest(manifest_path):
    """The per-project directory for per-sample sidecars (profiles, polygons,
    Notes), derived from a manifest's own path: `<manifest's parent>/<name
    without the .lame_project.json suffix>` -- e.g.
    `projects/Foo.lame_project.json` -> `projects/Foo/`, sitting alongside
    the manifest rather than nested inside a same-named folder.
    """
    name = manifest_path.name
    if name.endswith(PROJECT_FILE_SUFFIX):
        name = name[: -len(PROJECT_FILE_SUFFIX)]
    else:
        name = manifest_path.stem
    return manifest_path.parent / name


@auto_log_methods(logger_key='Project')
class ProjectManager(QObject):
    """Owns the current session's `Project` and mediates all changes to it.

    Parameters
    ----------
    ui : MainWindow
    """
    projectChanged = pyqtSignal()
    dirtyChanged = pyqtSignal(bool)

    def __init__(self, ui):
        super().__init__(ui)
        self.logger_key = 'Project'
        self.ui = ui
        self.status_manager = StatusMessageManager(ui)
        self.current_project: Project | None = None

        # Scratch directory standing in for `project_dir` until the project is
        # saved somewhere real -- created lazily, see `scratch_dir`.
        self._scratch_dir = None

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.apply_autosave_interval()

        self.projectChanged.connect(self._update_window_title)
        self.dirtyChanged.connect(lambda _dirty: self._update_window_title())
        self._update_window_title()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def new_project(self, name=None):
        """Start a fresh, empty, in-memory project. Nothing is written to disk
        until `save_project`/`save_project_as` is called.

        If a dirty project is currently open, prompts Save/Discard/Cancel
        first; does nothing if the user cancels.
        """
        if not self.close_project():
            return
        self.current_project = _new_untitled_project(name)
        self.projectChanged.emit()
        self.dirtyChanged.emit(False)
        self.status_manager.show_message(f"New project: {self.current_project.name}")

    def open_project(self, path=None):
        """Open a project manifest, replacing whatever project is currently open.

        If a dirty project is currently open, prompts Save/Discard/Cancel
        before switching; does nothing if the user cancels.

        Parameters
        ----------
        path : str or Path, optional
            Manifest file to open. If `None`, a file dialog is shown.
        """
        if path is None:
            projects_dir = BASEDIR / "projects"
            projects_dir.mkdir(parents=True, exist_ok=True)
            file_str, _ = QFileDialog.getOpenFileName(
                self.ui, "Open Project", str(projects_dir),
                f"LaME Project (*{PROJECT_FILE_SUFFIX})"
            )
            if not file_str:
                return
            path = Path(file_str)
        else:
            path = Path(path)

        if not path.exists():
            self.status_manager.show_message(f"Project file not found: {path}")
            return

        if not self.close_project():
            return

        self.current_project = _load_project_file(path)
        self._sync_app_data_from_project()

        # Restore the linked workflow file reference, if any -- set directly
        # (not via MainWindow.set_active_workflow_file()) so this doesn't
        # itself mark the just-loaded project dirty; that method's
        # mark_dirty() call is for the user actively linking a *new*
        # workflow, not for restoring one a save already recorded.
        if self.current_project.workflow_refs:
            self.ui.app_data.active_workflow_file = self.current_project.workflow_refs[0]
            if hasattr(self.ui, 'workflow'):
                self.ui.workflow.reload_active_file()

        self._add_to_recent_projects(path)
        self.projectChanged.emit()
        self.dirtyChanged.emit(False)
        self.status_manager.show_message(f"Project loaded: {self.current_project.name}")

    def save_project(self, path=None):
        """Save the current project.

        Parameters
        ----------
        path : str or Path, optional
            Where to write the manifest. If `None`, reuses
            `current_project.manifest_path` (a normal "Save"); if that's
            also unset (an untitled project's first save), prompts for a
            location.
        """
        if self.current_project is None:
            self.status_manager.show_message("No project to save.")
            return

        if path is None:
            path = self.current_project.manifest_path
        if path is None:
            path = self._prompt_save_location()
            if path is None:
                return

        self._pull_processing_state_from_loaded_samples()

        # Project.workflow_refs mirrors the current active workflow file
        # (a list of 0 or 1 entries) -- not a history of every workflow
        # ever linked. The AppData.active_workflow_file reference pattern
        # already is the source of truth; this just captures it into the
        # manifest at save time, same as processing state above.
        self.current_project.workflow_refs = (
            [self.ui.app_data.active_workflow_file] if self.ui.app_data.active_workflow_file else []
        )

        # Write the live Notes editor to its current file *before* the scratch
        # directory is copied across below -- otherwise a save-on-switch after
        # the copy would land in the old (about to be deleted) location.
        self._flush_notes()

        _save_project_file(self.current_project, path)  # also sets current_project.manifest_path

        project_dir = self.project_dir

        # Sidecars written while the project was untitled live in the scratch
        # directory; the project now has a real home, so they move into it.
        self._migrate_scratch_dir(project_dir)
        self._save_sidecars(project_dir)

        # Point the open Notes editor at the relocated file (a no-op if it was
        # already under project_dir) *before* the scratch copy goes away --
        # the notes_file setter saves the outgoing file on the way out, and
        # that file is still the scratch one.
        self._refresh_notes_file()
        self._discard_scratch_dir()

        self._add_to_recent_projects(path)
        self.dirtyChanged.emit(False)
        self.status_manager.show_message(f"Project saved: {Path(path).name}")

    def _save_sidecars(self, project_dir):
        """Write every loaded sample's profile/polygon sidecars under `project_dir`.

        Profile/polygon geometry round-trips through its own per-sample files
        (``.prfl``/``.poly``), not the JSON manifest, so saving the project
        has to save these separately.
        """
        if project_dir is None:
            return
        for sample_id in self.ui.data:
            if hasattr(self.ui, 'profile_dock'):
                self.ui.profile_dock.profiling.save_profiles(project_dir, sample_id)
                self.ui.profile_dock.profiling.project_dir = project_dir
            if hasattr(self.ui, 'mask_dock'):
                self.ui.mask_dock.polygon_tab.polygon_manager.save_polygons(project_dir, sample_id)

    def _flush_notes(self):
        """Write the open Notes editor's content to its current file, if any."""
        if hasattr(self.ui, 'notes_dock'):
            self.ui.notes_dock.notes.save_notes_file()

    def _refresh_notes_file(self):
        """Re-point the open Notes editor at the current sample's notes file."""
        if hasattr(self.ui, 'refresh_notes_file'):
            self.ui.refresh_notes_file()

    # ------------------------------------------------------------------
    # Autosave
    # ------------------------------------------------------------------

    @property
    def autosave_interval_minutes(self):
        """int : Minutes between autosaves, from `QSettings`.

        Clamped to [`MIN_AUTOSAVE_MINUTES`, `MAX_AUTOSAVE_MINUTES`]; setting
        it stores the value and restarts the timer, so a preferences dialog
        only needs to assign to this.
        """
        settings = QSettings("Adelaide University", "LaME")
        try:
            minutes = int(settings.value(AUTOSAVE_INTERVAL_KEY, DEFAULT_AUTOSAVE_MINUTES))
        except (TypeError, ValueError):
            minutes = DEFAULT_AUTOSAVE_MINUTES
        return max(MIN_AUTOSAVE_MINUTES, min(MAX_AUTOSAVE_MINUTES, minutes))

    @autosave_interval_minutes.setter
    def autosave_interval_minutes(self, minutes):
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = DEFAULT_AUTOSAVE_MINUTES
        minutes = max(MIN_AUTOSAVE_MINUTES, min(MAX_AUTOSAVE_MINUTES, minutes))
        QSettings("Adelaide University", "LaME").setValue(AUTOSAVE_INTERVAL_KEY, minutes)
        self.apply_autosave_interval()

    def apply_autosave_interval(self):
        """(Re)start the autosave timer from the stored interval."""
        self.autosave_timer.start(self.autosave_interval_minutes * 60 * 1000)

    def autosave(self):
        """Periodically persist the project without any user interaction.

        A saved project is written back to its own manifest; an untitled one
        goes to `scratch_manifest_path`, leaving it untitled (its
        `manifest_path` stays unset and its dirty flag stands) so the user is
        still prompted for a real location on save, but nothing is lost if
        the session ends first.

        Returns
        -------
        Path or None
            The manifest written, or None if there was nothing to do.
        """
        if self.current_project is None or not self.current_project.dirty:
            return None

        self._pull_processing_state_from_loaded_samples()
        self._flush_notes()

        manifest_path = self.current_project.manifest_path
        if manifest_path is not None:
            _save_project_file(self.current_project, manifest_path)
            self.dirtyChanged.emit(False)
        else:
            manifest_path = self.scratch_manifest_path
            # update_project_state=False: an autosave into scratch must not
            # make an untitled project look saved.
            _save_project_file(self.current_project, manifest_path, update_project_state=False)

        self._save_sidecars(self.project_dir)
        self.status_manager.show_message(f"Project autosaved: {manifest_path.name}")
        return manifest_path

    def save_project_as(self):
        """Prompt for a new location and save the current project there."""
        if self.current_project is None:
            self.status_manager.show_message("No project to save.")
            return
        path = self._prompt_save_location()
        if path is None:
            return
        self.save_project(path)

    def close_project(self, prompt_if_dirty=True):
        """Close the current project, resetting to "no project open."

        This is the one dirty-check + teardown implementation `new_project()`,
        `open_project()`, the "Close Project" action, and
        `MainWindow.closeEvent()` (app exit) all route through.

        Parameters
        ----------
        prompt_if_dirty : bool, optional
            If True (default) and the current project has unsaved changes,
            ask Save/Discard/Cancel first.

        Returns
        -------
        bool
            True if the project was closed (or there was nothing to close);
            False if the user cancelled a dirty-changes prompt, in which
            case nothing was touched.
        """
        if prompt_if_dirty and not self._confirm_discard_if_dirty():
            return False

        ui = self.ui

        # ui.data is aliased (not copied) into AppData.data -- must clear
        # in place, never reassign, or the two references silently desync.
        ui.data.clear()
        if ui.app_data.sample_list:
            ui.app_data.sample_list = []

        # add_samples()-style helpers on these only ever add -- without an
        # explicit clear, closing project A and opening project B in one
        # session would leak A's profiles/polygons into B.
        if hasattr(ui, 'profile_dock'):
            ui.profile_dock.profiling.clear_all()
        if hasattr(ui, 'mask_dock'):
            ui.mask_dock.polygon_tab.polygon_manager.clear_all()

        # Don't leave the Notes editor pointed at the closed project's last
        # sample -- the setter itself handles saving/autosave-stop/None safely.
        # Turn "Record to Notes" off first (mirrors close_workflow_file's own
        # capture-off-before-file-clear ordering below), so a reopened/new
        # project doesn't inherit a still-on toggle silently recording into it.
        if getattr(ui, 'notes_capture_enabled', False):
            ui.lame_action.RecordNotesToggle.setChecked(False)
        if hasattr(ui, 'notes_dock'):
            ui.notes_dock.notes.notes_file = None
            ui._refresh_notes_indicator()

        # Detach the workflow file and stop action-capture into it.
        ui.close_workflow_file()

        # Explicit rather than relying on the sample_list=[] -> sampleChanged
        # -> change_sample() cascade to reach this: that path depends on
        # combobox widget state (whether currentText() already reads '')
        # and isn't a reliable place to hang this on.
        ui.lame_action.toggle_actions(False)

        # Nothing in the scratch directory outlives the project it belonged
        # to -- a closed untitled project's notes/sidecars were either
        # migrated by a save or deliberately discarded.
        self._discard_scratch_dir()

        self.current_project = None
        self.projectChanged.emit()
        self.dirtyChanged.emit(False)
        return True

    # ------------------------------------------------------------------
    # Dirty-check prompt
    # ------------------------------------------------------------------

    def _confirm_discard_if_dirty(self):
        """Ask Save/Discard/Cancel if the current project has unsaved changes.

        Returns
        -------
        bool
            True if it's safe to proceed (nothing dirty, user discarded, or
            user saved successfully); False if the user cancelled, or chose
            Save but the save itself was then cancelled (e.g. an untitled
            project's location prompt) -- either way nothing should proceed.
        """
        if self.current_project is None or not self.current_project.dirty:
            return True

        response = QMessageBox.question(
            self.ui, "Unsaved Changes",
            f"Project '{self.current_project.name}' has unsaved changes. Save before closing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Cancel:
            return False
        if response == QMessageBox.StandardButton.Save:
            self.save_project()
            return not self.current_project.dirty
        return True  # Discard

    def _update_window_title(self):
        if self.current_project is None:
            self.ui.setWindowTitle("LaME")
            return
        title = f"LaME - {self.current_project.name}"
        if self.current_project.dirty:
            title += " *"
        self.ui.setWindowTitle(title)

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    def mark_dirty(self, reason=''):
        """Mark the current project as having unsaved changes.

        Call only for meaningful changes (sample added, processing changed,
        notes edited) -- never incidental UI/view state -- so a session
        where the user only looked at data without modifying anything
        doesn't trigger a save prompt on close.

        Parameters
        ----------
        reason : str, optional
            Short description of what changed; not stored, just useful in
            logs (`auto_log_methods` already captures the call itself).
        """
        if self.current_project is None or self.current_project.dirty:
            return
        self.current_project.dirty = True
        self.dirtyChanged.emit(True)

    # ------------------------------------------------------------------
    # Add Samples
    # ------------------------------------------------------------------

    def add_sample_files_dialog(self):
        """Show a multi-file picker and add the selected sample files.

        Qt's native file dialogs can't mix "pick files" and "pick a
        directory" in one dialog -- this and `add_sample_directory_dialog`
        are the two entry points the File menu's "Add Sample Files..."/
        "Add Sample Directory..." actions use instead, both funneling into
        the same `add_samples()`.

        Returns
        -------
        list of str
            Sample IDs actually added (see `add_samples`); ``[]`` if
            cancelled.
        """
        files, _ = QFileDialog.getOpenFileNames(
            self.ui, "Add Sample Files", str(BASEDIR), "LaME CSV (*.csv)"
        )
        if not files:
            return []
        return self.add_samples([Path(f) for f in files])

    def add_sample_directory_dialog(self):
        """Show a directory picker and add every ``*.lame.csv`` file in it.

        Returns
        -------
        list of str
            Sample IDs actually added (see `add_samples`); ``[]`` if
            cancelled.
        """
        directory = QFileDialog.getExistingDirectory(self.ui, "Add Sample Directory", str(BASEDIR))
        if not directory:
            return []
        return self.add_samples([Path(directory)])

    def add_samples(self, paths):
        """Add samples to the current project, creating an untitled project
        first if none is open. The single underlying code path for the
        "Add Samples..." menu action; import wizards call it too once their
        output is written to disk.

        Parameters
        ----------
        paths : list of (str or Path)
            Files (``*.lame.csv``) and/or directories (scanned non-recursively
            for ``*.lame.csv``) to add.

        Returns
        -------
        list of str
            Sample IDs actually added; already-present sample IDs are
            skipped, so re-adding the same directory is a safe no-op for
            samples already in the project.
        """
        if self.current_project is None:
            self.new_project()

        file_list = []
        for p in paths:
            p = Path(p)
            if p.is_dir():
                file_list.extend(
                    f for f in p.iterdir()
                    if f.is_file() and f.name.endswith('.lame.csv')
                )
            elif p.is_file() and p.suffix == '.csv':
                file_list.append(p)

        if not file_list:
            self.status_manager.show_message("No valid *.lame.csv files found.")
            return []

        added_ids = []
        for file_path in file_list:
            file_path = file_path.resolve()
            sample_id = file_path.stem.replace('.lame', '')
            if sample_id in self.current_project.samples:
                continue
            self.current_project.samples[sample_id] = ProjectSampleEntry(sample_path=file_path)
            added_ids.append(sample_id)

        if not added_ids:
            self.status_manager.show_message("Selected sample(s) already in project.")
            return []

        self._sync_app_data_from_project()
        self.mark_dirty('samples added')
        self.status_manager.show_message(f"Added {len(added_ids)} sample(s) to project.")
        return added_ids

    def locate_missing_sample(self, sample_id, new_path):
        """Update a project sample entry's path after the user relocates a
        moved/missing raw file (the `ProjectFilesDock`'s "Locate..." action).

        Parameters
        ----------
        sample_id : str
        new_path : str or Path
        """
        if self.current_project is None or sample_id not in self.current_project.samples:
            return
        self.current_project.samples[sample_id].sample_path = Path(new_path).resolve()
        self.mark_dirty('sample relocated')
        self._sync_app_data_from_project()

    # ------------------------------------------------------------------
    # Per-sample sidecar locations (profiles/polygons/notes)
    # ------------------------------------------------------------------

    @property
    def project_dir(self):
        """Directory for this project's per-sample sidecars (profiles,
        polygons, Notes, import settings).

        Once the project has been saved this is derived from the manifest's
        own location. Before that it's the session's scratch directory (see
        `scratch_dir`) -- an untitled project still needs somewhere to put
        notes and sidecars *while* it's being worked on, and everything
        written there is moved under the real project directory on the first
        save (see `_migrate_scratch_dir`).

        Returns
        -------
        Path or None
            None only when there's no project open at all.
        """
        if self.current_project is None:
            return None
        if self.current_project.manifest_path is None:
            return self.scratch_dir
        return _project_dir_for_manifest(self.current_project.manifest_path)

    @property
    def scratch_dir(self):
        """This session's scratch directory for the current untitled project,
        created on first use under the system temp directory.

        Returns
        -------
        Path or None
            None if no project is open; otherwise a directory that exists.
        """
        if self.current_project is None:
            return None
        if self._scratch_dir is None:
            root = Path(tempfile.gettempdir()) / SCRATCH_ROOT_NAME
            root.mkdir(parents=True, exist_ok=True)
            self._scratch_dir = Path(tempfile.mkdtemp(prefix=f'{self._safe_name()}-', dir=root))
        return self._scratch_dir

    @property
    def scratch_manifest_path(self):
        """Where `autosave` writes an untitled project's manifest, so a
        session interrupted before its first real save can still be
        recovered from `scratch_dir`.
        """
        if self.current_project is None:
            return None
        return self.scratch_dir / f'{self._safe_name()}{PROJECT_FILE_SUFFIX}'

    def _safe_name(self):
        """The project name reduced to a filesystem-safe stem."""
        name = (self.current_project.name if self.current_project else '') or 'project'
        return re.sub(r'[^A-Za-z0-9._-]+', '_', name).strip('_') or 'project'

    def _discard_scratch_dir(self):
        """Forget (and delete) the current scratch directory, if any.

        Called once its contents have been migrated into a real project
        directory, and when the project it belonged to is closed.
        """
        scratch, self._scratch_dir = self._scratch_dir, None
        if scratch is not None and scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    def _migrate_scratch_dir(self, project_dir):
        """Copy everything written to the scratch directory into `project_dir`.

        Runs on the first save of a previously-untitled project: notes,
        profiles, polygons and import settings written while the project had
        no home on disk follow it to its real one. Existing files in
        `project_dir` are overwritten -- the scratch copy is the live session
        state, and this only ever runs for a project that had no directory of
        its own until now.

        The scratch manifest itself is left behind: `save_project` has
        already written the real one. The scratch directory is *not* deleted
        here -- widgets still pointing into it (the Notes editor) have to be
        moved across first; `save_project` calls `_discard_scratch_dir()`
        once they have been.
        """
        scratch = self._scratch_dir
        if scratch is None or not scratch.exists():
            return

        project_dir.mkdir(parents=True, exist_ok=True)
        for entry in scratch.iterdir():
            target = project_dir / entry.name
            if entry.is_dir():
                shutil.copytree(entry, target, dirs_exist_ok=True)
            elif entry.name.endswith(PROJECT_FILE_SUFFIX):
                continue
            else:
                shutil.copy2(entry, target)

    def notes_path_for_sample(self, sample_id):
        """Path to a sample's Notes ``.rst`` file under the current project
        directory, creating its parent directory if needed (the Notes
        widget's autosave writes there directly and doesn't create missing
        directories itself).

        Parameters
        ----------
        sample_id : str

        Returns
        -------
        Path or None
            None if there's no sample selected or no project open. An
            unsaved project resolves to its scratch directory rather than
            None, so Notes always has somewhere to write.
        """
        return self._sidecar_path(sample_id, 'notes.rst')

    def import_settings_path_for_sample(self, sample_id):
        """Path to a sample's import-settings JSON under the current project
        directory (see `save_import_settings`).

        Parameters
        ----------
        sample_id : str

        Returns
        -------
        Path or None
        """
        return self._sidecar_path(sample_id, IMPORT_SETTINGS_FILENAME)

    def _sidecar_path(self, sample_id, filename):
        """``<project_dir>/<sample_id>/<filename>``, with the parent created."""
        project_dir = self.project_dir
        if not sample_id or project_dir is None:
            return None
        path = project_dir / sample_id / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def save_import_settings(self, sample_id, settings):
        """Record the settings a sample was imported with, alongside its other
        per-sample sidecars.

        Written automatically by the import tool (`MapImporter.import_data`)
        so an import can be traced -- and repeated -- without the user having
        to remember to save the metadata table by hand. Like every other
        sidecar it lands in the scratch directory for an untitled project and
        moves under the project directory on the first save.

        Parameters
        ----------
        sample_id : str
        settings : dict
            JSON-serializable import parameters. Values that aren't (numpy
            scalars from the metadata table, `Path`s) are stringified.

        Returns
        -------
        Path or None
            Where it was written, or None if there was nowhere to write it.
        """
        path = self.import_settings_path_for_sample(sample_id)
        if path is None:
            return None
        payload = dict(settings)
        payload.setdefault('saved', datetime.now().isoformat(timespec='seconds'))
        with open(path, 'w') as f:
            json.dump(payload, f, indent=2, default=str)
        return path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pull_processing_state_from_loaded_samples(self):
        """Capture every currently-loaded sample's live filters/masks/computed
        fields into its `ProjectSampleEntry.processing` before writing the
        manifest -- `SampleObj` is the live source of truth for this state
        while a sample is loaded (`ui.data[sample_id]`); the project entry is
        only a snapshot, refreshed here at save time via
        `SampleObj.export_processing_state()`. Samples in the project that
        aren't currently loaded (e.g. never selected this session) keep
        whatever `processing` they already had.
        """
        for sample_id, entry in self.current_project.samples.items():
            sample_obj = self.ui.data.get(sample_id)
            if sample_obj is not None:
                entry.processing = sample_obj.export_processing_state()

    def _sync_app_data_from_project(self):
        """Rebuild `AppData.selected_directory`/`csv_files`/`sample_list` from
        the current project's sample entries, preserving the current
        selection if it's still present.

        `selected_directory`/`csv_files` can only reflect one directory at a
        time, so for a project spanning multiple directories they're kept
        populated as a reasonable default elsewhere in the app (e.g.
        `SavePlotDialog`'s remembered directory) rather than as the sample
        loader's source of truth -- `LameIO.initialize_sample_object()`
        resolves each sample's actual file from `ProjectSampleEntry.sample_path`
        (an absolute path) when a project entry exists, falling back to
        `selected_directory / csv_files[index]` only otherwise.
        """
        ui = self.ui
        sample_ids = list(self.current_project.samples.keys())
        if not sample_ids:
            return

        first_path = self.current_project.samples[sample_ids[0]].sample_path
        ui.app_data.selected_directory = first_path.parent
        ui.app_data.csv_files = [
            self.current_project.samples[sid].sample_path.name for sid in sample_ids
        ]

        previous_id = ui.app_data.sample_id
        ui.app_data.sample_list = sample_ids
        if previous_id and previous_id in sample_ids:
            ui.app_data.sample_id = previous_id

    def _prompt_save_location(self):
        projects_dir = BASEDIR / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        default_name = (self.current_project.name or 'project').replace(' ', '_')
        file_str, _ = QFileDialog.getSaveFileName(
            self.ui, "Save Project",
            str(projects_dir / f"{default_name}{PROJECT_FILE_SUFFIX}"),
            f"LaME Project (*{PROJECT_FILE_SUFFIX})"
        )
        if not file_str:
            return None
        path = Path(file_str)
        if not path.name.endswith(PROJECT_FILE_SUFFIX):
            path = path.with_name(path.name + PROJECT_FILE_SUFFIX)
        return path

    def recent_projects(self):
        """Paths of recently opened/saved projects, most recent first.

        Entries whose file no longer exists are silently dropped, so a
        caller (e.g. the Recent Projects submenu) can render the returned
        list directly without checking existence itself.

        Returns
        -------
        list of Path
        """
        settings = QSettings("Adelaide University", "LaME")
        raw = settings.value(RECENT_PROJECTS_KEY, [])
        if isinstance(raw, str):
            raw = [raw]
        return [p for p in (Path(s) for s in raw if s) if p.exists()]

    def _add_to_recent_projects(self, path):
        settings = QSettings("Adelaide University", "LaME")
        raw = settings.value(RECENT_PROJECTS_KEY, [])
        if isinstance(raw, str):
            raw = [raw]
        entries = [str(path)] + [s for s in raw if s != str(path)]
        settings.setValue(RECENT_PROJECTS_KEY, entries[:MAX_RECENT_PROJECTS])
