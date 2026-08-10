"""Project Files dock -- a tree of the samples in the current project, with
per-sample link/calibration/processing/notes status.

Follows `MaskDock`'s registered-dock-area pattern (`src/data/Masking.py`)
rather than the floating-panel pattern used by `GeochronDock`/`DiffusionDock`,
since this is meant to sit alongside the app's other permanent docks. Tree
built with `lame_core.CustomWidgets.CustomTreeView` + `QStandardItemModel`
(the only existing tree-dock precedent in this codebase, `src/tree/PlotTree.py`).

No icon-per-row asset pipeline exists anywhere in this codebase today (no
`.setIcon(` outside toolbar/menu actions) -- status is shown via item text
(a bracketed tag, using plain Unicode glyphs, not image icons) plus text
color and a tooltip with full detail, matching that convention rather than
introducing a new one.
"""
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QDockWidget, QToolBar, QMenu, QMainWindow, QFileDialog, QMessageBox

from lame_core.CustomWidgets import CustomDockWidget, CustomTreeView, CustomAction
from lame_core.UITheme import default_font

from src.control.Logger import auto_log_methods
from src.project.ProjectModel import is_calibration_stale

_WARNING_COLOR = QColor(200, 120, 0)
_ERROR_COLOR = QColor(200, 0, 0)


