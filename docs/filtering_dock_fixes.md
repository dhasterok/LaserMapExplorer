# Filtering Dock — Bug Fixes (2026-03-26)

## Background

The Tools > Filtering dock (accessible via the Tools menu or the filter toolbar button) was completely non-functional. Clicking the button crashed the application before any UI appeared. This document describes every bug found and fixed during the debugging session, in the order they were encountered.

---

## Bug 1 — Crash on open: `AttributeError: property 'data' of 'MaskDock' object has no setter`

**File:** `src/common/Masking.py`
**Triggered at:** `MaskDock.__init__` → `FieldLogicUI.__init__` → `self.data = data`

### What happened

`MaskDock` uses multiple inheritance:

```python
class MaskDock(CustomDockWidget, FieldLogicUI):
```

Python's MRO (Method Resolution Order) for this class is:

```
MaskDock → CustomDockWidget → FieldLogicUI → QDockWidget → ...
```

When `MaskDock.__init__` calls `super().__init__(ui)`, it chains into `CustomDockWidget.__init__`, which in turn calls `super().__init__(parent=parent)`. Because `FieldLogicUI` is the next class in the MRO after `CustomDockWidget`, this cooperative `super()` chain ends up calling `FieldLogicUI.__init__`, which does:

```python
def __init__(self, data=None):
    self.data = data   # <-- crashes here
```

`MaskDock` already defined a read-only `@property` called `data`:

```python
@property
def data(self):
    if hasattr(self.ui, 'app_data') and self.ui.app_data.current_data:
        return self.ui.app_data.current_data
    return None
```

This property has a getter but no setter. Python does not permit assignment to a property with no setter — `self.data = data` raised `AttributeError` immediately.

An earlier attempt at a fix removed an **explicit** `FieldLogicUI.__init__(self, data=None)` call that had been placed in `MaskDock.__init__`, but the crash persisted because the call was still happening **implicitly** through the cooperative `super()` chain in `CustomDockWidget`.

### Fix

Added a no-op `data.setter` to `MaskDock`:

```python
@data.setter
def data(self, value):
    """Ignored — data is always derived from self.ui.app_data.current_data"""
    pass
```

The setter exists solely to satisfy Python's property protocol when `FieldLogicUI.__init__` tries to assign `self.data = None`. It discards the value. The getter is unchanged and always returns the live value from `self.ui.app_data.current_data`.

**Why a no-op setter is correct here:** `MaskDock` intentionally computes `data` dynamically. Storing a direct reference to the data object would create a stale-reference bug (the reference would go out of date when the user loads a new sample) and also potentially create circular reference issues. The setter discards the assignment so the property continues to reflect live state.

---

## Bug 2 — Dock opens empty: `AttributeError: 'MaskDock' object has no attribute 'app_data'`

**File:** `src/common/Masking.py`
**Triggered at:** `FilterTab.initialize_combo_boxes` → `FieldLogicUI.update_field_combobox` → `self.app_data.get_field_list(...)`

### What happened

After Bug 1 was fixed the dock opened, but was completely empty — no combo boxes populated, no fields shown. The error occurred during `FilterTab.__init__` while initialising the field type and field combo boxes.

`FieldLogicUI` is a mixin designed to be used by classes that have `self.app_data` as a direct attribute. For example, `MainWindow` sets this up in its own `__init__`:

```python
self.app_data = AppData(parent=self)
```

Every method in `FieldLogicUI` that queries field lists, field types, or sample data references `self.app_data` directly. For instance:

```python
def update_field_combobox(self, parentBox, childBox):
    if self.data is None:
        return
    fields = self.app_data.get_field_list(parentBox.currentText())  # <-- self.app_data
    childBox.clear()
    childBox.addItems(fields)
```

`MaskDock` does not own an `AppData` instance. It accesses app data through its parent window: `self.ui.app_data`. When `FilterTab.initialize_combo_boxes` called `self.dock.update_field_combobox(...)` (where `self.dock` is the `MaskDock` instance), Python looked for `app_data` on `MaskDock` and found nothing.

### Fix

Added an `app_data` property to `MaskDock` that transparently delegates to `self.ui.app_data`:

```python
@property
def app_data(self):
    """Delegate to ui.app_data so FieldLogicUI methods work correctly"""
    return self.ui.app_data
```

