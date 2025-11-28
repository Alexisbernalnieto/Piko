import json
import os
import psycopg2
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# --- CONEXIÓN DB ---
# Vercel inyectará esta variable
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL no configurada")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                productos TEXT NOT NULL,
                total REAL NOT NULL,
                estado TEXT NOT NULL,
                modo TEXT,
                created_at TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Init Error: {e}")

# Intentar iniciar DB al arrancar (en serverless esto corre en cada inicio en frío)
init_db()

# --- DATOS ---
productos = [
    {"id": 1, "nombre": "Chilaquiles verdes", "precio": 95.0, "seccion": "Desayunos", "descripcion": "Totopos en salsa verde."},
    {"id": 2, "nombre": "Molletes", "precio": 72.0, "seccion": "Desayunos", "descripcion": "Bolillo con frijoles y queso."},
    {"id": 3, "nombre": "Omelette espinacas", "precio": 88.0, "seccion": "Desayunos", "descripcion": "Con queso panela."},
    {"id": 4, "nombre": "Ensalada César", "precio": 110.0, "seccion": "Comidas", "descripcion": "Con pollo a la plancha."},
    {"id": 5, "nombre": "Tacos Arrachera", "precio": 125.0, "seccion": "Comidas", "descripcion": "3 piezas con guacamole."},
    {"id": 6, "nombre": "Hamburguesa", "precio": 118.0, "seccion": "Comidas", "descripcion": "Res, queso y papas."},
    {"id": 7, "nombre": "Sopa Lentejas", "precio": 76.0, "seccion": "Cenas", "descripcion": "Estilo casero."},
    {"id": 8, "nombre": "Sandwich Pavo", "precio": 82.0, "seccion": "Cenas", "descripcion": "Pan integral."},
    {"id": 9, "nombre": "Crema Champiñones", "precio": 79.0, "seccion": "Cenas", "descripcion": "Con crotones."},
    {"id": 10, "nombre": "Cheesecake", "precio": 68.0, "seccion": "Postres", "descripcion": "Frutos rojos."},
    {"id": 11, "nombre": "Brownie", "precio": 64.0, "seccion": "Postres", "descripcion": "Con helado."},
    {"id": 12, "nombre": "Affogato", "precio": 58.0, "seccion": "Postres", "descripcion": "Helado con espresso."},
    {"id": 13, "nombre": "Americano", "precio": 25.0, "seccion": "Bebidas", "descripcion": "Caliente o frío."},
    {"id": 14, "nombre": "Capuchino", "precio": 35.0, "seccion": "Bebidas", "descripcion": "Con espuma."},
    {"id": 15, "nombre": "Latte Vainilla", "precio": 38.0, "seccion": "Bebidas", "descripcion": "Saborizante natural."},
]

class Pedido(BaseModel):
    productos: List[int]
    total: float = 0.0
    estado: str = "pendiente"
    modo: Optional[str] = None

class PedidoOffline(Pedido):
    temp_id: Optional[str] = None

class PedidoEstado(BaseModel):
    estado: str

class PedidosSync(BaseModel):
    pedidos: List[PedidoOffline]

def _producto_por_id(pid: int):
    return next((p for p in productos if p["id"] == pid), None)

# --- ENDPOINTS ---
@app.get("/api/menu")
async def get_menu():
    return sorted(productos, key=lambda p: (p.get("seccion", ""), p.get("nombre", "")))

@app.post("/api/pedidos")
async def create_pedido(pedido: Pedido):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO pedidos (productos, total, estado, modo, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (json.dumps(pedido.productos), pedido.total, pedido.estado, pedido.modo, datetime.now().isoformat())
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"mensaje": "Creado", "id": new_id}
    finally:
        cur.close(); conn.close()

@app.get("/api/pedidos")
async def get_pedidos():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
        rows = cur.fetchall()
        # Mapeo manual de la tupla de Postgres a Diccionario
        res = []
        for r in rows:
            p_ids = json.loads(r[1]) # r[1] es productos
            nombres = [(_producto_por_id(pid) or {}).get("nombre", "Unknown") for pid in p_ids]
            res.append({
                "id": r[0],
                "productos": p_ids,
                "productos_nombres": nombres,
                "total": r[2],
                "estado": r[3],
                "modo": r[4],
                "created_at": r[5]
            })
        return res
    finally:
        cur.close(); conn.close()

@app.put("/api/pedidos/{pid}/estado")
async def update_estado(pid: int, data: PedidoEstado):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE pedidos SET estado = %s WHERE id = %s", (data.estado, pid))
        conn.commit()
        return {"mensaje": "Actualizado"}
    finally:
        cur.close(); conn.close()

@app.post("/api/pedidos/sync")
async def sync(payload: PedidosSync):
    conn = get_conn()
    cur = conn.cursor()
    ids_map = {}
    try:
        for item in payload.pedidos:
            cur.execute(
                "INSERT INTO pedidos (productos, total, estado, modo, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (json.dumps(item.productos), item.total, item.estado, item.modo, datetime.now().isoformat())
            )
            new_id = cur.fetchone()[0]
            if item.temp_id: ids_map[item.temp_id] = new_id
        conn.commit()
        return {"mensaje": "Sincronizados", "ids": ids_map}
    finally:
        cur.close(); conn.close()