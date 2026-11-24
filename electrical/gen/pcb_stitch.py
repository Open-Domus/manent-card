"""Join the ground: vias from the pours on the outer layers to the plane inside.

The autorouter is not given the ground net (gen/pcb_route.py). This script proposes ground vias
and KiCad's rule check judges them. Runs with KiCad's own Python, from the electrical directory:
    pre <out>                       before routing: a via beside each small part's ground pad, where there is room
    grid <try> [base]               a via on every point of a grid that is clear of pads, added to those of base
    apply <file>                    put the vias and tracks of a file on the board, pour, save
    judge <try> <drc> <out>         keep what broke no rule and reached the ground
    pads <base> <n> <try>           for each small ground pad without a via of its own, the n-th place to try one
    islands <base> <try>            vias in the pieces of the outer pours that have none
A file holds {"vias": [[x, y, group]], "tracks": [[x1, y1, x2, y2, group]]}; of the entries that
share a group other than "" only the first that survives is kept.
"""
import json
import math
import re
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parents[1]
mm = pcbnew.FromMM
PITCH, INSET, PAD_MARGIN, VIA, DRILL, TRACK = 1.0, 0.7, 0.35, 0.4, 0.2, 0.15
load = lambda name: json.loads((HERE / name).read_text())
save = lambda name, d: (HERE / name).write_text(json.dumps(d) + "\n")
key = lambda x, y: (round(x, 2), round(y, 2))


def near_segment(p, a, b):
    ax, ay, bx, by = *a, *b
    L = (bx - ax) ** 2 + (by - ay) ** 2
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L))
    return math.hypot(p[0] - ax - t * (bx - ax), p[1] - ay - t * (by - ay)) < 0.03


cmd = sys.argv[1]
if cmd in ("pre", "grid", "apply", "pads", "islands"):
    pcb = str(HERE / "kicad" / "card.kicad_pcb")
    board = pcbnew.LoadBoard(pcb)
    data = load("out/board.json")
    # No ground via under a microphone's gasket or in the antenna's corner.
    no_via = [r["box"] for r in data["reserved"] if r["kind"] == "gasket"]
    no_via += [[k["x"], k["y"], k["x"] + k["w"], k["y"] + k["h"]] for k in data["keepouts"] if k["name"].startswith("antenna")]
    barred = lambda x, y, m=0.12: any(q[0] - m < x < q[2] + m and q[1] - m < y < q[3] + m for q in no_via)
    copper = lambda pad: pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)      # not a paste opening

if cmd == "grid":
    boxes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            if not copper(pad) or (pad.GetNetname() == "GND" and min(b.GetWidth(), b.GetHeight()) > mm(2.0)):
                continue                     # the exposed pad of a chip: vias in it are welcome
            boxes.append((pcbnew.ToMM(b.GetLeft()) - PAD_MARGIN, pcbnew.ToMM(b.GetTop()) - PAD_MARGIN,
                          pcbnew.ToMM(b.GetRight()) + PAD_MARGIN, pcbnew.ToMM(b.GetBottom()) + PAD_MARGIN))
    boxes += [(k["x"], k["y"], k["x"] + k["w"], k["y"] + k["h"]) for k in data["keepouts"] if k["name"].startswith("antenna")]
    vias, y = [], INSET
    while y <= data["width"] - INSET:
        x = INSET
        while x <= data["length"] - INSET:
            if not any(b[0] < x < b[2] and b[1] < y < b[3] for b in boxes) and not barred(x, y):
                vias.append([round(x, 3), round(y, 3), ""])
            x += PITCH
        y += PITCH
    base = load(sys.argv[3]) if len(sys.argv) > 3 else {"vias": [], "tracks": []}
    vias = [v for v in vias if all(math.hypot(v[0] - q[0], v[1] - q[1]) >= 0.7 for q in base["vias"])]
    save(sys.argv[2], {"vias": base["vias"] + vias, "tracks": base["tracks"]})
    print(f"{len(vias)} ground vias to try")

elif cmd == "apply":
    d = load(sys.argv[2])
    gnd = board.FindNet("GND")
    for x, y, _ in d["vias"]:
        via = pcbnew.PCB_VIA(board)
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        via.SetWidth(pcbnew.F_Cu, mm(VIA))
        via.SetDrill(mm(DRILL))
        via.SetNet(gnd)
        board.Add(via)
    for x1, y1, x2, y2, _ in d["tracks"]:
        seg = pcbnew.PCB_TRACK(board)
        seg.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1))), seg.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        seg.SetWidth(mm(TRACK)), seg.SetLayer(pcbnew.F_Cu), seg.SetNet(gnd)
        board.Add(seg)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb, board)
    save("out/vias.json", [[t.GetNetname(), pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)]
                           for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T])
    print(f"{len(d['vias'])} ground vias, {len(d['tracks'])} ground tracks on the board")

