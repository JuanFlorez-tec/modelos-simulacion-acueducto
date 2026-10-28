
"""Callbacks de Dash: conectan la interfaz con la simulación."""
from __future__ import annotations

from copy import deepcopy

from dash import Dash, Input, Output, State, ctx, no_update

from . import events as ev
from .config import DEFAULT_CONFIG, TABLE_ROWS
from .figures import make_flow_figure, make_level_figure, make_tank_figure
from .model import (
    auto_equilibrium,
    hydrostatic_pressure_kpa,
    inlet_flow,
    linear_time_constant,
    manual_equilibrium,
)
from .simulation import (
    add_manual_event,
    advance_simulation,
    config_from_inputs,
    initial_state,
    safe_float,
    safe_setpoint,
    set_events_automatic,
)
from .layout import EVENT_MODE_HELP


def _stability_note(state: dict) -> str:
    cfg = state["config"]

    if state["automatic"]:
        h_eq = auto_equilibrium(cfg, state["h_ref"])
        tau = linear_time_constant(cfg, h_eq, automatic=True)

        return (
            f"Equilibrio teórico AUTO sin demanda: "
            f"h* ≈ {h_eq:.3f} m, τ ≈ {tau:.1f} s. "
            "Pendiente local negativa ⇒ estable si la bomba no está saturada."
        )

    h_eq = manual_equilibrium(cfg)
    tau = linear_time_constant(cfg, h_eq, automatic=False)

    return (
        f"Equilibrio teórico MANUAL sin demanda: "
        f"h* = (Qin/C)² ≈ {h_eq:.3f} m, τ ≈ {tau:.1f} s."
    )


def _measure_rows(history: list[dict]) -> list[dict]:
    """Últimas muestras formateadas, la más reciente primero."""
    return [
        {
            "t": f"{row['t']:.1f}",
            "h": f"{row['h']:.3f}",
            "pressure": f"{row['pressure']:.2f}",
            "qin": f"{row['qin'] * 1000:.1f}",
            "qout": f"{row['qout'] * 1000:.1f}",
            "demand": f"{row['demand'] * 1000:.1f}",
            "mode": row["mode"],
        }
        for row in reversed(history[-TABLE_ROWS:])
    ]


