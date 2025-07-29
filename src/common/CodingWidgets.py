import re, json
from pathlib import Path
from typing import Callable
from dataclasses import dataclass
from PyQt6.QtWidgets import ( 
        QWidget, QDialog, QDialogButtonBox, QPlainTextEdit, QTextEdit, QCheckBox, QPushButton,
        QVBoxLayout, QHBoxLayout, QColorDialog, QFormLayout, QLineEdit, QMessageBox, QListWidget,
        QLabel, QComboBox, QCheckBox, QFontComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QMenu, QMenuBar, QToolBar, QToolTip, QSlider
    )
from PyQt6.QtGui import (
    QFont, QCursor, QPainter, QTextCursor, QKeyEvent, QAction, QIcon, QTextBlockUserData,
    QColor, QTextFormat, QTextCharFormat, QSyntaxHighlighter
)
from PyQt6.QtCore import Qt, QRect, QSize
from src.common.reSTRules import *

#from pygments import lex
#from pygments.token import Token
#from pygments.lexers.markup import MarkdownLexer
#from pygments.lexers.python import Python3Lexer
def default_font():
    # set default font for application
    font = QFont()
    font.setPointSize(11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferDefault)

    return font

BASE_PATH = Path(__file__).parents[2] 
ICON_PATH = BASE_PATH / "resources/icons"

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        # set font to monospaced
        self.setFont(QFont("Monaco", 10))

        self.lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        # for syntax hints
        self.hover_regions = []
        self.setMouseTracking(True)

        self.updateLineNumberAreaWidth(0)

        self._highlight_line = True

        self.highlightCurrentLine()

        # auto format settings
        self.default_settings = {
            'auto_heading': {'phrase': "Auto complete heading", 'enabled': True},
            'tab_indent': {'phrase': "Convert tabs to spaces", 'enabled': True},
            'quick_indent': {'phrase': "Shortcut indenting (Ctrl/⌘ + <, >)", 'enabled': True},
            'block_indent': {'phrase': "Auto indent blocks", 'enabled': True},
            'auto_list': {'phrase': "Auto bullet and numbering", 'enabled': True},
        }
        # Make a working copy so defaults aren't overwritten
        self.settings = {
            key: value.copy() for key, value in self.default_settings.items()
        }

        # Allows for tabs to be included in the editor
        self.setTabChangesFocus(False)

        # Sample rules
        self.rules = RST_HIGHLIGHT_RULES
        self.highlighter = RstHighlighter(self, True, self.rules)

    @property
    def highlight_line(self):
        return self._highlight_line
    
    @highlight_line.setter
    def highlight_line(self, new_state):
        if not isinstance(new_state, bool):
            raise TypeError("Highlight line should be a bool.")
        self._highlight_line = new_state
        self.highlightCurrentLine()

    def keyPressEvent(self, event: QKeyEvent):
        cursor = self.textCursor()

        # Handle heading underline auto-complete
        if (
            self.settings['auto_heading']['enabled']
            and event.key() == Qt.Key.Key_Tab
            and not event.modifiers()
        ):
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            current_line = cursor.selectedText()

            match = re.match(r'^([=\-+~#\*])\1{2,}$', current_line)
            if match:
                self.repeat_heading_char(match.group(1))
                return

        if self.settings['block_indent']['enabled']:
            ctrl_or_cmd = event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
            if ctrl_or_cmd:
                key = event.key()
            
                # Indent (Ctrl+.)
                if key == Qt.Key.Key_Period:  # '>' is shift+period
                    self._indent_selection()
                    return
                # Un-indent (Ctrl+,)
                elif key == Qt.Key.Key_Comma:  # '<' is shift+comma
                    self._unindent_selection()
                    return

        if self.settings['tab_indent']['enabled']:
            if event.key() == Qt.Key.Key_Tab and not event.modifiers():
                self.textCursor().insertText(" " * 4)
            elif event.key() == Qt.Key.Key_Backtab:
                cursor = self.textCursor()
                cursor.movePosition(
                    QTextCursor.MoveOperation.StartOfBlock,
                    QTextCursor.MoveMode.KeepAnchor
                )
                selected = cursor.selectedText()
                if selected.startswith("    "):
                    cursor.removeSelectedText()
                    cursor.insertText(selected[4:])

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
            current_line = cursor.selectedText()

            # Get leading whitespace
            indent_match = re.match(r'^([ \t]*)', current_line)
            leading_ws = indent_match.group(1).replace('\t', '    ') if indent_match else ''

            next_prefix = ''
            is_list = False
            if self.settings['auto_list']['enabled']: 
                # Detect unordered bullet
                bullet_match = re.match(r'^([ \t]*)([-*+#])(\.|\s+)(.*)', current_line)
                # Detect ordered list: numeric or lettered
                enum_match = re.match(r'^([ \t]*)([0-9]+|[a-zA-Z])(\.)(\s+)(.*)', current_line)

                if bullet_match and bullet_match.group(4).strip():
                    is_list = True
                    indent = bullet_match.group(1)
                    bullet = bullet_match.group(2)
                    sep = bullet_match.group(3)
                    # repeat the bullet with same separator and indentation
                    next_prefix = f"{bullet}{sep}"
                elif enum_match and enum_match.group(5).strip():
                    is_list = True
                    indent = enum_match.group(1)
                    enum = enum_match.group(2)
                    punct = enum_match.group(3)
                    space = enum_match.group(4)

                    if enum.isdigit():
                        next_enum = str(int(enum) + 1)
                    elif len(enum) == 1 and enum.isalpha():
                        if enum.islower():
                            next_enum = chr(((ord(enum) - ord('a') + 1) % 26) + ord('a'))
                        else:
                            next_enum = chr(((ord(enum) - ord('A') + 1) % 26) + ord('A'))
                    else:
                        next_enum = enum  # fallback

                    next_prefix = f"{indent}{next_enum}{punct}{space}"

                if is_list:
                    self.insertPlainText(next_prefix) 

            # Insert newline and prefix
            if self.settings['block_indent']['enabled'] and not is_list:
                self.insertPlainText(leading_ws)

        super().keyPressEvent(event)

    def _indent_selection(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        
        cursor.beginEditBlock()

        cursor.setPosition(start)
        while cursor.position() < end:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.insertText("    ")  # 4 spaces indent
            cursor.movePosition(QTextCursor.MoveOperation.Down)
            end += 4  # Adjust end position as we added chars

        cursor.endEditBlock()


    def _unindent_selection(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.beginEditBlock()

        cursor.setPosition(start)
        while cursor.position() < end:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            line_text = cursor.selectedText()

            # Remove up to 4 leading spaces or one tab
            new_line = line_text
            if new_line.startswith("    "):
                new_line = new_line[4:]
            elif new_line.startswith("\t"):
                new_line = new_line[1:]

            if new_line != line_text:
                cursor.insertText(new_line)

                # Adjust end position because line got shorter
                end -= (len(line_text) - len(new_line))

            cursor.movePosition(QTextCursor.MoveOperation.Down)

        cursor.endEditBlock()

    def repeat_heading_char(self, char):
        cursor = self.textCursor()

        # Move to the previous line and get the line's text
        cursor.movePosition(QTextCursor.MoveOperation.Up)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        prev_line = cursor.selectedText()
        underline = char * len(prev_line)

        # Move back down and select just the current line's text (not the newline)
        cursor.movePosition(QTextCursor.MoveOperation.Down)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)

        # Replace only the text on this line, leaving the line itself and its newline intact
        cursor.setCharFormat(QTextCharFormat())  # Reset format
        cursor.insertText(underline)  # No newline here

        self.setTextCursor(cursor)

    def lineNumberAreaWidth(self):
        digits = len(str(max(1, self.blockCount())))
        space = 6 + self.fontMetrics().horizontalAdvance('9') * digits
        return max(space, 30)

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#e0e0e0"))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(Qt.GlobalColor.darkGray)
                painter.drawText(
                    0, top, self.lineNumberArea.width() - 4, self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []

        if self.highlight_line:
            if not self.isReadOnly():
                selection = QTextEdit.ExtraSelection()

                lineColor = QColor("#edeff1")

                selection.format.setBackground(lineColor)
                selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
                selection.cursor = self.textCursor()
                selection.cursor.clearSelection()
                extraSelections.append(selection)

        self.setExtraSelections(extraSelections)
    
    def update_font_size(self, new_size):
        font = self.font()
        font.setPointSize(new_size)

        self.setFont(font)

    def open_settings_dialog(self):
        dialog = EditorSettingsDialog(
            settings=self.settings,
            default_settings=self.default_settings,
            parent=self
        )
        if dialog.exec():
            print("Updated settings:", self.settings)

    def setHighlighter(self, highlighter):
        self.highlighter = highlighter

    def toggle_highlighter(self, enable):
        if hasattr(self, "highlighter"):
            self.highlighter.enable_highlighting = enable
            self.highlighter.rehighlight()
        # if hasattr(self, "highlighter") and self.highlighter:
        #     self.highlighter.setDocument(self.document() if enable else None)

    def open_highlight_dialog(self):
        if hasattr(self, "highlighter") and self.highlighter:
            self.highlighter.open_highlight_dialog()

    def save_all_settings(self):
        with open("editor.json", "w") as f:
            json.dump({
                'editor_settings': self.settings
            }, f, indent=2)
        with open("highlight_rules.json","w") as f:
            json.dump({
                'highlight_rules': self.rules
            }, f, indent=2)

    def load_all_settings(self):
        settings_path = Path("all_settings.json")
        editor_path = Path("editor.json")
        highlight_path = Path("highlight_rules.json")

        if settings_path.exists():
            if editor_path.exists():
                with editor_path.open("r") as f:
                    data = json.load(f)
                    self.settings.update(data.get('editor_settings', {}))
            if highlight_path.exists():
                with highlight_path.open("r") as f:
                    data = json.load(f)
                    self.rules.update(data.get('highlight_rules', {}))

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        block = cursor.block()
        pos_in_block = cursor.position() - block.position()
        data = block.userData()

        if isinstance(data, RstBlockData):
            for start, end, hover_text in data.hover_regions:
                if start <= pos_in_block <= end:
                    QToolTip.showText(event.globalPosition().toPoint(), hover_text, self)
                    break
            else:
                QToolTip.hideText()
        else:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

def save_highlight_rules(rules, filepath):
    """_summary_

    _extended_summary_

    Parameters
    ----------
    rules : _type_
        _description_
    filepath : _type_
        _description_

    Example
    --------

    .. code-block:: python

        highlight_rules = load_highlight_rules("highlight_rules.json")
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in rules], f, indent=2)

def load_highlight_rules(filepath):
    """Load highlighting rules.

    Parameters
    ----------
    filepath : path
        _description_

    Returns
    -------
    dict
        Highlight rules

    Example
    -------

    .. code-block:: python

        from pathlib import Path

        config_path = Path.home() / ".myapp" / "highlight_rules.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        save_highlight_rules(AYU_RST_HIGHLIGHT_RULES, config_path)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [HighlightRule.from_dict(d) for d in data]

class RstBlockData(QTextBlockUserData):
    def __init__(self):
        super().__init__()
        self.block_type = None
        self.active_directive = None
        self.hover_regions = []  # [(start, end, hover_text)]

class RstHighlighter(QSyntaxHighlighter):
    def __init__(self, editor, enable, rules=None):
        super().__init__(editor.document())
        self.editor = editor

        if rules:
            self.rules = rules
        else:
            self.rules = RST_HIGHLIGHT_RULES  # From your definition

        self.enable_highlighting = enable

        # Map of HighlightRule.name -> QTextCharFormat
        self.formats = self._build_formats(self.rules)

    def _build_formats(self, rules):
        formats = {}
        for rule in rules:
            fmt = QTextCharFormat()
            if rule.foreground:
                fmt.setForeground(QColor(rule.foreground))
            if rule.background:
                fmt.setBackground(QColor(rule.background))
            if rule.font_family:
                fmt.setFontFamily(rule.font_family)
            if rule.font_weight:
                fmt.setFontWeight(FONT_WEIGHT_MAP.get(rule.font_weight.lower(), QFont.Weight.Normal))
            if rule.font_italic:
                fmt.setFontItalic(True)
            if rule.underline:
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
            formats[rule.name] = fmt
        return formats

    def _default_format(self):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(LIGHT_THEME['text']))
        font = QFont()
        font.setFamily("Monaco")
        font.setPointSize(10)
        fmt.setFont(font)
        fmt.setFontItalic(False)
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
        return fmt

    def highlightBlock(self, text: str):
        block_data = RstBlockData()

        self.setCurrentBlockState(-1)
        current_priority = -1

        # Step 1a: Try to identify the starting block type
        for btype, rules in sorted(RST_BLOCK_TYPES.items(), key=lambda x: -x[1]['priority']):
            if btype == "definition_list":
                continue
            start_pattern = rules["start"]
            if start_pattern and start_pattern.match(text):
                priority = rules["priority"]
                if priority > current_priority:
                    current_priority = priority
                    block_data.block_type = btype

        #print(f"Line: {text.strip()} | BlockType: {block_data.block_type} | Priority: {current_priority}")

        # Step 1b: If no block type is identified, check definition
        # definition lists require special handling because they can only be
        # identified retrospectively as they otherwise appear as a paragraph
        # unless the line below is indented.
        if block_data.block_type is None and self.currentBlock().next().isValid():
            btype = "definition_list"
            rules = RST_BLOCK_TYPES['definition_list']
            next_text = self.currentBlock().next().text()
            start_pattern = rules['start']
            line_pattern = rules['line']
            if start_pattern and start_pattern.match(text) and line_pattern and line_pattern.match(next_text):
                priority = rules["priority"]
                if priority > current_priority:
                    current_priority = priority
                    block_data.block_type = btype

        # Step 2: If no block start, try to continue previous block
        prev_state = self.previousBlockState()
        if block_data.block_type is None and prev_state != -1:
            #print(f"The current block type is {block_data.block_type}")
            for btype, rules in RST_BLOCK_TYPES.items():
                if rules["priority"] == prev_state:
                    line_pattern = rules.get("line")
                    #print(f"Block type: {btype}, Line test: {line_pattern}, Text: {text}")
                    if line_pattern and line_pattern.match(text):
                        block_data.block_type = btype
                        current_priority = rules["priority"]
                        self.setCurrentBlockState(current_priority)  # <- Set state again here
                        #print(f"PrevState: {prev_state}, Continuing as: {block_data.block_type}")
                        break

        if block_data.block_type:
            self.setCurrentBlockState(current_priority)
        else:
            # Possibly a continuation of a directive block
            prev_data = self.currentBlock().previous().userData()
            if isinstance(prev_data, RstBlockData) and prev_data.block_type == "directive":
                if text.strip().startswith(":") or text.startswith("  "):  # looks like an option or continuation
                    block_data.block_type = "directive"
                    block_data.active_directive = prev_data.active_directive
                    self.setCurrentBlockState(RST_BLOCK_TYPES["directive"]["priority"])

        # Walk backwards to find active directive if still None
        if block_data.block_type == "directive" and not block_data.active_directive:
            block = self.currentBlock().previous()
            while block.isValid():
                data = block.userData()
                if isinstance(data, RstBlockData) and data.active_directive:
                    block_data.active_directive = data.active_directive
                    break
                block = block.previous()

        # Step 3: Apply block-specific highlighting
        if block_data.block_type and block_data.block_type in RST_BLOCK_RULES:
            for rule in RST_BLOCK_RULES[block_data.block_type]:
                if len(rule) == 3:
                    pattern, fmt_name, group = rule
                    #print(f"Using {block_data.block_type} group {group} rule")
                else:
                    pattern, fmt_name = rule
                    group = 0  # Default to the whole match if no group specified

                if fmt_name in self.formats:
                    for match in pattern.finditer(text):
                        try:
                            start, end = match.span(group)
                            matched_text = text[start:end]

                            isinvalid, hover_text = self.validate_match(fmt_name, matched_text, block_data)

                            #print(f"Applying {fmt_name} group {group} start: {start} length: {end - start} text: {text[start:end]!r}")
                            if self.enable_highlighting:
                                fmt = QTextCharFormat(self.formats[fmt_name])
                            else:
                                fmt = self._default_format()

                            if isinvalid:
                                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DashUnderline)
                                fmt.setUnderlineColor(QColor(LIGHT_THEME["error"]))

                                # Add to hover regions
                                block_data.hover_regions.append((start, end, hover_text))

                            self.setFormat(start, end - start, fmt)
                        except IndexError:
                            continue  # Group didn't exist in match, skip

        # Step 4: Apply global and body rules if not literal or comment
        if block_data.block_type not in ("literal_block", "comment"):
            for pattern, fmt_name, group in RST_BLOCK_RULES.get("global", []):
                if fmt_name in self.formats:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        #print(f"Applying {fmt_name} start: {start} length: {end-start} text: {text[start:end]!r}")

                        if self.enable_highlighting:
                            fmt = QTextCharFormat(self.formats[fmt_name])
                        else:
                            fmt = self._default_format()
                        self.setFormat(start, end-start, fmt)

            # for pattern, fmt_name in RST_BLOCK_RULES.get("body", []):
            #     if fmt_name in self.formats:
            #         for match in pattern.finditer(text):
            #             start, end = match.span()
            #             self.setFormat(start, end-start, self.formats[fmt_name])

        # # Step 5: Check syntax
        # if btype == "directive": 
        #     directive_name = group.strip().split("::")[0].replace("..", "").strip()
        #     if directive_name not in RST_KNOWN_DIRECTIVES:
        #         self.setFormat(start, end - start, self.invalid_directive_format)

            active_directive = None
        if block_data.block_type == "directive":
            print(f"[{self.currentBlock().blockNumber()}] {text.strip()} → type={block_data.block_type}, active={block_data.active_directive}")
        self.setCurrentBlockUserData(block_data)

    def validate_match(self, fmt_name: str, matched_text: str, block_data: RstBlockData):
        """Determine whether a match is invalid based on formatting and block context.
        
        Parameters
        ----------
        fmt_name : str
            Name of formatting rule that will be checked for syntax accuracy
        matched_text : str
            The matched text fitting the regex pattern on the current line
        block_data : RstBlockData
            The current block data
            
        Returns
        -------
        invalid : bool
            Flag indicating valid (False) or invalid (True) syntax
        hover_text : str
            Text to display if syntax check is invalid
        """
        isinvalid = False
        hover_text = None
        # test for known directive types

        if fmt_name == "directive.keyword" and block_data.block_type == "directive":
            # remove "::" from directive
            directive_name = ''
            directive_name = matched_text.strip().removesuffix("::")
            print(directive_name)

            isinvalid = (directive_name not in RST_KNOWN_DIRECTIVES)
            if isinvalid:
                hover_text = f"Unknown directive: {directive_name}"
                block_data.active_directive = None
            else:
                block_data.active_directive = directive_name

        elif fmt_name == "directive.option" and block_data.block_type == "directive":
            option_text = matched_text.strip().strip(':')
            if block_data.active_directive:
                valid_options = RST_KNOWN_DIRECTIVES.get(block_data.active_directive, [])
                optname = option_text.split(':')[0]
                isinvalid = optname not in valid_options
                if isinvalid:
                    hover_text = f"Unknown option ({optname}) for directive '{block_data.active_directive}'"
        elif fmt_name == "heading.adornment":

            # Ensure all charcters in the header adornments are the same
            hline = self.currentBlock().text()
            hline_chars = set(hline.strip())

            isinvalid = len(hline_chars) != 1
            if isinvalid:
                hover_text = f"Heading adornment has mixed characters ({hline_chars})"
                return isinvalid, hover_text

            # Determine if the underline is shorter than the title
            # Make sure there is a next block to check underline
            next_block = self.currentBlock().previous()
            if next_block.isValid():
                heading_text = next_block.text()
                # A heading underline is only valid if it uses a single repeated character
                if heading_text:
                    # Compare lengths
                    title_len = len(heading_text.strip())
                    line_len = len(hline.strip())
                    isinvalid = line_len < title_len
                    if isinvalid:
                        hover_text = f"Header adornment is too short (needs to be at least {title_len} characters)"

        return isinvalid, hover_text

    def open_highlight_dialog(self):
        dialog = HighlightRulesDialog(rules=self.rules, parent=None)
        if dialog.exec():
            print("Updated settings:", self.rules)


