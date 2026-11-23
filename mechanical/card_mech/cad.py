"""Solid model of the card for STEP export and a visual check. Run as a module."""
from build123d import Axis, Box, Compound, Pos, export_step, fillet

from . import stack as S
from .checks import envelope_report
from .drawings import cell_origin
from .params import ADOPTED, ENVELOPES


def _box(x, y, z, w, h, t, label):
    """Box with its low corner at (x, y, z), card coordinates: origin at a back corner of the card."""
    b = Pos(x + w / 2, y + h / 2, z + t / 2) * Box(w, h, t)
    b.label = label
    return b


def build(key: str) -> Compound:
    p, rep, parts = ENVELOPES[key], envelope_report(key), S.load_parts()
    outer = Pos(p.length / 2, p.width / 2, p.height / 2) * Box(p.length, p.width, p.height)
    outer = fillet(outer.edges().filter_by(Axis.Z), p.corner_r)
    rib_y = p.wall + p.board_gap + p.board_w
    shell = outer - _box(p.wall, p.wall, p.back, *p.cavity, "cavity") + _box(p.wall, rib_y, p.back, p.cavity[0], S.RIB, p.cavity[2], "rib")
    shell.label = "shell"
    solids = [shell]
    off = p.wall + p.board_gap
    board_z = p.height - p.front - S.FACE_GAP - p.board_t
    if rep["cell"]:
        cl, cw, ct = rep["cell"]["size"]
        solids.append(_box(*cell_origin(p, rep), p.back + S.CELL_PAD, cl, cw, ct, f"cell {rep['cell']['mpn']}"))
    solids.append(_box(off, off, board_z, *p.board, p.board_t, "board"))
    for pl in rep["placed"]:
        if pl["part"] is None:
            continue
        h = min(parts["parts"][pl["part"]]["size"][2], board_z - p.back)
        z = board_z - h if pl["face"] == "top" else board_z + p.board_t
        solids.append(_box(off + pl["x"], off + pl["y"], z, pl["w"], pl["h"], h, pl["name"]))
    return Compound(label=f"manent-card-{key}", children=solids)


if __name__ == "__main__":
    out = S.ROOT / "mechanical" / "out"
    model = build(ADOPTED)
    export_step(model, str(out / f"card-{ADOPTED}.step"))
    print(f"card-{ADOPTED}.step: {len(model.children)} bodies, "
          f"bounding box {tuple(round(v, 2) for v in model.bounding_box().size)}")
