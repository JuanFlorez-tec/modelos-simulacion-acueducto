"""Punto de entrada: `python app.py` y abrir http://127.0.0.1:8050.

La lógica vive en el paquete `regulador/`. La configuración de ejecución se lee
de `.env` (ver `.env.example`).
"""
from regulador import create_app
from regulador.config import SETTINGS

app = create_app()
server = app.server  # para servidores WSGI (p. ej. `waitress-serve app:server`)

if __name__ == "__main__":
    app.run(host=SETTINGS.host, port=SETTINGS.port, debug=SETTINGS.debug)
