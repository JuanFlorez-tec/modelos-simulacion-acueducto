"""Eventos discretos: apertura intermitente de consumidores.

Cada evento es un pulso rectangular de demanda: caudal q durante [start, end).
La demanda total D(t) es la suma de los pulsos activos en t.

Las llegadas automáticas siguen un proceso de Poisson (tiempos entre llegadas
exponenciales con media `mean_gap`). Cada número aleatorio se obtiene de un
generador inicializado con (seed, índice del evento), de modo que la misma
semilla reproduce exactamente la misma secuencia, sin depender del orden en
que se pidan los números.
"""
from __future__ import annotations

import random

from .config import (
    CONSUMERS,
    EVENT_DURATION_RANGE,
    EVENT_FLOW_RANGE,
    MIN_INTERARRIVAL,
)

AUTOMATIC = "Automático"
MANUAL = "Manual"


def next_interarrival(seed: int, event_index: int, mean_gap: float) -> float:
    """Tiempo hasta la siguiente llegada automática (exponencial, acotado a >= 1 s)."""
    rng = random.Random(int(seed) + 17 + 1009 * int(event_index))
    return max(MIN_INTERARRIVAL, rng.expovariate(1.0 / max(1.0, float(mean_gap))))


def make_event(seed: int, event_index: int, start: float, kind: str = AUTOMATIC) -> dict:
    """Crea un evento reproducible: misma semilla e índice => mismo evento."""
    salt = 503 if kind == AUTOMATIC else 100_000
    rng = random.Random(int(seed) + salt + int(event_index) * 7919)
    flow = rng.uniform(*EVENT_FLOW_RANGE)
    duration = rng.uniform(*EVENT_DURATION_RANGE)
    consumer = CONSUMERS[rng.randrange(len(CONSUMERS))]
    prefix = "E" if kind == AUTOMATIC else "M"
    return {
        "id": f"{prefix}{event_index:03d}",
        "kind": kind,
        "consumer": consumer,
        "start": float(start),
        "end": float(start + duration),
        "duration": float(duration),
        "q": float(flow),
    }


def is_active(event: dict, at_time: float) -> bool:
    return event["start"] <= at_time < event["end"]


def active_events(events: list[dict], at_time: float) -> list[dict]:
    return [e for e in events if is_active(e, at_time)]


def active_demand(events: list[dict], at_time: float) -> float:
    """D(t): suma de caudales de los eventos activos en `at_time` [m^3/s]."""
    return sum(e["q"] for e in events if is_active(e, at_time))


def breakpoints(events: list[dict], t0: float, t1: float) -> list[float]:
    """Instantes dentro de (t0, t1) donde D(t) cambia (inicio o fin de un evento)."""
    points = {
        edge
        for e in events
        for edge in (e["start"], e["end"])
        if t0 < edge < t1
    }
    return sorted(points)


def log_row(event: dict) -> dict:
    """Fila resumida para la tabla de eventos de la interfaz."""
    return {
        "id": event["id"],
        "tipo": event["kind"],
        "consumidor": event["consumer"],
        "t0": round(event["start"], 2),
        "duracion": round(event["duration"], 2),
        "q_lps": round(event["q"] * 1000.0, 2),
    }
