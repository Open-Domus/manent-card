# Manent card: design

Status: first draft on paper, written 2026-11-23. No board, no card, no measurement.
Numbers are either from manufacturers' documents or estimates, and each table says which.
Choices marked "chosen" were made on 2026-11-23 when the project owner asked for the best
answer to every open question. Each says what it rests on, and
[open-questions.md](open-questions.md) says what would overturn it.

## What the card does

It is a voice recorder with the outline of a payment card. It rides on the back of the
phone or lies on the table. Slide its switch and it records; slide it back and it stops.
The words reach the phone as audio, to be turned into text there, and the card keeps a
recording only until the phone confirms it has it.

The ring records a thought; the band listens all day; the card records a meeting. It is
started on purpose like the ring and it runs for hours like the band. Its switch stays
where it was put, so anyone at the table can see whether it is on.

## Requirements

| Requirement | Source |
| --- | --- |
| Records only while its switch is on | chosen, as the ring: started by its owner |
| The switch cuts the power of everything that listens, not through firmware | chosen |
| A light other people can see whenever anything that listens has power | as the band |
| Hears both sides of a phone call when it is on the phone | chosen: see "Phone calls" |
| At least 30 hours of recording on a charge; 40 is the stretch goal | chosen: what Plaud publishes for its Note; a working week |
| A long meeting, three and a half hours, kept with the phone out of reach | chosen: the card lives next to its phone; more costs ten times as much |
| 16 kHz mono, Opus at about 16 kbit/s encoded on the card | `mnemo-band` |
| Bluetooth LE; store and forward; one phone; no server of ours; no Wi-Fi | `mnemo-band` |
| Firmware the owner can rebuild and load | as the ring |
| Outline of a payment card, 85.6 x 54.0 mm | what Plaud and Bee ship |
| 3.5 mm thick | chosen: see "Why 3.5 mm" |
| Two microphones; one switch and one button, both on the edge | chosen |
| Closed card, charged through pads on its face; no USB socket | chosen: a socket is as thick as the card |
| No magnets in the card: a sleeve holds it to the phone | chosen: see "On the phone" |
| No vibration motor, no screen | chosen |

## Switch and button

| Gesture | Meaning | Handled by |
| --- | --- | --- |
| Switch on | Record | the switch: it powers the microphones, the call sensor and the light |
| Switch off | Stop | the switch |
| Short press of the button, while recording | Mark this moment | firmware |
| Button held while the switch goes on, and for 5 s more | Factory reset | firmware |
| Press while in ship mode (96 ms) | Wake from storage | power chip |
| Hold 10 s | Power cycle: the way out of a hung firmware | power chip |

The factory reset takes two hands and two controls, so it does not happen in a pocket, and
it ends before the power chip's ten seconds. The card puts itself in ship mode after
14 days with the switch off and no phone in reach; the button wakes it.

The switch is not a request to the firmware. It is a part in the supply line of the
microphones and of the call sensor: off, they have no power and their rail is tied to ground. Firmware reads the
rail through a resistor to know when to start encoding. It can also refuse to record, by
opening the load switch upstream (flash full, cell empty); it cannot record with the
switch off.

## Light

One red LED, about 0.5 mA. Its switch is driven by the supply rail of the microphones and
of the call sensor, not by firmware: if anything that listens has power, the light is on,
and there is no code path that can record in the dark. A second path lets firmware add
light, to blink for a mark, for charging and for errors. It has no pin that can remove
the light.

The LED sits 1.3 mm from the edge of the card, between the switch and the button, mounted
upside down over a hole in the board. A clear insert in the corner of the card carries its
light to the front and to the edge. So it is seen with the card face up on a table, on the
back of a phone held to an ear, and, from the edge, with the card face down.

The card records for a few hours a day, not for all of it, so the light can be ten times
brighter than the band's steady glow and still take under a quarter of the recording
current. Whether 0.5 mA is seen across a table in daylight is not known.