class ContextSensitiveHighlightRule:
    def __init__(self, name: str, trigger: Callable[[str], bool], apply: Callable[[str], bool], format: QTextCharFormat):
        """
        Parameters:
        - name: Name of the rule
        - trigger: Function that returns True when a line indicates the start of a context
        - apply: Function that returns True for lines that should be styled after trigger is activated
        - format: QTextCharFormat to apply to matching lines
        """
        self.name = name
        self.trigger = trigger
        self.apply = apply
        self.format = format
        self.active = False  # Whether we are inside the block

# def qformat_from_style(style: dict) -> QTextCharFormat:
#     fmt = QTextCharFormat()
#     if 'color' in style:
#         fmt.setForeground(QColor(style['color']))
#     if 'bgcolor' in style:
#         fmt.setBackground(QColor(style['bgcolor']))
#     if style.get('bold'):
#         fmt.setFontWeight(QFont.Weight.Bold)
#     if style.get('font_italic'):
#         fmt.setFontItalic(True)
#     if style.get('underline'):
#         fmt.setFontUnderline(True)
#     return fmt

# PYGMENTS_RST_STYLE = {
#     Token.Text:                     {'color': LIGHT_THEME['text']},                  # standard text
#     Token.Whitespace:               {'color': '#999999'},
#     Token.Punctuation:              {'color': LIGHT_THEME['orange']},                # punctuation characters, *, -, +, =, etc.
#     Token.Generic.Emph:             {'color': LIGHT_THEME['red'], 'font_italic': True},   # *font_italic*
#     Token.Generic.Strong:           {'color': LIGHT_THEME['red'], 'bold': True},     # **bold**
#     Token.Literal.String:           {'color': LIGHT_THEME['green']},                 # for ``inline literals``
#     Token.Name.Tag:                 {'color': LIGHT_THEME['blue']},                  # for directives, e.g., .. note::, .. code:: python
#     Token.Name.Builtin:             {'color': LIGHT_THEME['link']},
#     Token.Operator:                 {'color': LIGHT_THEME['purple']},
#     Token.Comment:                  {'color': LIGHT_THEME['grey'], 'font_italic': True},
#     Token.Generic.Subheading:       {'color': LIGHT_THEME['text'], 'bold': True},
#     Token.Generic.Heading:          {'color': LIGHT_THEME['text'], 'bold': True},
#     Token.Name.Attribute:           {'color': '#ffd580'},
#     Token.Comment.Special:          {'color': LIGHT_THEME['grey']},
#     Token.Literal.Number:           {'color': LIGHT_THEME['teal']},
#     Token.Keyword:                  {'color': LIGHT_THEME['blue']},
#     Token.Name.Function:            {'color': '#ffd580'},
#     Token.Name.Variable:            {'color': '#ffd580'},
#     Token.Generic.Error:            {'color': '#ff0000'},                           # for error messages
#     Token:                          {'color': '#000000'}  # fallback
# }

