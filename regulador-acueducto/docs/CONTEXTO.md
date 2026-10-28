# Contexto y documentación del proyecto

## 1. Enunciado

> **Alternativa 8: Regulador Dinámico de Flujo y Presión en Redes de Acueducto.**
> Enfoque: ecuaciones diferenciales continuas para la dinámica hidráulica de
> presiones y flujos en tanques (RA3) y eventos discretos que representan la
> demanda intermitente de los consumidores. Muestra el nivel de agua oscilando
> dinámicamente.

## 2. Qué hace la aplicación

Simula un tanque de almacenamiento que abastece a un sector de acueducto:

- Una **bomba** llena el tanque. En modo **MANUAL** entrega un caudal fijo; en
  modo **AUTO** un **regulador proporcional** ajusta el caudal para llevar el
  nivel a un valor objetivo $h_{ref}$.
- El tanque **descarga por gravedad** hacia la red (ley de Torricelli).
- **Consumidores** (Residencial Norte, Zona Comercial, Sector Escolar, Conjunto
  Los Pinos, Barrio La Rivera) abren y cierran su demanda. Un interruptor
  elige cómo se generan: **Manual** (cada clic en **GED** abre uno) o
  **Automático** (llegan solos en instantes aleatorios). La app inicia en Manual.
- Se muestran en tiempo real el nivel (tanque 3D y curva $h(t)$), la presión
  hidrostática, los caudales y los registros de telemetría y eventos.

## 3. Modelo matemático

### 3.1 Parte continua (RA3)

Tanque cilíndrico de área constante $A$, volumen $V = A\,h$. Balance de volumen:

$$\frac{dV}{dt} = Q_{in} - Q_{out} - D(t) \quad\Longrightarrow\quad
\boxed{\frac{dh}{dt} = \frac{Q_{in}(h) - Q_{out}(h) - D(t)}{A}}$$

| Término | Expresión | Significado |
|---|---|---|
| $Q_{out}(h)$ | $C\sqrt{h}$ | Descarga por gravedad (Torricelli) |
| $Q_{in}$ AUTO | $\mathrm{sat}_{[0,Q_{max}]}\big[Q_b + K_p(h_{ref}-h)\big]$ | Regulador P con bomba limitada |
| $Q_b$ | $C_{nom}\sqrt{h_{ref}}$ | Caudal base calibrado con $C_{nom}=0.018$ |
| $Q_{in}$ MANUAL | $\mathrm{sat}_{[0,Q_{max}]}(Q_{manual})$ | Caudal fijo |
| $D(t)$ | $\sum_i q_i\,\mathbf{1}[t_i \le t < t_i + d_i]$ | Demanda de los eventos activos |
| $P$ | $\rho g h$ | Presión manométrica en el fondo |

Restricciones físicas: $0 \le h \le H_{max} = 6\,\text{m}$ (tanque vacío / rebose).

### 3.2 Parte discreta (eventos)

Cada consumidor que abre genera un **pulso rectangular** de demanda:

- **Modo Manual** (por defecto): un evento por cada clic en GED, con inicio en
  el instante actual. No se generan llegadas automáticas.
- **Modo Automático**: llegadas como proceso de Poisson, tiempos entre llegadas
  $X \sim \text{Exp}(\text{media}=12\,\text{s})$, acotados a $\ge 1$ s. La
  primera llegada se programa desde el instante en que se activa el
  interruptor (sin ráfaga de eventos "atrasados"). GED queda deshabilitado.
- El interruptor de eventos es **independiente** del modo AUTO/MANUAL del
  regulador hidráulico.
- Caudal $q \sim U(9, 23)$ L/s; duración $d \sim U(6, 15)$ s; consumidor uniforme.
- Cada número aleatorio se genera con `random.Random(f(seed, índice))`: la
  **misma semilla reproduce exactamente** la misma secuencia de eventos, siempre
  que se repitan también los clics de GED y el instante en que se activa el
  modo Automático.

### 3.3 Acoplamiento híbrido

$D(t)$ es **constante a trozos**: solo cambia cuando un evento empieza o
termina. El simulador (`simulation.integrate_interval`) parte cada intervalo en
esos instantes y en cada tramo integra una EDO autónoma con **Runge–Kutta 4**
(paso $\le 0.05$ s). Así el integrador nunca cruza una discontinuidad y conserva
su precisión. Ver la prueba 8 de [VERIFICACION.md](VERIFICACION.md).

### 3.4 Parámetros nominales

| Parámetro | Valor | Unidad |
|---|---:|---|
| Área $A$ | 3.0 | m² |
| Coeficiente $C$ | 0.018 | m^(5/2)/s |
| Ganancia $K_p$ | 0.12 | m²/s |
| Caudal máximo $Q_{max}$ | 0.09 | m³/s |
| Caudal manual $Q_{manual}$ | 0.036 | m³/s |
| Nivel objetivo $h_{ref}$ | 4.0 | m |
| Nivel inicial $h(0)$ | 3.35 | m |
| Semilla | 42 | — |
| Intervalo medio entre eventos | 12 | s |

Resultados clave (derivados en [VERIFICACION.md](VERIFICACION.md)):

- Equilibrio AUTO nominal sin demanda: $h^* = 4.000$ m, $\tau \approx 24.1$ s.
- Con $C = 0.030$: $h^* \approx 3.812$ m (error estacionario del regulador P).
- Equilibrio MANUAL: $h^* = (Q_{manual}/C)^2 = 4.000$ m, $\tau \approx 667$ s.

## 4. Arquitectura del código