## Blocks

```
contact pads --TVS-- VBUS --> [ nPM1300 ] <--> cell (+ protection)
                               |  |  |
                  1.8 V buck --+  |  +-- load switch 2 --> flash supply
                               |  +----- load switch 1 --> RECORDING SWITCH --> listening supply --> light
                               v                                  |
   button --+--> SHPHLD     [ nRF54L15 ] <----- 10k --------------+
            +-|<|-> wake      |  |  |
                         SPI --+  |  +-- matching -- tuning -- antenna
                          v       +--PDM--> microphone A + call sensor; microphone B
                    256 Mbit flash
```

One logic rail at 1.8 V, as on the ring: the microphones accept nothing higher.

## Parts

| Block | Part | Size (mm) | Why | Confidence |
| --- | --- | --- | --- | --- |
| Microcontroller | Nordic nRF54L15, QFN48 | 6 x 6 x 0.85 | The firmware targets it; its PDM clock suits the microphone | as on the band: pin table read once |
| Power | Nordic nPM1300, QFN32 | 5 x 5 x 0.85 | Charges at 32 to 800 mA; the band's nPM1304 stops at 100 mA, five hours for this cell | pin names match the nPM1304's, pin for pin; read through a summary |
| Flash | Winbond W25Q256JWEIQ, WSON-8 | 8 x 6 x 0.8 | 256 Mbit holds about 3 h 38 min not yet uploaded, for a tenth of the price of 1 Gbit | distributor listing; height and pin order not read |
| Microphones | 2 x TDK T5838 | 3.5 x 2.65 x 0.98 | Already planned by the firmware; sound enters through the board | verified |
| Call sensor | Syntiant V2S200D | 3.3 x 2.3 x 0.93 | Hears the phone through its back; PDM, 1.8 V, 290 uA at the microphones' clock; senses across the board | datasheet read: pins, land pattern, clock edges |
| Recording switch | Alps SSSS811101 | 6.7 x 2.6 x 1.4 | Slider parallel to the board, 1.5 mm beyond the body; works down to 50 uA; two bosses and four ground lands hold it | maker's catalogue read: drawing and land pattern |
| Button | Panasonic EVQP7J01P | 3.5 x 2.9 x 1.35 | Side push, 1.6 N, stands 30 N, on the board surface | catalogue read: drawing and land pattern |
| Light | Wuerth 156125RS75000, reverse-mount | 3.2 x 1.2 x 1.1 | Sits with the other parts; its lens goes into a 1.75 mm hole in the board | datasheet read |
| Cell protection | ABLIC S-82A1A | 1.4 x 1.4 | Fitted only if the cell has none of its own | verified |
| Exposed pads | 3 x Infineon ESD230-B1-W0201 | 0.58 x 0.28 | One on the charging pad, one on each service pad | verified; capacitance on a debug line not checked |
| Cell | flat LiPo pouch, 2.0 x 35 x 80 | 80 x 35 x 2.0 | See the space budget | custom size: makers offer 2.0 mm cells to order; none asked yet |

The full list with part numbers is `electrical/out/bom.csv`. Both Nordic chips are the QFN
versions, on an ordinary four-layer board, for the reasons and with the caveats written in
the band's design document. Both pin tables were read a second time, word for word, on
2026-11-23 and match. The power chip is the band's larger sibling in the same package: the pin tables were read once as page text, and the supply
filtering and antenna matching follow the ring's verified circuit with the QFN values.

### Microcontroller pins