# class RstHighlighter(QSyntaxHighlighter):
#     def __init__(self, document, style_map=None):
#         super().__init__(document)
#         self.lexer = RstLexer()
#         self.style_map = style_map or PYGMENTS_RST_STYLE

#     def highlightBlock(self, text):
#         offset = 0
#         for token_type, value in lex(text, self.lexer):
#             length = len(value)
#             style = self.style_map.get(token_type)

#             # Fallback to Token hierarchy if direct match not found
#             while style is None and token_type.parent:
#                 token_type = token_type.parent
#                 style = self.style_map.get(token_type)

#             if style:
#                 fmt = qformat_from_style(style)
#                 self.setFormat(offset, length, fmt)
#             offset += length
# class MarkdownHighlighter(QSyntaxHighlighter):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.rules = []

#         header = QTextCharFormat()
#         header.setFontWeight(QFont.Weight.Bold)
#         header.setForeground(QColor("blue"))
#         self.rules.append((re.compile(r'^(#{1,6})\s+.*'), header))

#         bold = QTextCharFormat()
#         bold.setFontWeight(QFont.Weight.Bold)
#         self.rules.append((re.compile(r'\*\*(.*?)\*\*|__(.*?)__'), bold))

#         font_italic = QTextCharFormat()
#         font_italic.setFontItalic(True)
#         self.rules.append((re.compile(r'\*(.*?)\*|_(.*?)_'), font_italic))

