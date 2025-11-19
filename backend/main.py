from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from pathlib import Path
import json


app = FastAPI()


# ---------------------- Datos de menú ---------------------- #
MENU: List[Dict] = [
    {
        "seccion": "Desayunos",
        "productos": [
            {
                "id": 101,
                "nombre": "Chilaquiles verdes",
                "descripcion": "Totopos crujientes bañados en salsa verde con pollo deshebrado, queso y crema.",
                "precio": 75.0,
            },
            {
                "id": 102,
                "nombre": "Molletes universitarios",
                "descripcion": "Bolillo al horno con frijoles de la casa, queso gratinado y pico de gallo fresco.",
                "precio": 48.0,
            },
            {
                "id": 103,
                "nombre": "Omelette de espinaca",
                "descripcion": "Huevos batidos con espinaca, champiñones y queso panela; se sirve con ensalada.",
                "precio": 62.0,
            },
        ],
    },
    {
        "seccion": "Comidas",
        "productos": [
            {
                "id": 201,
                "nombre": "Pasta poblana",
                "descripcion": "Fettuccine en salsa cremosa de poblano con elote tierno y tiras de pollo a la plancha.",
                "precio": 95.0,
            },
            {
                "id": 202,
                "nombre": "Ensalada mediterránea",
                "descripcion": "Mezcla de hojas verdes con jitomate cherry, aceitunas, queso feta y vinagreta de limón.",
                "precio": 78.0,
            },
            {
                "id": 203,
                "nombre": "Bowl de quinoa",
                "descripcion": "Quinoa al vapor con garbanzos rostizados, vegetales asados y aderezo de tahini.",
                "precio": 88.0,
            },
        ],
    },
    {
        "seccion": "Cenas",
        "productos": [
            {
                "id": 301,
                "nombre": "Wrap de pollo a la parrilla",
                "descripcion": "Tortilla de harina con pollo marinado, lechuga, jitomate y aderezo de yogur.",
                "precio": 72.0,
            },
            {
                "id": 302,
                "nombre": "Sopa de tomate rostizado",
                "descripcion": "Crema ligera de tomate asado con albahaca fresca y crotones de mantequilla.",
                "precio": 55.0,
            },
            {
                "id": 303,
                "nombre": "Tostadas de atún",
                "descripcion": "Base crujiente con atún fresco marinado en soya, aguacate y ajonjolí.",
                "precio": 84.0,
            },
        ],
    },
    {
        "seccion": "Postres",
        "productos": [
            {
                "id": 401,
                "nombre": "Cheesecake de frutos rojos",
                "descripcion": "Rebanada cremosa con base de galleta y coulis de frutos rojos casero.",
                "precio": 58.0,
            },
            {
                "id": 402,
                "nombre": "Brownie de cacao",
                "descripcion": "Brownie oscuro con nuez, servido tibio con ralladura de naranja.",
                "precio": 44.0,
            },
            {
                "id": 403,
                "nombre": "Panqué de plátano",
                "descripcion": "Panqué casero con plátano maduro, chispas de chocolate y toque de canela.",
                "precio": 38.0,
            },
        ],
    },
]


# ---------------------- Modelos ---------------------- #
class PedidoIn(BaseModel):
    productos: List[int]
    total: float
    estado: str
    modo: str


# ---------------------- Utilidades ---------------------- #
DATA_FILE = Path(__file__).parent / "pedidos.json"


def flatten_menu() -> Dict[int, Dict]:
    items = {}
    for section in MENU:
        for prod in section.get("productos", []):
            items[int(prod["id"])] = {
                **prod,
                "seccion": section.get("seccion", "")
            }
    return items


PRODUCTS_BY_ID = flatten_menu()


def load_pedidos() -> List[Dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_pedidos(data: List[Dict]):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


PEDIDOS: List[Dict] = load_pedidos()


def next_id() -> int:
    if not PEDIDOS:
        return 1
    return max(p.get("id", 0) for p in PEDIDOS) + 1


# ---------------------- Endpoints ---------------------- #
@app.get("/api/menu")
async def get_menu():
    return MENU


@app.post("/api/pedidos")
async def create_pedido(pedido: PedidoIn):
    prods = [PRODUCTS_BY_ID.get(pid) for pid in pedido.productos if pid in PRODUCTS_BY_ID]
    if not prods:
        raise HTTPException(status_code=400, detail="Productos no encontrados")

    server_total = sum(float(p.get("precio", 0)) for p in prods)
    data = {
        "id": next_id(),
        "productos": pedido.productos,
        "productos_nombres": [p.get("nombre") for p in prods],
        "total": server_total,
        "estado": pedido.estado,
        "modo": pedido.modo,
    }

    PEDIDOS.append(data)
    save_pedidos(PEDIDOS)
    return {"id": data["id"], "total": server_total}


@app.get("/api/pedidos")
async def get_pedidos():
    return PEDIDOS


@app.get("/api/pedidos/{pedido_id}")
async def get_pedido(pedido_id: int):
    for p in PEDIDOS:
        if int(p.get("id")) == pedido_id:
            return p
    raise HTTPException(status_code=404, detail="Pedido no encontrado")


@app.put("/api/pedidos/{pedido_id}/estado")
async def update_estado(pedido_id: int, data: Dict[str, str]):
    nuevo_estado = data.get("estado")
    for p in PEDIDOS:
        if int(p.get("id")) == pedido_id:
            p["estado"] = nuevo_estado
            save_pedidos(PEDIDOS)
            return {"ok": True, "id": pedido_id, "estado": nuevo_estado}
    raise HTTPException(status_code=404, detail="Pedido no encontrado")
