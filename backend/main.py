from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


# Base de datos simulada
productos = [
    {"id": 1, "nombre": "Café Americano", "precio": 25.0},
    {"id": 2, "nombre": "Capuchino", "precio": 35.0},
    {"id": 3, "nombre": "Latte", "precio": 30.0},
    {"id": 4, "nombre": "Pan dulce", "precio": 15.0},
]

pedidos: List[Dict[str, object]] = []


# Modelo de datos de un pedido
class Pedido(BaseModel):
    productos: List[int]
    total: float
    estado: str = "pendiente"
    modo: Optional[str] = None


class PedidoEstado(BaseModel):
    estado: str


def _producto_por_id(pid: int) -> Optional[Dict[str, object]]:
    return next((p for p in productos if p["id"] == pid), None)


def _serializar_pedido(data: Dict[str, object]) -> Dict[str, object]:
    nombres = []
    for pid in data["productos"]:
        prod = _producto_por_id(pid)
        if prod:
            nombres.append(prod.get("nombre"))
    return {
        **data,
        "productos_nombres": nombres,
    }


@app.get("/api/menu")
async def get_menu():
    return productos


@app.post("/api/pedidos")
async def create_pedido(pedido: Pedido):
    pedido_id = len(pedidos) + 1
    total = 0.0
    for pid in pedido.productos:
        prod = _producto_por_id(pid)
        if prod:
            total += float(prod.get("precio", 0))
    stored = {
        "id": pedido_id,
        "productos": pedido.productos,
        "total": total or pedido.total,
        "estado": pedido.estado,
        "modo": pedido.modo,
    }
    pedidos.append(stored)
    return {"mensaje": "Pedido creado", "id": pedido_id}


@app.get("/api/pedidos")
async def get_pedidos():
    return [_serializar_pedido(p) for p in pedidos]


@app.get("/api/pedidos/{pedido_id}")
async def get_pedido(pedido_id: int):
    pedido = next((p for p in pedidos if p["id"] == pedido_id), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return _serializar_pedido(pedido)


@app.put("/api/pedidos/{pedido_id}/estado")
async def update_estado(pedido_id: int, data: PedidoEstado):
    pedido = next((p for p in pedidos if p["id"] == pedido_id), None)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    nuevo_estado = (data.estado or "").strip().lower()
    if nuevo_estado:
        pedido["estado"] = nuevo_estado
    return {"mensaje": "Estado actualizado", "estado": pedido["estado"]}