#         code = QTextCharFormat()
#         code.setFontFamily("Courier")
#         code.setBackground(QColor("#e0e0e0"))
#         self.rules.append((re.compile(r'`([^`]+)`'), code))

#         link = QTextCharFormat()
#         link.setForeground(QColor("purple"))
#         self.rules.append((re.compile(r'\[.*?\]\(.*?\)'), link))

#     def highlightBlock(self, text):
#         for pattern, fmt in self.rules:
#             for match in pattern.finditer(text):
#                 self.setFormat(match.start(), match.end() - match.start(), fmt)

# class PythonHighlighter(QSyntaxHighlighter):
#     def __init__(self, parent):
#         super().__init__(parent)
#         self.rules = []

#         # Keywords
#         keyword_format = QTextCharFormat()
#         keyword_format.setForeground(QColor("blue"))
#         keyword_format.setFontWeight(QFont.Weight.Bold)

#         keywords = [
#             "def", "class", "if", "else", "elif", "try", "except", "finally", "for", "while", "import",
#             "from", "as", "pass", "break", "continue", "return", "with", "lambda", "yield", "assert", "raise"
#         ]
#         for kw in keywords:
#             self.rules.append((re.compile(rf'\b{kw}\b'), keyword_format))

#         # Strings
#         string_format = QTextCharFormat()
#         string_format.setForeground(QColor("darkred"))
#         self.rules.append((re.compile(r'".*?"|\'.*?\''), string_format))

