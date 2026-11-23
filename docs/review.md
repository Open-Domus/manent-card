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

## Open, most serious first

### Could make the card not work

1. **The slide switch may point the wrong way.** Its datasheet was not read. If the slider
   stands up from the board instead of leaving by its edge, the card cannot be 3.5 mm with
   this part, and no other this low was found. Read the drawing before anything else.
2. **The slider does not reach the outside.** The switch is 1.5 mm inside the card (frame
   and gap) and its slider is listed as 1.5 mm long. As drawn, the finger cannot move it:
   the frame needs a slot and the slider a cap that rides on it. Not designed.
3. **The antenna lies 1.5 mm over an aluminium sheet.** That was chosen so that the antenna
   sees the same metal on a table and on a phone. The price may be most of the range. A
   chip antenna wants bare board and free space around it. Measure it with a development
   kit over a sheet of aluminium before the shell is drawn; the fallback is a window in
   the skin under that corner, or an antenna made for metal backing.
4. **Whether the call sensor hears anything.** Already the first measurement in the open
   questions. If it does not, the part and its 2.6 dollars go, and nothing else changes.
5. **Four parts have placeholder land patterns** (switch, button, light, call sensor), and
   the call sensor's pin numbers are those of an evaluation flex. A board made from this
   file would not take those parts. Known, and the reason the board is not routed.
6. **The two Nordic pin tables were read as page text**, and the nPM1300's through a
   summary. One wrong pin on either chip is a dead board. Compare with the package figures.

### Firmware must do this, and nothing in the hardware forces it

7. **Pins into unpowered parts.** With the recording switch off the listening rail is at
   ground, and the microphones' clock, threshold and select pins lead into parts without
   supply. If firmware drives one of them high, current flows through the part's
   protection diode into ground: wasted, and outside the parts' ratings. The same holds
   for the four flash pins when load switch 2 is open. Rule: every pin towards a part is
   low or high-impedance before that part loses power, and the switch going off is an
   interrupt that does it at once. The band has the same rule without saying it.
8. **The charger starts at 100 mA.** With the USB-C configuration pins grounded the power
   chip limits its input to 100 mA until firmware raises it, and it falls back each time
   the charger is removed. Without that write the card charges in five hours, not two and
   a half, and the 225 mA setting does nothing. One forum report says some chips start at
   500 mA; read the register, do not trust the default.
9. **A call needs two channels.** Microphone A and the call sensor arrive as left and
   right. Encoding both doubles the encoder's work, which is already the largest and least
   certain line of the power budget, and the protocol in `mnemo-band` carries one channel.
   Mixing them into one before encoding is the cheap answer and loses who said what.
10. **The debug port is on the outside of the card.** Anyone holding the card can attach
    to SWDIO and SWDCLK. With the chip's access protection off, that reads the firmware
    and whatever audio is still in the flash of a lost card. Production cards need the
    protection on, which makes "firmware the owner can rebuild and load" a recovery by
    full erase, not a free read. The audio in the flash is not encrypted.
11. **Flash addresses.** 256 Mbit needs four-byte addresses; the ring's 128 Mbit part did not.

### Could make it unreliable

12. **A slide switch carrying one milliamp.** Its contacts carry only the microphones'
    current at 1.8 V. Many small switches need more than that to keep their contacts
    clean, and state a minimum load. If this one does, the remedy is to let the switch
    drive the gate of a transistor that carries the rail: still copper, still not firmware.
13. **Bending.** One aluminium skin and a plastic one are not a stiff sandwich. The card
    will be sat on with a lithium pouch inside. Nothing here calculates or tests it, and
    it is the one risk in this design that is about safety and not about function. A
    steel front skin with a plastic window over the antenna, or a cell maker's word on
    what bend the pouch tolerates, would settle it.
14. **Pressing on the pads.** The four contact pads are on the board face under the front
    skin, and the charger's spring pins push the board inwards with nothing behind it but
    air and the power chip's small parts. It needs a post from the back skin under that
    end of the board. The same for the button and the switch: a side push of 1.6 N on a
    part held only by its solder needs the frame to take the load.
15. **Radio next to microphone A.** The antenna is 9 mm from microphone A and its clock
    line runs the length of the board. A radio that transmits in bursts can be heard in a
    microphone as a buzz. The T5838 has a metal lid; whether that is enough at this
    distance is a measurement. Microphone B is 75 mm away and gives the comparison.
16. **The cell tabs have no way to the board.** A cell 80 x 35 has its tabs on a short
    side; the board is along a long side, behind a rib. The model reserves 1.5 mm for tabs
    and no path. The cell needs leads or a flexible tail, and the rib a gap, at the end
    where the pads for it are.
17. **The protection diode of the charging pad is 10 mm from the pad.** The placer put it
    by the power chip. It belongs at the pad, as the two on the service pads are. A
    placement review before routing would catch it; it is written here so it does.
18. **Heat while charging.** The charger is linear: at 225 mA it turns about 0.3 W into
    heat inside a closed card, next to the cell. The thermistor now watches it; nobody
    has estimated how warm the skin gets.

### Smaller

19. The light's two resistors assume a 1.9 V red LED on a 3.7 V rail. On the charger the
    rail is near 5 V and the light is about twice as bright. Harmless.
20. The 32 MHz crystal ended 2.5 mm from the antenna keep-out. Legal, not pretty; look at
    it when routing.
21. A board 82.6 x 14 x 0.6 mm is a ruler. It will need a panel with rails and probably a
    carrier through the oven, and the 0.6 mm thickness with 0201 parts puts it in the
    assembler's dearer service.
22. The exposed pads are gold on a face that lives in pockets. Wear and skin are not
    assessed.
23. Water: two microphone holes, a switch slot, a button, a light insert, four pad
    windows. No seal is designed and no rating is claimed.

## Checked and found sound

- The recording switch is the only supply of the microphones and of the call sensor, and
  its off position grounds their rail. The pin that reads the rail does so through 10 k
  and cannot lift a grounded rail. A test fails if any part that could feed the rail is
  added.
- The light's gate is that rail and nothing else; firmware has a way to add light and no
  net that removes it. Tested.
- Every pad a finger can reach, except ground, has a protection diode. Tested.
- One clock for three listening parts at 768 kHz is inside the low-power range of both
  kinds (the microphone's and the sensor's 600 to 950 kHz).
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
