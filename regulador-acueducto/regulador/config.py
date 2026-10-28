"""Constantes físicas, parámetros nominales y configuración de ejecución.

La configuración de ejecución (host, puerto, debug, semilla...) se lee de
variables de entorno o de un archivo `.env` en la raíz del proyecto.
Ver `.env.example`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

load_dotenv(PROJECT_ROOT / ".env")


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


@dataclass(frozen=True)
class Settings:
    """Configuración del servidor y del reloj de simulación."""

    host: str
    port: int
    debug: bool
    real_interval_ms: int        # periodo del dcc.Interval [ms reales]
    sim_seconds_per_tick: float  # tiempo simulado que avanza cada tick [s]
    integration_step: float      # paso máximo del integrador RK4 [s]
    default_seed: int


def load_settings() -> Settings:
    return Settings(
        host=_env_str("APP_HOST", "127.0.0.1"),
        port=_env_int("APP_PORT", 8050),
        debug=_env_bool("APP_DEBUG", False),
        real_interval_ms=max(100, _env_int("SIM_INTERVAL_MS", 500)),
        sim_seconds_per_tick=max(0.05, _env_float("SIM_SECONDS_PER_TICK", 0.5)),
        integration_step=min(0.5, max(0.001, _env_float("SIM_INTEGRATION_STEP", 0.05))),
        default_seed=_env_int("SIM_SEED", 42),
    )


SETTINGS = load_settings()

# -----------------------------------------------------------------------------
# Constantes físicas
# -----------------------------------------------------------------------------
H_MAX = 6.0          # altura física máxima del tanque [m]
C_NOMINAL = 0.018    # coeficiente de descarga de calibración [m^(5/2)/s]
RHO_WATER = 1000.0   # densidad del agua [kg/m^3]
GRAVITY = 9.81       # gravedad [m/s^2]

# -----------------------------------------------------------------------------
# Límites y tamaños de los registros
# -----------------------------------------------------------------------------
MAX_HISTORY = 360    # muestras guardadas (3 min simulados con ticks de 0.5 s)
MAX_EVENT_LOG = 40
MAX_EVENTS = 100
TABLE_ROWS = 18

SETPOINT_MIN = 0.2
SETPOINT_MAX = H_MAX - 0.2

# -----------------------------------------------------------------------------
# Eventos discretos (demanda de consumidores)
# -----------------------------------------------------------------------------
CONSUMERS = (
    "Residencial Norte",
    "Zona Comercial",
    "Sector Escolar",
    "Conjunto Los Pinos",
    "Barrio La Rivera",
)
EVENT_FLOW_RANGE = (0.009, 0.023)     # caudal por evento [m^3/s] (9–23 L/s)
EVENT_DURATION_RANGE = (6.0, 15.0)    # duración por evento [s simulados]
MIN_INTERARRIVAL = 1.0                # tiempo mínimo entre llegadas [s]

# -----------------------------------------------------------------------------
# Parámetros nominales del modelo
# -----------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "area": 3.0,                       # área transversal del tanque [m^2]
    "c": C_NOMINAL,                    # coeficiente hidráulico real [m^(5/2)/s]
    "kp": 0.12,                        # ganancia proporcional [m^2/s]
    "q_max": 0.09,                     # caudal máximo de la bomba [m^3/s]
    "q_manual": 0.036,                 # caudal fijado en modo manual [m^3/s]
    "seed": SETTINGS.default_seed,     # semilla aleatoria inicial
    "mean_gap": 12.0,                  # intervalo medio entre eventos automáticos [s]
}
DEFAULT_SETPOINT = 4.0
DEFAULT_INITIAL_LEVEL = 3.35

# Rangos admitidos para cada parámetro editable: (mínimo, máximo).
CONFIG_LIMITS = {
    "area": (0.25, 100.0),
    "c": (0.001, 0.08),
    "kp": (0.001, 1.0),
    "q_max": (0.005, 0.5),
    "q_manual": (0.0, 0.5),
    "mean_gap": (2.0, 120.0),
}
