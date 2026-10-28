"""Verificación matemática de la simulación.

Ejecutar:  python -m regulador.verificacion

Cada prueba compara el simulador con un resultado conocido de forma
independiente (solución analítica, ley de conservación o propiedad
estadística). La explicación detallada está en docs/VERIFICACION.md.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from . import events as ev
from .config import DEFAULT_CONFIG, DEFAULT_SETPOINT, EVENT_DURATION_RANGE, EVENT_FLOW_RANGE
from .model import (
    auto_equilibrium,
    inlet_flow,
    linear_time_constant,
    manual_equilibrium,
    outflow,
)
from .simulation import advance_simulation, initial_state, integrate_interval


@dataclass
class Check:
    name: str
    expected: float
    obtained: float
    tolerance: float
    detail: str = ""

    @property
    def error(self) -> float:
        return abs(self.obtained - self.expected)

    @property
    def passed(self) -> bool:
        return self.error <= self.tolerance


def _config(**overrides) -> dict:
    return {**DEFAULT_CONFIG, **overrides}


def _integrate(h0: float, t_end: float, config: dict, automatic: bool,
               events: list[dict] | None = None, max_step: float = 0.05,
               t0: float = 0.0) -> float:
    return integrate_interval(h0, t0, t_end, events or [], config, DEFAULT_SETPOINT,
                              automatic, max_step)


def generate_events(seed: int, horizon: float, mean_gap: float = DEFAULT_CONFIG["mean_gap"]) -> list[dict]:
    """Todas las llegadas automáticas en [0, horizon] (misma regla que el simulador)."""
    events, index = [], 0
    t = ev.next_interarrival(seed, 0, mean_gap)
    while t <= horizon:
        index += 1
        events.append(ev.make_event(seed, index, t, ev.AUTOMATIC))
        t += ev.next_interarrival(seed, index, mean_gap)
    return events


# -----------------------------------------------------------------------------
# 1. Solución analítica exacta: vaciado libre (Torricelli)
# -----------------------------------------------------------------------------
def drain_exact(h0: float, t: float, c: float, area: float) -> float:
    """Q_in = 0, D = 0  =>  dh/dt = −C√h/A  =>  √h(t) = √h0 − C·t/(2A)."""
    root = max(0.0, math.sqrt(h0) - c * t / (2.0 * area))
    return root * root


def drain_numeric(h0: float, t: float, max_step: float) -> float:
    return _integrate(h0, t, _config(q_manual=0.0), automatic=False, max_step=max_step)


def check_drain(h0: float = 5.0, t: float = 120.0) -> Check:
    exact = drain_exact(h0, t, DEFAULT_CONFIG["c"], DEFAULT_CONFIG["area"])
    return Check("Vaciado libre vs. solución exacta (√h0 − Ct/2A)²",
                 exact, drain_numeric(h0, t, 0.05), 1e-9, f"h0 = {h0} m, t = {t} s")


# -----------------------------------------------------------------------------
# 2. Orden de convergencia de RK4
# -----------------------------------------------------------------------------
def convergence_table(h0: float = 5.0, t: float = 120.0,
                      steps: tuple[float, ...] = (8.0, 4.0, 2.0, 1.0)) -> list[tuple[float, float]]:
    exact = drain_exact(h0, t, DEFAULT_CONFIG["c"], DEFAULT_CONFIG["area"])
    return [(dt, abs(drain_numeric(h0, t, dt) - exact)) for dt in steps]


def check_order() -> Check:
    table = convergence_table()
    orders = [math.log2(e1 / e2) for (_, e1), (_, e2) in zip(table, table[1:])]
    detail = "; ".join(f"Δt={dt:g}s → e={err:.2e}" for dt, err in table)
    return Check("Orden observado de RK4 (teórico 4)", 4.0, statistics.mean(orders), 0.3, detail)


# -----------------------------------------------------------------------------
# 3. Equilibrios analíticos
# -----------------------------------------------------------------------------
def check_auto_equilibrium(c: float) -> Check:
    cfg = _config(c=c)
    return Check(f"Equilibrio AUTO sin demanda, C = {c}",
                 auto_equilibrium(cfg, DEFAULT_SETPOINT),
                 _integrate(3.35, 600.0, cfg, automatic=True), 1e-6,
                 "h* = ((−C + √(C² + 4Kp(Qb + Kp·href))) / 2Kp)²")


def check_manual_equilibrium() -> Check:
    cfg = _config()
    # En MANUAL no hay Kp: τ ≈ 667 s, así que se integra mucho más tiempo.
    return Check("Equilibrio MANUAL sin demanda h* = (Qmanual/C)²",
                 manual_equilibrium(cfg), _integrate(3.35, 15_000.0, cfg, automatic=False),
                 1e-6)


# -----------------------------------------------------------------------------
# 4. Constante de tiempo de la linealización
# -----------------------------------------------------------------------------
def check_time_constant(delta: float = 0.005) -> Check:
    """Una perturbación pequeña decae como e^(−t/τ): en t = τ queda δ/e."""
    cfg = _config()
    h_eq = auto_equilibrium(cfg, DEFAULT_SETPOINT)
    tau = linear_time_constant(cfg, h_eq)
    h_tau = _integrate(h_eq + delta, tau, cfg, automatic=True)
    return Check("Decaimiento lineal (h(τ) − h*)/δ = e⁻¹", math.exp(-1.0),
                 (h_tau - h_eq) / delta, 1e-3, f"τ = {tau:.2f} s")


# -----------------------------------------------------------------------------
# 5. Conservación de volumen con eventos discretos
# -----------------------------------------------------------------------------
def check_volume_balance(seed: int = 42, horizon: float = 300.0, grid: float = 0.01) -> Check:
    """A·(h(T) − h(0)) = ∫(Qin − Qout)dt − ∫D dt.

    ∫(Qin − Qout) es continua y se integra con la regla del trapecio sobre la
    trayectoria simulada; ∫D dt es exacta: Σ q_i · (duración dentro de [0, T]).
    """
    cfg = _config(seed=seed)
    events = generate_events(seed, horizon)
    n = round(horizon / grid)
    h = h0 = 3.35
    smooth = []
    for k in range(n + 1):
        if k:
            h = _integrate(h, k * grid, cfg, True, events, t0=(k - 1) * grid)
        smooth.append(inlet_flow(h, cfg, DEFAULT_SETPOINT, True) - outflow(h, cfg["c"]))
    flux_smooth = grid * (sum(smooth) - 0.5 * (smooth[0] + smooth[-1]))
    flux_demand = sum(e["q"] * max(0.0, min(e["end"], horizon) - max(e["start"], 0.0))
                      for e in events)
    return Check("Balance de volumen A·Δh = ∫(Qin − Qout − D)dt  [m³]",
                 flux_smooth - flux_demand, cfg["area"] * (h - h0), 1e-5,
                 f"{len(events)} eventos en {horizon:.0f} s")


# -----------------------------------------------------------------------------
# 6. Integrador híbrido vs. referencia muy fina
# -----------------------------------------------------------------------------
def check_event_handling(seed: int = 42, horizon: float = 120.0) -> Check:
    cfg = _config(seed=seed)
    events = generate_events(seed, horizon)
    reference = _integrate(3.35, horizon, cfg, True, events, max_step=0.001)
    obtained = _integrate(3.35, horizon, cfg, True, events, max_step=0.05)
    return Check("Con eventos: Δt = 0.05 s vs. referencia Δt = 0.001 s",
                 reference, obtained, 1e-9, "las discontinuidades de D(t) se respetan")


# -----------------------------------------------------------------------------
# 7. Reproducibilidad con la semilla
# -----------------------------------------------------------------------------
def run_levels(seed: int, ticks: int = 240) -> list[float]:
    state = initial_state(_config(seed=seed), automatic=True, events_automatic=True)
    for _ in range(ticks):
        advance_simulation(state)
    return [row["h"] for row in state["history"]]


def check_reproducibility() -> Check:
    a, b = run_levels(42), run_levels(42)
    return Check("Misma semilla ⇒ trayectoria idéntica (máx |Δh|)", 0.0,
                 max(abs(x - y) for x, y in zip(a, b)), 0.0)


# -----------------------------------------------------------------------------
# 8. Propiedades estadísticas de los eventos
# -----------------------------------------------------------------------------
def check_interarrival_mean(samples: int = 40_000) -> Check:
    """E[max(1, X)] con X ~ Exp(media m) = 1 + m·e^(−1/m)."""
    m = DEFAULT_CONFIG["mean_gap"]
    values = [ev.next_interarrival(42, i, m) for i in range(samples)]
    return Check("Media entre llegadas = 1 + m·e^(−1/m)  [s]", 1.0 + m * math.exp(-1.0 / m),
                 statistics.fmean(values), 0.02 * m)


def check_mean_demand(horizon: float = 200_000.0) -> Check:
    """Ley de Little: D̄ = λ·E[q]·E[d] con λ = 1 / E[intervalo]."""
    m = DEFAULT_CONFIG["mean_gap"]
    events = generate_events(7, horizon)
    rate = 1.0 / (1.0 + m * math.exp(-1.0 / m))
    expected = rate * statistics.fmean(EVENT_FLOW_RANGE) * statistics.fmean(EVENT_DURATION_RANGE)
    obtained = sum(e["q"] * (min(e["end"], horizon) - e["start"]) for e in events) / horizon
    return Check("Demanda media D̄ = λ·E[q]·E[d]  [L/s]", expected * 1000, obtained * 1000,
                 0.03 * expected * 1000)


def run_all() -> list[Check]:
    return [
        check_drain(),
        check_order(),
        check_auto_equilibrium(0.018),
        check_auto_equilibrium(0.030),
        check_manual_equilibrium(),
        check_time_constant(),
        check_volume_balance(),
        check_event_handling(),
        check_reproducibility(),
        check_interarrival_mean(),
        check_mean_demand(),
    ]


def main() -> int:
    checks = run_all()
    for i, chk in enumerate(checks, 1):
        status = "OK  " if chk.passed else "FALLA"
        print(f"[{status}] {i:2d}. {chk.name}")
        print(f"         esperado = {chk.expected:.10g} | obtenido = {chk.obtained:.10g}"
              f" | error = {chk.error:.2e} (tol {chk.tolerance:.0e})")
        if chk.detail:
            print(f"         {chk.detail}")
    failed = sum(not c.passed for c in checks)
    print(f"\n{len(checks) - failed}/{len(checks)} verificaciones superadas.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
