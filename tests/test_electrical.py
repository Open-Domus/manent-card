from pathlib import Path

import pytest

from gen import checks
from gen.design import build, netlist

NETLIST = Path(__file__).resolve().parents[1] / "electrical" / "out" / "netlist.xml"


def test_circuit_rules_hold():
    assert checks.lint() == []


def test_kicad_reads_the_same_nets_we_wrote():
    if not NETLIST.exists():
        pytest.skip("run `make schematic` first")
    assert checks.compare(NETLIST) == []
    assert len(checks.kicad_netlist(NETLIST)) == len(netlist()) > 40


def test_light_follows_the_microphone_rail():
    # The recording light must not depend on firmware: its switch is gated by VMIC itself.
    comps = build()
    gate = [c for c in comps if c.sym.name == "NMOS" and c.nets["1"] == "VMIC"]
    assert len(gate) == 1 and gate[0].nets["3"] == "LED_SW"
    assert all("VMIC" in c.nets.values() for c in comps if c.value == "T5838")


def test_firmware_can_add_light_but_not_remove_it():
    comps = build()
    led = next(c for c in comps if c.sym.name == "LED")
    cathode = led.nets["1"]
    paths = {next(n for n in c.nets.values() if n != cathode) for c in comps
             if c.sym.name == "R" and cathode in c.nets.values()}
    assert paths == {"LED_SW", "LED_HI"}
    # Nothing but the light and its two resistors touches the cathode: no pin can hold it off.
    assert len(netlist(comps)[cathode]) == 3


def test_the_switch_is_the_only_supply_of_the_microphones():
    comps = build()
    switch = next(c for c in comps if c.sym.name == "SPDT")
    names = {p.name: switch.nets[p.number] for p in switch.sym.pins}
    assert names == {"COM": "VMIC", "ON": "VMIC_SW", "OFF": "GND"}
    mics = [c for c in comps if c.value == "T5838"]
    assert len(mics) == 2 and all(c.nets["7"] == "VMIC" for c in mics)
    # On the microphone rail: the two microphones and the call sensor, their capacitors, the
    # switch, the light's gate, and the resistor through which the SoC reads the switch.
    # Nothing that supplies it.
    on_rail = sorted(c.sym.name for c in comps if "VMIC" in c.nets.values() and not c.sym.virtual)
    assert on_rail == ["C", "C", "C", "NMOS", "R", "R", "SPDT", "T5838", "T5838", "V2S200D"]
    others = sorted(next(n for n in c.nets.values() if n != "VMIC") for c in comps
                    if c.sym.name == "R" and "VMIC" in c.nets.values())
    assert others == ["GND", "MIC_ON"]            # a pull-down, and the SoC reading the switch


def test_one_interface_hears_the_owner_and_the_phone_together():
    comps = build()
    line1 = sorted(c.value for c in comps if c.sym.prefix == "MK" and "PDM_DIN" in c.nets.values())
    assert line1 == ["T5838", "V2S200D"]
    line2 = [c.value for c in comps if c.sym.prefix == "MK" and "PDM_DIN2" in c.nets.values()]
    assert line2 == ["T5838"]


def test_every_pad_a_finger_can_reach_has_a_protection_diode():
    comps = build()
    exposed = {c.nets["1"] for c in comps if c.sym.name == "CONTACT"} - {"GND"}
    protected = {c.nets["1"] for c in comps if c.sym.name == "TVS"}
    assert exposed == protected == {"VBUS", "SWDIO", "SWDCLK"}


def test_firmware_can_also_cut_the_microphones():
    pmic = next(c for c in build() if c.value == "nPM1300")
    names = {p.name: pmic.nets[p.number] for p in pmic.sym.pins}
    assert names["LSOUT1"] == "VMIC_SW" and names["GPIO1"] == "MIC_EN"


def test_flash_holds_a_long_meeting():
    flash = next(c for c in build() if c.sym.name == "SPI-NOR-8")
    assert flash.value == "W25Q256JW"
    slots = 2 ** 28 // 8 // 256                    # one 256-byte slot holds 100 ms of speech
    assert slots / 10 / 3600 > 3.5


def test_the_cell_protection_lets_the_charge_current_through():
    comps = build()
    sense = next(c for c in comps if c.sym.name == "R" and set(c.nets.values()) == {"CELL_N", "SENSE"})
    trip_ma = 50 / float(sense.value)              # 50 mV assumed threshold
    assert trip_ma > 2 * 225


def test_the_charger_reads_a_thermistor():
    comps = build()
    pmic = next(c for c in comps if c.value == "nPM1300")
    assert {p.name: pmic.nets[p.number] for p in pmic.sym.pins}["NTC"] == "NTC"
    assert any("NTC" in c.value for c in comps if c.sym.name == "R")


def test_both_nordic_chips_are_the_qfn_versions():
    fps = {c.value: c.fields["Footprint"] for c in build() if c.value in ("nRF54L15", "nPM1300")}
    assert "QFN-48" in fps["nRF54L15"] and "QFN-32" in fps["nPM1300"]


