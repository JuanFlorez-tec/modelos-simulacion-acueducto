from regulador import events as ev


def test_same_seed_same_event():
    assert ev.make_event(42, 3, 10.0) == ev.make_event(42, 3, 10.0)
    assert ev.make_event(42, 3, 10.0) != ev.make_event(7, 3, 10.0)


def test_event_ranges():
    for i in range(200):
        e = ev.make_event(1, i, 0.0)
        assert 0.009 <= e["q"] <= 0.023
        assert 6.0 <= e["duration"] <= 15.0
        assert e["end"] == e["start"] + e["duration"]


def test_active_demand_is_half_open_interval():
    e = {"start": 1.0, "end": 2.0, "q": 0.01}
    assert ev.active_demand([e], 0.999) == 0.0
    assert ev.active_demand([e], 1.0) == 0.01
    assert ev.active_demand([e], 2.0) == 0.0


def test_breakpoints_inside_interval_only():
    events = [{"start": 1.0, "end": 3.0}, {"start": 0.0, "end": 1.5}]
    assert ev.breakpoints(events, 0.0, 2.0) == [1.0, 1.5]
