import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import flet as ft
import httpx

# --- CONFIGURACIÓN ---
# IMPORTANTE: En Vercel, el frontend y backend comparten dominio.
# Usamos una ruta relativa.
API_URL = "/api" 

POLL_SECONDS = 3
PENDING_KEY = "piko_offline_pedidos"

# Colores
BG, PANEL, BORDER = "#0b0f14", "#111827", "#1f2937"
BOX, MUTED, BADGE = "#0f172a", "#9aa3af", "#1f2937"
BLUE600, BLUE700, GREEN, WHITE = "#2563eb", "#1d4ed8", "#16a34a", "#ffffff"

MODE_CHOICES = {
    "comer_aqui": {"label": "Comer aquí", "tag": "Consumo en sala", "desc": "Prepara tu pedido para disfrutarlo en la cafetería.", "color": "#0ea5e9", "icon": "restaurant"},
    "para_llevar": {"label": "Para llevar", "tag": "Empaque para llevar", "desc": "Empaquetamos tu pedido para que lo lleves contigo.", "color": "#f97316", "icon": "lunch_dining"},
}

# --- HELPERS ---
def adaptive_padding(page: ft.Page, base: int = 20) -> int:
    try: width = page.window_width or page.width or 0
    except: return base
    if width <= 480: return max(8, int(base * 0.6))
    if width <= 820: return max(12, int(base * 0.8))
    return base

def adaptive_text_size(page: ft.Page, base: int) -> int:
    try: width = page.window_width or page.width or 0
    except: return base
    if width <= 480: return max(12, int(base * 0.85))
    if width <= 820: return max(13, int(base * 0.92))
    return base

def button_padding(page: ft.Page, *, h: int = 14, v: int = 12) -> ft.PaddingValue:
    return ft.padding.symmetric(horizontal=adaptive_padding(page, h), vertical=adaptive_padding(page, v))

def money(n) -> str:
    try: return f"${float(n or 0):.2f}"
    except: return "$0.00"

def tag_chip(text: str, color: str = "#374151"):
    return ft.Container(content=ft.Text(text.capitalize(), size=12, color="#e5e7eb"), bgcolor=color, padding=ft.padding.symmetric(5, 10), border_radius=999)

def card_container(content: ft.Control, pad: int = 16, *, height: int | None = None, expand: bool = False):
    return ft.Container(bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=14, padding=pad, height=height, expand=expand, content=content)

def box_container(content: ft.Control, pad: int = 14):
    return ft.Container(bgcolor=BOX, border=ft.border.all(1, BORDER), border_radius=12, padding=pad, content=content)

def state_color(estado: str) -> str:
    e = (estado or "").lower()
    if e == "pendiente": return "#f59e0b"
    if e == "preparando": return BLUE700
    if e == "listo": return GREEN
    if e == "confirmado": return "#059669"
    return "#374151"

def mode_meta(value: Optional[str]) -> dict:
    key = (value or "").strip().lower()
    if "llevar" in key: return MODE_CHOICES["para_llevar"]
    if "aqui" in key or "aquí" in key: return MODE_CHOICES["comer_aqui"]
    return {"label": "", "tag": "", "desc": "", "color": "#374151", "icon": "info"}

def top_bar(page: ft.Page, title: str, *, badge: Optional[ft.Control] = None, nav_controls: Optional[List[ft.Control]] = None) -> ft.Container:
    pad = adaptive_padding(page)
    is_piko = title.lower() == "piko"
    title_ctrl = ft.Text(title, size=adaptive_text_size(page, 24 if is_piko else 20), weight=ft.FontWeight.W_900 if is_piko else ft.FontWeight.W_700)
    left = [title_ctrl]
    if badge: left.append(badge)
    nav = ft.Row(spacing=12, controls=nav_controls, alignment="center") if nav_controls else ft.Container()
    status = ft.Row(spacing=6, vertical_alignment="center", controls=[ft.Text("Conectado", color=MUTED), ft.Container(width=10, height=10, border_radius=999, bgcolor="#22c55e")])
    return ft.Container(padding=ft.padding.only(bottom=pad), content=ft.ResponsiveRow(controls=[
        ft.Container(ft.Row(spacing=12, controls=left, vertical_alignment="center"), col={"xs": 12, "md": 5, "lg": 6}, alignment=ft.alignment.center_left),
        ft.Container(nav, col={"xs": 12, "md": 4}, alignment=ft.alignment.center),
        ft.Container(status, col={"xs": 12, "md": 3, "lg": 2}, alignment=ft.alignment.center_right),
    ], spacing=12, run_spacing=12, vertical_alignment="center"))

