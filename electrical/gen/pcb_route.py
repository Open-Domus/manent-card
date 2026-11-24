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
    dsn.write_text(text)
    print("out/card.dsn written")
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
    print(f"{len(tracks) - vias} track segments, {vias} vias -> card.kicad_pcb")
