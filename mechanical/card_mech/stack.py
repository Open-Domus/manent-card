"""What is inside the card and where.

Nothing is stacked on the cell: a card is too thin for that. The board is a strip along one
long edge and the cell takes the rest of the plan, so there are two stacks to check.
Through the board, from the phone outwards: back skin, parts, board, front skin. Every part
sits on the face of the board that looks at the phone; the other face lies right under the
front skin and carries only the contact pads. The microphones are bottom-port parts, so their
sound comes through the board from the front. Button and switch are worked from the edge.
Through the cell: back skin, cell, front skin.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from .params import CardParams

ROOT = Path(__file__).resolve().parents[2]

SWELL = 0.08          # cell thickness growth over its life
CELL_PAD = 0.10       # adhesive under the cell
CELL_GAP = 0.20       # around the cell, each side
CELL_TABS = 1.5       # beyond the cell body, for its tabs
CELL_TOP = 0.10       # between the swollen cell and the skin above it
RIB = 0.8             # wall of the frame between the board and the cell
PART_GAP = 0.15       # between the tallest part and the back skin
FACE_GAP = 0.25       # between the board and the front skin: adhesive, microphone gaskets and membranes
PART_SPACING = 0.15   # between the land patterns of small parts
FINE_PITCH_MARGIN = 0.30
PACKING = 0.50        # share of the free board area that small parts may take; the rest is for tracks
MIN_MIC_DISTANCE = 40.0
EDGE = 0.40           # copper to the board edge
SLIDE_INSET = 0.25    # switch body to the board edge: keeps its ground lands off the edge
MIN_PROUD = 0.5       # how far the slider must stand out of the bottom of its hollow
SMALL = {"passive0201", "passive0402", "passive0603", "inductor0402", "nfet", "xtal32m", "xtal32k", "inductor", "protector"}


@lru_cache
def load_parts() -> dict:
    return yaml.safe_load((ROOT / "parts" / "parts.yaml").read_text())


def body_of(c) -> str | None:
    """Key in parts.yaml of the body a circuit component occupies; None if it occupies none."""
    name, value, pkg = c.sym.name, c.value, c.fields.get("Package", "")
    if c.sym.virtual:
        return None
    by_value = {"nRF54L15": "soc", "nPM1300": "pmic", "W25Q256JW": "flash", "T5838": "mic", "V2S200D": "vps", "S-82A1A": "protector"}
    by_symbol = {"SW": "button", "SPDT": "slide", "LED": "led", "ANTENNA": "antenna", "NMOS": "nfet",
                 "CONTACT": "contact", "PAD": "testpad", "CELL": "celltabs", "XTAL4": "xtal32m"}
    if value in by_value:
        return by_value[value]
    if name in by_symbol:
        return by_symbol[name]
    if name == "XTAL":
        return "xtal32k"
    if pkg == "0806":
        return "inductor"
    if name == "L" and value == "4.7uH":
        return "inductor0402"
    return {"0603": "passive0603", "0402": "passive0402"}.get(pkg, "passive0201")


@dataclass(frozen=True)
class Placed:
    name: str
    part: str | None      # key in parts.yaml; None for a keep-out
    face: str             # "top" (parts, towards the phone), "bottom" (bare, under the front skin) or "both"
    x: float              # rectangle on the board, origin at one corner
    y: float
    w: float
    h: float
    rot: int = 0          # degrees, as KiCad turns a footprint

    @property
    def centre(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2

    @property
    def area(self) -> float:
        return self.w * self.h

    def overlaps(self, o: "Placed") -> bool:
        if "both" not in (self.face, o.face) and self.face != o.face:
            return False
        return self.x < o.x + o.w and o.x < self.x + self.w and self.y < o.y + o.h and o.y < self.y + self.h


def on_board(pl: Placed, p: CardParams) -> bool:
    """Inside the board outline, rounded corners included."""
    L, W = p.board
    r = p.board_corner_r
    for x, y in ((pl.x, pl.y), (pl.x + pl.w, pl.y), (pl.x, pl.y + pl.h), (pl.x + pl.w, pl.y + pl.h)):
        if not (-1e-9 <= x <= L + 1e-9 and -1e-9 <= y <= W + 1e-9):
            return False
        dx, dy = max(r - x, x - (L - r), 0.0), max(r - y, y - (W - r), 0.0)
        if dx > 0 and dy > 0 and dx * dx + dy * dy > r * r:
            return False
    return True


def layout(p: CardParams, parts=None) -> list[Placed]:
    """Every part whose place is decided by the card, and every keep-out. The board generator
    (electrical/gen/board.py) takes these positions and arranges the remaining parts around them.
    The board is seen from the phone side; y = 0 is the edge of the card."""
    parts = parts or load_parts()
    L, W = p.board
    out = []

    def part(name, key, face, cx, cy, margin=0.0, rot=0):
        w, h = parts["parts"][key]["size"][:2]
        out.append(Placed(name, key, face, cx - w / 2 - margin, cy - h / 2 - margin, w + 2 * margin, h + 2 * margin, rot))

    def keep(name, face, x, y, w, h):
        out.append(Placed(name, None, face, x, y, w, h))

    # one end: antenna in the outer corner, microphone A further in
    keep("antenna keep-out", "both", 0.0, 0.0, 6.0, 6.0)
    part("antenna", "antenna", "top", 3.2, 1.2, rot=180)
    part("microphone A", "mic", "top", 3.0, W - 4.0, rot=90)
    keep("microphone A gasket", "bottom", 1.5, W - 5.5, 3.0, 3.0)
    # the other end: microphone B and, on the bare face, the four contact pads in a row
    part("microphone B", "mic", "top", L - 3.0, W - 4.0, rot=90)
    keep("microphone B gasket", "bottom", L - 4.5, W - 5.5, 3.0, 3.0)
    for i, name in enumerate(("charge +", "charge -", "SWDIO", "SWDCLK")):
        part(f"contact {name}", "contact", "bottom", L - 8.0 - 3.0 * i, 4.5)
    part("cell tabs", "celltabs", "top", L - 9.0, W - 2.7)
    # on the edge of the card: the button and the recording switch, the light between them
    part("button", "button", "top", L / 2 - 12.0, 1.55)
    part("recording switch", "slide", "top", L / 2 + 12.0, 1.3 + SLIDE_INSET)
    # the light is 1.3 from the edge: its clear insert wraps the corner and shows on the front and on the edge
    part("light", "led", "top", L / 2, 1.3)
    keep("light window", "bottom", L / 2 - 2.0, 0.0, 4.0, 2.8)
    # The microcontroller is turned so that its antenna pin faces the antenna; the power chip
    # has its input and cell pins towards the contacts and the cell tabs.
    part("microcontroller", "soc", "top", 13.0, 6.5, margin=FINE_PITCH_MARGIN, rot=180)
    part("flash", "flash", "top", 24.5, 8.0)
    part("power chip", "pmic", "top", L - 22.0, 7.0, margin=FINE_PITCH_MARGIN)
    # the sensor that hears the phone through its back: in the middle, where the card lies flattest on it
    part("call sensor", "vps", "top", L / 2, 8.0)
    # posts from the back skin to the board: behind the pads the charger presses on, and beside the
    # call sensor, which must shake with the skin
    keep("post behind the pads", "top", L - 13.5, 0.6, 2.0, 2.0)
    keep("post behind the pads, inner", "top", L - 13.5, 6.4, 2.0, 2.0)
    keep("post by the call sensor", "top", L / 2 + 2.6, 7.0, 2.0, 2.0)
    for i, name in enumerate(("nRESET", "UART TX", "UART RX", "1V8", "GND", "VBAT", "VBUS")):
        part(f"test pad {name}", "testpad", "top", L / 2 - 4.5 + 1.5 * i, W - 1.2)
    return out


def small_area(bodies: list[str], parts=None) -> float:
    """Board area the small parts need, each with its share of spacing."""
    parts = parts or load_parts()
    total = 0.0
    for b in bodies:
        w, h = parts["parts"][b]["size"][:2]
        total += (w + PART_SPACING) * (h + PART_SPACING)
    return total
