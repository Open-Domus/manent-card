import pytest

from card_mech import stack as S
from card_mech.checks import circuit_bodies, envelope_report, size_sweep
from card_mech.params import ADOPTED, ENVELOPES


@pytest.fixture(scope="module")
def reports():
    return {k: envelope_report(k) for k in ENVELOPES}


def test_adopted_envelope_is_a_payment_card_and_fits(reports):
    rep = reports[ADOPTED]
    assert rep["ok"], rep["problems"]
    assert rep["card"] == [85.6, 54.0, 3.5]
    assert rep["cell"]["capacity_mah"] >= 400


def test_three_millimetres_is_too_thin_for_these_parts(reports):
    rep = reports["B"]
    assert not rep["ok"]
    assert len(rep["problems"]) == 1 and "too thick" in rep["problems"][0]
    assert rep["cell"] is not None                 # the cell is not what stops it


def test_both_stacks_add_up_to_the_card_height(reports):
    for key, rep in reports.items():
        for name in ("board_stack", "cell_stack"):
            assert sum(rep[name].values()) == pytest.approx(ENVELOPES[key].height, abs=0.02), (key, name)


def test_a_card_too_thin_has_no_cell():
    rep = envelope_report("A", ENVELOPES["A"].resized(height=2.4))
    assert not rep["ok"] and rep["cell"] is None


def test_nothing_is_stacked_on_the_cell(reports):
    p, rep = ENVELOPES[ADOPTED], reports[ADOPTED]
    used = p.board_gap + p.board_w + S.RIB + 2 * S.CELL_GAP + rep["cell"]["size"][1]
    assert used <= p.cavity[1]


def test_microphones_are_at_opposite_ends(reports):
    assert reports[ADOPTED]["mic_distance"] >= 70


def test_only_contact_pads_are_on_the_face_under_the_front_skin(reports):
    bare = {pl["part"] for pl in reports[ADOPTED]["placed"] if pl["part"] and pl["face"] == "bottom"}
    assert bare == {"contact"}


def test_button_and_switch_are_on_the_edge_of_the_card(reports):
    edge = {pl["part"]: pl["y"] for pl in reports[ADOPTED]["placed"] if pl["part"] in ("button", "slide")}
    assert len(edge) == 2 and all(y <= 0.2 for y in edge.values())


def test_every_part_of_the_circuit_is_in_the_model(reports):
    bodies = circuit_bodies()
    large = sorted(b for b in bodies if b not in S.SMALL)
    placed = sorted(pl["part"] for pl in reports[ADOPTED]["placed"] if pl["part"])
    assert placed == large and len(large) >= 20
    assert reports[ADOPTED]["area"]["small_parts"] == len(bodies) - len(large) > 40


def test_thicker_cards_and_narrower_boards_never_lose_capacity():
    by = {(r["height"], r["board_w"]): r["capacity_mah"] for r in size_sweep()}
    assert all(by.values())
    assert by[(4.0, 12.0)] >= by[(3.5, 14.0)] >= by[(3.0, 16.0)]


def test_parts_are_complete():
    parts = S.load_parts()
    for group in ("parts", "cells"):
        for key, part in parts[group].items():
            assert part["mpn"] and part["manufacturer"], key
            assert len(part["size"]) == 3 and all(v > 0 for v in part["size"]), key
            assert part["status"] in {"verified", "secondary", "unverified"}, key
    assert set(circuit_bodies()) - {"testpad"} <= set(parts["parts"])
