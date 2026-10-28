"""Simulación híbrida: integra la dinámica continua entre eventos discretos.

El estado es un diccionario serializable a JSON para poder guardarse en un
`dcc.Store` de Dash. Ninguna función de este módulo importa Dash.
"""
from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from . import events as ev
from .config import (
    CONFIG_LIMITS,
    DEFAULT_CONFIG,
    DEFAULT_INITIAL_LEVEL,
    DEFAULT_SETPOINT,
    H_MAX,
    MAX_EVENT_LOG,
    MAX_EVENTS,
    MAX_HISTORY,
    SETPOINT_MAX,
    SETPOINT_MIN,
    SETTINGS,
)
from .model import hydrostatic_pressure_kpa, inlet_flow, outflow, rk4_step

# Tope de llegadas automáticas por tick: evita bucles si mean_gap es muy pequeño.
MAX_ARRIVALS_PER_TICK = 20


# -----------------------------------------------------------------------------
# Validación de entradas de la interfaz
# -----------------------------------------------------------------------------
def safe_float(value: Any, default: float, low: float, high: float) -> float:
    """Convierte un valor de la UI a float y lo limita a [low, high]."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return min(high, max(low, result))


def safe_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def safe_setpoint(value: Any, default: float = DEFAULT_SETPOINT) -> float:
    return safe_float(value, default, SETPOINT_MIN, SETPOINT_MAX)


def config_from_inputs(**inputs: Any) -> dict:
    """Construye una configuración válida a partir de los campos de la UI."""
    config = {
        key: safe_float(inputs.get(key), DEFAULT_CONFIG[key], low, high)
        for key, (low, high) in CONFIG_LIMITS.items()
    }
    config["seed"] = safe_int(inputs.get("seed"), DEFAULT_CONFIG["seed"])
    return config


# -----------------------------------------------------------------------------
# Integración continua por tramos
# -----------------------------------------------------------------------------
def integrate_interval(h: float, t0: float, t1: float, events: list[dict], config: dict,
                       setpoint: float, automatic: bool, max_step: float) -> float:
    """Integra h desde t0 hasta t1 respetando las discontinuidades de D(t).

    D(t) es constante a trozos. El intervalo se parte en los instantes en que
    un evento empieza o termina; en cada tramo D se evalúa en el punto medio
    (valor exacto del tramo) y se integra con RK4 en subpasos <= max_step.
    Así RK4 nunca cruza una discontinuidad y conserva su orden 4.
    """
    edges = [t0, *ev.breakpoints(events, t0, t1), t1]
    for a, b in zip(edges, edges[1:]):
        span = b - a
        if span <= 0.0:
            continue
        demand = ev.active_demand(events, 0.5 * (a + b))
        n_steps = max(1, math.ceil(span / max_step - 1e-9))
        dt = span / n_steps
        for _ in range(n_steps):
            h = rk4_step(h, dt, demand, config, setpoint, automatic)
    return h


# -----------------------------------------------------------------------------
# Estado de la simulación
# -----------------------------------------------------------------------------
def measurement_row(state: dict) -> dict:
    cfg = state["config"]
    t, h = state["time"], state["h"]
    return {
        "t": round(t, 2),
        "h": round(h, 4),
        "href": round(state["h_ref"], 4),
        "pressure": round(hydrostatic_pressure_kpa(h), 3),
        "qin": round(inlet_flow(h, cfg, state["h_ref"], state["automatic"]), 5),
        "qout": round(outflow(h, cfg["c"]), 5),
        "demand": round(ev.active_demand(state["events"], t), 5),
        "mode": "AUTO" if state["automatic"] else "MANUAL",
    }


def initial_state(config: dict | None = None, setpoint: float = DEFAULT_SETPOINT,
                  initial_level: float = DEFAULT_INITIAL_LEVEL, automatic: bool = False,
                  running: bool = True, events_automatic: bool = False) -> dict:
    cfg = deepcopy(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    state = {
        "time": 0.0,
        "h": safe_float(initial_level, DEFAULT_INITIAL_LEVEL, 0.0, H_MAX),
        "h_ref": safe_setpoint(setpoint),
        "automatic": bool(automatic),   # modo del regulador hidráulico
        "events_automatic": False,      # modo de generación de eventos discretos
        "running": bool(running),
        "config": cfg,
        "events": [],
        "event_log": [],
        "auto_event_index": 0,
        "manual_event_index": 0,
        "next_auto_time": 0.0,          # se programa al activar los eventos automáticos
        "history": [],
    }
    if events_automatic:
        set_events_automatic(state, True)
    state["history"].append(measurement_row(state))
    return state


def set_events_automatic(state: dict, enabled: bool) -> dict:
    """Activa/desactiva la generación automática de eventos discretos.

    No cambia el modo del regulador hidráulico. Al activar, la primera llegada
    se programa desde el instante actual para no generar una ráfaga de eventos
    "atrasados".
    """
    state["events_automatic"] = bool(enabled)
    if enabled:
        cfg = state["config"]
        state["next_auto_time"] = state["time"] + ev.next_interarrival(
            cfg["seed"], state["auto_event_index"], cfg["mean_gap"])
    return state


def _register_event(state: dict, event: dict) -> None:
    state["events"].append(event)
    state["event_log"].append(ev.log_row(event))
    state["events"] = state["events"][-MAX_EVENTS:]
    state["event_log"] = state["event_log"][-MAX_EVENT_LOG:]


def schedule_arrivals(state: dict, until: float) -> None:
    """Agenda las llegadas automáticas con instante <= `until` (si están activas)."""
    if not state.get("events_automatic", False):
        return
    cfg = state["config"]
    for _ in range(MAX_ARRIVALS_PER_TICK):
        if state["next_auto_time"] > until:
            break
        index = state["auto_event_index"] + 1
        start = max(state["time"], state["next_auto_time"])
        _register_event(state, ev.make_event(cfg["seed"], index, start, ev.AUTOMATIC))
        state["auto_event_index"] = index
        state["next_auto_time"] += ev.next_interarrival(cfg["seed"], index, cfg["mean_gap"])


def advance_simulation(state: dict, tick: float = SETTINGS.sim_seconds_per_tick,
                       max_step: float = SETTINGS.integration_step) -> dict:
    """Avanza `tick` segundos simulados. Modifica y devuelve `state`."""
    t0 = float(state["time"])
    t1 = t0 + tick
    schedule_arrivals(state, t1)
    state["h"] = integrate_interval(
        state["h"], t0, t1, state["events"], state["config"],
        state["h_ref"], state["automatic"], max_step,
    )
    state["time"] = round(t1, 6)
    # Los eventos ya terminados no vuelven a afectar a D(t).
    state["events"] = [e for e in state["events"] if e["end"] > state["time"]]
    state["history"].append(measurement_row(state))
    state["history"] = state["history"][-MAX_HISTORY:]
    return state


def add_manual_event(state: dict) -> dict:
    """Abre un consumidor en el instante actual (reproducible con la semilla)."""
    state["manual_event_index"] += 1
    event = ev.make_event(state["config"]["seed"], state["manual_event_index"],
                          state["time"], ev.MANUAL)
    _register_event(state, event)
    return state
