"""Clipart faces, drawn in the terminal.

A portrait is a small grid of coloured cells. The face is assembled from
independently chosen parts -- skin tone, hair style, hair colour, facial
hair, glasses, attire, an accessory -- and then an EXPRESSION band is laid
over the brows, eyes and mouth. The same person can therefore be drawn
happy, bored, smug or furious without redrawing anything else.

Appearance is drawn completely independently of personality and of
behaviour. What someone looks like tells you nothing about how they
negotiate, which is true in the terminal and true across a table.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ui

WIDTH = 20
HEAD_LEFT = 2          # left border column of the head
HEAD_RIGHT = 14        # right border column
INNER_LEFT = HEAD_LEFT + 1
INNER_WIDTH = HEAD_RIGHT - HEAD_LEFT - 1   # 11

ROW_TOP, ROW_HAIR1, ROW_HAIR2 = 0, 1, 2
ROW_BROW, ROW_EYES, ROW_NOSE = 3, 4, 5
ROW_LIP, ROW_MOUTH, ROW_CHIN = 6, 7, 8
ROW_JAW, ROW_SHOULDER, ROW_TORSO = 9, 10, 11
HEIGHT = 12

# -- palettes (xterm-256 colour numbers) -----------------------------------

SKIN_TONES = (224, 223, 216, 180, 173, 137, 130, 94)
SKIN_SHADOW = {224: 180, 223: 180, 216: 173, 180: 137, 173: 137, 137: 94, 130: 94, 94: 58}
HAIR_COLOURS = (232, 235, 58, 94, 130, 166, 178, 220, 245, 252)
ATTIRE_COLOURS = (17, 18, 23, 52, 88, 22, 236, 238, 60, 31, 25, 130, 255, 237)
INK = 235          # the dark colour features are drawn in
LIP_INK = 95

# -- parts ------------------------------------------------------------------


@dataclass(frozen=True)
class HairStyle:
    key: str
    row1: str          # 11 chars: '#' hair, '.' skin
    row2: str
    char: str = "▓"
    sides: bool = False   # hair down the sides of the face
    tall: bool = False    # extra volume above the head


HAIR_STYLES = (
    HairStyle("buzz", "###########", "...........", "▒"),
    HairStyle("short", "###########", "##.......##"),
    HairStyle("crop", "###########", "#.........#", "▒"),
    HairStyle("afro", "###########", "###########", "▓", sides=True, tall=True),
    HairStyle("curls", "###########", "##.......##", "@", tall=True),
    HairStyle("locs", "###########", "###.....###", "≣", sides=True),
    HairStyle("braids", "###########", "##.......##", "≠", sides=True),
    HairStyle("long", "###########", "##.......##", "▓", sides=True),
    HairStyle("slick", "###########", "#.........#", "▀"),
    HairStyle("parted", "####.######", "##.......##"),
    HairStyle("wavy", "###########", "##.......##", "~", tall=True),
    HairStyle("receding", "##.......##", "...........", "▒"),
    HairStyle("bald", "...........", "..........."),
    HairStyle("topknot", "###########", "##.......##", "▓", tall=True),
    HairStyle("fade", "###########", "#.........#", "░"),
)

FACIAL_HAIR = ("clean", "clean", "clean", "stubble", "moustache", "goatee", "beard", "fullbeard")
EYEWEAR = ("none", "none", "none", "none", "glasses", "round", "thick")
ACCESSORIES = ("none", "none", "none", "none", "cigar", "cigar", "toothpick", "earpiece", "pen", "vape")

ATTIRE = (
    ("suit and tie", "tie"),
    ("charcoal suit", "tie"),
    ("open-collar suit", "open"),
    ("polo shirt", "polo"),
    ("hoodie", "hoodie"),
    ("quarter-zip", "zip"),
    ("dress shirt, no jacket", "open"),
    ("turtleneck", "turtle"),
    ("fleece vest over a shirt", "vest"),
    ("loud patterned shirt", "loud"),
    ("waistcoat", "vest"),
    ("crewneck sweater", "turtle"),
)


# -- expressions ------------------------------------------------------------

NEUTRAL, THINKING, PLEASED, DELIGHTED = "neutral", "thinking", "pleased", "delighted"
LAUGHING, SMUG, ANNOYED, ANGRY = "laughing", "smug", "annoyed", "angry"
FURIOUS, BORED, ASLEEP, SHOCKED, WORRIED = "furious", "bored", "asleep", "shocked", "worried"

BROWS = {
    "flat": " ▁▁▁   ▁▁▁ ",
    "raised": " ▔▔▔   ▔▔▔ ",
    "angry": " ▔▔▁   ▁▔▔ ",
    "worried": " ▁▁▔   ▔▁▁ ",
}
EYES = {
    "open": "  ◉     ◉  ",
    "wide": "  ◎     ◎  ",
    "squint": "  ━     ━  ",
    "happy": "  ◠     ◠  ",
    "closed": "  ─     ─  ",
    "dollar": "  $     $  ",
    "side": "  ◔     ◔  ",
}
MOUTHS = {
    "flat": "   ─────   ",
    "smile": "   ╰───╯   ",
    "grin": "  ╰─────╯  ",
    "laugh": "   ╰▄▄▄╯   ",
    "frown": "   ╭───╮   ",
    "snarl": "   ╭▄▄▄╮   ",
    "smirk": "   ───╯    ",
    "oh": "     ◯     ",
    "sleep": "     ◡     ",
}

# expression -> (brows, eyes, mouth, floating marks)
EXPRESSIONS: dict[str, tuple[str, str, str, str]] = {
    NEUTRAL:   ("flat", "open", "flat", ""),
    THINKING:  ("raised", "side", "smirk", "hmm"),
    PLEASED:   ("raised", "happy", "smile", ""),
    DELIGHTED: ("raised", "dollar", "grin", "cha"),
    LAUGHING:  ("raised", "happy", "laugh", "ha"),
    SMUG:      ("raised", "squint", "smirk", ""),
    ANNOYED:   ("angry", "side", "flat", ""),
    ANGRY:     ("angry", "open", "frown", ""),
    FURIOUS:   ("angry", "wide", "snarl", "rage"),
    BORED:     ("flat", "squint", "flat", ""),
    ASLEEP:    ("flat", "closed", "sleep", "zzz"),
    SHOCKED:   ("raised", "wide", "oh", "sweat"),
    WORRIED:   ("worried", "open", "frown", "sweat"),
}


# -- the drawing surface ----------------------------------------------------


@dataclass
class Grid:
    width: int
    height: int
    cells: list[list[tuple[str, int | None, int | None]]] = field(default_factory=list)

    def __post_init__(self):
        self.cells = [
            [(" ", None, None) for _ in range(self.width)] for _ in range(self.height)
        ]

    def put(self, x: int, y: int, ch: str, fg: int | None = None, bg: int | None = None):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = (ch, fg, bg)

    def text(self, x: int, y: int, s: str, fg: int | None = None, bg: int | None = None,
             skip_blank: bool = False):
        for i, ch in enumerate(s):
            if skip_blank and ch == " ":
                continue
            self.put(x + i, y, ch, fg, bg)

    def span(self, x0: int, x1: int, y: int, ch: str = " ",
             fg: int | None = None, bg: int | None = None):
        for x in range(x0, x1 + 1):
            self.put(x, y, ch, fg, bg)

    def render(self) -> list[str]:
        lines = []
        for row in self.cells:
            parts, run_fg, run_bg, buf = [], "sentinel", "sentinel", []

            def flush():
                if not buf:
                    return
                text = "".join(buf)
                if ui.colour_enabled():
                    codes = ""
                    if run_fg is not None:
                        codes += f"\033[38;5;{run_fg}m"
                    if run_bg is not None:
                        codes += f"\033[48;5;{run_bg}m"
                    parts.append(f"{codes}{text}\033[0m" if codes else text)
                else:
                    parts.append(text)

            for ch, fg, bg in row:
                if fg != run_fg or bg != run_bg:
                    flush()
                    buf, run_fg, run_bg = [], fg, bg
                buf.append(ch)
            flush()
            lines.append("".join(parts).rstrip())
        return lines


# -- assembling a face ------------------------------------------------------


@dataclass(frozen=True)
class Look:
    """Everything about how a character appears. No behaviour lives here."""

    skin: int
    hair_colour: int
    hair: HairStyle
    facial_hair: str
    eyewear: str
    accessory: str
    attire_name: str
    attire_cut: str
    attire_colour: int
    shirt_colour: int


def draw(look: Look, expression: str = NEUTRAL) -> list[str]:
    g = Grid(WIDTH, HEIGHT)
    skin, shadow = look.skin, SKIN_SHADOW.get(look.skin, look.skin)
    brows_key, eyes_key, mouth_key, marks = EXPRESSIONS.get(
        expression, EXPRESSIONS[NEUTRAL]
    )

    # head block: everything from the hairline to the chin
    for row in range(ROW_HAIR1, ROW_CHIN + 1):
        g.span(INNER_LEFT, HEAD_RIGHT - 1, row, " ", INK, skin)
    # rounded outline, so the face still reads with colour switched off
    g.put(HEAD_LEFT, ROW_TOP, "╭", shadow)
    g.span(HEAD_LEFT + 1, HEAD_RIGHT - 1, ROW_TOP, "─", shadow)
    g.put(HEAD_RIGHT, ROW_TOP, "╮", shadow)
    for row in range(ROW_HAIR1, ROW_CHIN + 1):
        g.put(HEAD_LEFT, row, "│", shadow)
        g.put(HEAD_RIGHT, row, "│", shadow)
    g.put(HEAD_LEFT, ROW_JAW, "╰", shadow)
    g.span(HEAD_LEFT + 1, HEAD_RIGHT - 1, ROW_JAW, "─", shadow)
    g.put(HEAD_RIGHT, ROW_JAW, "╯", shadow)

    _draw_hair(g, look)
    _draw_face(g, look, brows_key, eyes_key, mouth_key)
    _draw_facial_hair(g, look)
    if look.eyewear != "none":
        _draw_eyewear(g, look)
    _draw_body(g, look)
    if look.accessory != "none":
        _draw_accessory(g, look, expression)
    _draw_marks(g, marks)
    return g.render()


def _draw_hair(g: Grid, look: Look) -> None:
    style, colour = look.hair, look.hair_colour
    if style.tall:
        g.span(HEAD_LEFT, HEAD_RIGHT, ROW_TOP, style.char, colour, colour)
    for row, pattern in ((ROW_HAIR1, style.row1), (ROW_HAIR2, style.row2)):
        for i, mark in enumerate(pattern):
            if mark == "#":
                g.put(INNER_LEFT + i, row, style.char, colour, colour)
    if style.sides:
        for row in range(ROW_BROW, ROW_MOUTH + 1):
            g.put(INNER_LEFT, row, style.char, colour, colour)
            g.put(HEAD_RIGHT - 1, row, style.char, colour, colour)


def _draw_face(g: Grid, look: Look, brows: str, eyes: str, mouth: str) -> None:
    skin = look.skin
    g.text(INNER_LEFT, ROW_BROW, BROWS[brows], look.hair_colour, skin, skip_blank=True)
    g.text(INNER_LEFT, ROW_EYES, EYES[eyes], INK, skin, skip_blank=True)
    g.put(INNER_LEFT + 5, ROW_NOSE, "▾", SKIN_SHADOW.get(skin, skin), skin)
    g.text(INNER_LEFT, ROW_MOUTH, MOUTHS[mouth], LIP_INK, skin, skip_blank=True)


def _draw_facial_hair(g: Grid, look: Look) -> None:
    kind, colour, skin = look.facial_hair, look.hair_colour, look.skin
    if kind == "clean":
        return
    if kind in ("moustache", "fullbeard"):
        g.text(INNER_LEFT + 3, ROW_LIP, "▀▀▀▀▀", colour, skin)
    if kind == "stubble":
        g.text(INNER_LEFT + 2, ROW_CHIN, "░░░░░░░", colour, skin)
    if kind == "goatee":
        g.text(INNER_LEFT + 4, ROW_CHIN, "▓▓▓", colour, skin)
        g.text(INNER_LEFT + 3, ROW_LIP, "▀▀▀▀▀", colour, skin)
    if kind in ("beard", "fullbeard"):
        g.text(INNER_LEFT + 1, ROW_CHIN, "▓▓▓▓▓▓▓▓▓", colour, skin)
        for row in (ROW_MOUTH, ROW_CHIN):
            g.put(INNER_LEFT, row, "▓", colour, colour)
            g.put(HEAD_RIGHT - 1, row, "▓", colour, colour)


def _draw_eyewear(g: Grid, look: Look) -> None:
    skin, kind = look.skin, look.eyewear
    rim = {"glasses": ("(", ")", "─"), "round": ("(", ")", "="), "thick": ("[", "]", "━")}[kind]
    left, right, bridge = rim
    g.put(INNER_LEFT + 1, ROW_EYES, left, INK, skin)
    g.put(INNER_LEFT + 3, ROW_EYES, right, INK, skin)
    g.put(INNER_LEFT + 7, ROW_EYES, left, INK, skin)
    g.put(INNER_LEFT + 9, ROW_EYES, right, INK, skin)
    for x in range(INNER_LEFT + 4, INNER_LEFT + 7):
        g.put(x, ROW_EYES, bridge, INK, skin)


def _draw_body(g: Grid, look: Look) -> None:
    coat, shirt, skin = look.attire_colour, look.shirt_colour, look.skin
    # With colour off, a blank cell is invisible, so shade the clothing in.
    cloth = " " if ui.colour_enabled() else "▒"
    # neck
    g.span(INNER_LEFT + 4, INNER_LEFT + 6, ROW_SHOULDER, " ", INK, skin)
    # shoulders
    g.span(0, 3, ROW_SHOULDER, cloth, INK, coat)
    g.span(INNER_LEFT + 7, WIDTH - 4, ROW_SHOULDER, cloth, INK, coat)
    g.span(0, WIDTH - 4, ROW_TORSO, cloth, INK, coat)

    cut = look.attire_cut
    mid = INNER_LEFT + 5
    if cut == "tie":
        g.span(mid - 2, mid + 2, ROW_TORSO, cloth, INK, shirt)
        g.put(mid, ROW_TORSO, "▮", 232, shirt)
        g.put(mid - 1, ROW_SHOULDER, "╲", shirt, coat)
        g.put(mid + 1, ROW_SHOULDER, "╱", shirt, coat)
    elif cut == "open":
        g.span(mid - 2, mid + 2, ROW_TORSO, cloth, INK, shirt)
        g.put(mid - 1, ROW_SHOULDER, "╲", shirt, coat)
        g.put(mid + 1, ROW_SHOULDER, "╱", shirt, coat)
    elif cut == "polo":
        g.put(mid - 1, ROW_TORSO, "╲", 255, coat)
        g.put(mid + 1, ROW_TORSO, "╱", 255, coat)
        g.put(mid, ROW_TORSO, "▪", 255, coat)
    elif cut == "hoodie":
        g.span(mid - 3, mid + 3, ROW_SHOULDER, cloth, INK, coat)
        g.put(mid - 1, ROW_TORSO, "│", 255, coat)
        g.put(mid + 1, ROW_TORSO, "│", 255, coat)
    elif cut == "zip":
        g.put(mid, ROW_TORSO, "┃", 250, coat)
        g.put(mid, ROW_SHOULDER, "▴", 250, coat)
    elif cut == "turtle":
        g.span(INNER_LEFT + 3, INNER_LEFT + 7, ROW_SHOULDER, "▄", coat, coat)
    elif cut == "vest":
        g.span(mid - 2, mid + 2, ROW_TORSO, cloth, INK, shirt)
        g.put(mid - 2, ROW_TORSO, "▏", coat, shirt)
        g.put(mid + 2, ROW_TORSO, "▕", coat, shirt)
    elif cut == "loud":
        for x in range(0, WIDTH - 3, 3):
            g.put(x, ROW_TORSO, "❋", shirt, coat)


def _draw_accessory(g: Grid, look: Look, expression: str) -> None:
    kind, skin = look.accessory, look.skin
    if kind == "cigar":
        g.text(HEAD_RIGHT + 1, ROW_MOUTH, "══", 94)
        g.put(HEAD_RIGHT + 3, ROW_MOUTH, "▪", 202)
        if expression not in (FURIOUS, ANGRY):
            g.put(HEAD_RIGHT + 3, ROW_NOSE, "˚", 250)
            g.put(HEAD_RIGHT + 2, ROW_LIP, "°", 245)
    elif kind == "toothpick":
        g.text(HEAD_RIGHT + 1, ROW_MOUTH, "╱", 223)
    elif kind == "vape":
        g.text(HEAD_RIGHT + 1, ROW_MOUTH, "▭", 244)
        g.put(HEAD_RIGHT + 2, ROW_NOSE, "~", 250)
    elif kind == "earpiece":
        g.put(HEAD_RIGHT - 1, ROW_EYES, "◖", 250, skin)
        g.put(HEAD_RIGHT, ROW_NOSE, "│", 250)
    elif kind == "pen":
        g.put(HEAD_LEFT - 1, ROW_EYES, "╲", 33)
        g.put(HEAD_LEFT, ROW_BROW, "╲", 33, look.hair_colour)


def _draw_marks(g: Grid, marks: str) -> None:
    if marks == "zzz":
        g.text(HEAD_RIGHT + 2, ROW_HAIR2, "z", 250)
        g.text(HEAD_RIGHT + 3, ROW_HAIR1, "Z", 252)
    elif marks == "rage":
        g.text(HEAD_LEFT - 2, ROW_HAIR1, "╳", 196)
        g.text(HEAD_RIGHT + 2, ROW_HAIR1, "╳", 196)
        g.text(HEAD_RIGHT + 1, ROW_TOP, "!", 196)
    elif marks == "cha":
        g.text(HEAD_RIGHT + 1, ROW_HAIR1, "$", 226)
        g.text(HEAD_LEFT - 2, ROW_HAIR2, "$", 226)
    elif marks == "ha":
        g.text(HEAD_RIGHT + 1, ROW_HAIR2, "h", 250)
        g.text(HEAD_RIGHT + 2, ROW_HAIR1, "a", 250)
    elif marks == "sweat":
        g.text(HEAD_RIGHT + 1, ROW_BROW, "'", 45)
    elif marks == "hmm":
        g.text(HEAD_RIGHT + 1, ROW_HAIR1, "?", 250)
