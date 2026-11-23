"""Does it fit? Run as a module to write mechanical/out/fit-report.json."""
import json
import math

from . import stack as S
from .params import ADOPTED, ENVELOPES, CardParams

PLASTIC, ALUMINIUM, FR4 = 1.4, 2.7, 1.85   # g/cm3; the plastic is glass-filled
CELL_G_PER_MAH = 0.023                     # estimate
ELECTRONICS_G = 0.6                        # parts and solder, estimate


def circuit_bodies() -> list[str]:
    from electrical.gen.design import build
    return [b for b in map(S.body_of, build()) if b]


def tallest(parts, placed) -> tuple[str, float]:
    """Name and height of the tallest part on the board."""
    tall = [(pl.name, parts["parts"][pl.part]["size"][2]) for pl in placed if pl.part and pl.face == "top"]
    tall += [(parts["parts"][k]["function"].lower(), parts["parts"][k]["size"][2]) for k in sorted(S.SMALL)]
    return max(tall, key=lambda t: t[1])


def cell_room(p: CardParams) -> dict:
    """The box left for the cell: beside the board strip, from skin to skin."""
    cl, cw, ch = p.cavity
    return {
        "length": round(cl - 2 * S.CELL_GAP - S.CELL_TABS, 2),
        "width": round(cw - p.board_gap - p.board_w - S.RIB - 2 * S.CELL_GAP, 2),
        "thickness": round((ch - S.CELL_PAD - S.CELL_TOP) / (1 + S.SWELL), 2),
    }


def best_cell(p: CardParams, parts) -> str | None:
    room = cell_room(p)
    fits = [k for k, c in parts["cells"].items()
            if c["size"][0] <= room["length"] and c["size"][1] <= room["width"] and c["size"][2] <= room["thickness"]]
    return max(fits, key=lambda k: parts["cells"][k]["capacity_mah"]) if fits else None


