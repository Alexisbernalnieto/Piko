# Piko — entrada y salida de órdenes para restaurante

PWA para llevar el flujo de órdenes de un restaurante sin papel: capturar la orden, verla avanzar y cerrarla. La idea de diseño es que un mesero la use de pie y en segundos, no que se siente a llenar un formulario.

Estado: en desarrollo.

## Stack

- **API:** FastAPI + Pydantic, servida con Uvicorn
- **Interfaz:** Flet (una sola base de código para web y escritorio)
- **Base de datos:** PostgreSQL (`psycopg2`)
- **Cliente HTTP:** `httpx`
- **Despliegue:** Vercel (`vercel.json`)

## Correr en local

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

La API:

```bash
uvicorn api.main:app --reload
```

La interfaz:

```bash
python src/main.py
```

Necesita una cadena de conexión a PostgreSQL en el entorno antes de arrancar.

## Estructura

```
api/      endpoints FastAPI
src/      interfaz Flet
```
