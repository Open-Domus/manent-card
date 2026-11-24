"""Hand the placed board to an autorouter and bring the tracks back.

Runs with KiCad's own Python:   python3 gen/pcb_route.py export | import <session file>
`export` writes out/card.dsn; Freerouting turns it into a session file; `import` reads that
into the board, adds ground pours on both outer layers, fills them and saves.
"""
import json
import re
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parents[1]
pcb = str(HERE / "kicad" / "card.kicad_pcb")
board = pcbnew.LoadBoard(pcb)
if sys.argv[1] == "export":
    dsn = HERE / "out" / "card.dsn"
    assert pcbnew.ExportSpecctraDSN(board, str(dsn))
    text = dsn.read_text()
    assert "(clearance 90)" in text
    text = text.replace("(clearance 90)", "(clearance 100)")            # route at 0.1, check at 0.09
    # The first inner layer is the ground plane: tell the router it is not for signals.
    plane_layer = "(layer In1.Cu\n      (type signal)"
    assert plane_layer in text
    text = text.replace(plane_layer, "(layer In1.Cu\n      (type power)")
    # Ground is not the router's job: it tries to draw sixty ground connections track by track and
    # loses the signals doing it. The net keeps one pin, so that the plane still has a net and the
    # router stays off that layer; the other ground pads become obstacles. The pours, the plane and
    # the vias of gen/pcb_stitch.py join them after the import.
    # The pin kept is the ground test point: a wide pad with room for the one via it needs.
    text, n = re.subn(r"(\n    \(net GND\n      \(pins )[^)]*\bTP5-1\b[^)]*\)", r"\1TP5-1)", text)
    assert n == 1
    # Areas the router must respect (board.json, "reserved"); y points down in KiCad, up here.
    data = json.loads((HERE / "out" / "board.json").read_text())
    um = lambda v: round(v * 1000)
    rect = lambda layer, q: f"(rect {layer} {um(q[0])} {-um(q[3])} {um(q[2])} {-um(q[1])})"
    lines = []
    for r in data["reserved"]:
        lines += [f'    (via_keepout "{r["name"]}" {rect(layer, r["box"])})' for layer in ("F.Cu", "In2.Cu", "B.Cu")]
        if r["kind"] == "antenna":
            lines += [f'    (keepout "{r["name"]}" {rect(layer, r["box"])})' for layer in ("In2.Cu", "B.Cu")]
    for fp in board.GetFootprints():        # nothing between the two pads of a crystal
        boxes = [p.GetBoundingBox() for p in fp.Pads() if p.GetNumber() and p.IsOnLayer(pcbnew.F_Cu)]
        if fp.GetReference().startswith("Y") and len(boxes) == 2:
            a, b = sorted(boxes, key=lambda q: (q.GetLeft(), q.GetTop()))
            mmv = pcbnew.ToMM
            if a.GetRight() < b.GetLeft():
                q = (mmv(a.GetRight()) + 0.2, mmv(a.GetTop()), mmv(b.GetLeft()) - 0.2, mmv(a.GetBottom()))
            else:
                q = (mmv(a.GetLeft()), mmv(a.GetBottom()) + 0.2, mmv(a.GetRight()), mmv(b.GetTop()) - 0.2)
            if q[2] > q[0] and q[3] > q[1]:
                lines.append(f'    (keepout "{fp.GetReference()}" {rect("F.Cu", q)})')
    # The radio line stays on the top layer, over the plane: no via, no inner layer.
    text, n = re.subn(r"(\(class Radio\b.*?\(circuit\s*)", r"\1(use_layer F.Cu)\n      ", text, flags=re.S)
    assert n == 1
    marker = '\n    (via "Via'
    assert marker in text                   # the first one is in the structure section
    text = text.replace(marker, "\n" + "\n".join(lines) + marker, 1)
    dsn.write_text(text)
    print(f"out/card.dsn written, {len(lines)} keep-outs")