class AppState:
    def __init__(self):
        self.modo = None; self.menu = []; self.carrito = []; self.pedidos = []
    def total(self) -> float:
        return sum(float(item["product"].get("precio", 0)) * item["quantity"] for item in self.carrito)
    def clear_cart(self):
        self.carrito.clear()

state = AppState()

# --- SYNC OFFLINE ---
async def sync_offline_orders(page: ft.Page):
    print("--- 📡 Servicio de Sincronización Iniciado ---")
    while True:
        try:
            pending_json = await page.client_storage.get_async(PENDING_KEY)
            pending_orders = json.loads(pending_json) if pending_json else []
            if pending_orders:
                still_pending = []
                synced_count = 0
                async with httpx.AsyncClient(trust_env=False) as client:
                    for order in pending_orders:
                        try:
                            r = await client.post(f"{API_URL}/pedidos", json=order, timeout=5)
                            if r.status_code == 200:
                                synced_count += 1
                                print(f"✅ Pedido sincronizado")
                            else: still_pending.append(order)
                        except: still_pending.append(order)
                if synced_count > 0:
                    page.snack_bar = ft.SnackBar(ft.Text("¡Conexión recuperada! Pedidos subidos."), bgcolor=GREEN)
                    page.snack_bar.open = True; page.update()
                    await page.client_storage.set_async(PENDING_KEY, json.dumps(still_pending))
        except: pass
        await asyncio.sleep(5)

async def save_order_offline(page: ft.Page, payload):
    try:
        existing_json = await page.client_storage.get_async(PENDING_KEY)
        current_list = json.loads(existing_json) if existing_json else []
        payload["modo"] = f"{payload['modo']} (OFFLINE)" 
        current_list.append(payload)
        await page.client_storage.set_async(PENDING_KEY, json.dumps(current_list))
        return True
    except: return False

# --- VIEWS ---

def StartView(page: ft.Page):
    page.appbar = None; page.scroll = None; page.vertical_alignment = "center"; page.horizontal_alignment = "center"
    pad = adaptive_padding(page)
    def sel(k): state.modo = k; page.go("/menu")
    cards = []
    for k, i in MODE_CHOICES.items():
        btn = ft.FilledButton("Elegir", icon="check_circle", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), bgcolor={"": i["color"]}, color=WHITE, padding=button_padding(page, h=16, v=12)), on_click=lambda e, _k=k: sel(_k))
        cards.append(ft.Container(ft.Container(bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=16, padding=adaptive_padding(page, 18), on_click=lambda e, _k=k: sel(_k), content=ft.Column(spacing=16, alignment="spaceBetween", horizontal_alignment="center", controls=[ft.Icon(i["icon"], size=48, color=i["color"]), ft.Text(i["label"], size=adaptive_text_size(page, 20), weight="bold"), ft.Text(i["desc"], color=MUTED, size=adaptive_text_size(page, 14), text_align="center"), btn])), col={"xs": 12, "sm": 6}))
    
    page.views.append(ft.View(route="/", padding=0, vertical_alignment="center", horizontal_alignment="center", controls=[ft.Container(content=ft.Column(controls=[ft.Container(ft.Column([tag_chip("Bienvenido", BLUE700), ft.Text("Elige cómo será tu pedido", size=22, weight="bold")], horizontal_alignment="center"), width=800, alignment=ft.alignment.center), ft.Container(ft.ResponsiveRow(controls=cards, spacing=pad, run_spacing=pad), width=800, alignment=ft.alignment.center)], spacing=40, alignment="center"), bgcolor=BG, expand=True, padding=pad, alignment=ft.alignment.center)]))

