# Open questions

## Decisions taken

On 2026-11-23 the project owner asked for the best answer to every open question. These
are the answers, what each rests on, and what would overturn it. None has been tested.

| Question | Chosen | Because | What would overturn it |
| --- | --- | --- | --- |
| Does the card hear the far side of a phone call | Yes: a Knowles V2S200D on the switched rail | It is what a card on a phone is for, and the part speaks the microphones' interface at their voltage and clock | The sensor hearing too little through a phone's back |
| A switch that starts the recording, or a card that listens whenever it is on | Switch | A meeting is started on purpose, and a switch shows its state to everyone for as long as it lasts | Nothing found |
| Switch in the listening supply, or read by firmware | In the supply | Off cannot be overridden, at no cost in parts. The price: the phone cannot start a recording | Owners asking to start from the phone |
| Thickness | 3.5 mm | Meets 30 hours even if the power budget is five times too low; 3.0 mm would not | A bench that confirms the budget: then 3.0 mm with a lower button and a 0.4 mm board |
| Magnets in the card, or in a sleeve | Sleeve | The ring is as wide as the card and would lie on the cell | A thinner cell and a card wider than a payment card: a different product |
| Pads on the front, or on the back | Front | The bare face of the board is already there: no springs. Each pad has a protection diode | Pads wearing or corroding in a pocket |
| Where the light is | 1.3 mm from the edge, with a clear insert round the corner | Seen on the front and on the edge, so also with the card face down | The insert carrying too little light to either face |
| Shell | Aluminium back skin; glass-filled plastic frame and front | Stiffness for the cell, one known piece of metal behind the antenna, a path for the call sensor; plastic where the radio leaves | Too short a range on a table: then a window under the antenna |
| One microphone or two | Two, on two data lines | One may be covered; the first line pairs microphone A with the call sensor | Nothing found |
| Power chip | nPM1300 | Charges this cell in about 2.5 hours instead of 5; same 32 pins as the band's nPM1304 | The two pin tables differing when read from the package figures |
| Charge current | 225 mA, half the capacity per hour | Gentle on a thin cell; the chip could give more | The cell's datasheet |
| Flash | 256 Mbit NOR, W25Q256JWEIQ | Three and a half hours away from the phone for about 1.6 dollars; 1 Gbit is listed at about 15 | Owners who leave the phone behind: the 512 Mbit and 1 Gbit parts fit the same pads |
| Slide switch | Same Sky SLW-66527511-SMT-TR, 1.1 mm | The lowest found | Its slider pointing up from the board instead of out of the edge |
| Button | Panasonic EVQ-P7, 1.35 mm | Side push on the board surface, no cut-out, fits 3.5 mm | Going to 3.0 mm: then EVP-AN |
| Light | Wuerth 156125RS75000, reverse-mount | Reverse-mount parts this low exist only in this length | Its height over the board being more than 1.1 |
| Ship mode | After 14 days with the switch off and no phone in reach | A card forgotten in a drawer keeps its charge | Nothing found |
| Factory reset | Button held while the switch goes on, 5 s | Two controls, two hands; ends before the power chip's 10 s | Nothing found |
| Name | Manent card | The project owner's decision | |
| Licence | CERN-OHL-S v2 for the hardware and the scripts that generate it; CC BY-SA 4.0 for the documents | The project owner's decision: open hardware | |
| The law on recording conversations and calls | Not the card's business: left to whoever uses it | The project owner's decision | |

## To confirm from documents

Everything listed in the band's open questions for the nRF54L15, the T5838, the crystals,
the inductor, the MOSFETs and the cell protection applies here unchanged. What is new, in
the order in which a wrong answer would cost most:

| Item | Where to look |
| --- | --- |
| V2S200D: pin numbers, land pattern, which SELECT level is which clock edge, how it must be fixed to what it listens to | Syntiant's datasheet, revision C: distributors link it, it could not be opened |
| SLW-66527511: that the slider moves parallel to the board and reaches past its edge; land pattern; which terminal is common | Same Sky's datasheet: the site refused the request |
| EVQ-P7: land pattern, force options, terminal shape, sealing | Panasonic's drawing |
| EVP-AN: what "0.7 mm, half dive" means on a 0.6 mm board | Panasonic's drawing |
| 156125RS75000: height over the board, hole size, land pattern, cathode, brightness at 0.5 mA | Wuerth's datasheet |
| nPM1300 against nPM1304: both pin tables from the package figures; register differences for the firmware's driver | Nordic's product specifications |
| W25Q256JWEIQ: height, exposed pad, standby current, pin order | Winbond's datasheet |
| nRF54L15: whether it has one PDM interface or two | Nordic's instantiation table |
| ESD230 on SWDIO and SWDCLK: its capacitance against the debug clock | Infineon's datasheet, Nordic's guidance |
| Cell: a 2.0 x 35 x 80 mm part with drawing, capacity, protection, tab position, charge current, and what bending it tolerates | quotes from two makers of thin cells to order |
| The magnet ring phones use: exact diameters, pull, effect on the phone's compass | Apple's accessory design guidelines, the chapter on the magnet array |
| What the Bee Eclipse actually contains | a teardown or its radio approval file, when one appears |

## To measure, no card needed (development kit and breakouts)

1. The call sensor's evaluation board taped to the back of three phones, bare and in a
   sleeve, behind 0.5 mm of aluminium: is the far side of a call intelligible.
2. Current while recording: Opus duty cycle, PDM with three parts on it, flash writes. This
   decides whether the card can be 3.0 mm.
3. Upload speed for an hour of audio, and its energy.
4. Light: current needed to be seen through a clear insert, indoors and outdoors.
5. A T5838 behind a 0.6 mm board, a gasket and a 0.5 mm skin: what the tunnel does to speech.
6. A chip antenna 1.5 mm over an aluminium sheet: range to a phone across a room.
7. Charging a 450 mAh cell at 225 mA; fuel-gauge behaviour.

## To measure on a card

1. Hours of recording on a charge, against the budget's 154 and Plaud's 30.
2. Speech across a meeting table, card flat on it; and in a pocket.
3. Range, card alone and on three different phones.
4. Whether the card on the phone disturbs the phone: its wireless charging, its compass, its radios.
5. Stiffness: what a bent card does to the cell.
6. Heat while charging in a closed card; water.

## Not designed yet

Board routing (parts are placed, no track is drawn) and a review of the placement; the
frame and the two skins, their joint and seal; the switch slot, the button cap, the clear
insert of the light, the microphone gaskets and membranes, the pad under the call sensor;
the sleeve with its magnets; the charger; the antenna; firmware changes against
`mnemo-band` (pins, the nPM1300 driver, two data lines, a second audio channel for calls,
the recording switch, four-byte flash addresses, ship mode, factory reset, and the rules in
`review.md`); compliance (radio,
lithium cell).