@auto_log_methods(logger_key='ProjectFiles')
class ProjectFilesDock(CustomDockWidget):
    """Tree of the current project's samples with status indicators.

    Parameters
    ----------
    ui : MainWindow
    """
    def __init__(self, ui=None):
        self.logger_key = 'ProjectFiles'

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(ui)
        self.ui = ui

        self.setObjectName("ProjectFilesDock")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setFloating(False)
        self.setWindowTitle("Project Files")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint
        )

        self.ui.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self)

        self.setup_ui()
        self.connect_signals()
        self.refresh()

    def setup_ui(self):
        font = default_font()
        self.setFont(font)
        self.setMinimumSize(QSize(256, 276))

        container = QWidget()
        container.setObjectName("ProjectFilesDockContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setWidget(container)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        layout.addWidget(toolbar)

        self.action_refresh = CustomAction(
            text="Refresh",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self,
        )
        self.action_refresh.setObjectName("actionProjectFilesRefresh")
        self.action_refresh.setToolTip("Refresh link/calibration/processing status")
        toolbar.addAction(self.action_refresh)

        self.treeView = CustomTreeView(parent=self)
        self.treeView.setFont(font)
        self.treeView.setObjectName("treeViewProjectFiles")
        self.treeView.setHeaderHidden(True)
        layout.addWidget(self.treeView)

    def connect_signals(self):
        self.action_refresh.triggered.connect(self.refresh)
        self.treeView.doubleClicked.connect(self.on_double_click)
        self.treeView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.show_context_menu)

        pm = self.ui.project_manager
        pm.projectChanged.connect(self.refresh)
        pm.dirtyChanged.connect(lambda _dirty: self.refresh())

    def refresh(self):
        """Rebuild the tree from the current project, one branch per sample."""
        # Deliberately not CustomTreeView.clear_tree() (== treeModel.clear()):
        # QStandardItemModel.clear() invalidates the cached root_node
        # reference (confirmed empirically -- the old root item's rowCount()
        # returns garbage afterward), and CustomTreeView doesn't refresh
        # root_node when clear_tree() is called. No existing caller in this
        # codebase does a full clear+rebuild (PlotTree only ever adds
        # incrementally), so this is untested territory in the shared
        # widget -- removeRows() on the existing root item sidesteps it
        # entirely rather than depending on/patching the shared library.
        root = self.treeView.root_node
        root.removeRows(0, root.rowCount())

        project = self.ui.project_manager.current_project
        if project is None:
            return

        for sample_id, entry in project.samples.items():
            self._add_sample_branch(sample_id, entry)

        self.treeView.expandAll()

    def _add_sample_branch(self, sample_id, entry):
        treeView = self.treeView
        raw_path = Path(entry.sample_path)
        linked = raw_path.exists()

        # "moved" vs "never existed" aren't distinguishable from sample_path
        # alone -- both surface as "missing" here, with the same Locate...
        # remedy, which is the actionable requirement either way.
        link_tag = "✓ linked" if linked else "⚠ missing"
        branch = treeView.add_branch(treeView.root_node, f"{sample_id}  [{link_tag}]", data=sample_id)
        if not linked:
            branch.setForeground(QBrush(_ERROR_COLOR))

        tooltip_lines = [f"Path: {raw_path}"]
        if not linked:
            tooltip_lines.append("Raw file not found -- right-click to Locate...")

        # ---- calibration ----
        if entry.calibration is None:
            cal_text = "calibration: none"
        elif linked and is_calibration_stale(entry.calibration, raw_path):
            cal_text = f"calibration: ⚠ stale (calibrated {entry.calibration.calibrated_at.date()})"
        else:
            cal_text = f"calibration: ✓ {entry.calibration.calibrated_at.date()}"
        cal_leaf = treeView.add_leaf(branch, cal_text)
        if entry.calibration is not None and '⚠' in cal_text:
            cal_leaf.setForeground(QBrush(_WARNING_COLOR))

        # ---- processing (filters/masks/computed fields) ----
        # Prefer the live SampleObj's current state if this sample is loaded
        # this session -- more up to date than the last-saved entry.processing
        # snapshot for a sample that's been edited but not yet saved.
        loaded_sample = self.ui.data.get(sample_id)
        processing = loaded_sample.export_processing_state() if loaded_sample is not None else entry.processing

        parts = []
        if processing.applied_filters:
            n = len(processing.applied_filters)
            parts.append(f"{n} filter{'s' if n != 1 else ''}")
        if processing.masks:
            n = len(processing.masks)
            parts.append(f"{n} mask{'s' if n != 1 else ''}")
        if processing.computed_fields:
            n = len(processing.computed_fields)
            parts.append(f"{n} computed field{'s' if n != 1 else ''}")
        proc_text = "processing: " + (", ".join(parts) if parts else "none")
        treeView.add_leaf(branch, proc_text)

        # ---- notes ----
        # Existence-check only (no parent-dir creation) -- unlike
        # ProjectManager.notes_path_for_sample(), status display shouldn't
        # have the side effect of creating a directory for a sample that
        # has never actually had notes written.
        notes_path = self.ui.project_manager.project_dir / sample_id / "notes.rst" \
            if self.ui.project_manager.project_dir else None
        treeView.add_leaf(branch, "notes: present" if notes_path and notes_path.exists() else "notes: none")

        branch.setToolTip("\n".join(tooltip_lines))

    def on_double_click(self, index):
        """Selecting a sample's top-level branch loads it (drives the
        existing change_sample() cascade); leaves do nothing.
        """
        item = self.treeView.treeModel.itemFromIndex(index)
        if len(self.treeView.get_item_path(item)) != 1:
            return
        sample_id = item.data()
        if sample_id:
            self.ui.app_data.sample_id = sample_id
            self.ui.change_sample()

    def show_context_menu(self, pos):
        index = self.treeView.indexAt(pos)
        if not index.isValid():
            return
        item = self.treeView.treeModel.itemFromIndex(index)
        if len(self.treeView.get_item_path(item)) != 1:
            return
        sample_id = item.data()
        if not sample_id:
            return

        menu = QMenu(self.treeView)
        action_locate = menu.addAction("Locate...")
        action_notes = menu.addAction("Open Notes")
        action_remove = menu.addAction("Remove from Project")
        chosen = menu.exec(self.treeView.viewport().mapToGlobal(pos))
        if chosen is action_locate:
            self._locate_sample(sample_id)
        elif chosen is action_notes:
            self.ui.app_data.sample_id = sample_id
            self.ui.change_sample()
            self.ui.open_notes()
        elif chosen is action_remove:
            self._remove_sample(sample_id)

    def _locate_sample(self, sample_id):
        file_str, _ = QFileDialog.getOpenFileName(self.ui, f"Locate {sample_id}", "", "LaME CSV (*.csv)")
        if not file_str:
            return
        self.ui.project_manager.locate_missing_sample(sample_id, file_str)
        self.refresh()

    def _remove_sample(self, sample_id):
        project = self.ui.project_manager.current_project
        if project is None or sample_id not in project.samples:
            return
        response = QMessageBox.question(
            self.ui, "Remove from Project",
            f"Remove '{sample_id}' from the current project? The raw data file is not affected.",
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        del project.samples[sample_id]
        self.ui.data.pop(sample_id, None)
        self.ui.project_manager.mark_dirty('sample removed')
        self.refresh()