def MenuView(page: ft.Page):
    if not state.modo: page.go("/"); return
    pad = adaptive_padding(page); current_mode = mode_meta(state.modo)
    header = top_bar(page, "Piko", nav_controls=[ft.TextButton("Pantalla", on_click=lambda e: page.go("/pantalla")), ft.TextButton("Barista", on_click=lambda e: page.go("/barista"))])
    cart_col = ft.Column(spacing=10); menu_grid = ft.ResponsiveRow(run_spacing=15, spacing=15, alignment="center")
    total_text = ft.Text("$0.00", size=24, weight="bold")

    def update_total(): total_text.value = money(state.total()); page.update()
    def change_qty(pid, delta, p_data=None):
        found = False
        for item in state.carrito:
            if item["product"]["id"] == pid:
                item["quantity"] += delta
                if item["quantity"] <= 0: state.carrito.remove(item)
                found = True; break
        if not found and delta > 0 and p_data: state.carrito.append({"product": p_data, "quantity": 1})
        render_cart(); update_total()
    
    def render_cart():
        cart_col.controls.clear()
        if not state.carrito: cart_col.controls.append(ft.Text("Carrito vacío", color=MUTED))
        else:
            for item in state.carrito:
                p = item["product"]; q = item["quantity"]
                cart_col.controls.append(box_container(ft.Row([ft.Column([ft.Text(p["nombre"], weight="bold"), ft.Text(money(p["precio"]), color=MUTED)], expand=True), ft.Row([ft.IconButton("remove", on_click=lambda e, pid=p["id"]: change_qty(pid, -1)), ft.Text(str(q), weight="bold"), ft.IconButton("add", on_click=lambda e, pid=p["id"]: change_qty(pid, 1))])], alignment="spaceBetween"), pad=10))
        page.update()

    def render_menu():
        menu_grid.controls.clear()
        for p in state.menu:
            menu_grid.controls.append(ft.Container(box_container(ft.Column([ft.Row([ft.Text(p["nombre"], weight="bold", expand=True), tag_chip(p.get("seccion", ""))]), ft.Text(money(p["precio"]), weight="bold"), ft.Row([ft.OutlinedButton("Detalles"), ft.IconButton("add_circle", icon_color=BLUE600, icon_size=32, data=p, on_click=lambda e: change_qty(e.control.data["id"], 1, e.control.data))], alignment="spaceBetween")]), pad=16), col={"xs": 12, "sm": 6, "lg": 3}))
        page.update()

    left_p = ft.Container(content=ft.Column([ft.Text("Menú", size=24, weight="bold"), menu_grid], scroll=ft.ScrollMode.AUTO, expand=True), bgcolor=BG, padding=10, expand=True)
    right_p = card_container(ft.Column([ft.Text("Tu pedido", size=20, weight="bold"), cart_col, ft.Divider(), ft.Row([ft.Text("Total"), total_text], alignment="spaceBetween"), ft.FilledButton("PAGAR", bgcolor=GREEN, on_click=lambda e: page.go("/checkout") if state.carrito else None, width=float("inf"))], scroll=ft.ScrollMode.AUTO), pad=20)
    
    layout = ft.ResponsiveRow([ft.Container(left_p, col={"xs": 12, "md": 8}), ft.Container(right_p, col={"xs": 12, "md": 4})], expand=True)
    
    async def init_menu():
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                r = await client.get(f"{API_URL}/menu", timeout=5)
                state.menu = r.json(); render_menu()
        except: menu_grid.controls.append(ft.Text("Error cargando menú", color="red")); page.update()

    page.run_task(init_menu)
    view = ft.View(route="/menu", padding=pad, bgcolor=BG, controls=[ft.Column([header, layout], expand=True)])
    page.views.append(view)

def CheckoutView(page: ft.Page):
    if not state.carrito: page.go("/menu"); return
    pad = adaptive_padding(page)
    current_mode = mode_meta(state.modo)
    
    async def procesar_pago(metodo):
        loading = ft.AlertDialog(modal=True, content=ft.Row([ft.ProgressRing(), ft.Text("Procesando...")]))
        page.open(loading); page.update()
        await asyncio.sleep(1)
        prod_ids = []
        for item in state.carrito: prod_ids.extend([item["product"]["id"]] * item["quantity"])
        payload = {"productos": prod_ids, "total": state.total(), "estado": "pendiente", "modo": f"{current_mode['label']} - {metodo}"}
        
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                r = await client.post(f"{API_URL}/pedidos", json=payload, timeout=5)
                page.close(loading)
                if r.status_code == 200:
                    state.clear_cart()
                    dlg = ft.AlertDialog(title=ft.Text("¡Pedido Enviado!"), actions=[ft.TextButton("Ok", on_click=lambda e: (page.close(dlg), page.go("/menu")))])
                    page.open(dlg)
                else: raise Exception("Error")
        except:
            page.close(loading)
            if await save_order_offline(page, payload):
                state.clear_cart()
                page.open(ft.AlertDialog(title=ft.Text("Guardado Offline"), content=ft.Text("Se enviará cuando haya internet."), actions=[ft.TextButton("Ok", on_click=lambda e: page.go("/"))]))

    page.views.append(ft.View(route="/checkout", bgcolor=BG, controls=[ft.Container(card_container(ft.Column([ft.Text("Confirmar", size=24), ft.Text(f"Total: {money(state.total())}", size=20, color=GREEN), ft.FilledButton("Pagar en Efectivo", on_click=lambda e: page.run_task(procesar_pago, "efectivo")), ft.FilledButton("Pagar con Tarjeta", on_click=lambda e: page.run_task(procesar_pago, "tarjeta")), ft.TextButton("Cancelar", on_click=lambda e: page.go("/menu"))])), alignment=ft.alignment.center, expand=True)]))