else:
    assert pcbnew.ImportSpecctraSES(board, str(HERE / sys.argv[2]))
    narrow = 0
    for t in board.GetTracks():             # the router necks some tracks down below the board's minimum
        if t.Type() != pcbnew.PCB_VIA_T and t.GetWidth() < pcbnew.FromMM(0.09):
            t.SetWidth(pcbnew.FromMM(0.09))
            narrow += 1
    print(f"{narrow} segments widened to 0.09 mm")
    necked = 0
    net_settings = json.loads((HERE / "kicad" / "card.kicad_pro").read_text())["net_settings"]
    radio = {p["pattern"] for p in net_settings["netclass_patterns"] if p["netclass"] == "Radio"}
    want = pcbnew.FromMM(next(c["track_width"] for c in net_settings["classes"] if c["name"] == "Radio"))
    for t in board.GetTracks():             # and it necks the radio line, whose width sets its impedance
        if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() in radio and t.GetWidth() < want:
            t.SetWidth(want)
            necked += 1
    print(f"{necked} radio segments brought back to their width")
    # No poured copper next to the radio line on the top layer: only the plane under it.
    data = json.loads((HERE / "out" / "board.json").read_text())
    x0, y0, x1, y1 = (pcbnew.FromMM(v) for v in data["rf_region"])
    if not any(z.GetZoneName() == "radio line: no top pour" for z in board.Zones()):
        area = pcbnew.ZONE(board)
        area.SetZoneName("radio line: no top pour")
        shape = area.Outline()
        shape.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            shape.Append(x, y)
        area.SetIsRuleArea(True)
        area.SetLayer(pcbnew.F_Cu)
        area.SetDoNotAllowZoneFills(True)
        area.SetDoNotAllowTracks(False), area.SetDoNotAllowVias(False), area.SetDoNotAllowPads(False)
        area.SetDoNotAllowFootprints(False)
        board.Add(area)
    # Ground pours on both outer layers, around the tracks: the router counts on the inner plane
    # to join every ground pad, and leaves a few ground tracks that never reach it.
    plane = next(z for z in board.Zones() if z.GetZoneName() == "ground plane")
    chain = plane.Outline().Outline(0)
    have = {z.GetLayer() for z in board.Zones() if not z.GetIsRuleArea()}
    for layer, name in ((pcbnew.F_Cu, "ground pour, top"), (pcbnew.B_Cu, "ground pour, bottom")):
        if layer in have:
            continue
        pour = pcbnew.ZONE(board)
        shape = pour.Outline()
        shape.NewOutline()
        for i in range(chain.PointCount()):
            shape.Append(chain.CPoint(i).x, chain.CPoint(i).y)
        pour.SetLayer(layer)
        pour.SetNetCode(plane.GetNetCode())
        pour.SetZoneName(name)
        pour.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        pour.SetMinThickness(pcbnew.FromMM(0.1))
        pour.SetLocalClearance(pcbnew.FromMM(0.15))
        pour.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        board.Add(pour)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(pcb, board)
    tracks = board.GetTracks()
    vias = sum(1 for t in tracks if t.Type() == pcbnew.PCB_VIA_T)
    # Every track segment, for the tests: net, layer, width, length, ends.
    rows = [[t.GetNetname(), t.GetLayerName(), pcbnew.ToMM(t.GetWidth()), round(pcbnew.ToMM(t.GetLength()), 4),
             pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)]
            for t in tracks if t.Type() != pcbnew.PCB_VIA_T]
    (HERE / "out" / "tracks.json").write_text(json.dumps(rows) + "\n")
    (HERE / "out" / "vias.json").write_text(json.dumps(
        [[t.GetNetname(), pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)]
         for t in tracks if t.Type() == pcbnew.PCB_VIA_T]) + "\n")
    print(f"{len(tracks) - vias} track segments, {vias} vias -> card.kicad_pcb")