| Signal | Pin | Rule it satisfies |
| --- | --- | --- |
| Listening clock; data line 1 (microphone A and call sensor) | P1.04, P1.05 | PDM lives on port 1; the clock is on a clock pin |
| Data line 2 (microphone B) | P1.14 | port 1 |
| Microphone A threshold, wake | P1.06, P1.07 | port 1 can wake the chip |
| Microphone B threshold, wake | P1.09, P1.10 | port 1 can wake the chip |
| Recording switch, read | P1.08 | port 1 can wake the chip |
| Microphone power request | P1.13 | to the power chip's GPIO1, which drives load switch 1 |
| Flash clock, out, in, select | P2.01, P2.02, P2.04, P2.05 | the dedicated fast-SPI pins |
| Power chip clock, data, interrupt | P0.03, P0.02, P0.01 | clock on a clock pin; port 0 can wake the chip |
| Button | P0.00 | port 0 can wake the chip |
| Extra light | P0.04 | |
| Test serial port | P1.11, P1.12 | test pads on the board |
| 32.768 kHz crystal | P1.00, P1.01 | fitted |

Everything but the recording switch and the second data line is where the band has it, so one firmware pin map
serves both. `electrical/gen/checks.py` enforces these rules on every build.

### Choices worth explaining

- **A switch, not a button, starts the recording.** A meeting lasts an hour and a slide
  switch shows its state for all of it, to the owner and to the others. Plaud's Note has a
  switch too, but there it chooses between two ways of recording and a button starts them.
- **The switch is in the supply.** It costs nothing more than wiring it to a pin would, and
  it turns "the firmware promises" into "the copper cannot". Its off position grounds the
  rail, so the light goes out at once and the pin that reads the rail cannot feed it.
- **256 Mbit of flash.** At 16 kbit/s an hour of speech is 7.2 MB. Plaud's 64 GB would hold
  a year of it. The card lives next to its phone and sends as it records, so the flash
  only bridges the gaps: 256 Mbit is 3 h 38 min. The 1 Gbit part chosen at first is listed
  at about 15 dollars, more than the rest of the board, and was out of stock; this one is
  about 1.6. The 512 Mbit and 1 Gbit parts fit the same pads if a buyer wants the day.
  It sits behind load switch 2.
- **A thermistor by the cell tabs.** The charger reads it and stops when the closed card is
  too warm or too cold. The band grounds that pin.
- **Bluetooth only.** At an assumed 400 kbit/s an hour of audio crosses in about two and a
  half minutes, and it crosses while it is being recorded if the phone is in reach. Wi-Fi
  would bring a second radio and its current for a need the card does not have.
- **Two microphones, at the two ends of the board, 77 mm apart, on two data lines.** Line 1
  carries microphone A and the call sensor, one on each edge of the clock, so the chip's
  one audio interface hears the owner and the phone together: that is a call. Pointed at
  line 2 it hears microphone B, for when A's hole is under a thumb. Hearing both
  microphones at once needs a second interface in the chip, which was looked for in
  Nordic's documents and not found; nothing in the design depends on it.
- **The 32.768 kHz crystal is fitted**, as on the band: the card stays connected for weeks.
- **Pads, not a socket.** A USB-C socket is about 3.2 mm tall and the card is 3.5. Four
  2 mm pads on the bare face of the board show through windows in the front skin: two
  charge it, two carry SWDIO and SWDCLK, so the card can be reprogrammed closed. Being on
  the front they need no springs inside the card. They are at one end only, so a card laid
  on its charger the wrong way round touches nothing. Each pad that is not ground has a
  protection diode, because fingers reach them.
- **The larger power chip.** Half the cell's capacity per hour is 225 mA, which fills it
  in about two and a half hours. The band's chip cannot give more than 100.
- **Button to two chips**, as on the ring: to the power chip's ship-mode input, and through
  a diode to the microcontroller.

## Phone calls

Plaud's cards hear both sides of a call: next to their microphones they list a sensor that
picks up the phone's own sound through its back. Amazon names calls among the uses of the
Bee Eclipse and does not say how. A card that rides on a phone and is deaf to the phone
would be the lesser product, so this card has the sensor too.