def BaristaView(page: ft.Page):
    orders_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    async def update_est(pid, est):
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                await client.put(f"{API_URL}/pedidos/{pid}/estado", json={"estado": est})
                render()
        except: pass

    def render():
        orders_col.controls.clear()
        filtrados = [p for p in state.pedidos if p.get("estado") != "confirmado"]
        for p in filtrados:
            pid = p["id"]; est = p["estado"]
            orders_col.controls.append(box_container(ft.Row([ft.Text(f"#{pid}"), ft.Text(est), ft.Row([ft.ElevatedButton("Preparar", on_click=lambda e, _p=pid: page.run_task(update_est, _p, "preparando")), ft.ElevatedButton("Listo", on_click=lambda e, _p=pid: page.run_task(update_est, _p, "listo"))])], alignment="spaceBetween")))
        page.update()

    running = [True]
    async def poll():
        while running[0]:
            try:
                async with httpx.AsyncClient(trust_env=False) as c:
                    r = await c.get(f"{API_URL}/pedidos")
                    state.pedidos = r.json(); render()
            except: pass
            await asyncio.sleep(3)
    
    page.run_task(poll)
    view = ft.View(route="/barista", bgcolor=BG, controls=[ft.Column([ft.Text("Barista", size=24), orders_col])])
    view.on_dispose = lambda e: running.__setitem__(0, False)
    page.views.append(view)

def PantallaView(page: ft.Page):
    col_p = ft.Column(); col_l = ft.Column()
    def render():
        col_p.controls.clear(); col_l.controls.clear()
        pp = [p for p in state.pedidos if p.get("estado") == "preparando"]
        pl = [p for p in state.pedidos if p.get("estado") == "listo"]
        for p in pp: col_p.controls.append(ft.Container(ft.Text(f"#{p['id']}", size=30, color=BLUE600), bgcolor=BOX, padding=10))
        for p in pl: col_l.controls.append(ft.Container(ft.Text(f"#{p['id']}", size=30, color=GREEN), bgcolor=BOX, padding=10))
        page.update()
    
    running = [True]
    async def poll():
        while running[0]:
            try:
                async with httpx.AsyncClient(trust_env=False) as c:
                    r = await c.get(f"{API_URL}/pedidos")
                    state.pedidos = r.json(); render()
            except: pass
            await asyncio.sleep(3)

    page.run_task(poll)
    view = ft.View(route="/pantalla", bgcolor=BG, controls=[ft.Row([ft.Column([ft.Text("PREPARANDO", color=BLUE600), col_p], expand=True), ft.Column([ft.Text("LISTO", color=GREEN), col_l], expand=True)], expand=True)])
    view.on_dispose = lambda e: running.__setitem__(0, False)
    page.views.append(view)

def main(page: ft.Page):
    page.title = "Piko"; page.theme_mode = ft.ThemeMode.DARK; page.bgcolor = BG
    page.run_task(sync_offline_orders, page)
    def route_change(route):
        page.views.clear()
        if page.route == "/": StartView(page)
        elif page.route == "/menu": MenuView(page)
        elif page.route == "/checkout": CheckoutView(page)
        elif page.route == "/barista": BaristaView(page)
        elif page.route == "/pantalla": PantallaView(page)
        page.update()
    page.on_route_change = route_change; page.go("/")

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, assets_dir="assets")