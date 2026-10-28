# Aqua Dynamics — Regulador dinámico de flujo y presión

Proyecto de **Modelos de Simulación** (Alternativa 8). Simulación híbrida de un
tanque de acueducto: una **ecuación diferencial continua** gobierna el nivel y la
presión, y **eventos discretos** representan la demanda intermitente de los
consumidores. La interfaz web muestra el nivel del agua oscilando en tiempo real.

- Contexto, modelo y arquitectura: [docs/CONTEXTO.md](docs/CONTEXTO.md)
- Cómo comprobar matemáticamente que la simulación es correcta: [docs/VERIFICACION.md](docs/VERIFICACION.md)

Los eventos discretos tienen dos modos (interruptor en el panel **Eventos
discretos**): **Manual**, donde cada demanda se abre con el botón GED, y
**Automático**, donde llegan solas como proceso de Poisson. La app inicia en
Manual.

## Inicio rápido

Requisitos: [uv](https://docs.astral.sh/uv/) y un navegador moderno. uv
descarga la versión de Python indicada en `.python-version` (3.12) si no está
instalada, crea el entorno virtual `.venv` e instala las versiones exactas de
`uv.lock`.

Instalar uv (una sola vez):

```powershell
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ejecutar:

```bash
cp .env.example .env     # Windows: copy .env.example .env
uv sync                  # crea .venv e instala dependencias
uv run app.py
```

En Windows también basta con doble clic en `run_windows.bat`.

Abrir <http://127.0.0.1:8050>. Detener con `Ctrl+C`.

Gestión de dependencias:

```bash
uv add <paquete>             # agrega dependencia y actualiza uv.lock
uv add --dev <paquete>       # dependencia solo de desarrollo
uv lock --upgrade            # actualiza versiones bloqueadas
```

## Configuración (`.env`)

| Variable | Defecto | Uso |
|---|---|---|
| `APP_HOST` | `127.0.0.1` | Interfaz donde escucha el servidor |
| `APP_PORT` | `8050` | Puerto |
| `APP_DEBUG` | `false` | Modo depuración de Dash |
| `SIM_INTERVAL_MS` | `500` | Periodo real de refresco de la pantalla [ms] |
| `SIM_SECONDS_PER_TICK` | `0.5` | Tiempo simulado por refresco [s] |
| `SIM_INTEGRATION_STEP` | `0.05` | Paso máximo de RK4 [s] |
| `SIM_SEED` | `42` | Semilla inicial de los eventos |

`.env` es local y no se versiona; `.env.example` es la plantilla.

## Pruebas y verificación

```bash
uv run pytest                          # 34 pruebas unitarias y de verificación
uv run python -m regulador.verificacion   # informe numérico para la sustentación
```

## Estructura

```
pyproject.toml          dependencias y configuración (uv, pytest)
uv.lock                 versiones exactas bloqueadas
.python-version         versión de Python para uv
app.py                  punto de entrada (uv run app.py)
regulador/
  config.py             constantes físicas, parámetros nominales, lectura de .env
  model.py              ecuación diferencial, regulador P, RK4, equilibrios
  events.py             generación de eventos discretos (Poisson + semilla)
  simulation.py         simulación híbrida: integra entre discontinuidades
  figures.py            gráficas Plotly (tanque 3D, h(t), caudales)
  layout.py             componentes de la interfaz Dash
  callbacks.py          conexión interfaz ↔ simulación
  app.py                fábrica create_app()
  verificacion.py       verificaciones matemáticas ejecutables
assets/style.css        estilos
tests/                  pruebas pytest
docs/                   documentación
```

## Dónde está la ecuación diferencial

`regulador/model.py` → `level_derivative()`:

$$\frac{dh}{dt}=\frac{Q_{in}(h)-C\sqrt{h}-D(t)}{A}$$

Se integra con `rk4_step()` y `simulation.integrate_interval()`.

## Alcance

Modelo concentrado y educativo de un tanque, no una simulación de ingeniería de
una red real. No usar para operación real.
