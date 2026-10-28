from regulador.config import DEFAULT_CONFIG, MAX_HISTORY
from regulador.simulation import (
    add_manual_event,
    advance_simulation,
    config_from_inputs,
    initial_state,
    safe_float,
)


def test_safe_float_handles_bad_input():
    assert safe_float(None, 1.0, 0.0, 2.0) == 1.0
    assert safe_float("abc", 1.0, 0.0, 2.0) == 1.0
    assert safe_float(float("nan"), 1.0, 0.0, 2.0) == 1.0
    assert safe_float(10, 1.0, 0.0, 2.0) == 2.0


def test_config_from_inputs_uses_defaults_and_limits():
    cfg = config_from_inputs(area=None, c=1.0, seed="7")
    assert cfg["area"] == DEFAULT_CONFIG["area"]
    assert cfg["c"] == 0.08
    assert cfg["seed"] == 7


def test_advance_moves_clock_and_records_history():
    state = initial_state()
    advance_simulation(state)
    assert state["time"] == 0.5
    assert len(state["history"]) == 2


def test_history_is_bounded():
    state = initial_state()
    for _ in range(MAX_HISTORY + 20):
        advance_simulation(state)
    assert len(state["history"]) == MAX_HISTORY


def test_manual_event_starts_now():
    state = initial_state()
    advance_simulation(state)
    add_manual_event(state)
    assert state["events"][-1]["start"] == state["time"]
    assert state["event_log"][-1]["tipo"] == "Manual"


def test_state_is_json_serializable():
    import json

    state = initial_state(automatic=True)
    for _ in range(50):
        advance_simulation(state)
    json.dumps(state)


def test_auto_events_off_by_default():
    state = initial_state()
    for _ in range(200):
        advance_simulation(state)
    assert state["events_automatic"] is False
    assert state["event_log"] == []


def test_enabling_auto_events_schedules_from_now():
    from regulador.simulation import set_events_automatic

    state = initial_state()
    for _ in range(100):
        advance_simulation(state)
    set_events_automatic(state, True)
    assert state["next_auto_time"] > state["time"]
    for _ in range(200):
        advance_simulation(state)
    starts = [row["t0"] for row in state["event_log"]]
    assert starts and min(starts) >= 50.0


def test_disabling_auto_events_stops_arrivals():
    from regulador.simulation import set_events_automatic

    state = initial_state(events_automatic=True)
    for _ in range(100):
        advance_simulation(state)
    set_events_automatic(state, False)
    count = len(state["event_log"])
    for _ in range(200):
        advance_simulation(state)
    assert len(state["event_log"]) == count
