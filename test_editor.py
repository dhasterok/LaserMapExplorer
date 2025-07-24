import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QMenu, QToolBar
)
from PyQt6.QtGui import QAction, QFont, QColor, QTextCursor, QKeyEvent
from PyQt6.QtCore import Qt
from src.common.CodingWidgets import CodeEditor, RstHighlighter, RST_HIGHLIGHT_RULES, HighlightRulesDialog, EditorSettingsDialog, CodeEditorMenu, CodeEditorToolbar
import re

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RST Highlighter Debugger")

        self.editor = CodeEditor()
        #self.highlighter = RstHighlighter(self.editor.document(), self.rules)

        menu_bar = self.menuBar()
        toolbar = QToolBar(self)

        file_menu = QMenu("File", self)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.load_file_dialog)
        file_menu.addAction(open_action)

        menu_bar.addMenu(file_menu)

        CodeEditorMenu(self.editor, menu_bar)
        CodeEditorToolbar(self.editor, toolbar)

        container = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(toolbar)
        layout.addWidget(self.editor)
        container.setLayout(layout)
        self.setCentralWidget(container)


        preload_file = "docs/source/left_toolbox.rst"  # Adjust path as needed
        try:
            with open(preload_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.editor.setPlainText(content)
        except FileNotFoundError:
            self.editor.setPlainText("test.rst not found.\nStart typing or open a file.")

    def load_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open ReStructuredText File",
            "",
            "ReStructuredText Files (*.rst *.txt);;All Files (*)"
        )
        if file_name:
            with open(file_name, 'r', encoding='utf-8') as f:
                content = f.read()
                self.editor.setPlainText(content)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(800, 600)
    win.show()
    sys.exit(app.exec())