#         # Comments
#         comment_format = QTextCharFormat()
#         comment_format.setForeground(QColor("darkgreen"))
#         comment_format.setFontItalic(True)
#         self.rules.append((re.compile(r'#.*'), comment_format))

#         # Numbers
#         number_format = QTextCharFormat()
#         number_format.setForeground(QColor("darkmagenta"))
#         self.rules.append((re.compile(r'\b\d+(\.\d+)?\b'), number_format))

#     def highlightBlock(self, text):
#         for pattern, fmt in self.rules:
#             for match in pattern.finditer(text):
#                 self.setFormat(match.start(), match.end() - match.start(), fmt)

# def setWordWrap(self, enabled: bool):
#     """Enable or disable word wrap."""
#     mode = QPlainTextEdit.LineWrapMode.WidgetWidth if enabled else QPlainTextEdit.LineWrapMode.NoWrap
#     self.setLineWrapMode(mode)

class EditorSettingsDialog(QDialog):
    def __init__(self, settings, default_settings, parent=None):
        super().__init__(parent)
        self.setFont(default_font())
        self.setWindowTitle("Editor Settings")

        self.settings = settings
        self.default_settings = default_settings

        layout = QVBoxLayout()

        if parent is not None:
            slider_layout = QHBoxLayout()
            layout.addLayout(slider_layout)

            slider_label = QLabel()
            slider_label.setText("Font size")

            self.font_size_slider = QSlider()
            self.font_size_slider.setOrientation(Qt.Orientation.Horizontal)
            self.font_size_slider.setMinimum(6)
            self.font_size_slider.setMaximum(24)
            self.font_size_slider.setSingleStep(1)
            self.font_size_slider.setTickInterval(4)
            font = parent.font()
            self.font_size_slider.setValue(font.pointSize())
            self.font_size_slider.valueChanged.connect(lambda new_size: parent.update_font_size(new_size))

            slider_layout.addWidget(slider_label)
            slider_layout.addWidget(self.font_size_slider)

        self.table = QTableWidget(len(settings), 2)
        self.table.setHorizontalHeaderLabels(["Setting", "Enabled"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)

        for row, (key, opt) in enumerate(settings.items()):
            label_item = QTableWidgetItem(opt["phrase"])
            label_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, label_item)

            checkbox = QCheckBox()
            checkbox.setChecked(opt["enabled"])
            checkbox.stateChanged.connect(self._make_checkbox_handler(key))
            cell_widget = QWidget()
            layout_checkbox = QHBoxLayout(cell_widget)
            layout_checkbox.addWidget(checkbox)
            layout_checkbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_checkbox.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 1, cell_widget)

        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset")
        reset_btn.setToolTip('Reset to default options')
        reset_btn.clicked.connect(self._reset_defaults)
        save_btn = QPushButton("Save")
        save_btn.setToolTip('Save options to file')
        save_btn.clicked.connect(self._save_settings)
        load_btn = QPushButton("Load")
        load_btn.setToolTip('Load options from file')
        load_btn.clicked.connect(self._load_settings)
        ok_btn = QPushButton("OK")
        ok_btn.setToolTip('Close dialog')
        ok_btn.clicked.connect(self.accept)

        for b in [reset_btn, save_btn, load_btn, ok_btn]:
            button_layout.addWidget(b)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _make_checkbox_handler(self, key):
        def handler(state):
            self.settings[key]['enabled'] = bool(state)
        return handler

    def _reset_defaults(self):
        for row, key in enumerate(self.settings):
            default_state = self.default_settings[key]["enabled"]
            checkbox = self._get_checkbox(row)
            checkbox.setChecked(default_state)

    def _get_checkbox(self, row):
        return self.table.cellWidget(row, 1).layout().itemAt(0).widget()

    def _save_settings(self):
        path = Path("editor_settings.json")
        if path.exists():
            with path.open("w") as f:
                json.dump(self.settings, f, indent=2)
            print(f"Settings saved to {path}")

    def _load_settings(self):
        path = Path("editor_settings.json")
        if path.exists():
            with path.open("r") as f:
                data = json.load(f)
                for row, key in enumerate(self.settings):
                    if key in data:
                        self.settings[key]["enabled"] = data[key]["enabled"]
                        self._get_checkbox(row).setChecked(data[key]["enabled"])
            print(f"Settings loaded from {str(path)}")

