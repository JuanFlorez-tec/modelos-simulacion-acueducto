"""Estructura visual (componentes Dash) de la aplicación."""
from __future__ import annotations

from dash import dash_table, dcc, html

from .config import DEFAULT_CONFIG, DEFAULT_SETPOINT, SETPOINT_MAX, SETPOINT_MIN, SETTINGS, TABLE_ROWS
from .figures import make_flow_figure, make_level_figure, make_tank_figure

GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}

# Texto de ayuda del interruptor de eventos, indexado por `events_automatic`.
EVENT_MODE_HELP = {
    False: "Modo manual: pulsa Generar evento para registrar una demanda.",
    True: "Modo automático: se generan eventos según el intervalo medio configurado.",
}

TABLE_STYLE = {"overflowX": "auto", "maxHeight": "350px", "overflowY": "auto"}
TABLE_CELL = {
    "backgroundColor": "#111c2e", "color": "#dbe5f0", "border": "1px solid #233149",
    "fontFamily": "Inter, Segoe UI, sans-serif", "fontSize": "12px", "padding": "9px 10px",
    "width": "auto", "whiteSpace": "normal",
}

TABLE_HEADER = {
    "backgroundColor": "#1c2a40",
    "color": "#92a9c3",
    "fontWeight": "700",
    "fontSize": "10px",
    "letterSpacing": "0.06em",
    "textTransform": "uppercase",
    "border": "1px solid #2a3a53",
    "textAlign": "left",
}

# -----------------------------------------------------------------------------
# Componentes reutilizables
# -----------------------------------------------------------------------------
def metric_card(label: str, value_id: str, unit: str, accent: str) -> html.Div:
    return html.Div(className=f"metric-card {accent}", children=[
        html.Div(label, className="metric-label"),
        html.Div(className="metric-number", children=[
            html.Span(id=value_id, children="—", className="metric-value"),
            html.Span(unit, className="metric-unit"),
        ]),
    ])


def number_field(label: str, id_: str, value: float, step: float, min_: float, max_: float,
                 unit: str = "") -> html.Div:
    return html.Div(className="parameter-field", children=[
        html.Label(label, htmlFor=id_),
        html.Div(className="input-with-unit", children=[
            dcc.Input(id=id_, type="number", value=value, step=step, min=min_, max=max_,
                      className="dark-input"),
            html.Span(unit, className="input-unit") if unit else html.Span(),
        ]),
    ])


def card_heading(symbol: str, title: str) -> html.Div:
    return html.Div(className="control-card-heading", children=[
        html.Span(symbol, className="card-symbol"), html.Span(title),
    ])


def panel_heading(kicker: str, title: str) -> html.Div:
    return html.Div([html.Div(kicker, className="panel-kicker"), html.H2(title)])



def data_table(
    id_: str,
    columns: list[tuple[str, str]],
    align: str,
    min_width: str,
    max_width: str,
    **kwargs
) -> dash_table.DataTable:
    # Estilos predeterminados; kwargs puede sobrescribirlos sin duplicar argumentos.
    style_table = kwargs.pop("style_table", TABLE_STYLE)
    style_cell = kwargs.pop("style_cell", {
        **TABLE_CELL,
        "textAlign": align,
        "minWidth": min_width,
        "maxWidth": max_width,
    })
    style_header = kwargs.pop("style_header", TABLE_HEADER)

    return dash_table.DataTable(
        id=id_,
        columns=[{"name": name, "id": col_id} for name, col_id in columns],
        data=[],
        page_action="none",
        fixed_rows={"headers": True},
        style_table=style_table,
        style_cell=style_cell,
        style_header=style_header,
        **kwargs,
    )


