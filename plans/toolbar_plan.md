I have an alternate suggestion for the Ribbon-style toolbars


What I actually want is something with a **fixed, bounded footprint** (so nothing jumps around) that **doesn't try to fill dead space** (so an underpopulated group doesn't look broken, unlike a sparse ribbon group). That's a **paged toolbar**: includes pinned actions that never changes, plus one content row whose contents swap based on a page selector — think ribbon *tabs*, but only one row of content ever, sized to exactly what that page needs.

## Proposed structure

**Page selector** (small tab-like text buttons, exclusive/checkable, horizontal layout):

`Home | Plot | Processing | Log | Analysis`

**Pinned set (always visible, never swaps):**
- Sample selector (combobox)
- Analytes
- Update Plot
- Save Project
- Record indicator (visible only when a workflow is open — this is the persistence requirement from our Capture discussion, and it belongs here specifically because it needs to stay visible regardless of what page is showing)

This is the right pinned set because these are the only things you're touching *continuously* regardless of what task you're doing — everything else is task-scoped.



**Content row, swapped per page:**

| Page | Contents |
|---|---|
| Home | Add Samples (files or directory — see below), Import Files, Open Project, Help, Theme |
| Plot | Add Plot to Tree, Full Map, Crop, Swap Axes, quick plot-type buttons (optional, can grow later) |
| Processing | Noise Reduction, Filters toggle, Filter (elemental) toggle, Polygons, Clusters |
| Log | Notes, Workflow Tool, Snapshot |
| Analysis | Calculator, Geochronology, Profile, Diffusion |

A few specific calls within that:

- **Drop "Add sample directory" as its own action** - A single `QFileDialog` in `ExistingFiles` mode with multi-select covers the individual-files case, and you can add a small dropdown arrow on the same button (`MenuButtonPopup`) offering "Add Directory..." as the secondary option, so it's one visual slot instead of two.
- Report Bug → Help menu, Reset → File or Edit menu.

## Implementation sketch

No custom ribbon framework needed — a `QStackedWidget` for the content row, driven by an exclusive button group for the page selector.  Build the general capability in ../lame-core (so it can be used elsewhere like CustomWidgets.py) with LaME specific pages and actions src/app/MainToolbar.py:

```python
class PagedToolBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(2)

        # Row 1: pinned actions (built by caller via self.pinned_bar)
        self.pinned_bar = QToolBar()
        self.pinned_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        outer.addWidget(self.pinned_bar)

        # Row 1b: page tabs
        self.page_bar = QToolBar()
        self._page_group = QButtonGroup(self)
        self._page_group.setExclusive(True)
        outer.addWidget(self.page_bar)

        # Row 2: swappable page content, fixed height
        self.pages = QStackedWidget()
        self.pages.setFixedHeight(36)
        outer.addWidget(self.pages)

    def add_page(self, name: str, page_widget: QWidget) -> None:
        idx = self.pages.addWidget(page_widget)
        btn = QToolButton(text=name, checkable=True, autoRaise=True)
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(idx))
        self._page_group.addButton(btn)
        self.page_bar.addWidget(btn)
        if idx == 0:
            btn.setChecked(True)
```

Each page widget is just a plain `QToolBar` or an `QHBoxLayout` of `QToolButton`s built with `setDefaultAction()`, exactly like the stacks from our earlier conversation — so everything still routes through the same `QAction` objects your menus use, no dual state.

One refinements worth building in from the start:

- Auto advance to `Plot` when a project is loaded.
