import math

import pytest

from regulador.config import DEFAULT_CONFIG, H_MAX
from regulador.model import (
    auto_equilibrium,
    hydrostatic_pressure_kpa,
    inlet_flow,
    level_derivative,
    linear_time_constant,
    nominal_inflow,
    outflow,
)

CFG = dict(DEFAULT_CONFIG)


def test_outflow_torricelli():
    assert outflow(4.0, 0.018) == pytest.approx(0.036)
    assert outflow(-1.0, 0.018) == 0.0


def test_inlet_flow_saturates():
    assert inlet_flow(0.0, CFG, 4.0, automatic=True) == CFG["q_max"]
    assert inlet_flow(H_MAX, {**CFG, "kp": 1.0}, 0.2, automatic=True) == 0.0


def test_inlet_flow_manual_ignores_level():
    assert inlet_flow(1.0, CFG, 4.0, False) == inlet_flow(5.0, CFG, 4.0, False) == CFG["q_manual"]


def test_derivative_zero_at_nominal_equilibrium():
    assert level_derivative(4.0, 0.0, CFG, 4.0, automatic=True) == pytest.approx(0.0, abs=1e-15)


def test_derivative_respects_tank_limits():
    assert level_derivative(0.0, 1.0, CFG, 4.0, automatic=True) == 0.0
    assert level_derivative(H_MAX, 0.0, {**CFG, "q_manual": 0.5, "q_max": 0.5}, 4.0, False) == 0.0


def test_auto_equilibrium_solves_balance():
    cfg = {**CFG, "c": 0.030}
    h = auto_equilibrium(cfg, 4.0)
    assert h == pytest.approx(3.8119, abs=1e-4)
    assert nominal_inflow(4.0) + cfg["kp"] * (4.0 - h) == pytest.approx(outflow(h, cfg["c"]))


def test_time_constant_nominal():
    assert linear_time_constant(CFG, 4.0) == pytest.approx(3.0 / (0.12 + 0.018 / 4.0))


def test_pressure():
    assert hydrostatic_pressure_kpa(1.0) == pytest.approx(9.81)
    assert math.isclose(hydrostatic_pressure_kpa(0.0), 0.0)
