# Design review

Done on 2026-11-23, by reading the circuit in `electrical/gen/design.py` net by net, the fit
model, and the placed board in `electrical/out/board.json`, and by looking up prices and two
facts about the power chip. It is a review on paper by the same hand that made the design:
no second person, no simulation, no bench. The scripts already prove that the nets are the
ones written, that the pin rules hold and that the boxes fit; this review looks at what
they cannot see.

## Wrong, and corrected in this review

| What | Why it was wrong | Now |
| --- | --- | --- |
| Cell protection sense resistor, 0.25 ohm | Copied from the band, where it trips at about 200 mA. This card charges at 225 mA: the protection would have cut the charge | 0.05 ohm, about 1 A, with a test |
| Flash, 1 Gbit | Listed at about 15 dollars a piece and out of stock: more than every other part on the board together | 256 Mbit, about 1.6 dollars, same pads; 3 h 38 min of buffer |
| No thermistor | A 450 mAh pouch charged at 225 mA in a closed card with no temperature reading | A 10 k thermistor on the charger's input, by the cell tabs |
| Light after a firmware mute | With the switch on and the load switch opened by firmware, nothing emptied the listening rail: the light could stay on for seconds, or half on | 1 Mohm from the rail to ground |
| Gap for the microphone gaskets, 0.1 mm | No gasket with a membrane is that thin | 0.25 mm. The spare over the tallest part drops from 0.3 to 0.15 |
| Call sensor "pressed to the back skin with adhesive" | It measures the shaking of its own body: a soft pad on its lid does nothing | The board is fixed to the back skin by a post beside the sensor |
| "A 3.0 mm card is one part away" | With the real gasket gap it is two: a lower button and a thinner board | Said so in the design document |

## Resolved in a second pass, the same day

The most serious open points of the first pass, and what was done about each. "Resolved"
here means resolved on paper: a document read, a part changed, a rule written, a
calculation made. None of it is a measurement.

| Was | Done | Left |
| --- | --- | --- |
| The slide switch's drawing unread; it might have pointed up from the board | Changed to Alps SSSS811101, whose catalogue was read: slider parallel to the board, 1.5 mm beyond the body. Its land pattern replaces the placeholder | Distances across the body were read off a small figure: take them from Alps's CAD data |
| The slider did not reach the outside of the card | A hollow 0.8 mm deep in the edge: the slider stands 0.55 mm proud in it, flush with the outline. The model fails if it stands less than 0.5 | The hollow, its slot and the seal are not drawn |
| Antenna 1.5 mm over aluminium | Both skins stop 10 mm short at the antenna end; plastic there. The antenna is tuned for the card on a table, the case that needs range | Range still unmeasured |
| Bending, with a lithium pouch inside | Both skins aluminium. Calculated: 0.08 mm of sag and a 4.9 m radius under 100 N on 70 mm if the skins are glued to the frame; useless if they slip | The glue line is the structural part and is not designed; no cell maker has said what radius a pouch tolerates |
| Four placeholder land patterns | Switch, button, light and call sensor are now drawn from their makers' documents. The call sensor's pin numbers are the datasheet's, and the earlier guess was wrong on every pin | The button's and switch's patterns are assumed centred under the body |
| Nordic pin tables read once | Both read again, word for word, by a second reader: no difference on any of 81 pins | The supply filtering and antenna matching, taken from the ring, are still not checked against Nordic's layout files |
| Firmware rules nowhere written | `firmware-requirements.md`: fourteen rules, each with a check | Nothing enforces them but a review of the firmware |
| Debug port outside, audio readable from a lost card | Rule 5: access protection on, audio in the flash encrypted with a key that the chip erase destroys | Firmware work; the hardware is unchanged |
| A slide switch carrying one milliamp | The Alps part is rated down to 50 uA; the card draws about 1.3 mA | Its minimum is stated at 3 V and the rail is 1.8 V: watch for it on the first cards |
| Nothing behind the board where the charger presses | Two posts from the back skin behind the pads, one beside the call sensor; the board keeps them clear, and a test fails if a pad has no post near it | The posts are boxes in a model, not a moulded part |
| The button held only by its solder | The part chosen stands 30 N of push by its maker's figure | |
| Cell tabs with no way to the board | The cell is ordered with a flexible tail; the rib has a gap by the pads for it | Not in the fit model: the tail is not drawn |
| The charging pad's protection diode 10 mm from the pad | The placer now puts protection diodes at their pads; a test checks all three | |
| Call sensor "pressed to the skin" | Its datasheet says it senses across the board, which is how a phone's back moves, and asks for no class 2 capacitor beside it: the capacitor next to it is now C0G | Whether it hears enough is still the first measurement |

## Still open, most serious first

1. **Whether the call sensor hears the far side of a call** through a phone's back, a
   sleeve and the card. One evaluation board and three phones answer it.
2. **Which clock edge the microphone uses.** The call sensor and microphone A share a
   data line and must speak on opposite edges. The sensor's table was read; the
   microphone's was not. If both conventions are the same the wiring is right as it is;
   if not, one resistor position swaps it. Read the T5838 table before routing.
3. **The power budget.** Every decision about thickness and cell rests on a sum that is
   five times kinder than what Plaud publishes. A development kit and a morning settle it.
4. **The joint between skins and frame.** See above: it is what makes the card stiff.
5. **Radio next to microphone A.** The antenna is 9 mm from it. A burst radio can be heard
   in a microphone. The plastic end makes it no better. Microphone B, 75 mm away, is the
   comparison and the fallback.
6. **Heat while charging.** About 0.3 W inside a closed card. The thermistor now watches
   it; nobody has estimated how warm the aluminium gets under a hand.
7. **A call needs two channels** and the protocol carries one. Firmware and protocol work.
8. **3.5 mm, and 0.1 mm to spare.** The switch is 1.4 mm tall in 1.5 mm of room. Every gap
   in the model is nominal; a tolerance study may ask for 3.6.
9. Smaller: the light is twice as bright on the charger; the 32 MHz crystal is 2.5 mm from
   the antenna end; the board is a ruler 82.6 x 14 x 0.6 mm and needs a carrier in the
   oven; the pads are gold on a face that lives in pockets; no seal is designed and no
   water rating is claimed; the light stands only 200 V of static and sits behind an
   insert that must keep fingers off it.

## Checked and found sound

- The recording switch is the only supply of the microphones and of the call sensor, and
  its off position grounds their rail. The pin that reads the rail does so through 10 k
  and cannot lift a grounded rail. A test fails if any part that could feed the rail is
  added.
- The light's gate is that rail and nothing else; firmware has a way to add light and no
  net that removes it. Tested.
- Every pad a finger can reach, except ground, has a protection diode, placed at the pad. Tested.
- One clock for three listening parts at 768 kHz is inside the low-power range of both
  kinds (the microphone's and the sensor's 600 to 950 kHz, read from its datasheet).
- The power chip gives 200 mA at 1.8 V; the card draws a few milliamps, with peaks of some
  tens while the flash erases. The load switches give 100 mA; the microphones and sensor
  take about 1.
- Board area: the small parts need 5 % of what is free. Space is not the problem on this
  board; its shape is.
- Both stacks add up to the card's height, and the test that says so runs on every build.

## Not checked at all

Routing, because there is none: power loops, the crystal's guard, the antenna feed, return
paths. The supply filtering of the microcontroller, taken from the ring. Tolerances: every
gap in the fit model is nominal. Electromagnetic compatibility, safety of the cell,
drop, and anything that needs the thing in a hand.
