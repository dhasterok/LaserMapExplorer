import re
from dataclasses import dataclass
from PyQt6.QtGui import QFont

# Light palette colors
LIGHT_THEME = {
    "brown": "#7b3915",
    "red": "#f07171",
    "orange": "#fa8d3e",
    "sunflower": "#f2af4a",
    "yellow": "#ffd580",
    "green": "#87b300",
    "teal": "#4cc09a",
    "light_teal": "#87e0c3",
    "dark_blue": "#153a5f",
    "blue": "#3990d7",
    "light_blue": "#82bceb",
    "link": "#56b4d5",
    "purple": "#a986cf",
    "light_purple": "#cfc1e2",
    "black": "#111122",
    "grey": "#acaeb1",
    "light_grey": "#dde0e4",
    "text": "#5c6167",
    "background": "#f9f9f9",
    "error": "#e65050",
}

@dataclass
class HighlightRule:
    def __init__(
        self,
        name: str,
        foreground: str=LIGHT_THEME['text'],
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
            foreground=data.get("format",{}).get("foreground", LIGHT_THEME['text']),
            background=data.get("format",{}).get("background", None),
            font_family=data.get("format",{}).get("font_family", None),
            font_weight=data.get("format",{}).get("font_weight", "normal"),
            font_italic=data.get("format",{}).get("font_italic", False),
            underline=data.get("format",{}).get("underline", False),
        )