def register_callbacks(app: Dash) -> None:

    @app.callback(
        Output("sim-state", "data"),
        Output("clock", "disabled"),
        Input("clock", "n_intervals"),
        Input("btn-continue", "n_clicks"),
        Input("btn-pause", "n_clicks"),
        Input("btn-reset", "n_clicks"),
        Input("btn-auto", "n_clicks"),
        Input("btn-event-mode", "n_clicks"),
        Input("btn-event", "n_clicks"),
        Input("btn-apply", "n_clicks"),
        State("sim-state", "data"),
        State("h-target", "value"),
        State("q-manual", "value"),
        State("p-area", "value"),
        State("p-c", "value"),
        State("p-kp", "value"),
        State("p-qmax", "value"),
        State("p-seed", "value"),
        State("p-arrival", "value"),
        prevent_initial_call=True,
    )
    def control_simulation(
        _tick, _cont, _pause, _reset, _auto,
        _event_mode, _event, _apply,
        state, target, q_manual,
        area, c, kp, q_max, seed, mean_gap
    ):
        trigger = ctx.triggered_id
        state = deepcopy(state) if state else initial_state()

        # El caudal manual se conserva y aplica desde el siguiente tick.
        state["config"]["q_manual"] = safe_float(
            q_manual,
            DEFAULT_CONFIG["q_manual"],
            0.0,
            0.5,
        )

        if trigger == "clock":
            if not state["running"]:
                return no_update, True

            return advance_simulation(state), no_update

        if trigger == "btn-continue":
            state["running"] = True

        elif trigger == "btn-pause":
            state["running"] = False

        elif trigger == "btn-auto":
            # Conserva el objetivo y alterna entre MANUAL y AUTOMÁTICO.
            state["h_ref"] = safe_setpoint(target, state["h_ref"])
            state["automatic"] = not state["automatic"]

        elif trigger == "btn-event-mode":
            # Solo cambia la generación de eventos.
            # No cambia el modo del regulador.
            state = set_events_automatic(
                state,
                not state.get("events_automatic", False),
            )

        elif trigger == "btn-event":
            # El botón GED solo genera eventos en modo manual.
            if state.get("events_automatic", False):
                return no_update, no_update

            state = add_manual_event(state)

        elif trigger in ("btn-reset", "btn-apply"):
            # Reinicia la simulación y vuelve al modo MANUAL.
            config = config_from_inputs(
                area=area,
                c=c,
                kp=kp,
                q_max=q_max,
                seed=seed,
                mean_gap=mean_gap,
                q_manual=q_manual,
            )

            state = initial_state(
                config,
                safe_setpoint(target),
                automatic=False,
                running=True,
            )

        else:
            return no_update, no_update

        return state, not state["running"]

    # Mostrar u ocultar el menú lateral sin ir al servidor.
    app.clientside_callback(
        """
        function(_clicks, current) {
            current = current || "sidebar";
            return current.includes("collapsed")
                ? "sidebar"
                : "sidebar collapsed";
        }
        """,
        Output("sidebar", "className"),
        Input("btn-menu", "n_clicks"),
        State("sidebar", "className"),
        prevent_initial_call=True,
    )

    @app.callback(
        Output("tank-graph", "figure"),
        Output("level-graph", "figure"),
        Output("flow-graph", "figure"),

        # Métricas superiores
        Output("metric-level", "children"),
        Output("metric-pressure", "children"),
        Output("metric-demand", "children"),
        Output("metric-inflow", "children"),
        Output("metric-outflow", "children"),  # NUEVO: caudal de salida

        Output("run-state-label", "children"),
        Output("run-dot", "className"),
        Output("sim-time-label", "children"),
        Output("btn-auto", "children"),
        Output("mode-note", "children"),
        Output("event-live-note", "children"),
        Output("btn-event-mode", "className"),
        Output("event-mode-label", "children"),
        Output("event-mode-label", "className"),
        Output("event-mode-help", "children"),
        Output("btn-event", "disabled"),
        Output("active-event-count", "children"),
        Output("live-c-value", "children"),
        Output("live-seed-value", "children"),
        Output("tank-status", "children"),
        Output("stability-note", "children"),
        Output("measure-table", "data"),
        Output("event-table", "data"),

        # Habilitar o deshabilitar los controles del regulador.
        Output("h-target", "disabled"),
        Output("q-manual", "disabled"),

        Input("sim-state", "data"),
    )
    def render_dashboard(state):
        state = state or initial_state()

        cfg = state["config"]
        h = float(state["h"])
        t = float(state["time"])

        # Estado del regulador.
        automatic = bool(state["automatic"])

        # Eventos y demanda activa.
        active = ev.active_events(state["events"], t)
        demand = sum(e["q"] for e in active)

        # Caudal de entrada (m³/s).
        qin = inlet_flow(
            h,
            cfg,
            state["h_ref"],
            automatic,
        )

        # NUEVO: caudal de salida (m³/s).
        # Ecuación hidráulica del modelo: Qout = C · √h.
        # Se evita la raíz cuadrada de un nivel negativo.
        qout = cfg["c"] * (max(h, 0.0) ** 0.5)

        running = state["running"]

        events_auto = bool(
            state.get("events_automatic", False)
        )

        event_mode = "automatic" if events_auto else "manual"

        if automatic:
            auto_button = "⚖️  Cambiar a modo manual"
            mode_note = (
                f"AUTO · objetivo {state['h_ref']:.2f} m "
                "· regulación proporcional"
            )
        else:
            auto_button = "⚖️  Equilibrar · Modo automático"
            mode_note = (
                f"MANUAL · Qin fijado en "
                f"{cfg['q_manual'] * 1000:.1f} L/s"
            )

        # Información de los eventos activos.
        if active:
            names = ", ".join(
                e["consumer"] for e in active
            )
            event_note = (
                f"{len(active)} evento(s) activo(s): {names}"
            )
        else:
            event_note = (
                "Sin eventos activos · demanda adicional D(t) = 0"
            )

        # En AUTO, los controles manuales quedan bloqueados.
        controls_disabled = automatic

        return (
            # Gráficas
            make_tank_figure(state),
            make_level_figure(state),
            make_flow_figure(state),

            # Métricas superiores
            f"{h:.3f}",
            f"{hydrostatic_pressure_kpa(h):.2f}",
            f"{demand * 1000:.1f}",
            f"{qin * 1000:.1f}",
            f"{qout * 1000:.1f}",  # NUEVO: Qout en L/s

            # Estado de la simulación
            "En ejecución" if running else "Pausada",
            "status-dot running" if running else "status-dot paused",
            f"t = {t:.1f} s",

            # Estado del regulador
            auto_button,
            mode_note,
            event_note,

            # Modo de eventos
            f"event-mode-switch {event_mode}",
            "Automático" if events_auto else "Manual",
            f"event-mode-label {event_mode}",
            EVENT_MODE_HELP[events_auto],

            events_auto,
            str(len(active)),
            f"{cfg['c']:.3f}",
            str(cfg["seed"]),
            "MODELO ACTIVO" if running else "SIMULACIÓN PAUSADA",
            _stability_note(state),

            # Tablas
            _measure_rows(state.get("history", [])),
            list(
                reversed(
                    state.get("event_log", [])[-TABLE_ROWS:]
                )
            ),

            # Estado de los controles de entrada
            controls_disabled,  # h-target.disabled
            controls_disabled,  # q-manual.disabled
        )