**Why this is correct:** `MaskDock` is a dock widget owned by `MainWindow`. It should never hold its own `AppData` instance — that would duplicate state and create synchronisation problems. The property is a thin proxy that satisfies `FieldLogicUI`'s expectation of `self.app_data` while keeping a single source of truth in `MainWindow`.

---

## Bug 3 — Crash when selecting preset: `TypeError: FilterTab.read_filter_table() takes 1 positional argument but 2 were given`

**File:** `src/common/Masking.py`
**Triggered at:** `combo_filter_presets.activated` signal → `read_filter_table`

### What happened

After the dock opened and populated successfully, selecting any item from the filter preset combo box crashed immediately. The error also triggered on first open because setting the current index of `combo_filter_presets` inside `load_filter_tables` fires the `activated` signal.

The combo box was connected like this:

```python
self.combo_filter_presets.activated.connect(self.read_filter_table)
```

`QComboBox.activated` is a signal that emits the **selected index** (an `int`) to its connected slot. The `read_filter_table` method has this signature:

```python
def read_filter_table(self):
    filter_name = self.combo_filter_presets.currentText()
    ...
```

It takes no arguments beyond `self`. When `activated` fired with an index like `1`, Python tried to call `read_filter_table(1)`, which the method signature didn't accept, raising `TypeError`.

### Fix

Wrapped the connection in a lambda to absorb and discard the emitted index:

```python
self.combo_filter_presets.activated.connect(lambda _: self.read_filter_table())
```

**Why the index can be discarded:** `read_filter_table` already reads the selected preset name directly from `self.combo_filter_presets.currentText()`. The index emitted by `activated` is redundant — the method doesn't need it.

---

## Bug 4 — Remove button had no effect (silent failure)

**File:** `src/common/Masking.py`
**Method:** `FilterTab.remove_selected_rows`

### What happened

Selecting rows in the filter table and clicking the remove button appeared to do nothing. No rows were ever deleted, no error was raised. The failure was silent.

The method iterated over table rows and checked column 7 to decide what to remove:

```python
print(self.filter_table.selectedIndexes())  # debug leftover

for row in range(self.filter_table.rowCount()-1, -1, -1):
    chkBoxItem = self.filter_table.item(row, 7)
    if chkBoxItem and chkBoxItem.checkState() == Qt.CheckState.Checked:
        filter_index = row
        indices_to_remove.append(filter_index)
        self.filter_table.removeRow(row)
```

Column 7 ("Persistent") is populated using `setCellWidget`:

```python
chkBoxItem_persistent = QCheckBox()
self.filter_table.setCellWidget(current_row, 7, chkBoxItem_persistent)
```

`QTableWidget.item(row, col)` only returns a `QTableWidgetItem` object — it only works for cells populated with `setItem()`. For cells populated with `setCellWidget()`, `item()` always returns `None`. The condition `if chkBoxItem and ...` was therefore always `False`, and the loop body never executed.

Even if this were fixed by using `cellWidget(row, 7)` instead, the logic was still wrong conceptually: it was checking whether the **persistent checkbox** was ticked to decide what to delete, rather than checking which rows the user had **selected** in the table.

There was also a leftover debug `print` statement that printed the raw selected indexes to the terminal on every remove attempt.

### Fix

Replaced the broken loop with the table's selection model, which is the correct API for identifying user-selected rows:

```python
selected_rows = sorted(
    {idx.row() for idx in self.filter_table.selectionModel().selectedRows()},
    reverse=True
)

indices_to_remove = []
for row in selected_rows:
    indices_to_remove.append(row)
    self.filter_table.removeRow(row)
```

Rows are sorted in **descending order** so that removing a row does not shift the indices of rows that still need to be processed. The debug `print` was also removed.

**Why `selectedRows()` is correct:** The table's `SelectionBehavior` is set to `SelectRows`, which means the user always selects entire rows. `selectionModel().selectedRows()` returns exactly those rows, regardless of whether cells contain items or widgets.

---

## Bug 5 — Status bar toggle button would crash: `AttributeError: 'MainWindow' object has no attribute 'toolButtonBottomDock'`

**File:** `src/app/MainWindow.py`
**Triggered at:** clicking the bottom dock toggle button in the status bar

### What happened

This bug did not crash on dock open — it would only crash later, when the user clicked the bottom dock toggle button in the status bar to hide/show the masking toolbox.

Inside `open_mask_dock`, the button was connected as follows:

```python
self.statusbar.toolButtonBottomDock.clicked.connect(
    lambda: self.toggle_dock_visibility(dock=self.mask_dock, button=self.toolButtonBottomDock)
)
```

The signal source — `self.statusbar.toolButtonBottomDock.clicked` — was correct. The button lives on the `LameStatusBar` instance at `self.statusbar`. However, inside the lambda, the `button=` argument passed `self.toolButtonBottomDock`, which references an attribute on `MainWindow` itself. `MainWindow` has no such attribute; `toolButtonBottomDock` only exists on `self.statusbar`. When the lambda executed, Python could not find the attribute and raised `AttributeError`.

The same bug existed one line above for `toolButtonRightDock` and the plot tree dock:

```python
# Line 1031 — same pattern
self.statusbar.toolButtonRightDock.clicked.connect(
    lambda: self.toggle_dock_visibility(dock=self.plot_tree, button=self.toolButtonRightDock)
)
```

### Fix

Changed the lambda to reference the attribute through `self.statusbar`:

```python
self.statusbar.toolButtonBottomDock.clicked.connect(
    lambda: self.toggle_dock_visibility(dock=self.mask_dock, button=self.statusbar.toolButtonBottomDock)
)
```

---

## Bug 6 — Qt warning: double layout on `QGroupBox`

**File:** `src/common/Masking.py`
**Symptom:** Not a crash, but every dock open printed `QLayout: Attempting to add QLayout "" to QGroupBox "", which already has a layout` to the log.

### What happened

In `FilterTab.setup_ui`, the filter settings groupbox was set up like this:

```python
self.filter_tools_groupbox = QGroupBox(self)
group_layout = QVBoxLayout(self.filter_tools_groupbox)   # (A) installs layout on groupbox
self.filter_tools_groupbox.setLayout(group_layout)       # (B) redundant, same layout

filter_layout = QGridLayout(self.filter_tools_groupbox)  # (C) tries to install a second layout
group_layout.addLayout(filter_layout)                    # (D) also adds it as child of group_layout
```

Passing a widget as the first argument to a `QLayout` constructor automatically installs that layout as the widget's **top-level layout**. Line (A) already installed `group_layout` on `filter_tools_groupbox`. Line (B) called `setLayout` again with the same layout — redundant but harmless.

Line (C) was the problem: `QGridLayout(self.filter_tools_groupbox)` attempted to install `filter_layout` as a **second** top-level layout on the same groupbox. Qt rejected this and emitted the warning. The `filter_layout` then ended up correctly nested inside `group_layout` via line (D) anyway — so the visual result was correct — but Qt still emitted the warning every time.

### Fix

Removed the parent-widget argument from the `QGridLayout` constructor so it is created as an unowned layout and only attached to the widget hierarchy through `group_layout.addLayout`:

```python
filter_layout = QGridLayout()          # no parent — just a plain layout
filter_layout.setContentsMargins(3, 3, 3, 3)
group_layout.addLayout(filter_layout)  # nested inside group_layout as intended
```

---

## Summary

| # | File | Line(s) | Severity | Description |
|---|------|---------|----------|-------------|
| 1 | `src/common/Masking.py` | ~126 | **Critical** | Added `data.setter` (no-op) to `MaskDock` — MRO-driven `FieldLogicUI.__init__` assigns `self.data = None` against a read-only property |
| 2 | `src/common/Masking.py` | ~121 | **Critical** | Added `app_data` property to `MaskDock` delegating to `self.ui.app_data` — `FieldLogicUI` methods expect `self.app_data` to exist |
| 3 | `src/common/Masking.py` | ~468 | **High** | `combo_filter_presets.activated` emits an int index; wrapped connection in `lambda _:` to discard it |
| 4 | `src/common/Masking.py` | ~662 | **High** | `remove_selected_rows` checked `.item(row, 7)` on a `setCellWidget` cell (always `None`); replaced with `selectionModel().selectedRows()`; removed debug `print` |
| 5 | `src/app/MainWindow.py` | ~1117 | **Medium** | `self.toolButtonBottomDock` → `self.statusbar.toolButtonBottomDock` in the dock toggle lambda |
| 6 | `src/common/Masking.py` | ~259 | **Low** | `QGridLayout(self.filter_tools_groupbox)` tried to install a second top-level layout on the groupbox; removed parent argument |