elif cmd == "judge":
    d, report = load(sys.argv[2]), load(sys.argv[3])
    items = [i for v in report["violations"] + report["unconnected_items"] for i in v["items"]]
    # A via dropped on somebody's track is reported under that track's net: go by position.
    bad_vias = {key(i["pos"]["x"], i["pos"]["y"]) for i in items if i["description"].startswith("Via [")}
    bad_points = [(i["pos"]["x"], i["pos"]["y"]) for i in items if i["description"].startswith("Track [GND]")]
    tracks = {t[4]: t for t in d["tracks"]}
    out, taken = {"vias": [], "tracks": []}, set()
    for x, y, group in d["vias"]:
        t = tracks.get(group)
        owner = group.rsplit("/", 1)[0]
        if key(x, y) in bad_vias or owner in taken:
            continue
        if t and any(near_segment(p, t[:2], t[2:4]) for p in bad_points):
            continue
        out["vias"].append([x, y, group])
        if t:
            out["tracks"].append(t)
            taken.add(owner)
    save(sys.argv[4], out)
    print(f"{len(d['vias'])} tried, {len(out['vias'])} kept")
    sys.exit(0 if len(out["vias"]) == len(d["vias"]) else 3)       # 3: something was dropped, judge again

elif cmd == "pads":
    # Every small ground pad on the parts side gets a via of its own, a short track away: the
    # pour does not reach between small parts, and near the radio line there is no pour at all.
    base, option = load(sys.argv[2]), int(sys.argv[3])
    served = {t[4].rsplit("/", 1)[0] for t in base["tracks"]}
    out = {"vias": list(base["vias"]), "tracks": list(base["tracks"])}
    reach = (0.4, 0.75, 1.1)[option // 8]
    ux, uy = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))[option % 8]
    tried = 0
    lands = []                                # every copper pad: a via does not go into a land
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if copper(pad):
                b = pad.GetBoundingBox()
                lands.append((pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()), pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom())))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            hw, hh = pcbnew.ToMM(b.GetWidth()) / 2, pcbnew.ToMM(b.GetHeight()) / 2
            owner = f"{fp.GetReference()}.{pad.GetNumber()}"
            if (pad.GetNetname() != "GND" or not pad.IsOnLayer(pcbnew.F_Cu) or not pad.GetNumber() or max(hw, hh) > 1.0
                    or owner in served):
                continue
            c = pad.GetPosition()
            cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            x, y = round(cx + ux * (hw + reach), 3), round(cy + uy * (hh + reach), 3)
            if barred(x, y) or any(q[0] - 0.3 < x < q[2] + 0.3 and q[1] - 0.3 < y < q[3] + 0.3 for q in lands):
                continue
            out["vias"].append([x, y, f"{owner}/{option}"])
            out["tracks"].append([round(cx, 3), round(cy, 3), x, y, f"{owner}/{option}"])
            tried += 1
    save(sys.argv[4], out)
    print(f"option {option}: {tried} ground pads without a via of their own")

elif cmd == "islands":
    # A piece of pour between tracks can hang on one pad and reach nothing else: give it vias.
    base = load(sys.argv[2])
    out = {"vias": list(base["vias"]), "tracks": list(base["tracks"])}
    have = [(x, y) for x, y, _ in base["vias"]]
    pt = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
    tried, step, r = 0, 0.1, VIA / 2 + 0.1
    for zone in board.Zones():
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if zone.GetNetname() != "GND" or not zone.IsOnLayer(layer):
                continue
            filled = zone.GetFilledPolysList(layer)
            for i in range(filled.OutlineCount()):
                piece = pcbnew.SHAPE_POLY_SET()
                piece.AddOutline(filled.Outline(i))
                for h in range(filled.HoleCount(i)):
                    piece.AddHole(filled.Hole(i, h))
                if any(piece.Contains(pt(x, y)) for x, y in have):
                    continue
                box, points = piece.BBox(), []
                x0, y0 = pcbnew.ToMM(box.GetLeft()), pcbnew.ToMM(box.GetTop())
                ring = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7))
                for a in range(int(pcbnew.ToMM(box.GetWidth()) / step) + 1):
                    for b in range(int(pcbnew.ToMM(box.GetHeight()) / step) + 1):
                        x, y = round(x0 + a * step, 3), round(y0 + b * step, 3)
                        # How deep in the piece the point lies; the rule check has the last word.
                        depth = next((d for d in (r, 0.2, 0.1, 0.02)
                                      if all(piece.Contains(pt(x + dx * d, y + dy * d)) for dx, dy in ring)), 0)
                        if depth:
                            points.append((depth, x, y))
                picked = []
                for _, x, y in sorted(points, reverse=True):
                    if len(picked) < 6 and all(math.hypot(x - q[0], y - q[1]) >= 0.7 for q in picked):
                        picked.append((x, y))
                out["vias"] += [[x, y, ""] for x, y in picked]
                tried += len(picked)
    save(sys.argv[3], out)
    print(f"{tried} vias to try in pieces of pour without one")