# Define the rules for the Ayu Light theme
RST_HIGHLIGHT_RULES = [
    HighlightRule( name="brackets.round",
        foreground=LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="brackets.square",
        foreground=LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="brackets.curly",
        foreground=LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="brackets.angle",
        foreground=LIGHT_THEME["yellow"],
        font_weight="bold"
    ),
    HighlightRule( name="bold",
        foreground=LIGHT_THEME["red"],
        font_weight="bold",
    ),
    HighlightRule( name="italic",
        foreground=LIGHT_THEME["red"],
        font_italic=True,
    ),
    HighlightRule( name="bullet",
        foreground=LIGHT_THEME["green"],
        font_weight="normal"
    ),
    HighlightRule( name="interpreted.inline",
        foreground=LIGHT_THEME["dark_blue"],
        font_family="Courier New",
        font_weight="normal",
    ),  
    HighlightRule( name="literal.inline",
        foreground=LIGHT_THEME["green"],
        font_family="Courier New",
        font_weight="normal",
    ),  
    HighlightRule( name="comment.firstline",
        foreground=LIGHT_THEME["grey"],
        font_italic=True
    ),
    HighlightRule( name="comment.multiline",
        foreground=LIGHT_THEME["grey"],
        font_italic=True
    ),
    HighlightRule( name="citation.key",
        foreground=LIGHT_THEME["teal"],
        font_weight="italic",
    ),
    HighlightRule( name="citation.marker",
        foreground=LIGHT_THEME["orange"],
        font_weight="normal",
    ),
    HighlightRule( name="citation.full",
        foreground=LIGHT_THEME["blue"],
        font_weight="normal",
    ),
    HighlightRule( name="heading.title",
        foreground=LIGHT_THEME["black"],
        font_weight="bold",
    ),  
    HighlightRule( name="heading.underline",
        foreground=LIGHT_THEME["orange"],
        font_weight="bold",
    ),  
    HighlightRule( name="line.marker",
        foreground=LIGHT_THEME["orange"],
    ),
    HighlightRule( name="line.block",
        foreground=LIGHT_THEME["green"],
    ),
    HighlightRule( name="field.name",
        foreground=LIGHT_THEME["black"],
        font_weight="bold",
    ),
    HighlightRule( name="field.body",
        foreground=LIGHT_THEME["text"],
    ),
    HighlightRule( name="blockquote",
        foreground=LIGHT_THEME["orange"],
        font_italic=True,
    ),
    HighlightRule( name="literal.marker",
        foreground=LIGHT_THEME["orange"],
    ),
    HighlightRule( name="literal.block",
        foreground=LIGHT_THEME["green"],
    ),
    HighlightRule(
        name="definition.term",
        foreground=LIGHT_THEME["black"],
        font_weight="bold",
    ),
    HighlightRule(
        name="definition.body",
        foreground=LIGHT_THEME["text"],
        font_weight="normal",
    ),
    HighlightRule( name="directive.option",
        foreground=LIGHT_THEME["green"],
        font_weight="normal",
    ),
    HighlightRule( name="directive.body",
        foreground=LIGHT_THEME["green"],
        font_weight="normal",
    ),
    HighlightRule(
        name="substitution",
        foreground=LIGHT_THEME["green"],
        font_weight="normal",
        font_italic=True,
    ),
    HighlightRule( name="hyperlink.marker",
        foreground=LIGHT_THEME["orange"],
        font_weight="normal",
    ),
    HighlightRule( name="hyperlink.name",
        foreground=LIGHT_THEME["link"],
        font_weight="normal",
    ),
    HighlightRule( name="hyperlink.target",
        foreground=LIGHT_THEME["light_blue"],
        font_weight="normal",
        underline=True
    ),
    HighlightRule( name="link",
        foreground=LIGHT_THEME["link"],
        underline=True
    ),
    HighlightRule( name="table.line",   
        foreground=LIGHT_THEME["purple"],
        font_weight="normal"
    ),
    HighlightRule(
        name="table.divider",
        foreground=LIGHT_THEME["purple"],
        font_weight="normal",
    ),
    HighlightRule(
        name="table.value",
        foreground=LIGHT_THEME["text"],
        font_weight="normal",
    ),
    HighlightRule( name="footnote.key",
        foreground=LIGHT_THEME["orange"],
        font_weight="italic",
    ),
    HighlightRule( name="footnote.marker",
        foreground=LIGHT_THEME["light_blue"],
        font_weight="italic",
    ),
    HighlightRule( name="footnote.body",
        foreground=LIGHT_THEME["error"],
        font_weight="italic",
    ),
    HighlightRule(
        name="cross.reference",
        #pattern=r":(ref|doc):`[^`]+`",
        foreground=LIGHT_THEME["link"],
    ),
    HighlightRule(
        name="cross.reference.target",
        #pattern=r":(?:ref|doc):`([^`]+)`",
        foreground=LIGHT_THEME["link"],
    ),
    HighlightRule( name="paragraph",
        foreground=LIGHT_THEME['text'],
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
        "priority": 65,
        "start": re.compile(r"^\s*([-+*•‣⁃#])(\.|\s+)"),
        "line": re.compile(r"^\s*([-+*•‣⁃#])(\.|\s+)"),
        "end": None,
    },
    "enumerated_list": {
        "priority": 65,
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
        "priority": 55,
        "start": re.compile(r"^\S.*\n\s{2,}\S"),
        "line": re.compile(r"^\s{2,}\S"),
        "end": re.compile(r"^\S"),
    },
    "definition_list": {
        "priority": 55,
        "start": re.compile(r"^[^\s].+$"),  # non-indented line
        "line": re.compile(r"^\s{2,}.*"),   # indented line
        "end": re.compile(r"^[^\s].+$"),    # next non-indented line
    },
    "field_list": {
        "priority": 60,
        "start": re.compile(r"^:\w.*?:"),
        "line": re.compile(r"^\s{2,}.*"),
        "end": re.compile(r"^\S"),
    },
    "literal_block": {
        "priority": 95,
        "start": re.compile(r"^(.*?)(::)\s*$"),
        "line": re.compile(r"^(\s{2,}.*|$)"),
        "end": re.compile(r"^[^\s].+"),
    },
    "line_block": {
        "priority": 60,
        "start": re.compile(r"^\| (?!.*\|$)"),
        "line": re.compile(r"^\| (?!.*\|$)"),
        "end": re.compile(r"^(?!\| )"),
    },
    "blockquote": {
        "priority": 5,
        "start": re.compile(r"^$"),
        "line": re.compile(r"^\s{2,}.*"),
        "end": re.compile(r"^\S"),
    },
    "table_complex": {
        "priority": 85,
        "start": re.compile(r"^\+(?:[-=]+?\+)+$"),
        #"line": re.compile(r"^\|.*\|$"),
        "line": re.compile(r"^[\|\+].*"),
        "end": re.compile(r"^(?![\s\|\+]).*"),
    },
    "table_simple": {
        "priority": 85,
        "start": re.compile(r"^(=+\s+)+=+\s*$"),
        "line": re.compile(r"^(?=.*\S).*$"),
        "end": re.compile(r"^\s*$"),
    },
    "footnote": {
        "priority": 75,
        "start": re.compile(r"^\.\.\s+\[(\d+|[#*†‡§¶♠♥♦♣])\]"),
        "line": re.compile(r"^\s+"),
        "end": re.compile(r"^\S"),
    },
    "citation": {
        "priority": 70,
        "start": re.compile(r"^(\.\.)\s+(\[([a-zA-Z0-9_.-]+)\])\s*(.+)?$"),
        "line": re.compile(r"^\s+"),
        "end": re.compile(r"^\S"),
        #"end": re.compile(r"^(?:\S|$)"),
    },
    "hyperlink_target": {
        "priority": 80,
        "start": re.compile(r"^(\.\.)\s+_(.+?)(:)(?:\s+(.*))?$"),
        "line": None,
        "end": None,
    },
    "directive": {
        "priority": 90,
        #pattern=r"^\s*(\.\.)\s+(\|.*?\|)\s+(image::)",  # capture all pieces
        "start": re.compile(r"^\.\.\s*(?:\s*\|[^|]+\|\s*)?\s+\S+::(\s+)?(.*)?$"),
        "line": re.compile(r"^\s*$|\s+"), # this doesn't capture blank lines properly
        "end": re.compile(r"^\S"),
    },
    "comment": {
        "priority": 1,
        "start": re.compile(r"^\.\.($|\s)"),
        "line": re.compile(r"^\s{2,}.+"),
        "end": re.compile(r"^\S"),
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
        (re.compile(r"(?<!\S)\*\*(?![\s*])(.+?)(?<![\s*])\*\*(?=\s|[.,;:!?)]|$)"), "bold", 0),
        (re.compile(r"(?<!\S)\*([^\s*][^*\n]*?)\*(?=\s|[.,;:!?)]|$)"), "italic", 0),
        (re.compile(r"(?<!\S)``([^`\n]+)``(?=\s|[.,;:!?)]|$)"),"literal.inline", 0),
        (re.compile(r"(?<!\S)`([^`\n]+)`(?=\s|[.,;:!?)]|$)"),"interpreted.inline", 0),
        (re.compile(r"`[^`]+`_|[\w-]+_(?=[\s.,;:!?)]|$)"), "link", 0),
        (re.compile(r"_`[^`]+`|[\w-]+_(?=[\s.,;:!?)]|$)"), "hyperline.name", 0),
        (re.compile(r"\[(?!\d+$)([a-zA-Z0-9_.-]+)\]_(?=[\s.,;:!?)]|$)"), "citation.key", 0),
        (re.compile(r"\[(\d+|[#*†‡§¶♠♥♦♣])\]_(\s+|$)"), "footnote.key", 0),
        (re.compile(r"\|[^|\s]+\|"), "substitution",0),
        (re.compile(r"[()]"), "brackets.round", 0),
        (re.compile(r"[\[\]]"), "brackets.square", 0),
        (re.compile(r"[{}]"), "brackets.curly", 0),
        (re.compile(r"[<>]"), "brackets.angle", 0),
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
        (re.compile(r"^(:[^:]+:)\s+(.*)?"), "field.name", 1),              # Match just the field name
        (re.compile(r"^(:[^:]+:)\s+(.*)?"), "field.body", 2),       # Match and color just the value part
        (re.compile(r"^\s{2,}.*"), "field.body", 0),               # Match indented body
    ],
    "bullet_list": [
        (re.compile(r"^\s*([-+*•‣⁃#])(\.|\s+)"), "bullet", 0),
    ],
    "enumerated_list": [
        (re.compile(r"^(\s*\d+[\.\)]) "), "bullet", 0),
    ],
    "directive": [
        (re.compile(r"^(\.\.)\s*(\|[^|]+\|\s*)?(\S+)(::)(?:\s+(.*))?$"), "directive.marker", 1),           # formats .. marker
        #(re.compile(r"^(\.\.)\s*(\|[^|]+\|\s*)?(\S+)(::)(?:\s+(.*))?$"), "directive.substitution", 2),    # the substitution is formatted by the substitution rule
        (re.compile(r"^(\.\.)\s*(\|[^|]+\|\s*)?(\S+)(::)(?:\s+(.*))?$"), "directive.keyword", 3),          # formats directive::
        (re.compile(r"^(\.\.)\s*(\|[^|]+\|\s*)?(\S+)(::)(?:\s+(.*))?$"), "directive.marker", 5),         # formats argument
        (re.compile(r"^(\.\.)\s*(\|[^|]+\|\s*)?(\S+)(::)(?:\s+(.*))?$"), "directive.argument", 5),         # formats argument
        (re.compile(r"^(\s{2,})(\s*:\w+:\s*)?(.+)$"), "directive.option", 2),                           # formats :option:
        (re.compile(r"^(\s{2,})(\s*:\w+:\s*)?(.+)$"), "directive.body", 3),                             # formats the body
    ],
    "footnote": [
        (re.compile(r"^(\.\.)\s+(\[(\d+|[#*†‡§¶♠♥♦♣])\])\s*(.+)?$"), "footnote.marker", 1),
        (re.compile(r"^(\.\.)\s+(\[(\d+|[#*†‡§¶♠♥♦♣])\])\s*(.+)?$"), "footnote.key", 2),
        (re.compile(r"^(\.\.)\s+(\[(\d+|[#*†‡§¶♠♥♦♣])\])\s*(.+)?$"), "footnote.body", 4),
        (re.compile(r"^\s{2,}.+"), "footnote.body", 0),
    ],
    "citation": [
        (re.compile(r"^(\.\.)\s+(\[([a-zA-Z0-9_.-]+)\])\s*(.+)?$"), "citation.marker", 1),
        (re.compile(r"^(\.\.)\s+(\[([a-zA-Z0-9_.-]+)\])\s*(.+)?$"), "citation.key", 2),
        (re.compile(r"^(\.\.)\s+(\[([a-zA-Z0-9_.-]+)\])\s*(.+)?$"), "citation.full", 4),
        (re.compile(r"^\s{2,}.+"), "citation.full", 0),
    ],
    "comment": [
        (re.compile(r"^\.\.($|\s).*"), "comment.firstline", 0),
        (re.compile(r"^\s{2,}.*"), "comment.multiline", 0),
    ],
    "blockquote": [
        (re.compile(r"^\s{2,}.*"), "blockquote", 0),
    ],
    # table rules have to be listed in a specific order so that the formatting is correct
    "table_complex": [
        (re.compile(r"\S*"), "table.value", 0),             # values within the table cells (i.e., the data)
        (re.compile(r"[+\|-]"), "table.divider", 0),        # formats the vertical dividers
        (re.compile(r"^(\+[-|=]+)+\+$"), "table.line", 0),  # reST table lines like +---+ or ===
    ],
    "table_simple": [
        #pattern=,        
        (re.compile(r"\S*"), "table.value", 0),             # values within the table cells (i.e., the data)
        (re.compile(r"^([-=]+\s+)+[-=]+\s*$"), "table.line", 0),    # lines === === or --- --- in the table
    ],
    "definition_list": [
        (re.compile(r"^\S.+$"), "definition.term", 0),
        (re.compile(r"^\s{2,}.*"), "definition.body", 0),
    ],
    "hyperlink_target": [
        (re.compile(r"^(\.\.)\s+(_.+?)(:)(?:\s+(.*))?$"), "hyperlink.marker", 1),
        (re.compile(r"^(\.\.)\s+(_.+?)(:)(?:\s+(.*))?$"), "hyperlink.name", 2),
        (re.compile(r"^(\.\.)\s+(_.+?)(:)(?:\s+(.*))?$"), "hyperlink.marker", 3),
        (re.compile(r"^(\.\.)\s+(_.+?)(:)(?:\s+(.*))?$"), "hyperlink.target", 4),
    ],
}

RST_KNOWN_DIRECTIVES = {
    'note', 'warning', 'attention', 'caution', 'danger', 'error',
    'hint', 'important', 'tip', 'admonition', 'image', 'figure',
    'include', 'code-block', 'literalinclude', 'seealso', 'contents',
    'table', 'csv-table', 'list-table', 'rubric', 'topic', 'sidebar',
}
