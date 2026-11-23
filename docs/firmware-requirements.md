# What the firmware must do for this hardware

The card's firmware is `mnemo-band`'s with a different pin map. This list is what the
hardware asks of it beyond that. Each item is something the board cannot enforce by itself
and that breaks the card, or its promise, if it is missing. Each says how to check it.

## So that nothing is damaged

1. **No pin drives a part that has no power.** The microphones' clock (P1.04), their two
   threshold pins (P1.06, P1.09) and the four flash pins (P2.01, P2.02, P2.04, P2.05) lead
   into parts whose supply can be off. Before load switch 2 opens, the flash pins go low
   or high-impedance. When P1.08 reports that the recording switch went off, an interrupt
   stops the clock and releases the threshold pins before anything else runs. At reset
   all of them start high-impedance.
   *Check:* with the switch off, the current from the cell is the standby figure, and no
   pin towards the microphones measures above 0.2 V.
2. **The charger's input limit is raised on every connection.** With its USB-C pins
   grounded the power chip starts at 100 mA. On each "charger present" event the firmware
   writes the limit to 500 mA, and the charge current to 225 mA once. One report says some
   chips already start at 500: read the register back, do not assume.
   *Check:* the current into the pads, with an empty cell, is above 200 mA.
3. **The thermistor is used.** The charger is told the part's values (10 k, B 3380) and
   the four temperature limits; charging stops outside 0 to 45 degrees.
   *Check:* a hot-air gun on the cell end stops the charge.
4. **The cell is never drawn below its limit.** The firmware stops recording and goes to
   ship mode at a voltage above the protection chip's own cut-off.

## So that the promises hold

5. **A lost card gives up nothing.** The debug pads are on the outside. Production cards
   have the microcontroller's access protection on, so the port can only erase the whole
   chip. The audio waiting in the external flash is encrypted with a key that lives in the
   microcontroller's key store and dies with that erase. Reloading firmware through the
   pads is therefore a wipe, never a read.
   *Check:* a debugger on the pads cannot read memory; the flash chip, read out of
   circuit, holds nothing that plays.
6. **The light is never worked around.** Firmware may add light through P0.04. No build
   option, test mode or factory command may record with P1.08 low: that pin low means the
   switch is off and the microphones have no power, so there is nothing to record.
7. **Audio is kept only until the phone has it.** As in `mnemo-band`: a slot is freed when
   the phone confirms it, and not before.
8. **A full flash stops the recording and says so.** With 256 Mbit the card holds 3 h 38 min
   away from its phone. When it is full the firmware opens load switch 1, which puts the
   light out, and blinks the error. It does not overwrite what the phone has not taken.

## So that it works

9. **Two data lines, one interface.** The audio interface's input is P1.05 by default:
   microphone A on one clock edge, the call sensor on the other. Pointed at P1.14 it hears
   microphone B. The firmware chooses per recording, not per sample. On a call it keeps
   both channels of line 1 until the phone has decided how they are mixed.
10. **768 kHz clock.** It is the low-power clock of both the microphones and the call
    sensor (600 to 950 kHz). A faster clock more than doubles the sensor's current.
11. **Four-byte flash addresses**, which the ring's and the band's smaller parts did not need.
12. **Ship mode** after 14 days with the switch off and no phone in reach; the button wakes it.
13. **Factory reset** when the button is down as the switch goes on and stays down for 5 s.
    Released earlier, it is a normal recording with a mark at its start.
14. **The radio is quiet while it can be.** Connection events are placed between audio
    frames where the protocol allows it; whether its bursts are heard in microphone A is
    the first thing to listen for on a real board.