def envelope_report(key: str, p: CardParams | None = None) -> dict:
    p = p or ENVELOPES[key]
    parts = S.load_parts()
    placed = S.layout(p, parts)
    L, W = p.board
    problems = []

    for i, a in enumerate(placed):
        if a.part and not S.on_board(a, p):
            problems.append(f"{a.name} is off the board")
        # A part may sit inside its own keep-out (antenna); two parts may not overlap.
        problems += [f"{a.name} overlaps {b.name}" for b in placed[i + 1:]
                     if a.overlaps(b) and a.part and b.part]
    keepouts = [k for k in placed if k.part is None]
    owners = {"antenna keep-out": {"antenna"}}
    for k in keepouts:
        problems += [f"{a.name} is inside {k.name}" for a in placed
                     if a.part and a.overlaps(k) and a.name not in owners.get(k.name, set())]

    bodies = circuit_bodies()
    large = sorted(b for b in bodies if b not in S.SMALL)
    if large != sorted(pl.part for pl in placed if pl.part):
        problems.append("the placed parts are not the large parts of the circuit")
    small = [b for b in bodies if b in S.SMALL]
    taken = sum(pl.area for pl in placed if pl.face in ("top", "both") and not
                (pl.part and any(pl.overlaps(k) for k in keepouts)))
    free = L * W - taken
    need = S.small_area(small, parts)
    if need > S.PACKING * free:
        problems.append("not enough free board area for the small parts")

    # Through the board: the tallest part decides.
    tall_name, tall_h = tallest(parts, placed)
    board_spare = round(p.cavity[2] - S.PART_GAP - tall_h - p.board_t - S.FACE_GAP, 2)
    if board_spare < 0:
        problems.append(f"the board and its parts are {-board_spare} too thick ({tall_name}, {tall_h} tall)")

    # Through the cell.
    ck = best_cell(p, parts)
    room = cell_room(p)
    cell = None
    if ck is None:
        problems.append("no cell in the list fits")
    else:
        c = parts["cells"][ck]
        cell = {"key": ck, "mpn": c["mpn"], "size": c["size"], "capacity_mah": c["capacity_mah"],
                "spare_length": round(room["length"] - c["size"][0], 2),
                "spare_width": round(room["width"] - c["size"][1], 2),
                "spare_height": round((room["thickness"] - c["size"][2]) * (1 + S.SWELL), 2)}

    mics = [pl for pl in placed if pl.part == "mic"]
    distance = math.dist(*[m.centre for m in mics])
    if distance < S.MIN_MIC_DISTANCE:
        problems.append("the microphones are too close together")

    cl, cw, ch = p.cavity
    back_cm3 = p.length * p.width * p.back / 1000          # the back skin is aluminium
    rest_cm3 = (p.length * p.width * p.height - cl * cw * ch + S.RIB * cl * ch) / 1000 - back_cm3
    back_g, rest_g = back_cm3 * ALUMINIUM, rest_cm3 * PLASTIC
    board_g = L * W * p.board_t / 1000 * FR4 + ELECTRONICS_G
    cell_g = cell["capacity_mah"] * CELL_G_PER_MAH if cell else 0.0
    return {
        "envelope": p.name, "card": [p.length, p.width, p.height], "board": [round(L, 2), round(W, 2), p.board_t],
        "ok": not problems, "problems": problems,
        "board_stack": {"back skin": p.back, "gap over the parts": S.PART_GAP, f"tallest part ({tall_name})": tall_h,
                        "board": p.board_t, "adhesive and gaskets": S.FACE_GAP, "front skin": p.front,
                        "left over": board_spare},
        "cell_stack": {"back skin": p.back, "adhesive": S.CELL_PAD,
                       "cell, swollen": round(cell["size"][2] * (1 + S.SWELL), 2) if cell else None,
                       "gap over the cell": S.CELL_TOP, "front skin": p.front,
                       "left over": cell["spare_height"] if cell else None},
        "cell_room": room, "cell": cell,
        "area": {"board": round(L * W, 1), "large_parts_and_keepouts": round(taken, 1), "free": round(free, 1),
                 "small_parts": len(small), "small_parts_need": round(need, 1),
                 "share_of_free": round(need / free, 2)},
        "mic_distance": round(distance, 1),
        "mass": {"back_skin_g": round(back_g, 1), "frame_and_front_g": round(rest_g, 1),
                 "board_g": round(board_g, 2), "cell_g": round(cell_g, 2),
                 "total_g": round(back_g + rest_g + board_g + cell_g, 1)},
        "placed": [{"name": pl.name, "part": pl.part, "face": pl.face, "x": round(pl.x, 2), "y": round(pl.y, 2),
                    "w": round(pl.w, 2), "h": round(pl.h, 2), "rot": pl.rot} for pl in placed],
    }


def size_sweep() -> list[dict]:
    """What card thickness and board width buy in cell capacity."""
    parts = S.load_parts()
    rows = []
    for height in (3.0, 3.2, 3.5, 4.0):
        for board_w in (12.0, 14.0, 16.0):
            p = ENVELOPES["A"].resized(height=height, board_w=board_w)
            ck = best_cell(p, parts)
            rows.append({"height": height, "board_w": board_w, "room": cell_room(p), "best_cell": ck,
                         "capacity_mah": parts["cells"][ck]["capacity_mah"] if ck else None})
    return rows


def full_report() -> dict:
    return {"adopted": ADOPTED, "envelopes": {k: envelope_report(k) for k in ENVELOPES}, "size_sweep": size_sweep()}


if __name__ == "__main__":
    rep = full_report()
    out = S.ROOT / "mechanical" / "out"
    out.mkdir(exist_ok=True)
    (out / "fit-report.json").write_text(json.dumps(rep, indent=1) + "\n")
    for key, e in rep["envelopes"].items():
        c = e["cell"]
        print(f"{e['envelope']}: {'fits' if e['ok'] else 'DOES NOT FIT: ' + '; '.join(e['problems'])}"
              + (f"; cell {c['mpn']} {c['capacity_mah']} mAh, {c['spare_height']} of height left" if c else ""))
    raise SystemExit(0 if rep["envelopes"][ADOPTED]["ok"] else 1)
