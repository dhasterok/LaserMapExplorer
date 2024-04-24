import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag


class DraggableButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text())
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)


class DropZone(QWidget):
    def __init__(self):
        super().__init__()

        layout = QGridLayout()
        self.setLayout(layout)

        self.buttons = []

        for i in range(3):
            for j in range(3):
                button = DraggableButton(f"Button {i},{j}")
                layout.addWidget(button, i, j)
                self.buttons.append(button)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            source_text = event.mimeData().text()
            source_button = event.source()
            target_button = self.childAt(event.pos())
            if isinstance(target_button, QPushButton):
                target_text = target_button.text()
                source_button.setText(target_text)
                target_button.setText(source_text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Drag and Drop Example")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = DropZone()
        self.setCentralWidget(self.central_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