```
Navegador ──(cada 500 ms, dcc.Interval)──► callbacks.control_simulation
                                               │
                     simulation.advance_simulation(state)
                       ├─ schedule_arrivals  → events.make_event (semilla)
                       └─ integrate_interval → model.rk4_step → model.level_derivative
                                               │
                         dcc.Store("sim-state") │ (estado JSON)
                                               ▼
                               callbacks.render_dashboard → figures.*
```

| Módulo | Responsabilidad | Depende de Dash |
|---|---|---|
| `config.py` | Constantes, parámetros nominales, variables de `.env` | No |
| `model.py` | Física pura: EDO, regulador, RK4, equilibrios, τ | No |
| `events.py` | Eventos discretos y $D(t)$ | No |
| `simulation.py` | Estado, avance temporal, validación de entradas | No |
| `figures.py` | Figuras Plotly | No (solo Plotly) |
| `layout.py` | Componentes visuales | Sí |
| `callbacks.py` | Lógica de interacción | Sí |
| `app.py` | Fábrica `create_app()` | Sí |
| `verificacion.py` | Verificaciones matemáticas ejecutables | No |

El núcleo matemático no importa Dash: se puede probar y reutilizar en scripts.

### Estado de la simulación (`dcc.Store`)

```python
{
  "time": float, "h": float, "h_ref": float,
  "automatic": bool,          # regulador AUTO/MANUAL
  "events_automatic": bool,   # eventos discretos Automático/Manual
  "running": bool,
  "config": {"area", "c", "kp", "q_max", "q_manual", "seed", "mean_gap"},
  "events": [...],            # eventos aún no terminados
  "event_log": [...],         # últimos 40 para la tabla
  "auto_event_index": int, "manual_event_index": int, "next_auto_time": float,
  "history": [...],           # últimas 360 muestras (3 min simulados)
}
```

## 5. Controles de la interfaz

| Control | Efecto |
|---|---|
| Objetivo + **Equilibrar** | Alterna AUTO/MANUAL; en AUTO usa el objetivo escrito |
| Slider caudal manual | $Q_{manual}$ (aplica desde el siguiente tick) |
| Interruptor Manual / Automático | Modo de generación de eventos discretos (no afecta al regulador) |
| **GED · Generar evento** | Abre un consumidor en el instante actual (solo en modo Manual) |
| Continuar / Pausar | Reanuda o detiene el reloj (en pausa el `Interval` se desactiva) |
| Reiniciar / Aplicar parámetros | Reinicia con los valores del panel avanzado; vuelve a MANUAL |
| ☰ | Oculta/muestra el menú (callback en el navegador, sin ir al servidor) |

## 6. Cambios de la refactorización

1. **Bug del título que parpadeaba.** Dash, por defecto (`update_title="Updating..."`),
   cambia `document.title` mientras un callback está en curso. Con el
   `dcc.Interval` disparando cada 500 ms, la pestaña alternaba sin parar entre
   "Updating..." y el título real, como si la página se recargara. Solución:
   `Dash(..., update_title=None)` en `regulador/app.py`.
2. **Integración en discontinuidades.** Antes, RK4 evaluaba $D(t)$ en cada
   etapa y un evento que empezaba a mitad de paso mezclaba dos demandas en el
   mismo paso: error ≈ $10^{-5}$ m que no disminuía al reducir $\Delta t$. Ahora
   se integra por tramos entre discontinuidades: error ≈ $10^{-10}$ m.
3. **Estructura modular** (`regulador/`) separando física, eventos,
   simulación, gráficas, interfaz y callbacks.
4. **Configuración por entorno** (`.env` + `python-dotenv`) y gestión del
   proyecto con **uv**: dependencias en `pyproject.toml`, versiones exactas en
   `uv.lock`, Python fijado en `.python-version`, entorno `.venv` creado por
   `uv sync`.
5. **Pausa real:** el `dcc.Interval` se desactiva en pausa (antes seguía
   enviando peticiones cada 500 ms).
6. **Layout como función:** recargar la página inicia una simulación nueva.
7. **Sin pandas:** dependencia eliminada (solo se usaba para leer listas).
8. **Pruebas** (`tests/`, 34 casos) y **verificación numérica** ejecutable.
9. Nota de estabilidad: ahora también informa equilibrio y τ en modo MANUAL.
10. **Interruptor de eventos Manual/Automático** (de la versión `app_update.py`)
    integrado en la arquitectura modular, con sus estilos en `assets/style.css`
    y GED deshabilitado en modo Automático.

## 7. Limitaciones del modelo

- Un solo tanque concentrado; no se modelan tuberías, pérdidas de carga,
  golpe de ariete ni curva real de la bomba.
- La descarga $C\sqrt{h}$ es una aproximación de orificio.
- Regulador solo proporcional: puede quedar error estacionario si el $C$ real
  difiere del nominal (se deja así a propósito para la Prueba A).
- Los eventos son pulsos rectangulares (apertura/cierre instantáneos).
- Para uso real se requerirían geometría, curvas de bomba, calibración y
  validación con datos de campo.

## 8. Guion sugerido para la sustentación

1. Explicar el balance de volumen y mostrar `level_derivative()` en `model.py`.
2. Mostrar cómo `active_demand()` y `breakpoints()` (en `events.py`) acoplan los
   eventos discretos a la ecuación continua.
3. Activar AUTO y pulsar **GED**: el nivel cae, $Q_{in}$ sube, el nivel se recupera.
   Luego pasar el interruptor de eventos a **Automático** para ver la
   oscilación continua del nivel con demanda intermitente.
4. Cambiar $C$ a 0.030, aplicar, activar AUTO y comparar con $h^* \approx 3.812$ m
   calculado a mano.
5. Volver a $C = 0.018$ y cambiar la semilla a 7: cambian los eventos, no el
   equilibrio.
6. Ejecutar `python -m regulador.verificacion` y explicar cada comprobación.
