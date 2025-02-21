
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import ( QTableWidget, QTableWidgetItem, QCheckBox, QAbstractItemView  )
from PyQt6.QtGui import ( QDropEvent )
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

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

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
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()

        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (int(self.model().flags(index)) & Qt.ItemIsDropEnabled) and pos.y() >= rect.center().y()