# -----------------------------------------------------------------------------
# Secciones
# -----------------------------------------------------------------------------
def sidebar() -> html.Aside:
    return html.Aside(id="sidebar", className="sidebar", children=[
        html.Div(className="brand-row", children=[
            html.Div("≈", className="brand-mark"),
            html.Div([html.Div("AQUA", className="brand-title"),
                      html.Div("DYNAMICS LAB", className="brand-subtitle")]),
        ]),
        html.Div(className="sidebar-section-heading", children="CONTROL DEL SISTEMA"),

        html.Div(className="control-card regulator-card", children=[
            card_heading("◎", "Regulador de equilibrio"),
            html.Div(className="target-row", children=[
                dcc.Input(id="h-target", type="number", value=DEFAULT_SETPOINT,
                          min=SETPOINT_MIN, max=SETPOINT_MAX, step=0.1, className="target-input"),
                html.Span("m", className="target-unit"),
            ]),
            html.Button("⚖  Equilibrar · Modo automático", id="btn-auto", n_clicks=0,
                        className="auto-button"),
            html.Div(id="mode-note", className="mode-note", children="Modo manual · caudal fijado"),
            html.Div(className="manual-control", children=[
                html.Label("Caudal manual de entrada", htmlFor="q-manual"),
                dcc.Slider(id="q-manual", min=0.0, max=0.09, step=0.001,
                           value=DEFAULT_CONFIG["q_manual"],
                           marks={0: "0", 0.03: "30", 0.06: "60", 0.09: "90"},
                           tooltip={"placement": "bottom", "always_visible": False}),
                html.Div("Caudal en L/s (el control interno usa m³/s)", className="field-help"),
            ]),
        ]),

        html.Div(className="control-card event-card", children=[
            card_heading("✦", "Eventos discretos"),
            html.Div(className="event-mode-row", children=[
                html.Button(html.Span(className="event-mode-knob"), id="btn-event-mode", n_clicks=0,
                            className="event-mode-switch manual",
                            title="Cambiar entre generación manual y automática de eventos",
                            **{"aria-label": "Cambiar modo de eventos discretos"}),
                html.Span("Manual", id="event-mode-label", className="event-mode-label manual"),
            ]),
            html.Button("✳  GED · Generar evento", id="btn-event", n_clicks=0, className="event-button"),
            html.Div(EVENT_MODE_HELP[False], id="event-mode-help", className="event-help"),
            html.Div(id="event-live-note", className="event-live-note", children="Sin eventos activos"),
        ]),

        html.Div(className="sidebar-section-heading controls-title", children="REPRODUCCIÓN"),
        html.Div(className="transport-controls", children=[
            html.Button([html.Span("▶", className="control-icon"), "Continuar"], id="btn-continue",
                        n_clicks=0, className="transport-button play-button"),
            html.Button([html.Span("Ⅱ", className="control-icon"), "Pausar"], id="btn-pause",
                        n_clicks=0, className="transport-button pause-button"),
            html.Button([html.Span("↻", className="control-icon"), "Reiniciar"], id="btn-reset",
                        n_clicks=0, className="transport-button reset-button"),
        ]),

        html.Details(className="advanced-settings", children=[
            html.Summary("Parámetros físicos y semilla", className="advanced-summary"),
            html.Div(className="parameters-grid", children=[
                number_field("Área del tanque A", "p-area", DEFAULT_CONFIG["area"], 0.1, 0.25, 100, "m²"),
                number_field("Coeficiente de salida C", "p-c", DEFAULT_CONFIG["c"], 0.001, 0.001, 0.08, "m⁵ᐟ²/s"),
                number_field("Ganancia proporcional Kp", "p-kp", DEFAULT_CONFIG["kp"], 0.01, 0.001, 1.0, "m²/s"),
                number_field("Caudal máximo Qmax", "p-qmax", DEFAULT_CONFIG["q_max"], 0.005, 0.005, 0.5, "m³/s"),
                number_field("Semilla aleatoria", "p-seed", DEFAULT_CONFIG["seed"], 1, 0, 2_147_483_647, "seed"),
                number_field("Intervalo medio entre eventos", "p-arrival", DEFAULT_CONFIG["mean_gap"], 1, 2, 120, "s"),
            ]),
            html.Button("Aplicar parámetros y reiniciar", id="btn-apply", n_clicks=0, className="apply-button"),
            html.Div("A y C alteran la dinámica física. Kp afecta la respuesta del regulador. "
                     "La semilla controla la secuencia de eventos.", className="field-help advanced-help"),
        ]),

        html.Div(className="sidebar-footer", children=[
            html.Div(className="seed-info", children=[html.Span("●", className="online-dot"),
                                                      html.Span("Simulación híbrida local")]),
            html.Div("Modelo educativo · no usar para operación real", className="footer-disclaimer"),
        ]),
    ])


