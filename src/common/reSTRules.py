import re
from dataclasses import dataclass
from PyQt6.QtGui import QFont

# Ayu Light palette colors
AYU_LIGHT_THEME = {
    "red": "#f07171",
    "orange": "#fa8d3e",
    "yellow": "#ffd580",
    "green": "#87b300",
    "teal": "#4cc09a",
    "dark_blue": "#112f4e",
    "blue": "#399ee6",
    "link": "#56b4d5",
    "grey": "#acaeb1",
    "purple": "#bda0db",
    "text": "#5c6167",
    "background": "#f9f9f9",
}

@dataclass
class HighlightRule:
    def __init__(
        self,
        name: str,
        foreground: str=AYU_LIGHT_THEME['text'],
        background: str=None,
        font_family: str=None,
        font_weight: str="normal",
        font_italic: bool=False,
        underline: bool=False,
    ):
        self.name = name # name of rule
        self.foreground = foreground # text color
        self.background = background # background color
        self.font_family = font_family # font
        self.font_weight = font_weight # font weight (light, normal, bold, etc.)
        self.font_italic = font_italic # emphasis
        self.underline = underline # underlining

    def to_dict(self):
        return {
            "name": self.name,
            "format" : {
                "foreground": self.foreground,
                "background": self.background,
                "font_family": self.font_family,
                "font_weight": self.font_weight,
                "font_italic": self.font_italic,
                "underline": self.underline,
            }
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            foreground=data.get("format",{}).get("foreground", AYU_LIGHT_THEME['text']),
            background=data.get("format",{}).get("background", None),
            font_family=data.get("format",{}).get("font_family", None),
            font_weight=data.get("format",{}).get("font_weight", "normal"),
            font_italic=data.get("format",{}).get("font_italic", False),
            underline=data.get("format",{}).get("underline", False),
        )

