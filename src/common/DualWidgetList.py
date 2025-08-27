from PyQt6.QtWidgets import (
    QWidget, QListWidget, QToolButton, QVBoxLayout, QSizePolicy,
    QHBoxLayout, QApplication, QListWidgetItem, QSpacerItem
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
import sys


class DualListWidget(QWidget):
    movedRight = pyqtSignal(list)   # emits items moved to right
    movedLeft = pyqtSignal(list)    # emits items moved back to left

    def __init__(self, parent=None):
        super().__init__(parent)

        # Left (available) and right (selected) lists
        self.left_list = QListWidget()
        self.right_list = QListWidget()

        self.left_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.right_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

        # Tool buttons for moving items
        self.to_right_btn = QToolButton()
        self.to_right_btn.setFixedSize(QSize(24,24))
        self.to_right_btn.setText("→")
        self.to_right_btn.setToolTip("Move selected from to right to left")
        self.to_left_btn = QToolButton()
        self.to_left_btn.setFixedSize(QSize(24,24))
        self.to_left_btn.setText("←")
        self.to_right_btn.setToolTip("Move selected from to left to right")
        self.to_right_all_btn = QToolButton()
        self.to_right_all_btn.setFixedSize(QSize(24,24))
        self.to_right_all_btn.setText("⇒")
        self.to_right_all_btn.setToolTip("Move all to right")
        self.to_left_all_btn = QToolButton()
        self.to_left_all_btn.setFixedSize(QSize(24,24))
        self.to_left_all_btn.setText("⇐")
        self.to_left_all_btn.setToolTip("Move all to left")

        # Layout for buttons
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.to_right_btn)
        btn_layout.addWidget(self.to_left_btn)
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_layout.addItem(spacer)
        btn_layout.addWidget(self.to_right_all_btn)
        btn_layout.addWidget(self.to_left_all_btn)
        btn_layout.addStretch()

        # Main layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.left_list)
        layout.addLayout(btn_layout)
        layout.addWidget(self.right_list)

        # Connect signals
        self.to_right_btn.clicked.connect(self.move_selected_to_right)
        self.to_left_btn.clicked.connect(self.move_selected_to_left)
        self.to_right_all_btn.clicked.connect(self.move_all_to_right)
        self.to_left_all_btn.clicked.connect(self.move_all_to_left)

    def set_available_items(self, items):
        """Replace items on the left list."""
        self.left_list.clear()
        self.left_list.addItems(items)

    def set_selected_items(self, items):
        """Replace items on the right list."""
        self.right_list.clear()
        self.right_list.addItems(items)

    # ------------------------------------------------------------------
    # Move logic
    # ------------------------------------------------------------------
    def move_selected_to_right(self):
        """Move selected items from left to right."""
        items = [item.text() for item in self.left_list.selectedItems()]
        for item in self.left_list.selectedItems():
            self.left_list.takeItem(self.left_list.row(item))
            self.right_list.addItem(item.text())
        if items:
            self.movedRight.emit(items)

    def move_selected_to_left(self):
        """Move selected items from right to left."""
        items = [item.text() for item in self.right_list.selectedItems()]
        for item in self.right_list.selectedItems():
            self.right_list.takeItem(self.right_list.row(item))
            self.left_list.addItem(item.text())
        if items:
            self.movedLeft.emit(items)

    def move_all_to_right(self):
        """Move all items from left to right."""
        items = self.available_items()
        for i in range(self.left_list.count()):
            self.right_list.addItem(self.left_list.item(i).text())
        self.left_list.clear()
        if items:
            self.movedRight.emit(items)

    def move_all_to_left(self):
        """Move all items from right to left."""
        items = self.selected_items()
        for i in range(self.right_list.count()):
            self.left_list.addItem(self.right_list.item(i).text())
        self.right_list.clear()
        if items:
            self.movedLeft.emit(items)

    def available_items(self):
        return [self.left_list.item(i).text() for i in range(self.left_list.count())]

    def selected_items(self):
        return [self.right_list.item(i).text() for i in range(self.right_list.count())]

# Demo
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DualListWidget()
    w.set_available_items(["Apple", "Cherry", "Fig", "Date", "Banana", "Grape"])
    w.resize(500, 300)
    w.show()
    sys.exit(app.exec())