class HighlightRulesDialog(QDialog):
    def __init__(self, rules, parent=None):
        super().__init__(parent)
        self.setFont(default_font())
        self.rules = rules
        self.setWindowTitle("Edit Highlight Rules")
        self.layout = QHBoxLayout(self)
        self.scheme = LIGHT_THEME
        self.rule_list = QListWidget()
        for rule in self.rules:
            self.rule_list.addItem(rule.name)

        self.form = QFormLayout()
        self.name_edit = QLineEdit()
        self.fg_color_label = QLabel()
        self.bg_color_label = QLabel()
        self.family_combo = QFontComboBox()
        if rule.font_family:
            self.family_combo.setCurrentFont(QFont(rule.font_family))
        self.font_weight_combo = QComboBox()
        self.font_weight_combo.clear()
        self.font_weight_combo.addItem("font_italic")
        self.font_weight_combo.addItems(list(FONT_WEIGHT_MAP.keys()))
        self.font_weight_combo.setCurrentText("normal")
        self.font_italic_checkbox = QCheckBox()
        self.font_italic_checkbox.setChecked(False)
        self.underline_checkbox = QCheckBox()
        self.underline_checkbox.setChecked(False)

        self.fg_color_button = QPushButton("Change Color")
        self.fg_color_button.setFont(default_font())
        self.fg_color_button.clicked.connect(self.choose_color)

        self.bg_color_button = QPushButton("Change Background Color")
        self.bg_color_button.setFont(default_font())
        self.bg_color_button.clicked.connect(self.choose_color)

        self.form.addRow("Name", self.name_edit)
        self.form.addRow("Text Color", self.fg_color_button)
        self.form.addRow("Background Color", self.bg_color_button)
        self.form.addRow("Font Family", self.family_combo)
        self.form.addRow("Font Weigth", self.font_weight_combo)
        self.form.addRow("Italic", self.font_italic_checkbox)
        self.form.addRow("Underline", self.underline_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)

        self.button_box.accepted.connect(self.save_rule)
        self.button_box.rejected.connect(self.reject)

        right_layout = QVBoxLayout()
        right_layout.addLayout(self.form)
        right_layout.addWidget(self.button_box)

        self.layout.addWidget(self.rule_list)
        self.layout.addLayout(right_layout)

        self.rule_list.currentRowChanged.connect(self.load_rule)
        self.current_rule_index = 0
        self.load_rule(0)

    def load_rule(self, index):
        self.current_rule_index = index
        rule = self.rules[index]
        self.name_edit.setText(rule.name)
        if rule.foreground:
            self.fg_color_button.setText(rule.foreground)
            self.fg_color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {rule.foreground};" )
        else:
            self.fg_color_button.setText("None")
            self.fg_color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {self.scheme['text']};" )
        if rule.background:
            self.bg_color_button.setText(rule.background)
            self.bg_color_button.setStyleSheet( f"background-color: {rule.background}; color: {self.scheme['text']};" )
        else:
            self.bg_color_button.setText("None")
            self.bg_color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {self.scheme['text']};" )
        self.family_combo.setCurrentText(rule.font_family or "")
        self.font_weight_combo.setCurrentText(rule.font_weight or "")
        self.font_italic_checkbox.setChecked(rule.font_italic)
        self.underline_checkbox.setChecked(rule.underline)

    def choose_text_color(self):
        color = self.choose_color()
        if color.isValid():
            self.fg_color_button.setText(color.name())
            self.fg_color_button.setStyleSheet( f"background-color: {self.scheme['background']}; color: {color.name()};" )

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

        # Check if we're editing an existing rule or adding a new one
        existing_names = [r.name for r in self.rules]
        is_new = name not in existing_names

        if is_new:
            rule = HighlightRule(name=name)
            self.rules.append(rule)
            self.current_rule_index = len(self.rules) - 1
        else:
            rule = self.rules[self.current_rule_index]
            rule.name = name

        # Update remaining rule attributes
        rule.foreground = self.fg_color_button.text() or None
        rule.background = self.bg_color_button.text() or None
        rule.font_family = self.family_combo.currentFont().family() or None
        rule.font_weight = self.font_weight_combo.currentText() or None
        rule.font_italic = self.font_italic_checkbox.isChecked()
        rule.underline = self.underline_checkbox.isChecked()

        self.accept()

    def open_highlight_dialog(self):
        dialog = HighlightRulesDialog(self.rules, self)
        if dialog.exec():
            self.highlighter.rehighlight()

