from PyQt6.QtWidgets import (
    QWidget, QLineEdit, QToolButton, QHBoxLayout, QMessageBox, QLabel, QTextEdit
)
from PyQt6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QTextDocument, QAction
)
from PyQt6.QtCore import Qt
import re

class SearchWidget(QWidget):
    def __init__(self, text_edit, parent=None, enable_replace=True, realtime=False):
        super().__init__(parent)
        self.text_edit = text_edit
        self.realtime = realtime
        self.match_positions = []
        self.current_index = -1
        self.enable_replace = enable_replace

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        layout.addWidget(self.search_input)

        self.toggle_replace_button = QToolButton()
        self.toggle_replace_button.setText("⤵︎")
        self.toggle_replace_button.setToolTip("Show/hide replace options")
        self.toggle_replace_button.setCheckable(True)
        layout.addWidget(self.toggle_replace_button)

        if self.enable_replace and self.text_edit.isReadOnly() == False:
            self.replace_input = QLineEdit()
            self.replace_input.setPlaceholderText("Replace with...")
            layout.addWidget(self.replace_input)

            self.replace_button = QToolButton()
            self.replace_button.setText("Current")
            self.replace_button.setToolTip("Replace current match")
            layout.addWidget(self.replace_button)

            self.replace_all_button = QToolButton()
            self.replace_all_button.setText("All")
            self.replace_all_button.setToolTip("Replace all matches")
            layout.addWidget(self.replace_all_button)
        else:
            self.replace_input = None

        self.case_button = QToolButton()
        self.case_button.setText("Aa")
        self.case_button.setCheckable(True)
        self.case_button.setToolTip("Toggle case sensitivity")
        layout.addWidget(self.case_button)

        self.regex_button = QToolButton()
        self.regex_button.setText(".*")
        self.regex_button.setCheckable(True)
        self.regex_button.setToolTip("Regex search")
        layout.addWidget(self.regex_button)

        self.prev_button = QToolButton()
        self.prev_button.setText("↑")
        self.prev_button.setToolTip("Previous match")
        layout.addWidget(self.prev_button)

        self.next_button = QToolButton()
        self.next_button.setText("↓")
        self.next_button.setToolTip("Next match")
        layout.addWidget(self.next_button)
        
        self.match_label = QLabel("0 / 0")
        self.match_label.setMinimumWidth(60)
        layout.addWidget(self.match_label)

        self.clear_button = QToolButton()
        self.clear_button.setText("✖")
        self.clear_button.setToolTip("Clear search")
        layout.addWidget(self.clear_button)

        self.setLayout(layout)

        if self.replace_input:
            self.replace_input.setVisible(False)
            self.replace_button.setVisible(False)
            self.replace_all_button.setVisible(False)
            self.toggle_replace_button.setChecked(False)

    def _connect_signals(self):
        if self.realtime:
            self.search_input.textChanged.connect(self.highlight_matches)
        else:
            self.search_input.returnPressed.connect(self.highlight_matches)

        self.toggle_replace_button.clicked.connect(self.toggle_replace_fields)

        self.case_button.clicked.connect(self.highlight_matches)
        self.regex_button.clicked.connect(self.highlight_matches)
        self.clear_button.clicked.connect(self.clear_search)
        self.prev_button.clicked.connect(lambda: self.navigate_match(False))
        self.next_button.clicked.connect(lambda: self.navigate_match(True))

        if self.replace_input:
            self.replace_button.clicked.connect(self.replace_current)
            self.replace_all_button.clicked.connect(self.replace_all)

    def toggle_replace_fields(self):
        visible = self.toggle_replace_button.isChecked()

        if self.replace_input:
            self.replace_input.setVisible(visible)
            self.replace_button.setVisible(visible)
            self.replace_all_button.setVisible(visible)

    def highlight_matches(self):
        query = self.search_input.text()
        self.match_positions = []
        self.current_index = -1

        # Clear formatting
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        fmt_clear = QTextCharFormat()
        cursor.setCharFormat(fmt_clear)
        self.text_edit.setExtraSelections([])

        if not query:
            self.total_matches = 0
            self.current_index = -1
            self.update_match_label()
            return

        # Create search flags
        case_sensitive = self.case_button.isChecked()
        use_regex = self.regex_button.isChecked()

        text = self.text_edit.toPlainText()

        try:
            if use_regex:
                pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
                self.matches = list(pattern.finditer(text))
                self.match_positions = [m.start() for m in self.matches]
                match_lengths = [m.end() - m.start() for m in self.matches]
                self.match_lengths = match_lengths
            else:
                self.match_positions = []
                match_lengths = []
                self.matches = []

                i = 0
                search_text = text if case_sensitive else text.lower()
                query_text = query if case_sensitive else query.lower()

                while i < len(search_text):
                    index = search_text.find(query_text, i)
                    if index == -1:
                        break
                    self.match_positions.append(index)
                    match_lengths.append(len(query))
                    self.match_lengths = match_lengths

                    self.matches.append((index, len(query)))
                    i = index + len(query)
        except re.error as e:
            QMessageBox.warning(self, "Regex Error", f"Invalid regex pattern:\n{e}")
            return

        self.total_matches = len(self.matches)
        self.current_index = 0 if self.matches else -1
        self.update_match_label()

        # Apply highlight
        for i, pos in enumerate(self.match_positions):
            cursor = self.text_edit.textCursor()
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, match_lengths[i])
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("yellow"))
            fmt.setForeground(QColor("black"))
            cursor.mergeCharFormat(fmt)

        # Highlight current match
        if self.match_positions:
            self.current_index = 0
            self.select_current(match_lengths[self.current_index])

    def select_current(self, length):
        cursor = self.text_edit.textCursor()
        pos = self.match_positions[self.current_index]
        cursor.setPosition(pos)
        cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, length)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

        # Apply cyan highlight for current
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format.setBackground(QColor("cyan"))
        selection.format.setForeground(QColor("black"))
        self.text_edit.setExtraSelections([selection])

    def update_match_label(self):
        if self.total_matches == 0:
            self.match_label.setText("0 / 0")
        else:
            self.match_label.setText(f"{self.current_index + 1} / {self.total_matches}")

    def navigate_match(self, forward=True):
        print("Current index:", self.current_index)
        print("Total matches:", len(self.match_positions))

        if not self.match_positions:
            return
        if forward:
            self.current_index = (self.current_index + 1) % len(self.match_positions)
        else:
            self.current_index = (self.current_index - 1 + len(self.match_positions)) % len(self.match_positions)

        self.update_match_label()  # ← missing?
        match_length = self.match_lengths[self.current_index]
        self.select_current(match_length)

    def clear_search(self):
        self.search_input.setText("")
        if self.replace_input:
            self.replace_input.setText("")
        self.text_edit.setExtraSelections([])
        self.match_positions = []
        self.current_index = -1

        # Clear any residual formatting
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.setPosition(0)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.setCharFormat(QTextCharFormat())

    def replace_current(self):
        if self.current_index < 0 or not self.replace_input:
            return

        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return

        replacement = self.replace_input.text()

        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()

        self.highlight_matches()

    def replace_all(self):
        if not self.match_positions or not self.replace_input:
            return

        replacement = self.replace_input.text()
        query = self.search_input.text()
        case_sensitive = self.case_button.isChecked()
        text = self.text_edit.toPlainText()

        self.text_edit.selectAll()
        self.text_edit.textCursor().beginEditBlock()

        try:
            if self.regex_button.isChecked():
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(query, flags)
                new_text = pattern.sub(replacement, text)
            else:
                if not case_sensitive:
                    pattern = re.compile(re.escape(query), re.IGNORECASE)
                    new_text = pattern.sub(replacement, text)
                else:
                    new_text = text.replace(query, replacement)

            self.text_edit.setPlainText(new_text)

        except re.error as e:
            QMessageBox.warning(self, "Regex Error", f"Invalid regex pattern:\n{e}")
            return

        self.text_edit.textCursor().endEditBlock()
        self.highlight_matches()


