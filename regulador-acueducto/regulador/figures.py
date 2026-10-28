"""Construcción de las figuras Plotly a partir del estado de la simulación."""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go

from .config import H_MAX
from .events import active_demand

GRID_COLOR = "rgba(148,163,184,0.12)"
TRANSPARENT = "rgba(0,0,0,0)"
TANK_SEGMENTS = 42


def _base_layout(height: int, uirevision: str, **extra) -> dict:
    return dict(
        template="plotly_dark", height=height,
        paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
        uirevision=uirevision, **extra,
    )


def _time_axis() -> dict:
    return dict(title="Tiempo simulado (s)", gridcolor=GRID_COLOR, zeroline=False)


# -----------------------------------------------------------------------------
# Tanque 3D
# -----------------------------------------------------------------------------
def _water_traces(h: float, ring_x: np.ndarray, ring_y: np.ndarray) -> list[go.Mesh3d]:
    """Columna de agua (malla lateral) y superficie libre (tapa) a altura h."""
    n = len(ring_x)
    ii, jj, kk = [], [], []
    for i in range(n):
        j = (i + 1) % n
        ii += [i, i]
        jj += [j, n + j]
        kk += [n + j, n + i]
    column = go.Mesh3d(
        x=np.r_[ring_x, ring_x], y=np.r_[ring_y, ring_y],
        z=np.r_[np.zeros(n), np.full(n, h)], i=ii, j=jj, k=kk,
        color="#0EA5E9", opacity=0.37, flatshading=True,
        hovertemplate="Agua · nivel %{z:.2f} m<extra></extra>", name="Columna de agua",
        lighting=dict(ambient=0.65, diffuse=0.6, specular=0.25, roughness=0.45),
    )
    surface = go.Mesh3d(
        x=np.r_[0.0, ring_x], y=np.r_[0.0, ring_y], z=np.full(n + 1, h),
        i=[0] * n, j=list(range(1, n + 1)), k=list(range(2, n + 1)) + [1],
        color="#22D3EE", opacity=0.91, flatshading=False,
        hovertemplate=f"Nivel de agua: {h:.3f} m<extra></extra>", name="Superficie del agua",
        lighting=dict(ambient=0.85, diffuse=0.45, specular=0.35, roughness=0.25),
    )
    return [column, surface]


def _ring(radius: float, z: float, closed_theta: np.ndarray, **kwargs) -> go.Scatter3d:
    return go.Scatter3d(
        x=radius * np.cos(closed_theta), y=radius * np.sin(closed_theta),
        z=np.full_like(closed_theta, z), mode="lines", **kwargs,
    )


def _pipe(x: list[float], z: float, color: str, width: int, name: str) -> go.Scatter3d:
    return go.Scatter3d(
        x=x, y=[0.0] * len(x), z=[z] * len(x), mode="lines+markers",
        line=dict(color=color, width=width), marker=dict(size=4, color=color),
        name=name, hovertemplate=f"{name}<extra></extra>",
    )


def _label(x: float, z: float, text: str, color: str) -> go.Scatter3d:
    return go.Scatter3d(
        x=[x], y=[0.0], z=[z], mode="text", text=[text],
        textfont=dict(color=color, size=11), showlegend=False, hoverinfo="skip",
    )