def topbar() -> html.Header:
    return html.Header(className="topbar", children=[
        html.Button("☰", id="btn-menu", n_clicks=0, className="menu-button",
                    title="Mostrar u ocultar menú"),
        html.Div(className="page-heading", children=[
            html.Div("RED DE ACUEDUCTO / MODELO HÍBRIDO", className="eyebrow"),
            html.H1("Regulador dinámico de flujo y presión"),
            html.P("Dinámica continua del tanque + demanda intermitente de consumidores",
                   className="page-subtitle"),
        ]),
        html.Div(className="session-status", children=[
            html.Span(id="run-dot", className="status-dot"),
            html.Span(id="run-state-label", children="En ejecución"),
            html.Span("·", className="status-separator"),
            html.Span(id="sim-time-label", children="t = 0.0 s"),
        ]),
    ])


def metrics_section() -> html.Section:
    return html.Section(className="metric-grid", children=[
        metric_card("NIVEL DEL AGUA", "metric-level", "m", "metric-blue"),
        metric_card("PRESIÓN HIDROSTÁTICA", "metric-pressure", "kPa", "metric-violet"),
        metric_card("DEMANDA ACTIVA", "metric-demand", "L/s", "metric-pink"),
        metric_card("CAUDAL DE ENTRADA", "metric-inflow", "L/s", "metric-green"),
        metric_card("CAUDAL DE SALIDA", "metric-outflow", "L/s", "metric-orange"),
    ])



def simulation_section(state: dict) -> html.Section:
    tank_panel = html.Div(className="panel tank-panel", children=[
        html.Div(className="panel-header", children=[
            panel_heading("VISUALIZACIÓN EN TIEMPO REAL", "Tanque de almacenamiento 3D"),
            html.Div(id="tank-status", className="small-pill", children="MODELO ACTIVO"),
        ]),
        dcc.Graph(id="tank-graph", figure=make_tank_figure(state), config=GRAPH_CONFIG,
                  className="tank-graph"),
        html.Div(className="tank-legend", children=[
            html.Span([html.I(className="legend-dot water-dot"), "Nivel de agua"]),
            html.Span([html.I(className="legend-dot target-dot"), "Nivel objetivo"]),
            html.Span([html.I(className="legend-dot inlet-dot"), "Entrada de bomba"]),
            html.Span([html.I(className="legend-dot outlet-dot"), "Salida hidráulica"]),
        ]),
    ])
    model_panel = html.Div(className="panel model-panel", children=[
        html.Div(className="panel-kicker", children="NÚCLEO MATEMÁTICO"),
        html.H2("Ecuación del sistema"),
        html.Div(className="equation-box", children=[
            html.Div("dh / dt = (Qin − Qout − D(t)) / A", className="equation-main"),
            html.Div("Qout = C · √h", className="equation-sub"),
            html.Div("Qin = sat[Qbase + Kp(href − h)]", className="equation-sub"),
        ]),
        html.Div(className="definition-list", children=[
            html.Div([html.Span("h(t)", className="definition-symbol"), html.Span("Nivel del agua (m)")]),
            html.Div([html.Span("D(t)", className="definition-symbol demand-symbol"),
                      html.Span("Demanda intermitente (m³/s)")]),
            html.Div([html.Span("A, C", className="definition-symbol"), html.Span("Área y coeficiente hidráulico")]),
            html.Div([html.Span("Kp", className="definition-symbol"), html.Span("Ganancia del regulador proporcional")]),
        ]),
        html.Div(className="separator-line"),
        html.Div(className="model-facts", children=[
            html.Div([html.Span("Eventos activos", className="fact-label"),
                      html.Strong(id="active-event-count", children="0", className="fact-value")]),
            html.Div([html.Span("Coeficiente C", className="fact-label"),
                      html.Strong(id="live-c-value", children=f"{DEFAULT_CONFIG['c']:.3f}", className="fact-value")]),
            html.Div([html.Span("Semilla", className="fact-label"),
                      html.Strong(id="live-seed-value", children=str(DEFAULT_CONFIG["seed"]), className="fact-value")]),
        ]),
        html.Div(id="stability-note", className="stability-note",
                 children="La estabilidad depende de la pendiente de la ecuación diferencial."),
    ])
    return html.Section(className="simulation-grid", children=[tank_panel, model_panel])


