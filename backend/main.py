import json
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


# Base de datos simulada
productos = [
    {
        "id": 1,
        "nombre": "Chilaquiles verdes",
        "precio": 95.0,
        "seccion": "Desayunos",
        "descripcion": "Totopos bañados en salsa verde con pollo deshebrado, crema y queso fresco.",
    },
    {
        "id": 2,
        "nombre": "Molletes con pico de gallo",
        "precio": 72.0,
        "seccion": "Desayunos",
        "descripcion": "Pan bolillo con frijoles refritos, queso gratinado y pico de gallo fresco.",
    },
    {
        "id": 3,
        "nombre": "Omelette de espinacas",
        "precio": 88.0,
        "seccion": "Desayunos",
        "descripcion": "Huevos batidos con espinacas, queso panela y toque de orégano.",
    },
    {
        "id": 4,
        "nombre": "Ensalada César con pollo",
        "precio": 110.0,
        "seccion": "Comidas",
        "descripcion": "Lechuga romana, aderezo casero, crutones y pechuga de pollo a la plancha.",
    },
    {
        "id": 5,
        "nombre": "Tacos de arrachera",
        "precio": 125.0,
        "seccion": "Comidas",
        "descripcion": "Tres tacos en tortilla de maíz con arrachera marinada, cebolla y cilantro.",
    },
    {
        "id": 6,
        "nombre": "Hamburguesa clásica",
        "precio": 118.0,
        "seccion": "Comidas",
        "descripcion": "Carne de res, queso cheddar, jitomate, lechuga y aderezo de la casa.",
    },
    {
        "id": 7,
        "nombre": "Sopa de lentejas",
        "precio": 76.0,
        "seccion": "Cenas",
        "descripcion": "Caldo casero con lentejas, zanahoria y especias reconfortantes.",
    },
    {
        "id": 8,
        "nombre": "Sandwich de pavo y queso",
        "precio": 82.0,
        "seccion": "Cenas",
        "descripcion": "Pan integral con pavo al horno, queso gouda y verduras frescas.",
    },
    {
        "id": 9,
        "nombre": "Crema de champiñones",
        "precio": 79.0,
        "seccion": "Cenas",
        "descripcion": "Crema suave de champiñones salteados con toque de nuez moscada.",
    },
    {
        "id": 10,
        "nombre": "Cheesecake de frutos rojos",
        "precio": 68.0,
        "seccion": "Postres",
        "descripcion": "Rebanada cremosa con base de galleta y compota de frutos rojos.",
    },
    {
        "id": 11,
        "nombre": "Brownie con helado",
        "precio": 64.0,
        "seccion": "Postres",
        "descripcion": "Brownie de chocolate tibio acompañado de helado de vainilla.",
    },
    {
        "id": 12,
        "nombre": "Affogato de espresso",
        "precio": 58.0,
        "seccion": "Postres",
        "descripcion": "Helado de vainilla bañado con un espresso recién hecho.",
    },
    {
        "id": 13,
        "nombre": "Café Americano",
        "precio": 25.0,
        "seccion": "Bebidas",
        "descripcion": "Clásico café americano con granos tostados medios.",
    },
    {
        "id": 14,
        "nombre": "Capuchino",
        "precio": 35.0,
        "seccion": "Bebidas",
        "descripcion": "Espresso con leche vaporizada y espuma suave.",
    },
    {
        "id": 15,
        "nombre": "Latte de vainilla",
        "precio": 38.0,
        "seccion": "Bebidas",
        "descripcion": "Doble espresso con leche cremosa y jarabe de vainilla.",
    },
]

DATA_FILE = Path(__file__).resolve().with_name("pedidos.json")


def _cargar_pedidos() -> List[Dict[str, object]]:
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _guardar_pedidos():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with DATA_FILE.open("w", encoding="utf-8") as fh:
            json.dump(pedidos, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


pedidos: List[Dict[str, object]] = _cargar_pedidos()


# Modelo de datos de un pedido
class Pedido(BaseModel):
    productos: List[int]
    total: float = 0.0
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
    return sorted(productos, key=lambda p: (p.get("seccion", ""), p.get("nombre", "")))



@app.post("/api/pedidos")
async def create_pedido(pedido: Pedido):
    pedido_id = len(pedidos) + 1
    total = 0.0
    for pid in pedido.productos:
        prod = _producto_por_id(pid)
        if not prod:
            raise HTTPException(status_code=400, detail=f"Producto con id {pid} no existe")
        total += float(prod.get("precio", 0))
    stored = {
        "id": pedido_id,
        "productos": pedido.productos,
        "total": total or float(pedido.total or 0),
        "estado": pedido.estado,
        "modo": pedido.modo,
    }
    pedidos.append(stored)
    _guardar_pedidos()
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
        _guardar_pedidos()
    return {"mensaje": "Estado actualizado", "estado": pedido["estado"]}