elif cmd == "pre":
    # The ground pads of the small parts get their via before the router starts, so that it
    # routes around them: afterwards the room beside a pad is often gone.
    boxes = []                                # (pad, left, top, right, bottom) of every pad
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not copper(pad):
                continue
            b = pad.GetBoundingBox()
            boxes.append((pad, pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()), pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom())))
    off = [tuple(q) for q in no_via]
    gap = lambda x, y, b: math.hypot(max(b[1] - x, 0, x - b[3]), max(b[2] - y, 0, y - b[4]))
    out = {"vias": [], "tracks": []}
    missed = []
    # The pad under a chip is its ground: a square of vias in it, straight into the plane.
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            w, h = pcbnew.ToMM(b.GetWidth()), pcbnew.ToMM(b.GetHeight())
            if pad.GetNetname() == "GND" and copper(pad) and min(w, h) > 2.0:
                c = pad.GetPosition()
                nx, ny = max(2, int((w - 1.0) / 1.6) + 1), max(2, int((h - 1.0) / 1.6) + 1)
                for i in range(nx):
                    for j in range(ny):
                        out["vias"].append([round(pcbnew.ToMM(c.x) + (i - (nx - 1) / 2) * (w - 1.0) / (nx - 1), 3),
                                            round(pcbnew.ToMM(c.y) + (j - (ny - 1) / 2) * (h - 1.0) / (ny - 1), 3), ""])
    under_chips = len(out["vias"])
    # The straight ways between the pads of each radio net: a ground via in one of them sends
    # the radio line the long way round.
    net_settings = load("kicad/card.kicad_pro")["net_settings"]
    radio = {q["pattern"] for q in net_settings["netclass_patterns"] if q["netclass"] == "Radio"}
    ways = []
    for net in radio:
        ends = [((o[1] + o[3]) / 2, (o[2] + o[4]) / 2) for o in boxes if o[0].GetNetname() == net]
        ways += [(a, b) for i, a in enumerate(ends) for b in ends[i + 1:] if math.dist(a, b) < 4.0]

    def off_way(x, y, a, b):
        L = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
        t = 0 if L == 0 else max(0, min(1, ((x - a[0]) * (b[0] - a[0]) + (y - a[1]) * (b[1] - a[1])) / L))
        return math.hypot(x - a[0] - t * (b[0] - a[0]), y - a[1] - t * (b[1] - a[1]))

    chips = []                                # the land patterns of the parts with many pins
    for fp in board.GetFootprints():
        own = [o for o in boxes if o[0].GetParentFootprint().GetReference() == fp.GetReference()]
        if len(own) > 8:
            chips.append((min(o[1] for o in own), min(o[2] for o in own), max(o[3] for o in own), max(o[4] for o in own)))
    for fp in board.GetFootprints():
        if len(fp.Pads()) > 6:
            continue                          # a chip's ground pins are joined after routing
        for pad in fp.Pads():
            b = pad.GetBoundingBox()
            hw, hh = pcbnew.ToMM(b.GetWidth()) / 2, pcbnew.ToMM(b.GetHeight()) / 2
            if pad.GetNetname() != "GND" or not pad.IsOnLayer(pcbnew.F_Cu) or pad.GetNumber() == "" or max(hw, hh) > 1.0:
                continue
            owner = f"{fp.GetReference()}.{pad.GetNumber()}"
            c = pad.GetPosition()
            cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            others = [o for o in boxes if o[0].GetPosition() != c or o[0].GetParentFootprint().GetReference() != fp.GetReference()]
            found = []
            for option in range(24):
                reach = (0.4, 0.75, 1.1)[option // 8]
                ux, uy = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))[option % 8]
                x, y = round(cx + ux * (hw + reach), 3), round(cy + uy * (hh + reach), 3)
                if not (INSET <= x <= data["length"] - INSET and INSET <= y <= data["width"] - INSET):
                    continue
                if any(k[0] - 0.12 < x < k[2] + 0.12 and k[1] - 0.12 < y < k[3] + 0.12 for k in off):
                    continue
                if any(gap(x, y, o) < VIA / 2 + 0.15 for o in others):
                    continue
                along = [(cx + (x - cx) * i / 8, cy + (y - cy) * i / 8) for i in range(9)]
                if any(gap(px, py, o) < TRACK / 2 + 0.12 for px, py in along for o in others):
                    continue
                if any(math.hypot(x - q[0], y - q[1]) < 0.7 for q in out["vias"]):
                    continue
                if any(off_way(px, py, a, b) < 0.42 for px, py in along[4:] for a, b in ways):   # past the pad itself
                    continue
                # Away from the chips: the room next to their pins is for their own vias.
                away = min([math.hypot(max(q[0] - x, 0, x - q[2]), max(q[1] - y, 0, y - q[3])) for q in chips] + [3.0])
                found.append((away - 0.5 * reach, -option, x, y, option))
            if found:
                _, _, x, y, option = max(found)
                out["vias"].append([x, y, f"{owner}/{option}"])
                out["tracks"].append([round(cx, 3), round(cy, 3), x, y, f"{owner}/{option}"])
            else:
                missed.append(owner)
    save(sys.argv[2], out)
    print(f"{under_chips} vias under chips, {len(out['vias']) - under_chips} ground pads given a via before routing; "
          f"none found for {missed}")
