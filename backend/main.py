from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import json

app = FastAPI()

# Base de datos simulada
productos = [
    {"id": 1, "nombre": "Café Americano", "precio": 25.0},
    {"id": 2, "nombre": "Capuchino", "precio": 35.0},
    {"id": 3, "nombre": "Latte", "precio": 30.0},
    {"id": 4, "nombre": "Pan dulce", "precio": 15.0}
]

pedidos = []

# Modelo de datos de un pedido
class Pedido(BaseModel):
    productos: List[int]
    total: float
    estado: str

@app.get("/api/menu")
async def get_menu():
    return productos

@app.post("/api/pedidos")
async def create_pedido(pedido: Pedido):
    pedidos.append(pedido)
    return {"mensaje": "Pedido creado", "pedido_id": len(pedidos)}

@app.get("/api/pedidos")
async def get_pedidos():
    return pedidos
