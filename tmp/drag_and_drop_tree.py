import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QFileSystemModel, QGridLayout, QLabel, QWidget
from PyQt5.QtCore import Qt, QPoint, QMimeData
from PyQt5.QtGui import QPixmap


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Drag and Drop Example")
        self.setGeometry(100, 100, 800, 600)

        self.tree_view = QTreeView()
        self.tree_model = QFileSystemModel()
        self.tree_model.setRootPath("")
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.setDragEnabled(True)
        self.tree_view.viewport().setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)

        self.grid_layout = QGridLayout()
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.grid_layout)
        self.setCentralWidget(self.central_widget)

        self.central_widget.layout().addWidget(self.tree_view, 0, 0, 1, 1)

        self.tree_view.selectionModel().selectionChanged.connect(self.handle_selection_change)

    def handle_selection_change(self, selected, deselected):
        if selected.indexes():
            selected_file_path = self.tree_model.filePath(selected.indexes()[0])
            pixmap = QPixmap(selected_file_path)
            if not pixmap.isNull():
                self.create_draggable_label(pixmap)

    def create_draggable_label(self, pixmap):
        label = QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        label.setFixedSize(100, 100)  # Adjust the size as needed
        label.setAcceptDrops(True)
        label.mousePressEvent = self.mouse_press_event
        self.grid_layout.addWidget(label)

    def mouse_press_event(self, event):
        if event.buttons() == Qt.LeftButton:
            label = event.widget()
            if label is not None:
                mime_data = QMimeData()
                drag = QPixmap(label.pixmap())
                mime_data.setImageData(drag)
                drag = drag.scaled(100, 100)
                drag.hotSpot = QPoint(50, 50)
                drag_label = QLabel(label.text(), self)
                drag_label.setPixmap(drag)
                drag_label.move(event.globalPos())
                drag_label.show()
                drag_label.dragged = True
                drag_label.show()
                drag_label.exec_(Qt.CopyAction | Qt.MoveAction)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