def test_board_is_complete_and_breaks_no_rule():
    import json
    drc = NETLIST.with_name("drc.json")
    if not drc.exists():
        pytest.skip("run `make board` first")
    report = json.loads(drc.read_text())
    assert report["violations"] == []
    assert report["schematic_parity"] == []       # same parts, footprints and nets as the schematic
    # The tracks are in electrical/kicad/card.ses. If the placement changed since they were
    # drawn, connections open up here: run `make route` again.
    assert report["unconnected_items"] == []


def _tracks():
    import json
    path = NETLIST.with_name("tracks.json")
    if not path.exists():
        pytest.skip("run `make board` first")
    return json.loads(path.read_text())


def _share_at_width(nets, width):
    rows = [r for r in _tracks() if r[0] in nets]
    total = sum(r[3] for r in rows)
    assert total > 0
    return sum(r[3] for r in rows if r[2] >= width - 1e-6) / total


def test_radio_line_width_is_fifty_ohms_on_the_assumed_stack():
    from gen.board import STACK, microstrip_ohms, rf_width
    assert 0.15 < rf_width() < 0.25
    assert microstrip_ohms(rf_width(), STACK["prepreg_mm"], STACK["er"]) == pytest.approx(50, abs=1.5)


def test_no_signal_runs_on_the_ground_layer():
    assert [r[0] for r in _tracks() if r[1] == "In1.Cu"] == []


def test_radio_line_is_drawn_at_its_width():
    from gen.board import RF_NETS, rf_width
    assert _share_at_width(RF_NETS, rf_width()) > 0.9


def test_supply_tracks_are_wide():
    from gen.board import POWER_NETS, POWER_WIDTH
    assert _share_at_width(POWER_NETS, POWER_WIDTH) > 0.9


def test_kicad_put_every_pad_where_the_placer_assumed():
    import json
    board, pads = NETLIST.with_name("board.json"), NETLIST.with_name("pads.json")
    if not (board.exists() and pads.exists()):
        pytest.skip("run `make board` first")
    from gen.board import pad_positions
    real = {}
    for ref, num, x, y, net in json.loads(pads.read_text()):
        real.setdefault((ref, num), []).append((x, y, net))
    checked = 0
    for part in json.loads(board.read_text())["parts"]:
        for num, points in pad_positions(part["footprint"], part["x"], part["y"], part["rot"], part["side"]).items():
            for x, y in points:
                assert min(abs(x - a) + abs(y - b) for a, b, _ in real[(part["ref"], num)]) < 0.01, (part["ref"], num)
                checked += 1
            assert all(net == part["nets"][num] for _, _, net in real[(part["ref"], num)]), (part["ref"], num)
    assert checked > 200


def test_placed_parts_stay_close_to_what_they_connect_to():
    import json
    path = NETLIST.with_name("board.json")
    if not path.exists():
        pytest.skip("run `make board` first")
    from gen.board import pad_positions
    data = json.loads(path.read_text())
    pads = {}
    for part in data["parts"]:
        for num, points in pad_positions(part["footprint"], part["x"], part["y"], part["rot"], part["side"]).items():
            pads.setdefault(part["nets"].get(num), []).extend((x, y, part["ref"]) for x, y in points)
    # Every decoupling capacitor of the microcontroller within 3 mm of a supply pin of it.
    soc = next(p["ref"] for p in data["parts"] if p["value"] == "nRF54L15")
    caps = [p["ref"] for p in data["parts"] if p["value"] == "100nF" and "/" + p["path"].split("/")[1] ==
            "/" + next(q for q in data["parts"] if q["ref"] == soc)["path"].split("/")[1]]
    assert len(caps) == 4
    vdd = [(x, y) for x, y, ref in pads["V1V8"] if ref == soc]
    for cap in caps:
        own = [(x, y) for x, y, ref in pads["V1V8"] if ref == cap]
        assert min(((x - a) ** 2 + (y - b) ** 2) ** 0.5 for x, y in own for a, b in vdd) < 3.0, cap


def test_protection_diodes_sit_at_their_pads():
    import json
    path = NETLIST.with_name("board.json")
    if not path.exists():
        pytest.skip("run `make board` first")
    parts = json.loads(path.read_text())["parts"]
    pad = {p["nets"]["1"]: (p["x"], p["y"]) for p in parts if p["footprint"].startswith("Pad_Contact")}
    diodes = [p for p in parts if p["fields"].get("MPN") == "ESD230-B1-W0201"]
    assert len(diodes) == 3
    for d in diodes:
        x, y = pad[d["nets"]["1"]]
        assert abs(d["x"] - x) < 2.5 and abs(d["y"] - y) < 2.5, d["ref"]


def test_call_sensor_pins_are_the_datasheets():
    sensor = next(c for c in build() if c.value == "V2S200D")
    names = {p.number: p.name for p in sensor.sym.pins}
    assert names == {"1": "VDD", "2": "CLK", "3": "GND", "4": "GND", "5": "SELECT", "6": "DATA"}
    assert sensor.nets["5"] == "VMIC"              # SELECT high: speaks on the rising edge
    mic_a = next(c for c in build() if c.value == "T5838" and "PDM_DIN" in c.nets.values())
    assert mic_a.nets["2"] == "GND"                # the microphone on the same line takes the other edge


def test_no_vibration_motor_and_no_screen():
    assert not any(w in c.value.lower() for c in build() for w in ("haptic", "motor", "display", "oled"))