class CodeEditorMenu:
    def __init__(self, editor: CodeEditor, menu_bar: QMenuBar):
        self.editor = editor
        self.menu_bar = menu_bar
        self._init_menu()

    def _init_menu(self):
        edit_menu = self._get_or_create_menu("Edit")

        settings_action = QAction("Editor Settings", self.editor)
        settings_action.triggered.connect(self.editor.open_settings_dialog)
        edit_menu.addAction(settings_action)

        toggle_highlighter_action = QAction("Toggle Syntax Highlighter", self.editor)
        toggle_highlighter_action.setCheckable(True)
        toggle_highlighter_action.setChecked(True)
        toggle_highlighter_action.toggled.connect(self.editor.toggle_highlighter)
        edit_menu.addAction(toggle_highlighter_action)

        highlight_action = QAction("Highlight Rules", self.editor)
        highlight_action.triggered.connect(self.editor.open_highlight_dialog)
        edit_menu.addAction(highlight_action)

    def _get_or_create_menu(self, title: str) -> QMenu:
        for action in self.menu_bar.actions():
            if action.text() == title:
                return action.menu()
        new_menu = self.menu_bar.addMenu(title)
        return new_menu

class CodeEditorToolbar:
    def __init__(self, editor: CodeEditor, toolbar: QToolBar):
        self.editor = editor
        self.toolbar = toolbar

        self._init_toolbar()

    def _init_toolbar(self):
        settings_icon = QIcon(str(ICON_PATH / "icon-gear-64.svg"))
        settings_action = QAction("Format Settings", self.editor)
        settings_action.setIcon(settings_icon)
        settings_action.setToolTip("Editor Settings")
        settings_action.setFont(default_font())
        settings_action.triggered.connect(self.editor.open_settings_dialog)

        highlight_icon = QIcon(str(ICON_PATH / "icon-spotlight-64.svg"))
        toggle_action = QAction("Highlight", self.editor)
        toggle_action.setIcon(highlight_icon)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(True)
        toggle_action.setFont(default_font())
        toggle_action.toggled.connect(self.editor.toggle_highlighter)

        colors_icon = QIcon(str((ICON_PATH / "icon-style-palette-64.svg")))
        highlight_action = QAction("Highlight Rules", self.editor)
        highlight_action.setIcon(colors_icon)
        highlight_action.setToolTip("Highlighting Rules")
        highlight_action.setFont(default_font())
        highlight_action.triggered.connect(self.editor.open_highlight_dialog)

        self.toolbar.addAction(settings_action)
        self.toolbar.addAction(toggle_action)
        self.toolbar.addAction(highlight_action)