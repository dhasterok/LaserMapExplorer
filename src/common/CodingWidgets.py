import re, json
from dataclasses import dataclass
from PyQt6.QtWidgets import ( 
        QWidget, QWidget, QPlainTextEdit, QTextEdit
    )
from PyQt6.QtGui import (
    QFont, QCursor, QPainter,
    QColor, QTextFormat, QTextCharFormat, QSyntaxHighlighter,
)
from PyQt6.QtCore import Qt, QRect, QSize
from pygments import lex
from pygments.token import Token
from pygments.lexers.markup import RstLexer, MarkdownLexer
from pygments.lexers.python import Python3Lexer

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
        self.lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)

        self._highlight_line = True

        self.highlightCurrentLine()

    @property
    def highlight_line(self):
        return self._highlight_line
    
    @highlight_line.setter
    def highlight_line(self, new_state):
        if not isinstance(new_state, 'bool'):
            raise TypeError("Highlight line should be a bool.")
        self._highlight_line = new_state
        self.highlightCurrentLine()

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

# Ayu Light palette colors
AYU_LIGHT_THEME = {
    "red": "#f07171",
    "orange": "#fa8d3e",
    "yellow": "#ffd580",
    "green": "#87b300",
    "teal": "#4cc09a",
    "blue": "#399ee6",
    "link": "#56b4d5",
    "grey": "#acaeb1",
    "purple": "#bda0db",
    "text": "#5c6167",
    "background": "#f9f9f9",
}

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
    """_summary_

    _extended_summary_

    Parameters
    ----------
    filepath : _type_
        _description_

    Returns
    -------
    _type_
        _description_

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

# def qformat_from_style(style: dict) -> QTextCharFormat:
#     fmt = QTextCharFormat()
#     if 'color' in style:
#         fmt.setForeground(QColor(style['color']))
#     if 'bgcolor' in style:
#         fmt.setBackground(QColor(style['bgcolor']))
#     if style.get('bold'):
#         fmt.setFontWeight(QFont.Weight.Bold)
#     if style.get('italic'):
#         fmt.setFontItalic(True)
#     if style.get('underline'):
#         fmt.setFontUnderline(True)
#     return fmt

# PYGMENTS_RST_STYLE = {
#     Token.Text:                     {'color': AYU_LIGHT_THEME['text']},                  # standard text
#     Token.Whitespace:               {'color': '#999999'},
#     Token.Punctuation:              {'color': AYU_LIGHT_THEME['orange']},                # punctuation characters, *, -, +, =, etc.
#     Token.Generic.Emph:             {'color': AYU_LIGHT_THEME['red'], 'italic': True},   # *italic*
#     Token.Generic.Strong:           {'color': AYU_LIGHT_THEME['red'], 'bold': True},     # **bold**
#     Token.Literal.String:           {'color': AYU_LIGHT_THEME['green']},                 # for ``inline literals``
#     Token.Name.Tag:                 {'color': AYU_LIGHT_THEME['blue']},                  # for directives, e.g., .. note::, .. code:: python
#     Token.Name.Builtin:             {'color': AYU_LIGHT_THEME['link']},
#     Token.Operator:                 {'color': AYU_LIGHT_THEME['purple']},
#     Token.Comment:                  {'color': AYU_LIGHT_THEME['grey'], 'italic': True},
#     Token.Generic.Subheading:       {'color': AYU_LIGHT_THEME['text'], 'bold': True},
#     Token.Generic.Heading:          {'color': AYU_LIGHT_THEME['text'], 'bold': True},
#     Token.Name.Attribute:           {'color': '#ffd580'},
#     Token.Comment.Special:          {'color': AYU_LIGHT_THEME['grey']},
#     Token.Literal.Number:           {'color': AYU_LIGHT_THEME['teal']},
#     Token.Keyword:                  {'color': AYU_LIGHT_THEME['blue']},
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

@dataclass
class HighlightRule:
    """_summary_

    Notes
    -----

    - group=0: highlights the whole match
    - group=1: highlights the first capture group
    - group=N: for other specific groups

    """
    name: str
    pattern: str # A compiled re.Pattern
    color: str = AYU_LIGHT_THEME["text"]
    style: str = "normal"
    background: str = None
    font_family: str = None
    underline: bool = False
    group: int = 0     # Which capture group to apply formatting to

    def to_dict(self):
        return {
            "name": self.name,
            "pattern": self.pattern,
            "color": self.color,
            "style": self.style,
            "background": self.background,
            "font_family": self.font_family,
            "underline": self.underline,
            "group": self.group
        }

    def to_qtextcharformat(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.color))
        fmt.setForeground(QColor(self.color))
        font_style = {
            "bold": QFont.Weight.Bold,
            "italic": QFont.Style.StyleItalic,
            "normal": QFont.Style.StyleNormal
        }
        if self.style == "bold":
            fmt.setFontWeight(QFont.Weight.Bold)
        elif self.style == "italic":
            fmt.setFontItalic(True)
        if self.underline == "underline":
            fmt.setFontUnderline(True)
        if self.background:
            fmt.setBackground(QColor(self.background))
        if self.font_family:
            fmt.setFontFamily(self.font_family)
        return fmt

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            pattern=data["pattern"],
            color=data.get("color", "#000000"),
            style=data.get("style", "normal"),
            background=data.get("background"),
            font_family=data.get("font_family"),
            underline=data.get("underline", False)
        )

# Define the rules for the Ayu Light theme
RST_HIGHLIGHT_RULES = [
    HighlightRule( # Bold
        name="bold",
        pattern=r"\*\*[^*\n]+?\*\*",
        color=AYU_LIGHT_THEME["red"],
        style="bold",
        group=0,
    ),
    HighlightRule( # Italic
        name="italic",
        pattern=r"(?<!\*)\*[^\s*][^*\n]*?\*(?!\*)",
        color=AYU_LIGHT_THEME["red"],
        style="italic",
        group = 0,
    ),
    HighlightRule( # Inline code
        name="inline code",
        pattern=r"``[^`\n]+?``",
        color=AYU_LIGHT_THEME["green"],
        font_family="Courier New",
        group=0,
    ),  
    HighlightRule( # Directive
        name="directive",
        pattern=r"^\s*\.\. .*?::",    
        color=AYU_LIGHT_THEME["orange"],
        style="bold",
        group=0,
    ),         
    HighlightRule( # Titles
        name="title",
        pattern=r"^(?P<text>.+)\n(?P<line>=+|-+)$", 
        color=AYU_LIGHT_THEME["orange"],
        style="bold"
    ),  
    HighlightRule( # Block quotes
        name="block quote",
        pattern=r"(?m)^\s{3,}.*$",      
        color=AYU_LIGHT_THEME["grey"]
    ),
    HighlightRule( # Links
        name="link",
        pattern=r"`[^`]+? <[^>]+?>`_",  
        color=AYU_LIGHT_THEME["link"],
        underline=True
    ),
    HighlightRule( # Unordered list bullets
        name="list",
        pattern=r'^\s*([-+*])(?=\s)',   
        color=AYU_LIGHT_THEME["orange"],
        style="normal"
    ),
    HighlightRule( # numbered list items like 1. or 1)
        name="enumerate",
        pattern=r'^\s*\d+[\.\)](?=\s)', 
        color=AYU_LIGHT_THEME["orange"],
        style="normal"
    ),
    HighlightRule( # reST table lines like +---+ or ===
        name="table",
        pattern=r'^[-+|=]{3,}$',        
        color=AYU_LIGHT_THEME["purple"],
        style="normal"
    ),
    HighlightRule( # table borders: + or |
        name="table border",
        pattern=r'^[+|]',               
        color=AYU_LIGHT_THEME["purple"],
        style="normal"
    ),
]

class RstHighlighter(QSyntaxHighlighter):
    def __init__(self, parent, rules=None):
        super().__init__(parent)
        self.rules = []
        if rules is None:
            rules = []  # your default list here
        for rule in rules:
            compiled = re.compile(rule.pattern, re.MULTILINE)
            fmt = rule.to_qtextcharformat()
            self.rules.append((compiled, fmt, rule.group))

    def highlightBlock(self, text):
        for pattern, fmt, group in self.rules:
            for match in pattern.finditer(text):
                if group <= (match.lastindex or 0):
                    start, end = match.span(group)
                else:
                    start, end = match.span(0)
                self.setFormat(start, end - start, fmt)

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

#         italic = QTextCharFormat()
#         italic.setFontItalic(True)
#         self.rules.append((re.compile(r'\*(.*?)\*|_(.*?)_'), italic))

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