"""Modelo continuo del tanque: ecuación diferencial, regulador e integrador.

Ecuación de balance de volumen (tanque de área constante A):

    dh/dt = (Q_in(h) - Q_out(h) - D(t)) / A
    Q_out(h) = C * sqrt(h)                                  (Torricelli)
    Q_in(h)  = sat[Q_base + Kp * (h_ref - h)]   en AUTO      (regulador P)
    Q_in     = sat[Q_manual]                    en MANUAL
    Q_base   = C_nom * sqrt(h_ref)

D(t) es la demanda de los eventos discretos. Es constante a trozos, por lo que
el integrador recibe su valor ya evaluado para cada subintervalo (ver
`simulation.integrate_interval`).

Todas las funciones de este módulo son puras: no dependen de Dash ni de estado
global, lo que permite probarlas de forma aislada.
"""
from __future__ import annotations

import math

from .config import C_NOMINAL, GRAVITY, H_MAX, RHO_WATER


def clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def nominal_inflow(setpoint: float) -> float:
    """Caudal base del regulador, calibrado con C_NOMINAL (no con el C real).

    Mantener C_NOMINAL fijo permite demostrar cómo un cambio en el coeficiente
    físico C desplaza el equilibrio de un controlador solo proporcional.
    """
    return C_NOMINAL * math.sqrt(max(setpoint, 0.0))


def outflow(h: float, c: float) -> float:
    """Descarga hidráulica tipo Torricelli: Q_out = C * sqrt(h)."""
    return c * math.sqrt(max(h, 0.0))


def inlet_flow(h: float, config: dict, setpoint: float, automatic: bool) -> float:
    """Caudal de entrada con saturación de la bomba en [0, Q_max]."""
    if automatic:
        requested = nominal_inflow(setpoint) + config["kp"] * (setpoint - h)
    else:
        requested = config["q_manual"]
    return clamp(requested, 0.0, config["q_max"])


def level_derivative(h: float, demand: float, config: dict, setpoint: float,
                     automatic: bool) -> float:
    """ECUACIÓN DIFERENCIAL DEL MODELO: devuelve dh/dt [m/s].

    Incluye las restricciones físicas del recipiente: el nivel no baja de 0
    (tanque vacío) ni supera H_MAX (rebose).
    """
    # Las etapas intermedias de RK4 pueden salir del rango físico.
    h_phys = clamp(h, 0.0, H_MAX)
    net = (inlet_flow(h_phys, config, setpoint, automatic)
           - outflow(h_phys, config["c"])
           - demand)
    if h_phys <= 0.0 and net < 0.0:
        return 0.0
    if h_phys >= H_MAX and net > 0.0:
        return 0.0
    return net / config["area"]


def rk4_step(h: float, dt: float, demand: float, config: dict, setpoint: float,
             automatic: bool) -> float:
    """Un paso de Runge–Kutta clásico de 4.º orden con demanda constante."""
    def f(x: float) -> float:
        return level_derivative(x, demand, config, setpoint, automatic)

    k1 = f(h)
    k2 = f(h + 0.5 * dt * k1)
    k3 = f(h + 0.5 * dt * k2)
    k4 = f(h + dt * k3)
    return clamp(h + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4), 0.0, H_MAX)


def hydrostatic_pressure_kpa(h: float) -> float:
    """Presión manométrica en el fondo del tanque: P = rho * g * h [kPa]."""
    return RHO_WATER * GRAVITY * h / 1000.0


def auto_equilibrium(config: dict, setpoint: float) -> float:
    """Equilibrio analítico en AUTO, sin demanda y sin saturación de la bomba.

    De Q_base + Kp (h_ref - h*) = C sqrt(h*), con x = sqrt(h*):
        Kp x^2 + C x - (Q_base + Kp h_ref) = 0
    se toma la raíz positiva y h* = x^2.
    """
    c, kp = config["c"], config["kp"]
    q_base = nominal_inflow(setpoint)
    if kp <= 0.0:
        return clamp((q_base / c) ** 2, 0.0, H_MAX) if c > 0 else H_MAX
    discriminant = c * c + 4.0 * kp * (q_base + kp * setpoint)
    x = (-c + math.sqrt(max(discriminant, 0.0))) / (2.0 * kp)
    return clamp(x * x, 0.0, H_MAX)


def manual_equilibrium(config: dict) -> float:
    """Equilibrio en MANUAL sin demanda: Q_manual = C sqrt(h*) => h* = (Q/C)^2."""
    q = clamp(config["q_manual"], 0.0, config["q_max"])
    return clamp((q / config["c"]) ** 2, 0.0, H_MAX)


def linear_time_constant(config: dict, h_eq: float, automatic: bool = True) -> float:
    """Constante de tiempo de la linealización alrededor de h*.

    d(dh/dt)/dh |_{h*} = -(Kp + C / (2 sqrt(h*))) / A  =>  tau = A / (Kp + C/(2 sqrt(h*)))
    En MANUAL el término Kp desaparece.
    """
    if h_eq <= 0.0:
        return math.inf
    slope = config["c"] / (2.0 * math.sqrt(h_eq))
    if automatic:
        slope += config["kp"]
    return config["area"] / slope
