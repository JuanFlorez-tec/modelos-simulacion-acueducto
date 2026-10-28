"""Ejecuta las verificaciones matemáticas de docs/VERIFICACION.md como pruebas."""
import pytest

from regulador.verificacion import run_all


@pytest.mark.parametrize("check", run_all(), ids=lambda c: c.name)
def test_verificacion(check):
    assert check.passed, f"error {check.error:.3e} > tol {check.tolerance:.0e}"
