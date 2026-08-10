import pytest
from hr_overlay.heart_model import HeartModel


def test_initial_state(make_model):
    model = make_model(name="InitialBand", address="11:22:33:44:55:66")
    assert model.status() == "disconnected"
    assert model.current_bpm() == 0
    assert model.history() == []
    assert model.zone() == "green"
    assert model.connected() is False
    assert model.display_name == "InitialBand"
    assert model.address == "11:22:33:44:55:66"


def test_update_bpm(make_model):
    model = make_model()
    received_bpm = []
    received_history = []
    model.bpm_changed.connect(lambda b: received_bpm.append(b))
    model.history_changed.connect(lambda h: received_history.append(h))

    model.update_bpm(75)
    assert model.current_bpm() == 75
    assert model.history() == [75]
    assert received_bpm == [75]
    assert received_history == [[75]]


def test_history_window(make_model):
    model = HeartModel(history_size=3, name="SmallHist")
    model.update_bpm(70)
    model.update_bpm(80)
    model.update_bpm(90)
    model.update_bpm(100)

    hist = model.history()
    assert len(hist) == 3
    assert hist == [80, 90, 100]


def test_zone_determination(make_model):
    model = make_model(zone_low=100, zone_high=140)

    model.update_bpm(80)
    assert model.zone() == "green"

    model.update_bpm(110)
    assert model.zone() == "yellow"

    model.update_bpm(150)
    assert model.zone() == "red"


def test_zone_changed_signal_only_on_change(make_model):
    model = make_model(zone_low=100, zone_high=140)
    zone_emissions = []
    model.zone_changed.connect(lambda z: zone_emissions.append(z))

    model.update_bpm(80)   # green -> green (default initial is green, no change emitted)
    assert zone_emissions == []

    model.update_bpm(85)   # green -> green (no change)
    assert zone_emissions == []

    model.update_bpm(110)  # green -> yellow (emitted)
    assert zone_emissions == ["yellow"]

    model.update_bpm(120)  # yellow -> yellow (no change)
    assert zone_emissions == ["yellow"]

    model.update_bpm(150)  # yellow -> red (emitted)
    assert zone_emissions == ["yellow", "red"]


def test_status_changed_signal_only_on_change(make_model):
    model = make_model()
    status_emissions = []
    model.status_changed.connect(lambda s: status_emissions.append(s))

    model.set_status("connecting")
    model.set_status("connecting")
    assert status_emissions == ["connecting"]

    model.set_status("connected")
    assert status_emissions == ["connecting", "connected"]


def test_connected_property(make_model):
    model = make_model()
    assert model.connected() is False

    model.set_status("connecting")
    assert model.connected() is False

    model.set_status("connected")
    assert model.connected() is True

    model.set_status("disconnected")
    assert model.connected() is False


def test_display_name_and_address(make_model):
    model = make_model(name="Band 9 Pro", address="AA:BB:CC:DD:EE:01")
    assert model.display_name == "Band 9 Pro"
    assert model.address == "AA:BB:CC:DD:EE:01"
