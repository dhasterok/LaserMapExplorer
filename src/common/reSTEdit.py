import sys
from PyQt6.QtWidgets import QApplication
from src.common.reSTNotes import NotesMainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = NotesMainWindow()
    win.resize(800, 600)
    win.show()
    sys.exit(app.exec())