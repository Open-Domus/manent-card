"""Build electrical/kicad/card.kicad_pcb from electrical/out/board.json.

Runs with KiCad's own Python (the pcbnew module), not the project environment:
    python3 gen/pcb_build.py          (from the electrical directory)
Footprints are placed and their pads given their nets, and the ground plane of the first inner
layer is outlined. No tracks are drawn, so the plane is left unpoured: nothing reaches it yet.
"""
import json
import math
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parents[1]
data = json.loads((HERE / "out" / "board.json").read_text())
lib = str(HERE / "kicad" / (data["lib"] + ".pretty"))
mm = pcbnew.FromMM
pt = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
L, W, R = data["length"], data["width"], data["corner_r"]

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
board.GetDesignSettings().SetBoardThickness(mm(data["thickness"]))
nets = {}
for part in data["parts"]:
    for name in part["nets"].values():
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])

for part in data["parts"]:
    fp = pcbnew.FootprintLoad(lib, part["footprint"])
    assert fp is not None, part["footprint"]
    fp.SetFPID(pcbnew.LIB_ID(data["lib"], part["footprint"]))
    fp.SetReference(part["ref"])
    fp.SetValue(part["value"])
    fp.SetPath(pcbnew.KIID_PATH(part["path"]))
    fp.SetDNP(part["dnp"])
    for key, value in part["fields"].items():
        fp.SetField(key, value)
        fp.GetField(key).SetVisible(False)
    board.Add(fp)
    fp.SetPosition(pt(part["x"], part["y"]))
    fp.SetOrientationDegrees(part["rot"])
    if part["side"] == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for pad in fp.Pads():
        net = part["nets"].get(pad.GetNumber())
        if net:
            pad.SetNet(nets[net])


def outline_points(inset=0.0, steps=8):
    """The rounded rectangle of the board, moved inwards by inset."""
    r = max(R - inset, 0.05)
    out = []
    for cx, cy, a0 in ((L - inset - r, inset + r, -90), (L - inset - r, W - inset - r, 0),
                       (inset + r, W - inset - r, 90), (inset + r, inset + r, 180)):
        for i in range(steps + 1):
            a = math.radians(a0 + 90 * i / steps)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def line(a, b, layer, width=0.05):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a)), s.SetEnd(pt(*b)), s.SetLayer(layer), s.SetWidth(mm(width))
    board.Add(s)


def note(text, x, y, layer, size=0.5):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text), t.SetPosition(pt(x, y)), t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))), t.SetTextThickness(mm(size / 6))
    board.Add(t)


def ground_plane(points):
    """Ground on the first inner layer."""
    z = pcbnew.ZONE(board)
    z.SetZoneName("ground plane")
    o = z.Outline()
    o.NewOutline()
    for x, y in points:
        o.Append(mm(x), mm(y))
    z.SetLayer(pcbnew.In1_Cu)
    z.SetNet(nets["GND"])
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetMinThickness(mm(0.1))
    z.SetLocalClearance(mm(0.15))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)


edge = outline_points()
plane = outline_points(0.3)
for a, b in zip(edge, edge[1:] + edge[:1]):
    line(a, b, pcbnew.Edge_Cuts)
for k in data["keepouts"]:
    x0, y0, x1, y1 = k["x"], k["y"], k["x"] + k["w"], k["y"] + k["h"]
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        line(a, b, pcbnew.Dwgs_User, 0.03)
    note(k["name"], (x0 + x1) / 2, y0 - 0.35, pcbnew.Cmts_User, 0.3)
    if k["name"].startswith("antenna"):
        # No ground under the antenna: the plane's outline steps around that corner, which is the
        # last one outline_points() draws. A notch, not a hole or a rule area: the autorouter reads
        # a rule area as "no tracks" and does not see holes.
        assert (x0, y0) == (0.0, 0.0)
        plane = [q for q in plane if not (q[0] < x1 and q[1] < y1)] + [(0.3, y1), (x1, y1), (x1, 0.3)]
note("Top copper carries the parts and faces the phone, bottom copper lies under the front skin. In1: ground. In2: signals.",
     L / 2, -1.2, pcbnew.Cmts_User, 0.5)
ground_plane(plane)

out = HERE / "kicad" / (data["project"] + ".kicad_pcb")
pcbnew.SaveBoard(str(out), board)
# Where KiCad really put every pad, for the test that compares it with what the placer assumed.
pads = [[fp.GetReference(), pad.GetNumber(), pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y),
         pad.GetNetname()] for fp in board.GetFootprints() for pad in fp.Pads() if pad.GetNumber()]
(HERE / "out" / "pads.json").write_text(json.dumps(pads) + "\n")
print(f"{len(data['parts'])} footprints, {len(nets)} nets -> {out.name}")