It is a Syntiant V2S200D (Knowles's design), a vibration sensor that speaks the microphones' own digital
language at their own voltage and clock. It sits in the middle of the board, on the face
towards the phone. It measures how its own body shakes across the board, which is the way
a phone's back moves, so the board under it is fixed stiffly to the back skin with a post
beside it. It hangs on
the same switched rail as the microphones: the switch that silences them silences it, and
the light that follows them follows it.

What is not known: how much of a phone's earpiece reaches the back of the phone, through a
sleeve and an aluminium skin, on which phones. That is the first measurement to make, with
the sensor's evaluation board taped to three phones, before any card exists.

The rules on recording a call differ by country. The card does not enforce any of them:
that is left to its owner, by the project owner's decision of 2026-11-23.

## On the phone

The card has no magnets. The ring of magnets that phones use for accessories is 54 to
56 mm across and 46 inside, 0.55 to 1 mm thick (sellers' figures; Apple's guideline is
quoted second-hand as 54.1). The card is 54 wide with a frame, so the ring does not fit in
it, and it would lie on the cell, where there is 0.14 mm to spare. So the card goes in a
thin sleeve that carries the ring, as Plaud's does, and phones without magnets get a steel
ring to glue on. The sleeve is not designed. It must leave open the edge with the switch,
the light and the button, the two microphone holes and the pads, and it must not come
between the call sensor and the phone with anything soft.

## Card and assembly

- A flat box 85.6 x 54.0 x 3.5 mm with 3.2 mm corners: a frame 1.2 mm wide and two skins
  0.5 mm thick, about 26 g with everything in it.
- **Both skins are aluminium, glued to a glass-filled plastic frame.** The card gets sat on
  and a lithium pouch must not be bent. Under 100 N across 70 mm the two skins, working
  together, sag 0.08 mm; an aluminium back with a plastic front sags five times as much.
  Either is useless if the skins slip on the frame, so the glue line all round, and along
  the rib, is the structural part of the shell. See the space budget.
- **At the antenna end both skins stop 10 mm short**, over the board strip, and the frame's
  plastic takes their place. The antenna has no metal above or below it.
- The aluminium back also carries the phone's vibration to the call sensor, through a post
  to the board beside it. Two more posts stand behind the contact pads, so the charger's
  spring pins press on something.
- Where the front skin has windows for the pads, the frame's plastic lines them, so a
  spring pin cannot touch the skin.
- The board is a strip 82.6 x 14.0 mm, 0.6 thick, along one long edge. The cell lies
  beside it, with a rib of the frame between them. Nothing is stacked on the cell.
- Every part is on the face of the board that looks at the phone. The other face lies
  under the front skin, with only the four pads on it. One-sided assembly.
- The microphones' sound comes from the front, through a hole in the skin, a gasket and a
  hole in the board. The light shines the same way through its own hole.
- Switch and button are on the edge of the card, about 24 mm apart, the light between them.
  The switch's slider stands 0.55 mm proud in a hollow 0.8 mm deep in the edge, flush with
  the card's outline: a finger finds it, a pocket does not move it. The button's knob
  ends 0.55 mm outside the board and a cap in the frame carries it to the edge.
- The cell's tabs are on one of its short sides and the board is along a long one: the cell
  is ordered with a flexible tail that passes a gap in the rib, next to the pads for it.
- The call sensor is in the middle of the board, glued through to the back skin.
- Openings in the front skin: two microphone holes and four pad windows. In the frame: the
  hollow and slot for the switch, a cap for the button, the clear insert of the light. In
  the back skin: none.
- The antenna takes one corner of the board, with no copper under it, inside the plastic end.

Whether it all fits is in [space-budget.md](space-budget.md). In short: at 3.5 mm
everything fits with a cell of about 450 mAh and 0.1 mm to spare over the tallest part,
the switch.

### Why 3.5 mm

Plaud's card is 3.0. At 3.0 the cell still fits, 1.5 mm thick and about 335 mAh. The board
side is 0.4 too thick: the switch is 1.4 mm tall, the button 1.35, and the gap for the
microphone gaskets takes 0.25. Lower parts are listed (a Same Sky switch at 1.1, Panasonic's
EVP-AN button at 0.7 in a cut-out) but their drawings could not be read, and a 0.4 mm
board would be needed as well. So 3.0 is three changes away, none of them verified.

It is still not chosen. The power budget may be wrong by the factor that separates it from
what Plaud publishes, about five. At five times the budget's current the 450 mAh cell
records for about 31 hours and meets the requirement; the 335 mAh one records for 23 and
does not. Half a millimetre buys the certainty. If the bench shows the budget is right,
the thin card becomes the better one.

## Board

`electrical/kicad/card.kicad_pcb`: four copper layers, 82.6 x 14.0 mm with rounded
corners, seen from the phone side. Top copper carries the parts, bottom copper lies under
the front skin, the first inner layer is a ground plane with none of it under the antenna
corner.

What is done:

- Every part of the schematic has a footprint and a place. The parts the card decides
  (chips, microphones, call sensor, switch, button, light, antenna, pads) are where the fit model puts
  them. The rest are placed by a script, each as near as it can get to the pads it
  connects to, 0.35 mm between land patterns and 0.4 mm from the board edge.
- Every pad carries its net. KiCad's check finds no difference between board and schematic
  and no rule violation in the placement.
- The rules in the project file are an ordinary fabricator's: 0.1 mm track and gap,
  0.4 mm vias with a 0.2 mm hole. They are an assumption, not a quote.

What is not done: **no track is routed.** All 184 connections are still open and the
ground plane is not poured. The placement is a machine's first arrangement. The footprints
of the switch, the button, the light and the call sensor are drawn from their makers'
drawings; those of the antenna and the cell tabs are placeholders until those are chosen.
Protection diodes are placed at their pads. The board is five times longer than it is wide and
0.6 mm thick: whether it survives assembly without a carrier has not been asked.

## Power

In [power-budget.md](power-budget.md). In short, on the 450 mAh cell: about 154 hours of
recording at the nominal figures and 93 at the worst, against a requirement of 30. Those
figures come from the vendor's numbers and a guessed encoder load, not from a bench, and
Plaud's published 30 hours from 400 mAh mean almost five times this budget's current. Plan
on the requirement, not on the budget. Charging takes about two and a half hours.

## Radio

Unknown until measured. The antenna sits in a plastic end 10 mm long with no metal over or
under it and aluminium beginning 4 mm from it on one side. On a table that is close to the
free space it is tuned for. On a phone, the phone's back is 2 mm behind it and detunes it,
but there the other end of the link is the phone itself, a few millimetres away, where a
detuned antenna is still far more than enough. The case that needs range is the card on a
table and the phone in a pocket, and that is the case the antenna is tuned for.

## Prior art

| Product | What it shows |
| --- | --- |
| Plaud Note | 85.6 x 54.1 x 3.0 mm (converted from inches), about 30 g, 400 mAh, 30 h of recording, 60 days of standby, 64 GB, two microphones and a sensor for calls, Bluetooth and 2.4 GHz Wi-Fi, a button, aluminium, a magnetic case and a magnetic ring in the box |
| Plaud Note Pro | Same outline and weight, 500 mAh, four microphones and the call sensor, a small screen, Wi-Fi on two bands |
| Bee Eclipse (Amazon) | "About the size of a credit card", attaches magnetically to the back of a phone, one button to turn it on and off, a light, more than 21 days claimed, 99.99 dollars, pre-orders from 2026-11-18 |

Read on 2026-11-23 from Plaud's comparison page and from Amazon's announcement and the
press, not from a device. Amazon publishes no dimensions, weight, cell, microphone count,
charging method or radio for the Eclipse, and no teardown of any of the three was found.
Sources disagree on whether the Eclipse's light means "on", "recording" or "summarising".
