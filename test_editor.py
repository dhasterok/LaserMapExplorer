import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QDialogButtonBox,
    QWidget, QDialog, QFormLayout, QLineEdit, QColorDialog, QMessageBox,
    QPushButton, QListWidget, QLabel, QComboBox, QCheckBox, QFontComboBox
)
from PyQt6.QtGui import QAction, QFont, QColor
from PyQt6.QtCore import Qt
from src.common.CodingWidgets import CodeEditor, RstHighlighter, HighlightRule, AYU_LIGHT_THEME, FONT_WEIGHT_MAP, RST_HIGHLIGHT_RULES
import re

class RuleEditorDialog(QDialog):
    def __init__(self, rules, parent=None):
        super().__init__(parent)
        self.rules = rules
        self.setWindowTitle("Edit Highlight Rules")
        self.layout = QHBoxLayout(self)
        self.scheme = AYU_LIGHT_THEME
        self.rule_list = QListWidget()
        for rule in self.rules:
            self.rule_list.addItem(rule.name)

        self.form = QFormLayout()
        self.name_edit = QLineEdit()
        self.pattern_edit = QLineEdit()
        self.color_label = QLabel()
        self.bg_color_label = QLabel()
        self.family_combo = QFontComboBox()
        if rule.font_family:
            self.family_combo.setCurrentFont(QFont(rule.font_family))
        self.style_combo = QComboBox()
        self.style_combo.clear()
        self.style_combo.addItem("italic")
        self.style_combo.addItems(list(FONT_WEIGHT_MAP.keys()))
        self.style_combo.setCurrentText("normal")
        self.underline_checkbox = QCheckBox()
        self.underline_checkbox.setChecked(False)
        self.group_edit = QLineEdit()
        self.trigger_edit = QLineEdit()
        self.block_edit = QLineEdit()

        self.color_button = QPushButton("Change Color")
        self.color_button.clicked.connect(self.choose_color)

        self.bg_color_button = QPushButton("Change Background Color")
        self.bg_color_button.clicked.connect(self.choose_color)

        self.form.addRow("Name", self.name_edit)
        self.form.addRow("Pattern", self.pattern_edit)
        self.form.addRow("Color", self.color_button)
        self.form.addRow("Background Color", self.bg_color_button)
        self.form.addRow("Font Family", self.family_combo)
        self.form.addRow("Font Style", self.style_combo)
        self.form.addRow("Underline", self.underline_checkbox)
        self.form.addRow("Group", self.group_edit)
        self.form.addRow("Trigger", self.trigger_edit)
        self.form.addRow("Context", self.block_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.save_rule)
        self.button_box.rejected.connect(self.reject)

        right_layout = QVBoxLayout()
        right_layout.addLayout(self.form)
        right_layout.addWidget(self.save_button)

        self.layout.addWidget(self.rule_list)
        self.layout.addLayout(right_layout)

        self.rule_list.currentRowChanged.connect(self.load_rule)
        self.current_rule_index = 0
        self.load_rule(0)

    def load_rule(self, index):
        self.current_rule_index = index
        rule = self.rules[index]
        self.name_edit.setText(rule.name)
        self.pattern_edit.setText(rule.pattern)
        if rule.color:
            self.color_button.setText(rule.color)
            self.color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {rule.color};" )
        else:
            self.color_button.setText("None")
            self.color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {self.scheme['text']};" )
        if rule.background:
            self.bg_color_button.setText(rule.background)
            self.bg_color_button.setStyleSheet( f"background-color: {rule.background}; color: {self.scheme['text']};" )
        else:
            self.bg_color_button.setText("None")
            self.bg_color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {self.scheme['text']};" )
        self.family_combo.setCurrentText(rule.font_family or "")
        self.style_combo.setCurrentText(rule.style or "")
        self.underline_checkbox.setChecked(rule.underline)
        self.group_edit.setText(str(rule.group))
        self.trigger_edit.setText(str(rule.context_trigger))
        self.block_edit.setText(str(rule.context_apply))

    def choose_text_color(self):
        color = self.choose_color()
        if color.isValid():
            self.color_button.setText(color.name())
            self.color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {color.name()};" )

    def choose_bg_color(self):
        color = self.choose_color()
        if color.isValid():
            self.bg_color_button.setText(color.name())
            self.bg_color_button.setStyleSheet( f"background-color: {color.name()}; color: {self.scheme['text']};" )

    def choose_color(self):
        color = QColorDialog.getColor()
        return color

    def save_rule(self):
        name = self.name_edit.text().strip()

        # Check for valid regex first
        pattern = self.pattern_edit.text()
        try:
            re.compile(pattern)
        except re.error as e:
            QMessageBox.warning(self, "Invalid Regex", f"The regex pattern is invalid:\n\n{e}")
            return  # Do not proceed with saving

        # Check if we're editing an existing rule or adding a new one
        existing_names = [r.name for r in self.rules]
        is_new = name not in existing_names

        if is_new:
            rule = HighlightRule(name=name, pattern=pattern)
            self.rules.append(rule)
            self.current_rule_index = len(self.rules) - 1
        else:
            rule = self.rules[self.current_rule_index]
            rule.name = name
            rule.pattern = pattern

        # Update remaining rule attributes
        rule.color = self.color_button.text() or None
        rule.background = self.bg_color_button.text() or None
        rule.font_family = self.family_combo.currentFont().family() or None
        rule.style = self.style_combo.currentText() or None
        rule.underline = self.underline_checkbox.isChecked()
        rule.group = int(self.group_edit.text() or 0)
        rule.context_trigger = self.trigger_edit.text()
        rule.context_apply = self.block_edit.text()

        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RST Highlighter Debugger")

        # Sample rules
        self.rules = RST_HIGHLIGHT_RULES

        self.editor = CodeEditor()
        self.highlighter = RstHighlighter(self.editor.document(), self.rules)

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        container.setLayout(layout)
        self.setCentralWidget(container)

        menubar = self.menuBar()
        edit_menu = menubar.addMenu("Edit")
        rule_action = QAction("Edit Rules", self)
        rule_action.triggered.connect(self.open_rule_editor)
        edit_menu.addAction(rule_action)

    def open_rule_editor(self):
        dialog = RuleEditorDialog(self.rules, self)
        if dialog.exec():
            self.highlighter.rehighlight()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(800, 600)
    win.show()
    sys.exit(app.exec())