def charts_section(state: dict) -> html.Section:
    def chart_panel(kicker: str, title: str, unit: str, graph_id: str, figure) -> html.Div:
        return html.Div(className="panel chart-panel", children=[
            html.Div(className="panel-header chart-header", children=[
                panel_heading(kicker, title), html.Span(unit, className="chart-unit"),
            ]),
            dcc.Graph(id=graph_id, figure=figure, config=GRAPH_CONFIG),
        ])

    return html.Section(className="charts-grid", children=[
        chart_panel("RESPUESTA CONTINUA", "Nivel del agua h(t)", "m vs s",
                    "level-graph", make_level_figure(state)),
        chart_panel("FLUJOS DEL SISTEMA", "Entrada, salida y demanda", "L/s vs s",
                    "flow-graph", make_flow_figure(state)),
    ])



def data_section() -> html.Section:
    measure_table = data_table(
        "measure-table",
        [
            ("t (s)", "t"),
            ("h (m)", "h"),
            ("P (kPa)", "pressure"),
            ("Qin (L/s)", "qin"),
            ("Qout (L/s)", "qout"),
            ("D (L/s)", "demand"),
            ("Modo", "mode"),
        ],
        align="left",
        min_width="72px",
        max_width="none",
        style_table={
            "width": "100%",
            "minWidth": "100%",
            "maxWidth": "100%",
            "maxHeight": "350px",
            "overflowY": "auto",
            "overflowX": "auto",
        },
        style_cell={
            **TABLE_CELL,
            "textAlign": "left",
            "minWidth": "72px",
            "maxWidth": "none",
            "width": "auto",
            "whiteSpace": "normal",
        },
        style_data_conditional=[
            {
                "if": {
                    "filter_query": '{mode} = "AUTO"',
                    "column_id": "mode",
                },
                "color": "#6ee7b7",
                "fontWeight": "700",
            },
            {
                "if": {
                    "filter_query": '{mode} = "MANUAL"',
                    "column_id": "mode",
                },
                "color": "#fbbf24",
                "fontWeight": "700",
            },
        ],
    )

    event_table = data_table(
        "event-table",
        [
            ("ID", "id"),
            ("Tipo", "tipo"),
            ("Consumidor", "consumidor"),
            ("Inicio (s)", "t0"),
            ("Duración (s)", "duracion"),
            ("Caudal (L/s)", "q_lps"),
        ],
        align="left",
        min_width="90px",
        max_width="none",
        style_table={
            "width": "100%",
            "minWidth": "100%",
            "maxWidth": "100%",
            "maxHeight": "350px",
            "overflowY": "auto",
            "overflowX": "auto",
        },
        style_cell={
            **TABLE_CELL,
            "textAlign": "left",
            "minWidth": "90px",
            "maxWidth": "none",
            "width": "auto",
            "whiteSpace": "normal",
        },
    )

    return html.Section(
        className="data-grid",
        children=[
            # Primera tabla: Telemetría
            html.Div(
                className="panel data-panel",
                children=[
                    html.Div(
                        className="panel-header table-header",
                        children=[
                            panel_heading(
                                "TELEMETRÍA",
                                "Registros de la simulación",
                            ),
                            html.Span(
                                f"Últimas {TABLE_ROWS} muestras",
                                className="chart-unit",
                            ),
                        ],
                    ),
                    measure_table,
                ],
            ),

            # Segunda tabla: Registro de eventos, debajo de Telemetría
            html.Div(
                className="panel data-panel event-log-panel",
                children=[
                    html.Div(
                        className="panel-header table-header",
                        children=[
                            panel_heading(
                                "REGISTRO DE EVENTOS",
                                "Consumidores",
                            ),
                            html.Span(
                                "GED",
                                className="chart-unit event-unit",
                            ),
                        ],
                    ),
                    event_table,
                    html.Div(
                        "Los eventos no toman capturas: representan aperturas "
                        "de demanda durante la simulación.",
                        className="table-footnote",
                    ),
                ],
            ),
        ],
    )


def build_layout(state: dict) -> html.Div:
    return html.Div(className="app-shell", children=[
        dcc.Store(id="sim-state", data=state, storage_type="memory"),
        dcc.Interval(id="clock", interval=SETTINGS.real_interval_ms, n_intervals=0,
                     disabled=not state["running"]),
        sidebar(),
        html.Main(className="workspace", children=[
            topbar(),
            metrics_section(),
            simulation_section(state),
            charts_section(state),
            data_section(),
            html.Footer(className="page-footer", children=[
                html.Span("AQUA DYNAMICS · MODELO ACADÉMICO"),
                html.Span("Presión manométrica calculada como P = ρgh"),
            ]),
        ]),
    ])
