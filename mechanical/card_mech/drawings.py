"""SVG drawings for the design document: the card seen from the phone side and a section across it."""
from . import stack as S
from .checks import envelope_report
from .params import ENVELOPES

INK, SHELL, BOARD, PART, UNDER, CELL, KEEP = "#222", "#d9d4c8", "#3d7a4f", "#33475b", "#8fa3b5", "#c2603c", "#e8c66a"
LABELLED = ("soc", "pmic", "flash", "mic", "vps", "button", "slide", "led", "antenna")


def _svg(body, w, h, scale=12):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 {w + 2:.2f} {h + 2:.2f}" '
            f'width="{(w + 2) * scale:.0f}" font-family="sans-serif">\n'
            f'<rect x="-1" y="-1" width="{w + 2:.2f}" height="{h + 2:.2f}" fill="#fff"/>\n{body}</svg>\n')


def _rect(x, y, w, h, fill, dash=False, rx=0.0, opacity=1.0):
    d = ' stroke-dasharray="0.3 0.2"' if dash else ""
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx}" fill="{fill}" '
            f'fill-opacity="{opacity}" stroke="{INK}" stroke-width="0.05"{d}/>\n')


def _text(x, y, s, size=0.9):
    return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{INK}">{s}</text>\n'


def cell_origin(p, rep) -> tuple[float, float]:
    """Low corner of the cell in card coordinates."""
    cw = rep["cell"]["size"][1]
    y0 = p.wall + p.board_gap + p.board_w + S.RIB + S.CELL_GAP
    return p.wall + S.CELL_GAP, y0 + (rep["cell_room"]["width"] - cw) / 2


def plan(key: str) -> str:
    """Seen from the phone side. Solid: the parts. Dashed: what is on the face under the front skin."""
    p, rep = ENVELOPES[key], envelope_report(key)
    off = p.wall + p.board_gap
    L, W = p.board
    body = _rect(0, 0, p.length, p.width, SHELL, rx=p.corner_r) + _rect(off, off, L, W, BOARD, rx=p.board_corner_r, opacity=0.35)
    if rep["cell"]:
        cl, cw, _ = rep["cell"]["size"]
        x0, y0 = cell_origin(p, rep)
        body += _rect(x0, y0, cl, cw, CELL, opacity=0.25)
        body += _text(x0 + 1.0, y0 + cw / 2, f"cell {rep['cell']['mpn']}, about {rep['cell']['capacity_mah']} mAh", 1.4)
    for pl in rep["placed"]:
        fill = KEEP if pl["part"] is None else (UNDER if pl["face"] == "bottom" else PART)
        body += _rect(off + pl["x"], off + pl["y"], pl["w"], pl["h"], fill, dash=pl["face"] == "bottom",
                      opacity=0.45 if pl["part"] is None else 0.9)
    for pl in rep["placed"]:
        if pl["part"] in LABELLED:
            body += _text(off + pl["x"], off + pl["y"] + pl["h"] + 0.9, pl["name"], 0.8)
    return _svg(body, p.length, p.width)


def section(key: str) -> str:
    """Cut across the card, drawn four times thicker than it is. The phone is at the bottom."""
    p, rep, parts = ENVELOPES[key], envelope_report(key), S.load_parts()
    k, H = 4.0, p.height
    up = lambda z, h: (H - z - h) * k                 # SVG y of a layer that starts z above the phone
    body = _rect(0, 0, p.width, H * k, SHELL, rx=1.0)
    off = p.wall + p.board_gap
    body += _rect(p.wall, p.front * k, p.board_gap + p.board_w + S.RIB / 2, p.cavity[2] * k, "#fff")
    board_z = H - p.front - S.FACE_GAP - p.board_t
    body += _rect(off, up(board_z, p.board_t), p.board_w, p.board_t * k, BOARD)
    for pl in rep["placed"]:
        if pl["part"] is None or pl["face"] != "top":
            continue
        h = parts["parts"][pl["part"]]["size"][2]
        body += _rect(off + pl["y"], up(board_z - h, h), pl["h"], h * k, PART, opacity=0.6)
    if rep["cell"]:
        _, cw, ct = rep["cell"]["size"]
        _, y0 = cell_origin(p, rep)
        body += _rect(y0 - S.CELL_GAP, p.front * k, rep["cell_room"]["width"] + 2 * S.CELL_GAP, p.cavity[2] * k, "#fff")
        body += _rect(y0, up(p.back + S.CELL_PAD, ct), cw, ct * k, CELL, opacity=0.6)
        body += _text(y0 + 1.0, up(p.back + S.CELL_PAD, ct) + ct * k / 2 + 0.4, f"cell, {ct} thick", 1.2)
    body += _text(off, H * k + 0.9, "board strip, parts towards the phone", 0.8)
    return _svg(body, p.width, H * k, scale=16)


if __name__ == "__main__":
    out = S.ROOT / "mechanical" / "out"
    out.mkdir(exist_ok=True)
    for key in ENVELOPES:
        (out / f"plan-{key}.svg").write_text(plan(key))
        (out / f"section-{key}.svg").write_text(section(key))
    print(f"drawings written to {out}")
