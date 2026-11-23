# Manent card: hardware

Hardware design of the Manent card: a voice recorder with the outline of a payment card,
3.5 mm thick, that rides on the back of a phone or lies on the table in a meeting. A slide
switch starts it, a sensor lets it hear the phone it rides on, and the words reach the
phone as audio over Bluetooth LE. It is the
sibling of the ring in `manent-ring` and of the band in `manent-band`, in the form of the
Plaud Note and of Amazon's Bee Eclipse. Firmware and radio protocol live in the
`mnemo-band` repository.

Nothing here has been built or measured. This is a first design on paper, checked by
scripts. Its choices are made and each says what would overturn it; several parts are
chosen from listings whose datasheets have not been read.

| What | Where |
| --- | --- |
| Design document: requirements, architecture, decisions | [docs/design.md](docs/design.md) |
| Does it fit? Card, the two stacks, cell, board area | [docs/space-budget.md](docs/space-budget.md) |
| How long does it last? | [docs/power-budget.md](docs/power-budget.md) |
| What it costs to make | [docs/cost-estimate.md](docs/cost-estimate.md) |
| Design review: what was checked, what was wrong, what is at risk | [docs/review.md](docs/review.md) |
| What was decided and why, what is unknown, and what would settle it | [docs/open-questions.md](docs/open-questions.md) |
| Parts with sizes and how far each is verified | [parts/parts.yaml](parts/parts.yaml) |
| Circuit, as data | [electrical/gen/design.py](electrical/gen/design.py) |
| Schematic (KiCad 10), PDF, bill of materials | `electrical/kicad/`, `electrical/out/` |
| Board: parts placed, nets assigned, not routed | `electrical/kicad/card.kicad_pcb`, `electrical/out/board-*.svg` |
| Fit model, drawings, STEP | `mechanical/`, `mechanical/out/` |

## Build

Needs `uv`, and either KiCad 10 or Docker (`docker pull kicad/kicad:10.0`).

```
make all        # schematic, board, checks, tests, fit report, drawings, budgets, STEP
make test       # tests only
```

The schematic and the board are generated: edit `electrical/gen/design.py` and the fit
model, never the `.kicad_sch` or `.kicad_pcb` files.
Every pin carries a label with its net name instead of drawn wires. `make schematic` runs
KiCad's rule check and compares the netlist KiCad reads with the one in `design.py`.

The board is placed, not routed: every part has a footprint, a position and its nets, and
no track is drawn.

## Licences

Hardware and the scripts that generate it under CERN-OHL-S v2 (`LICENSE`), documents under
CC BY-SA 4.0 (`LICENSE-docs`).
