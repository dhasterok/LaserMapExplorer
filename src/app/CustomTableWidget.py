
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import ( QTableWidget, QTableWidgetItem, QCheckBox, QAbstractItemView  )
from PyQt6.QtGui import ( QDropEvent )
from lame_core.CustomWidgets import CustomTableWidget

# TableWidgetDragRows
# -------------------------------
class TableWidgetDragRows(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dropEvent(self, event: QDropEvent):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = []
            for row_index in rows:
                row_data = []
                for column_index in range(self.columnCount()):
                    item = self.item(row_index, column_index)
                    if item:
                        row_data.append(QTableWidgetItem(item))
                    else:
                        widget = self.cellWidget(row_index, column_index)
                        if isinstance(widget, QCheckBox):
                            state = widget.isChecked()
                            row_data.append(state)
                        else:
                            row_data.append(None)
                rows_to_move.append(row_data)
            
            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):
                row_pos = row_index + drop_row
                self.insertRow(row_pos)
                for column_index, value in enumerate(data):
                    if isinstance(value, QTableWidgetItem):
                        self.setItem(row_pos, column_index, value)
                    elif isinstance(value, bool):  # It's a checkbox state
                        checkbox = QCheckBox()
                        checkbox.setChecked(value)
                        self.setCellWidget(row_pos, column_index, checkbox)
            event.accept()
            #select the chosen row
            self.select_rows(drop_row, len(rows_to_move))
        super().dropEvent(event)
    
    def select_rows(self, start_row, num_rows):
        for row in range(start_row, start_row + num_rows):
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item:
                    item.setSelected(True)

    def drop_on(self, event):
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        if not index.isValid():
            return self.rowCount()

        return index.row() + 1 if self.is_below(pos, index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (int(self.model().flags(index)) & Qt.ItemIsDropEnabled) and pos.y() >= rect.center().y()


# compute_row_reorder
# -------------------------------
def compute_row_reorder(row_count, source_rows, target_row):
    """Computes the row-index permutation for a (possibly multi-row) row move.

    Parameters
    ----------
    row_count : int
        Total number of rows in the table before the move.
    source_rows : list of int
        Row indices being moved (need not be contiguous), in any order.
    target_row : int
        Row index to insert the moved rows before (in the *original*
        indexing, i.e. as returned by a drop-position calculation such as
        ``TableWidgetDragRows.drop_on``). May equal ``row_count`` to mean
        "insert at the end".

    Returns
    -------
    list of int
        Permutation of ``range(row_count)``: ``new_order[i]`` is the old row
        index that should occupy new row ``i``. Suitable for
        ``df.iloc[new_order]`` or ``[old_list[i] for i in new_order]``.
    """
    source_set = set(source_rows)
    moved = sorted(source_rows)
    remaining = [i for i in range(row_count) if i not in source_set]

    # shift target_row left by however many moved rows sat ahead of it
    insert_at = target_row - sum(1 for r in moved if r < target_row)
    insert_at = max(0, min(insert_at, len(remaining)))

    return remaining[:insert_at] + moved + remaining[insert_at:]


# ReorderableTableWidget
# -------------------------------
class ReorderableTableWidget(CustomTableWidget):
    """``CustomTableWidget`` that supports dragging one or more selected rows
    to reorder them, without moving any row content itself.

    Qt's built-in "InternalMove" drag/drop (and the item-shuffling approach
    in ``TableWidgetDragRows`` above) only relocates ``QTableWidgetItem``s --
    any cell populated via ``setCellWidget`` (e.g. a ``QCheckBox``) is left
    behind, and row-index-capturing signal closures on those widgets go
    stale. To avoid that class of bug, this widget only detects the drag
    gesture and reports it via ``rowsMoved`` -- the owner is expected to
    reorder its own backing data (see ``compute_row_reorder``) and fully
    rebuild the table in response, the same pattern already used for
    ``filter_table``'s ``reload=True`` path and ``roi_table``.
    """
    rowsMoved = pyqtSignal(list, int)  # (source_rows, target_row)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dropEvent(self, event: QDropEvent):
        if event.source() is not self:
            event.ignore()
            return

        selection_model = self.selectionModel()
        source_rows = sorted(set(index.row() for index in selection_model.selectedRows())) if selection_model else []
        if not source_rows:
            event.ignore()
            return

        target_row = self._drop_row(event)

        event.accept()
        self.rowsMoved.emit(source_rows, target_row)

    def _drop_row(self, event):
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        if not index.isValid():
            return self.rowCount()

        rect = self.visualRect(index)
        return index.row() + 1 if pos.y() >= rect.center().y() else index.row()