def make_tank_figure(state: dict) -> go.Figure:
    cfg = state["config"]
    h = min(H_MAX, max(0.0, state["h"]))
    href = state["h_ref"]
    radius = math.sqrt(cfg["area"] / math.pi)
    theta = np.linspace(0.0, 2.0 * math.pi, TANK_SEGMENTS, endpoint=False)
    closed_theta = np.r_[theta, theta[0]]
    ring_x, ring_y = radius * np.cos(theta), radius * np.sin(theta)

    fig = go.Figure()

    # Paredes transparentes del depósito.
    th_grid, z_grid = np.meshgrid(closed_theta, np.linspace(0.0, H_MAX, 16))
    fig.add_trace(go.Surface(
        x=radius * np.cos(th_grid), y=radius * np.sin(th_grid), z=z_grid,
        surfacecolor=np.zeros_like(z_grid),
        colorscale=[[0, "#8CA4B9"], [1, "#8CA4B9"]],
        opacity=0.20, showscale=False, hoverinfo="skip", name="Pared del tanque",
        lighting=dict(ambient=0.8, diffuse=0.35, specular=0.15, roughness=0.8),
    ))

    if h > 0.001:
        fig.add_traces(_water_traces(h, ring_x, ring_y))

    # Aros de base y borde, y referencia del nivel objetivo.
    fig.add_trace(_ring(radius, 0.0, closed_theta, line=dict(color="#94A3B8", width=4),
                        hoverinfo="skip", showlegend=False))
    fig.add_trace(_ring(radius, H_MAX, closed_theta, line=dict(color="#CBD5E1", width=5),
                        hoverinfo="skip", showlegend=False))
    fig.add_trace(_ring(radius * 1.03, href, closed_theta,
                        line=dict(color="#FBBF24", width=3, dash="dash"),
                        name=f"Objetivo {href:.2f} m",
                        hovertemplate=f"Nivel objetivo: {href:.2f} m<extra></extra>"))

    # Tuberías ilustrativas de entrada y salida.
    inlet_z = H_MAX * 0.72
    outlet_z = min(h, H_MAX * 0.28)
    fig.add_trace(_pipe([-radius * 1.9, -radius * 1.1, -radius * 0.95], inlet_z,
                        "#34D399", 9, "Entrada de la bomba"))
    fig.add_trace(_pipe([radius * 0.95, radius * 1.2, radius * 1.85], outlet_z,
                        "#FB923C", 8, "Salida hidráulica"))
    fig.add_trace(_label(radius * 1.45, outlet_z, "Qout", "#FDBA74"))
    fig.add_trace(_label(-radius * 1.55, H_MAX * 0.82, "Qin", "#6EE7B7"))

    demand = active_demand(state["events"], state["time"])
    mode_text = "AUTO" if state["automatic"] else "MANUAL"
    fig.update_layout(**_base_layout(
        420, "tank-camera",
        margin=dict(l=0, r=0, t=8, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=0.0, xanchor="center", x=0.5,
                    font=dict(size=10, color="#CBD5E1"), bgcolor="rgba(15,23,42,0.65)"),
        scene=dict(
            bgcolor=TRANSPARENT,
            xaxis=dict(visible=False, range=[-radius * 2.25, radius * 2.25]),
            yaxis=dict(visible=False, range=[-radius * 1.6, radius * 1.6]),
            zaxis=dict(title="Altura (m)", range=[0, H_MAX], backgroundcolor=TRANSPARENT,
                       gridcolor="rgba(148,163,184,0.15)", zerolinecolor="rgba(148,163,184,0.25)"),
            aspectmode="manual", aspectratio=dict(x=1.25, y=1.0, z=1.45),
            camera=dict(eye=dict(x=1.65, y=1.65, z=1.25)),
        ),
        annotations=[dict(
            x=0.02, y=0.98, xref="paper", yref="paper", xanchor="left", yanchor="top",
            text=(f"<b>t = {state['time']:.1f} s</b> &nbsp;·&nbsp; {mode_text}"
                  f" &nbsp;·&nbsp; D = {demand * 1000:.1f} L/s"),
            showarrow=False, font=dict(size=12, color="#E2E8F0"), bgcolor="rgba(15,23,42,0.78)",
            bordercolor="rgba(148,163,184,0.18)", borderpad=6,
        )],
    ))
    return fig


# -----------------------------------------------------------------------------
# Series temporales
# -----------------------------------------------------------------------------
def _column(history: list[dict], key: str, scale: float = 1.0) -> list[float]:
    return [row[key] * scale for row in history]


def make_level_figure(state: dict) -> go.Figure:
    history = state.get("history", [])
    t = _column(history, "t")
    fig = go.Figure()
    if history:
        fig.add_trace(go.Scatter(
            x=t, y=_column(history, "h"), mode="lines", name="Nivel h(t)",
            line=dict(color="#38BDF8", width=2.8), fill="tozeroy", fillcolor="rgba(56,189,248,0.08)",
            hovertemplate="t=%{x:.1f} s<br>h=%{y:.3f} m<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=t, y=_column(history, "href"), mode="lines", name="Nivel objetivo",
            line=dict(color="#FBBF24", width=1.7, dash="dash"),
            hovertemplate="Objetivo=%{y:.2f} m<extra></extra>",
        ))
    fig.update_layout(**_base_layout(
        300, "level-chart",
        margin=dict(l=42, r=15, t=12, b=38),
        xaxis=_time_axis(),
        yaxis=dict(title="Nivel (m)", range=[0, H_MAX], gridcolor=GRID_COLOR, zeroline=False),
        legend=dict(orientation="h", y=1.08, x=0.0, font=dict(size=10)),
    ))
    return fig


FLOW_SERIES = (
    ("qin", "Entrada Qin", "#34D399", 2.2),
    ("qout", "Salida Qout", "#FB923C", 2.0),
    ("demand", "Demanda discreta D(t)", "#E879F9", 2.4),
)


def make_flow_figure(state: dict) -> go.Figure:
    history = state.get("history", [])
    t = _column(history, "t")
    fig = go.Figure()
    if history:
        for key, label, color, width in FLOW_SERIES:
            fig.add_trace(go.Scatter(
                x=t, y=_column(history, key, 1000.0), mode="lines", name=label,
                line=dict(color=color, width=width),
                hovertemplate=f"{label}: %{{y:.1f}} L/s<br>t=%{{x:.1f}} s<extra></extra>",
            ))
    fig.update_layout(**_base_layout(
        300, "flow-chart",
        margin=dict(l=48, r=15, t=12, b=38),
        xaxis=_time_axis(),
        yaxis=dict(title="Caudal (L/s)", rangemode="tozero", gridcolor=GRID_COLOR, zeroline=False),
        legend=dict(orientation="h", y=1.08, x=0.0, font=dict(size=10)),
    ))
    return fig
