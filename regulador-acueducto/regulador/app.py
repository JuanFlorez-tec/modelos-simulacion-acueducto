"""Fábrica de la aplicación Dash."""
from __future__ import annotations

from dash import Dash

from .callbacks import register_callbacks
from .config import ASSETS_DIR
from .layout import build_layout
from .simulation import initial_state

APP_TITLE = "Aqua Dynamics · Simulador hidráulico"


def create_app() -> Dash:
    app = Dash(
        __name__,
        title=APP_TITLE,
        # Por defecto Dash cambia document.title a "Updating..." mientras corre
        # un callback. Con el dcc.Interval disparando cada 500 ms eso hacía que
        # el título de la pestaña parpadeara sin parar.
        update_title=None,
        assets_folder=str(ASSETS_DIR),
    )
    # Layout como función: cada recarga de la página arranca una simulación nueva.
    app.layout = lambda: build_layout(initial_state())
    register_callbacks(app)
    return app
