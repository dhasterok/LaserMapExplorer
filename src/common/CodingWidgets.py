import re, json
from typing import Callable
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

        # set font to monospaced
        self.setFont(QFont("Monaco", 10))

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
        if not isinstance(new_state, bool):
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


@dataclass
class HighlightRule:
    def __init__(
        self,
        name: str,
        pattern: str,
        color: str=None,
        background: str=None,
        font_family: str=None,
        font_weight: int=None,
        style: str="normal",
        underline: bool=False,
        group: int = 0,
        context_trigger: str=None,
        context_apply: str=None,
    ):
        self.name = name # name of rule

        self.pattern = pattern # pattern to match
        self.color = color
        self.background = background
        self.font_family = font_family
        self.font_weight = font_weight
        self.style = style
        self.underline = underline
        self.group = group

        # Context-sensitive additions
        self.context_trigger = context_trigger
        self.context_apply = context_apply

    def to_dict(self):
        return {
            "name": self.name,
            "pattern": self.pattern,
            "color": self.color,
            "background": self.background,
            "font_family": self.font_family,
            "font_weight": self.font_weight,
            "style": self.style,
            "underline": self.underline,
            "group": self.group,
            "context_trigger": self.context_trigger,
            "context_apply": self.context_apply,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            pattern=data["pattern"],
            color=data.get("color", "#000000"),
            style=data.get("style", "normal"),
            background=data.get("background"),
            font_family=data.get("font_family"),
            underline=data.get("underline", False),
            group=data.get("group", 0),
            context_trigger=data.get("context_trigger"),
            context_apply=data.get("context_apply"),
        )

# Define the rules for the Ayu Light theme
RST_HIGHLIGHT_RULES = [
    HighlightRule( # Bold
        name="bold",
        pattern=r"(?<!\S)\*\*(?!\s)(.+?)(?<!\s)\*\*(?=\s|[.,;!?)]|$)",
        color=AYU_LIGHT_THEME["red"],
        style="bold",
        group=0,
    ),
    HighlightRule( # Italic
        name="italic",
        pattern=r"(?<!\S)\*([^\s*][^*\n]*?)\*(?=\s|[.,;!?)]|$)",
        color=AYU_LIGHT_THEME["red"],
        style="italic",
        group = 0,
    ),
    HighlightRule( # Inline code
        name="literal.inline",
        pattern=r"(?<!\S)``([^`\n]+)``(?=\s|[.,;!?)]|$)",
        color=AYU_LIGHT_THEME["green"],
        font_family="Courier New",
        style="normal",
        group=0,
    ),  
    HighlightRule(
        name="literal.block",
        pattern="",  # No inline pattern
        color=AYU_LIGHT_THEME["green"],
        context_trigger=r"^::$",
        context_apply=r"^\s{2,}",
    ),
    HighlightRule( # Directive
        name="directive",
        pattern=r"^\s*\.\. .*?::",    
        color=AYU_LIGHT_THEME["orange"],
        style="normal",
        group=0,
    ),         
    HighlightRule( # Directive option
        name="directive.option",
        pattern=r"(:\w+:)",
        color=AYU_LIGHT_THEME["orange"],
        style="normal",
        group=1,
    ),
    HighlightRule( # Titles
        name="title",
        pattern=r"^(?P<text>.+)\n(?P<line>=+|-+)$", 
        color=AYU_LIGHT_THEME["orange"],
        style="bold"
    ),  
    HighlightRule( # Block quotes
        name="block.quote",
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
    HighlightRule(
        name="directive.figure",
        pattern=r"^\\s*\\.\\. figure::",
        color=AYU_LIGHT_THEME["blue"],
        context_trigger="^\\s*\\.\\. figure::",
        context_apply="directive.option",
    ),
    HighlightRule(
        name="directive.option",
        pattern=r"^\\s*:[a-zA-Z-]+:\\s+.*",
        color=AYU_LIGHT_THEME["blue"],
    ),
]

FONT_WEIGHT_MAP = {
    "thin": QFont.Weight.Thin,
    "extra_light": QFont.Weight.ExtraLight,
    "light": QFont.Weight.Light,
    "normal": QFont.Weight.Normal,
    "medium": QFont.Weight.Medium,
    "demi_bold": QFont.Weight.DemiBold,
    "bold": QFont.Weight.Bold,
    "extra_bold": QFont.Weight.ExtraBold,
    "black": QFont.Weight.Black,
}

class RstHighlighter(QSyntaxHighlighter):
    def __init__(self, document, highlight_rules=None):
        super().__init__(document)
        self.highlight_rules = []
        if highlight_rules:
            self.highlight_rules = highlight_rules
        else:
            self.highlight_rules = RST_HIGHLIGHT_RULES

        self.in_context = False

    def _make_format(self, rule: HighlightRule) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(rule.color))
        if rule.font_family:
            fmt.setFontFamily(rule.font_family)
        if rule.style == "italic":
            fmt.setFontItalic(True)
        elif rule.style in FONT_WEIGHT_MAP:
            fmt.setFontWeight(FONT_WEIGHT_MAP[rule.style])
        else:
            pass # ignore invalid rule.style
        if rule.underline:
            fmt.setFontUnderline(True)
        if rule.background:
            fmt.setBackground(QColor(rule.background))
        return fmt

    def _apply_rule_to_text(self, text, rule):
        try:
            matches = re.finditer(rule.pattern, text)
            fmt = self._make_format(rule)
            for match in matches:
                group = match.group(rule.group if rule.group else 0)
                start = match.start(rule.group if rule.group else 0)
                end = start + len(group)
                self.setFormat(start, end - start, fmt)
        except re.error as e:
            # Regex failed silently. Optionally log or debug.
            pass

    def highlightBlock(self, text):
        # Track context triggers
        if self.in_context:
            context_rule = self.context_rule

            # End context block if it no longer applies
            if context_rule and context_rule.context_apply:
                for rule in self.highlight_rules:
                    if rule.name == context_rule.context_apply:
                        self._apply_rule_to_text(text, rule)
                        break

                if text.strip() == "":
                    self.in_context = False
                    self.context_rule = None
            else:
                self.in_context = False
                self.context_rule = None

        else:
            for rule in self.highlight_rules:
                if rule.context_trigger:
                    if re.match(rule.context_trigger, text):
                        self.in_context = True
                        self.context_rule = rule
                        self.setFormat(0, len(text), self._make_format(rule))
                        return  # highlight only the trigger line
                elif rule.pattern:
                    self._apply_rule_to_text(text, rule)



    # def highlightBlock(self, text: str):
    #     # First: handle standard inline patterns
    #     for rule in self.highlight_rules:
    #         if rule.pattern:
    #             for match in re.finditer(rule.pattern, text):
    #                 start, end = match.start(rule.group), match.end(rule.group)
    #                 self.setFormat(start, end - start, self.format_for_rule(rule))

    #     # Second: handle context-sensitive rules
    #     for rule in self.highlight_rules:
    #         if rule.context_trigger:
    #             if rule.context_trigger(text):
    #                 rule.context_active = True
    #                 return  # skip highlighting the trigger line itself

    #             elif rule.context_active:
    #                 if rule.context_apply and rule.context_apply(text):
    #                     self.setFormat(0, len(text), self.format_for_rule(rule))
    #                     return
    #                 else:
    #                     rule.context_active = False

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