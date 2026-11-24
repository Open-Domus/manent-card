"""What a routed board must keep to beyond KiCad's rules: python3 gen/route_checks.py

Reads out/board.json (the reserved areas), out/tracks.json and out/vias.json, prints what is
wrong and exits 1 if anything is. tools/route.sh throws a routing away on that; the tests run it.
"""
import json
import math
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "out"
RF = {"ANT", "RF_A", "RF_B", "RF_50", "ANT_FEED"}
SLOT = 2.0          # mm: a row of signal vias longer than this cuts the ground plane under them
MERGE = 0.7         # vias nearer than this leave no ground between their holes in the plane


def crosses(row, box):
    x1, y1, x2, y2 = row[4:8]
    return any(box[0] < x1 + (x2 - x1) * i / 20 < box[2] and box[1] < y1 + (y2 - y1) * i / 20 < box[3] for i in range(21))


def problems(board=None, tracks=None, vias=None):
    board = board or json.loads((OUT / "board.json").read_text())
    tracks = tracks if tracks is not None else json.loads((OUT / "tracks.json").read_text())
    vias = vias if vias is not None else json.loads((OUT / "vias.json").read_text())
    own = {p["ref"]: set(p["nets"].values()) for p in board["parts"]}
    out = []
    for r in board["reserved"]:
        box, kind = r["box"], r["kind"]
        inside = [v for v in vias if box[0] < v[1] < box[2] and box[1] < v[2] < box[3]]
        allowed = {"radio": RF | {"GND"}, "line": RF | {"GND"}, "crystal": own.get(r["name"], set()) | {"GND"},
                   "gasket": set(), "antenna": {"GND"}}[kind]
        if kind == "antenna":
            inside = [v for v in inside if v[0] != "GND"]       # the stitching keeps ground out by itself
        out += [f"via of {v[0]} at {v[1]:.2f}, {v[2]:.2f} in {r['name']}" for v in inside if v[0] not in allowed]
        if kind in ("radio", "crystal"):
            m = 0.15 if kind == "crystal" else 0.0      # a crystal's box is 0.15 wider than its lands, for the vias
            under = [box[0] + m, box[1] + m, box[2] - m, box[3] - m]
            out += sorted({f"track of {t[0]} on the top layer through {r['name']}" for t in tracks
                           if t[1] == "F.Cu" and t[0] not in allowed and crosses(t, under)})
        if kind == "antenna":
            out += sorted({f"track of {t[0]} on {t[1]} in {r['name']}" for t in tracks
                           if t[1] in ("In2.Cu", "B.Cu") and crosses(t, box)})
    out += [f"via on the radio line {v[0]} at {v[1]:.2f}, {v[2]:.2f}" for v in vias if v[0] in RF]
    out += sorted({f"radio line {t[0]} on {t[1]}" for t in tracks if t[0] in RF and t[1] != "F.Cu"})
    pads = json.loads((OUT / "pads.json").read_text())
    for net in sorted(RF):                              # the radio line goes straight, or nearly
        ends = [(q[2], q[3]) for q in pads if q[4] == net]
        tree, rest, direct = ends[:1], ends[1:], 0.0
        while rest:
            d, q = min((math.dist(a, b), b) for a in tree for b in rest)
            direct += d
            tree.append(q), rest.remove(q)
        drawn = sum(t[3] for t in tracks if t[0] == net)
        if drawn > 1.6 * direct + 1.0:
            out.append(f"radio line {net} is {drawn:.1f} mm long for {direct:.1f} mm between its pads")
    signal = [v for v in vias if v[0] != "GND"]
    seen = set()
    for i in range(len(signal)):
        if i in seen:
            continue
        group, todo = [i], [i]
        seen.add(i)
        while todo:
            a = todo.pop()
            for j in range(len(signal)):
                if j not in seen and math.hypot(signal[a][1] - signal[j][1], signal[a][2] - signal[j][2]) < MERGE:
                    seen.add(j), group.append(j), todo.append(j)
        xs, ys = [signal[j][1] for j in group], [signal[j][2] for j in group]
        if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) > SLOT:
            out.append(f"{len(group)} signal vias in a row {math.hypot(max(xs) - min(xs), max(ys) - min(ys)):.1f} mm long "
                       f"at {min(xs):.1f}, {min(ys):.1f}: a slot in the ground plane")
    return out


if __name__ == "__main__":
    found = problems()
    print("\n".join(found) if found else "nothing against the reserved areas")
    sys.exit(1 if found else 0)
