"""Card envelope parameters. All lengths in millimetres.

The card is a closed, flat box with the outline of a payment card. X runs along its length,
Y across it, Z from the back (the face laid against the phone) to the front (the face other
people see). The board is a strip along one long edge; the cell lies beside it, not under it.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CardParams:
    name: str
    length: float
    width: float
    height: float
    wall: float = 1.2        # frame around the edge
    back: float = 0.5        # aluminium skin against the phone
    front: float = 0.5       # aluminium skin with the microphone holes and the contact windows
    antenna_window: float = 10.0   # at the antenna end, over the board strip, both skins give way to plastic
    scoop: float = 0.8       # depth of the hollow in the edge where the slider of the switch stands
    corner_r: float = 3.2    # payment cards have about 3.2
    board_gap: float = 0.3   # between the board edge and the frame
    board_w: float = 14.0    # width of the board strip
    board_t: float = 0.6

    @property
    def board(self) -> tuple[float, float]:
        return self.length - 2 * (self.wall + self.board_gap), self.board_w

    @property
    def board_corner_r(self) -> float:
        return self.corner_r - self.wall - self.board_gap

    @property
    def cavity(self) -> tuple[float, float, float]:
        return self.length - 2 * self.wall, self.width - 2 * self.wall, self.height - self.back - self.front

    def resized(self, **kw) -> "CardParams":
        return replace(self, **kw)


# Envelope A: a payment card's outline (85.6 x 54.0) and the thickness the parts chosen need.
CARD = CardParams("A-card", 85.6, 54.0, 3.5)
# Envelope B: the same outline at the 3.0 mm that Plaud publishes for its Note.
THIN = CardParams("B-thin", 85.6, 54.0, 3.0)

ENVELOPES = {"A": CARD, "B": THIN}
ADOPTED = "A"