# Define the rules for the Ayu Light theme
RST_HIGHLIGHT_RULES = [
    HighlightRule( name="brackets.round",
        foreground=AYU_LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="brackets.square",
        foreground=AYU_LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="brackets.curly",
        foreground=AYU_LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="brackets.angle",
        foreground=AYU_LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="bold",
        foreground=AYU_LIGHT_THEME["red"],
        font_weight="bold",
    ),
    HighlightRule( name="italic",
        foreground=AYU_LIGHT_THEME["red"],
        font_italic=True,
    ),
    HighlightRule( name="bullet",
        #pattern=r'^\s*([-+*#])(\.|\s+)',   
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="normal"
    ),
    HighlightRule( name="interpreted.inline",
        #pattern=r"(?<!\S)``([^`\n]+)``(?=\s|[.,;!?)]|$)",
        foreground=AYU_LIGHT_THEME["green"],
        font_family="Courier New",
        font_weight="normal",
    ),  
    HighlightRule( name="literal.inline",
        #pattern=r"(?<!\S)``([^`\n]+)``(?=\s|[.,;!?)]|$)",
        foreground=AYU_LIGHT_THEME["dark_blue"],
        font_family="Courier New",
        font_weight="normal",
    ),  
    HighlightRule( name="comment.firstline",
        foreground=AYU_LIGHT_THEME["grey"],
        font_italic=True
    ),
    HighlightRule( name="comment.multiline",
        foreground=AYU_LIGHT_THEME["grey"],
        font_italic=True
    ),
    HighlightRule( name="citation.reference",
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="italic",
    ),
    HighlightRule( name="citation.definition",
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="normal",
    ),
    HighlightRule( name="heading.title",
        font_weight="bold",
    ),  
    HighlightRule( name="heading.underline",
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="bold",
    ),  
    HighlightRule( name="line.marker",
        foreground=AYU_LIGHT_THEME["green"],
    ),
    HighlightRule( name="line.block",
        foreground=AYU_LIGHT_THEME["green"],
    ),
    HighlightRule( name="field.name",
        foreground=AYU_LIGHT_THEME["green"],
    ),
    HighlightRule( name="field.body",
        foreground=AYU_LIGHT_THEME["green"],
    ),
    HighlightRule( name="blockquote",
        foreground=AYU_LIGHT_THEME["orange"],
    ),
    HighlightRule( name="literal.marker",
        foreground=AYU_LIGHT_THEME["green"],
    ),
    HighlightRule( name="literal.block",
        foreground=AYU_LIGHT_THEME["green"],
    ),
    HighlightRule(
        name="definition.term",
        #pattern=r"^\s*$\n([a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*)\n(?=[ \t]{2,})",
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="bold",
    ),
    HighlightRule(
        name="definition.body",
        #pattern=r"^\s*$\n([a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*)\n(?=[ \t]{2,})",
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="normal",
        font_italic=True,
    ),
    HighlightRule( name="directive.marker",
        foreground=AYU_LIGHT_THEME["yellow"],
        font_weight="normal",
    ),
    # directive.substitution is handled by substitution
    #HighlightRule( name="directive.substitution",
    #    foreground=AYU_LIGHT_THEME["teal"],
    #    font_weight="normal",
    #),
    HighlightRule( name="directive.keyword",
        foreground=AYU_LIGHT_THEME["orange"],
        font_weight="normal",
    ),
    HighlightRule( name="directive.argument", # Directive argument (e.g., a filename in image::)
        foreground=AYU_LIGHT_THEME["green"],
        font_weight="normal",
    ),
    HighlightRule( name="directive.option",# Directive option
        foreground=AYU_LIGHT_THEME["purple"],
        font_weight="normal",
    ),
    HighlightRule( name="directive.body",# Directive option
        foreground=AYU_LIGHT_THEME["dark_blue"],
        font_weight="normal",
    ),
    HighlightRule(
        name="substitution",
        foreground=AYU_LIGHT_THEME["red"],
        font_weight="normal",
        font_italic=True,
    ),

    HighlightRule( name="link",
        foreground=AYU_LIGHT_THEME["link"],
        underline=True
    ),
    HighlightRule( name="table.divider",# reST table lines like +---+ or ===
        #pattern=r'^[-+|=]{3,}$',        
        foreground=AYU_LIGHT_THEME["purple"],
        font_weight="normal"
    ),
    HighlightRule(
        name="table.cells",
        #pattern=r"(?=(?:.*\|.*){2,})\|",  # Only match '|' if there are 2 or more on the line
        foreground=AYU_LIGHT_THEME["purple"],
        font_weight="normal",
    ),
    # HighlightRule( name="table.cell.divider",# table borders: + or |
    #     #pattern=r"(?<!^)\|",               
    #     foreground=AYU_LIGHT_THEME["purple"],
    #     font_weight="normal"
    # ),
    HighlightRule( name="table.simple.border",
        #pattern=r"^[=+\-]{2,}( [=+\-]{2,})*$",
        #pattern=r"^\s*(\+(?:[-=]+\+)+)",
        foreground=AYU_LIGHT_THEME["purple"],
        font_weight="normal"
    ),
    HighlightRule( name="table.simple.row",
        #pattern=r"^(\w.*\w)(\s+\w.*\w)*$",
        foreground=AYU_LIGHT_THEME["text"],
    ),
    HighlightRule( name="inline.role",
        #pattern=r":\w+:`[^`]+`",
        foreground=AYU_LIGHT_THEME["link"],
        font_weight="italic",
    ),
    HighlightRule( name="footnote.reference",
        foreground=AYU_LIGHT_THEME["purple"],
        font_weight="italic",
    ),
    HighlightRule( name="footnote.definition",
        #pattern=r"^\.\. \[\d+\]",
        foreground=AYU_LIGHT_THEME["purple"],
        font_weight="normal",
    ),
    HighlightRule(
        name="cross.reference",
        #pattern=r":(ref|doc):`[^`]+`",
        foreground=AYU_LIGHT_THEME["link"],
        underline=True
    ),
    HighlightRule(
        name="cross.reference.target",
        #pattern=r":(?:ref|doc):`([^`]+)`",
        foreground=AYU_LIGHT_THEME["link"],
        underline=True,
        #group=1
    ),
    HighlightRule( name="anchor.definition",
        foreground=AYU_LIGHT_THEME["link"],
        underline=True,
    ),
    HighlightRule( name="anchor.inline",
        foreground=AYU_LIGHT_THEME["link"],
        underline=True
    ),
    HighlightRule( name="paragraph",
        foreground=AYU_LIGHT_THEME['text'],
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

RST_BLOCK_TYPES = {
    "bullet_list": {
        "priority": 10,
        "start": re.compile(r"^\s*([-+*•‣⁃#])(\.|\s+)"),
        "line": re.compile(r"^\s*([-+*•‣⁃#])(\.|\s+)"),
        "end": None,
    },
    "enumerated_list": {
        "priority": 10,
        "start": re.compile(r"^\s*\d+[\.\)] "),
        "line": re.compile(r"^\s*\d+[\.\)] "),
        "end": None,
    },
    "heading":{
        "priority": 100,
        "start": re.compile(r"^(?P<char>[=\-~^\"+\'\*])\1{2,}\s*$"),  # Or custom
        "line": None,
        "priority": 100  # Very high so it overrides others
    },
    "definition_list": {
        "priority": 8,
        "start": re.compile(r"^\S.*\n\s{2,}\S"),
        "line": re.compile(r"^\s{2,}\S"),
        "end": re.compile(r"^\S"),
    },
    "field_list": {
        "priority": 9,
        "start": re.compile(r"^:\w.*?:"),
        "line": re.compile(r"^\s{2,}.*"),
        "end": re.compile(r"^\S"),
    },
    "literal_block": {
        "priority": 20,
        "start": re.compile(r"^(.*?)(::)\s*$"),
        "line": re.compile(r"^(\s{2,}.*|$)"),
        "end": re.compile(r"^[^\s].+"),
    },
    "line_block": {
        "priority": 9,
        "start": re.compile(r"^\| "),
        "line": re.compile(r"^\| "),
        "end": re.compile(r"^\S"),
    },
    "blockquote": {
        "priority": 2,
        "start": re.compile(r"^$"),
        "line": re.compile(r"^\s{2,}.*"),
        "end": re.compile(r"^\S"),
    },
    "table": {
        "priority": 15,
        "start": re.compile(r"^(\+[-|=]+)+\+$"),
        "line": re.compile(r"^[\s|+=-]{3,}$"),
        "end": re.compile(r"^\S"),
    },
    "footnote": {
        "priority": 12,
        "start": re.compile(r"^\[\d+\]"),
        "line": re.compile(r"^\s+"),
        "end": re.compile(r"^\S"),
    },
    "citation": {
        "priority": 12,
        "start": re.compile(r"^\s*\.\.\s+\[[^\]]+\]"),
        "line": re.compile(r"^\s+"),
        "end": re.compile(r"^\S"),
    },
    "hyperlink_target": {
        "priority": 14,
        "start": re.compile(r"^\.\. _.*:"),
        "line": None,
        "end": None,
    },
    "directive": {
        "priority": 18,
        #pattern=r"^\s*(\.\.)\s+(\|.*?\|)\s+(image::)",  # capture all pieces
        "start": re.compile(r"^\.\.\s*(?:\s*\|[^|]+\|\s*)?\s+\S+::(\s+)?(.*)?$"),
        "line": re.compile(r"^\s*$|\s+"), # this doesn't capture blank lines properly
        "end": re.compile(r"^\S"),
    },
    "comment": {
        "priority": 1,
        "start": re.compile(r"^\.\.($|\s)"),
        "line": re.compile(r"^\s{2,}.*"),
        "end": re.compile(r"^\S"),
    },
    "definition_list": {
        "priority": 8,
        "start": re.compile(r"^[^\s].+$"),  # non-indented line
        "line": re.compile(r"^\s{2,}.*"),   # indented line
        "end": re.compile(r"^[^\s].+$"),    # next non-indented line
    },
}

RST_BLOCK_RULES = {
    # "body": [
    #     (),
    # ],
    "heading": [
        (re.compile(r'^\S.*'), "heading.title", 0),
        (re.compile(r'^[\=\~\^\"\+\-\'\*]{3,}\s*$'), "heading.underline", 0),
    ],
    "global": [
        (re.compile(r"[()]"), "brackets.round", 0),
        (re.compile(r"[\[\]]"), "brackets.square", 0),
        (re.compile(r"[{}]"), "brackets.curly", 0),
        (re.compile(r"[<>]"), "brackets.angle", 0),
        (re.compile(r"(?<!\S)\*\*(?![\s*])(.+?)(?<![\s*])\*\*(?=\s|[.,;!?)]|$)"), "bold", 0),
        (re.compile(r"(?<!\S)\*([^\s*][^*\n]*?)\*(?=\s|[.,;!?)]|$)"), "italic", 0),
        (re.compile(r"(?<!\S)``([^`\n]+)``(?=\s|[.,;!?)]|$)"),"literal.inline", 0),
        (re.compile(r"(?<!\S)`([^`\n]+)`(?=\s|[.,;!?)]|$)"),"interpreted.inline", 0),
        (re.compile(r"`[^`]+? <[^>]+?>`_(\s+|$)"), "link", 0),
        (re.compile(r"\[[^\]]+\]_( |$)"), "citation.reference", 0),
        (re.compile(r"^\s*\.\.\s+_[^:]+:\s*$"), "anchor.definition", 0),
        (re.compile(r"\b\w+_(\s+|$)"), "anchor.inline", 0),
        (re.compile(r"\[\d+\]_(\s+|$)"), "footnote.reference", 0),
        (re.compile(r"\|[^|\s]+\|"), "substitution",0),
    ],
    "literal_block": [
        (re.compile(r"(::)\s*$"), "literal.marker", 1),  # Highlight ::
        (re.compile(r"^\s{2,}.*"), "literal.block", 0), # Indented lines
    ],
    "line_block": [
        (re.compile(r"^ *\| (?!.*(?<!\\)\|).*$"), "line.marker", 0),  # marker (|) that starts a line block
        (re.compile(r" (\s*\w*)"), "line.block", 0),  # body of the line block
    ],
    "field_list": [
        (re.compile(r"^(:[^:]+:)"), "field.name", 1),            # Match just the field name
        (re.compile(r"^(:[^:]+:)\s+(.*)"), "field.body", 2),   # Match and color just the value part
        (re.compile(r"^\s{2,}.*"), "field.body", 0),               # Match indented body
    ],
    "bullet_list": [
        (re.compile(r"^\s*([-+*•‣⁃#])(\.|\s+)"), "bullet", 0),
    ],
    "enumerated_list": [
        (re.compile(r"^(\s*\d+[\.\)]) "), "bullet", 0),
    ],
    "directive": [
        (re.compile("^(\.\.)\s*(\|[^|]+\|\s*)?(\S+::)(?:\s+(.*))?$"), "directive.marker", 1),           # formats .. marker
        #(re.compile("^(\.\.)\s*(\|[^|]+\|\s*)?(\S+::)(?:\s+(.*))?$"), "directive.substitution", 2),    # the substitution is formatted by the substitution rule
        (re.compile("^(\.\.)\s*(\|[^|]+\|\s*)?(\S+::)(?:\s+(.*))?$"), "directive.keyword", 3),          # formats directive::
        (re.compile("^(\.\.)\s*(\|[^|]+\|\s*)?(\S+::)(?:\s+(.*))?$"), "directive.argument", 4),         # formats argument
        (re.compile(r"^(\s{2,})(\s*:\w+:\s*)?(.+)$"), "directive.option", 2),                           # formats :option:
        (re.compile(r"^(\s{2,})(\s*:\w+:\s*)?(.+)$"), "directive.body", 3),                             # formats the body
    ],
    "citation": [
        (re.compile(r"^\s*\.\.\s+\[[^\]]+\]"), "citation.definition", 0),
    ],
    "comment": [
        (re.compile(r"^\.\.($|\s).*"), "comment.firstline", 0),
        (re.compile(r"^\s{2,}.*"), "comment.multiline", 0),
    ],
    "blockquote": [
        (re.compile(r"^\s{2,}.*"), "blockquote", 0),
    ],
    "table": [
        #pattern=,        
        (re.compile(r"^\+[-+|=]{3,}+"), "table.divider", 0),
        (re.compile(r"[+\|-]"), "table.cells", 0),
    ],
    "definition_list": [
        (re.compile(r"^\S.+$"), "definition.term", 0),
        (re.compile(r"^\s{2,}.*"), "definition.body", 0),
    ],
    # name="link",
    # name="table.simple.border"
    #     #pattern=r"^[=+\-]{2,}( [=+\-]{2,})*$",
    #     #pattern=r"^\s*(\+(?:[-=]+\+)+)",
    # name="table.simple.row",
    #     #pattern=r"^(\w.*\w)(\s+\w.*\w)*$",
    # name="inline.role",
    #     #pattern=r":\w+:`[^`]+`",
    # name="footnote.reference",
    # name="footnote.definition",
    #     #pattern=r"^\.\. \[\d+\]",
    # name="cross.reference",
    #     #pattern=r":(ref|doc):`[^`]+`",
    # name="cross.reference.target",
    #     #pattern=r":(?:ref|doc):`([^`]+)`",
    # name="anchor.definition",
    # name="anchor.inline",
}

RST_KNOWN_DIRECTIVES = {
    'note', 'warning', 'attention', 'caution', 'danger', 'error',
    'hint', 'important', 'tip', 'admonition', 'image', 'figure',
    'include', 'code-block', 'literalinclude', 'seealso', 'contents',
    'table', 'csv-table', 'list-table', 'rubric', 'topic', 'sidebar',
}
