"""Classification helpers for files and folders dropped onto the app.

Kept free of widget code so the path-sorting logic is unit-testable without
a window. The GUI side (``MainWindow.dragEnterEvent``/``dropEvent`` and the
forwarding hooks in widgets that already accept drops) only converts the
``QMimeData`` URLs to paths and hands them to ``classify_dropped_paths``.
"""
from dataclasses import dataclass, field
from pathlib import Path

from src.project.ProjectManager import PROJECT_FILE_SUFFIX


@dataclass
class DropPlan:
    """What to do with a set of dropped paths.

    Attributes
    ----------
    projects : list of Path
        ``*.lame_project.json`` manifests. Only the first is opened.
    samples : list of Path
        ``*.csv`` files and directories, passed straight to
        ``ProjectManager.add_samples`` (which does the ``*.lame.csv`` scan
        and reports an empty directory itself).
    rejected : list of Path
        Anything else, including paths that no longer exist.
    """
    projects: list = field(default_factory=list)
    samples: list = field(default_factory=list)
    rejected: list = field(default_factory=list)

    @property
    def is_empty(self):
        return not (self.projects or self.samples)


def classify_dropped_paths(paths):
    """Sort dropped paths into projects, sample candidates and rejects.

    Parameters
    ----------
    paths : iterable of (str or Path)

    Returns
    -------
    DropPlan
    """
    plan = DropPlan()
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            plan.samples.append(p)
        elif p.is_file() and p.name.endswith(PROJECT_FILE_SUFFIX):
            plan.projects.append(p)
        elif p.is_file() and p.suffix.lower() == '.csv':
            plan.samples.append(p)
        else:
            plan.rejected.append(p)
    return plan


def urls_to_local_paths(mime_data):
    """Local file paths carried by a drag's ``QMimeData``; empty if none.

    Parameters
    ----------
    mime_data : QMimeData
    """
    if mime_data is None or not mime_data.hasUrls():
        return []
    paths = []
    for url in mime_data.urls():
        if url.isLocalFile():
            local = url.toLocalFile()
            if local:
                paths.append(Path(local))
    return paths


def mime_has_droppable_files(mime_data):
    """True if the drag carries at least one path the app would act on.

    Used by ``dragEnterEvent`` so the "copy" cursor only appears for drops
    that would do something.
    """
    paths = urls_to_local_paths(mime_data)
    return bool(paths) and not classify_dropped_paths(paths).is_empty


# ----------------------------------------------------------------------
# Forwarding hooks for widgets that accept drops for their own purposes
# ----------------------------------------------------------------------

def _drop_target_window(widget):
    """The ancestor main window that implements ``handle_dropped_paths``,
    or None. Walks ``parentWidget()`` so floating docks (their own
    top-level windows) still resolve to the main window they belong to."""
    w = widget
    while w is not None:
        if hasattr(w, 'handle_dropped_paths') and hasattr(w, 'dragEnterEvent'):
            return w
        w = w.parentWidget()
    return None


def forward_file_drag(widget, event):
    """Route a drag-enter/move carrying file URLs to the main window.

    Returns
    -------
    bool
        True if the event was a file drag and has been handled (accepted or
        ignored) here; False if the caller should run its own logic.
    """
    if not event.mimeData().hasUrls():
        return False
    win = _drop_target_window(widget)
    if win is None:
        return False
    if mime_has_droppable_files(event.mimeData()):
        event.acceptProposedAction()
    else:
        event.ignore()
    return True


def forward_file_drop(widget, event):
    """Route a drop carrying file URLs to the main window's ``dropEvent``.

    Returns
    -------
    bool
        True if the event was a file drop and has been handled here.
    """
    if not event.mimeData().hasUrls():
        return False
    win = _drop_target_window(widget)
    if win is None:
        return False
    win.dropEvent(event)
    return True
