import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import flet as ft
import requests
from flet.core.page import PageDisconnectedException

# --- Configuración y Colores ---
API_URL = "http://127.0.0.1:9000/api" 
POLL_SECONDS = 3
PENDING_KEY = "piko_offline_pedidos"

BG      = "#0b0f14"
PANEL   = "#111827"
BORDER  = "#1f2937"
BOX     = "#0f172a"
MUTED   = "#9aa3af"
BADGE   = "#1f2937"
BLUE600 = "#2563eb"
BLUE700 = "#1d4ed8"
GREEN   = "#16a34a"
WHITE   = "#ffffff"

MODE_CHOICES = {
    "comer_aqui": {
        "label": "Comer aquí",
        "tag": "Consumo en sala",
        "desc": "Prepara tu pedido para disfrutarlo en la cafetería.",
        "color": "#0ea5e9",
        "icon": "restaurant",
    },
    "para_llevar": {
        "label": "Para llevar",
        "tag": "Empaque para llevar",
        "desc": "Empaquetamos tu pedido para que lo lleves contigo.",
        "color": "#f97316",
        "icon": "lunch_dining",
    },
}

# --- Funciones de Utilidad ---
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

def pill(text: str) -> ft.Container:
    return ft.Container(content=ft.Text(text, size=12, color="#cbd5e1"), bgcolor=BADGE, padding=ft.padding.symmetric(5, 10), border_radius=999)

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
        self.modo = None
        self.menu = []
        self.carrito = [] 
        self.pedido_id = None
        self.pedidos = []

    def total(self) -> float:
        return sum(float(item["product"].get("precio", 0)) * item["quantity"] for item in self.carrito)

    def clear_cart(self):
        self.carrito.clear()

state = AppState()

# --------------------- LÓGICA OFFLINE/SYNC --------------------- #

async def sync_offline_orders(page: ft.Page):
    """Revisa si hay pedidos guardados en el celular y trata de enviarlos."""
    while True:
        try:
            pending_json = await page.client_storage.get_async(PENDING_KEY)
            pending_orders = json.loads(pending_json) if pending_json else []

            if pending_orders:
                nuevos_pendientes = []
                synced_count = 0
                
                for order in pending_orders:
                    try:
                        r = requests.post(f"{API_URL}/pedidos", json=order, timeout=5)
                        if r.status_code == 200:
                            synced_count += 1
                        else:
                            nuevos_pendientes.append(order) 
                    except:
                        nuevos_pendientes.append(order)
                
                if synced_count > 0:
                    await page.client_storage.set_async(PENDING_KEY, json.dumps(nuevos_pendientes))
                    page.snack_bar = ft.SnackBar(ft.Text(f"¡Conexión recuperada! {synced_count} pedidos sincronizados."), bgcolor=GREEN)
                    page.snack_bar.open = True
                    page.update()
                    
        except Exception as e:
            print(f"Error en sync: {e}")
            
        await asyncio.sleep(10) 

async def save_order_offline(page: ft.Page, payload):
    """Guarda un pedido en el almacenamiento local del celular."""
    try:
        existing_json = await page.client_storage.get_async(PENDING_KEY)
        current_list = json.loads(existing_json) if existing_json else []
        
        payload["modo"] = f"{payload['modo']} (OFFLINE)" 
        current_list.append(payload)
        
        await page.client_storage.set_async(PENDING_KEY, json.dumps(current_list))
        return True
    except Exception as e:
        print(f"Error guardando offline: {e}")
        return False

# --------------------- VISTAS --------------------- #

def StartView(page: ft.Page):
    page.appbar = None; page.scroll = None; page.vertical_alignment = "center"; page.horizontal_alignment = "center"
    pad = adaptive_padding(page)
    def sel(k): state.modo = k; page.go("/menu")
    
    header = ft.Column(spacing=4, horizontal_alignment="center", controls=[tag_chip("Bienvenido", BLUE700), ft.Text("Elige cómo será tu pedido", size=adaptive_text_size(page, 22), weight="bold", text_align="center"), ft.Text("¿Consumirás en sala o prefieres llevarlo?", color=MUTED, size=adaptive_text_size(page, 14), text_align="center")])
    cards = []
    for k, i in MODE_CHOICES.items():
        btn = ft.FilledButton("Elegir", icon="check_circle", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), bgcolor={"": i["color"]}, color=WHITE, padding=button_padding(page, h=16, v=12)), on_click=lambda e, _k=k: sel(_k))
        cards.append(ft.Container(ft.Container(bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=16, padding=adaptive_padding(page, 18), on_click=lambda e, _k=k: sel(_k), content=ft.Column(spacing=16, alignment="spaceBetween", horizontal_alignment="center", controls=[ft.Icon(i["icon"], size=48, color=i["color"]), ft.Text(i["label"], size=adaptive_text_size(page, 20), weight="bold"), ft.Text(i["desc"], color=MUTED, size=adaptive_text_size(page, 14), text_align="center"), btn])), col={"xs": 12, "sm": 6}))
    
    page.views.append(ft.View(route="/", padding=0, vertical_alignment="center", horizontal_alignment="center", controls=[ft.Container(content=ft.Column(controls=[ft.Container(header, width=800, alignment=ft.alignment.center), ft.Container(ft.ResponsiveRow(controls=cards, spacing=pad, run_spacing=pad), width=800, alignment=ft.alignment.center)], spacing=40, alignment="center", horizontal_alignment="center"), bgcolor=BG, expand=True, padding=pad, alignment=ft.alignment.center)]))

def MenuView(page: ft.Page):
    page.appbar = None; page.vertical_alignment = "start"; page.horizontal_alignment = "start"
    if not state.modo: page.go("/"); return
    pad = adaptive_padding(page); current_mode = mode_meta(state.modo)
    header = top_bar(page, "Piko", nav_controls=[ft.TextButton("Pantalla de pedidos", on_click=lambda e: page.go("/pantalla")), ft.TextButton("Panel del barista", on_click=lambda e: page.go("/barista"))])

    cart_col = ft.Column(spacing=10)
    menu_grid = ft.ResponsiveRow(run_spacing=15, spacing=15, alignment="center")
    menu_col = ft.Column([menu_grid], horizontal_alignment="center")
    total_text = ft.Text("$0.00", size=24, weight="bold")

    def update_total(): total_text.value = money(state.total()); page.update()

    def change_qty(pid, delta, p_data=None):
        found = False
        for item in state.carrito:
            if item["product"]["id"] == pid:
                item["quantity"] += delta
                if item["quantity"] <= 0: state.carrito.remove(item)
                found = True
                break
        if not found and delta > 0 and p_data: state.carrito.append({"product": p_data, "quantity": 1})
        render_cart(); update_total()

    def delete_grp(pid):
        state.carrito = [i for i in state.carrito if i["product"]["id"] != pid]
        render_cart(); update_total()

    def render_cart():
        cart_col.controls.clear()
        if not state.carrito:
            cart_col.controls.append(ft.Container(content=ft.Column([ft.Icon("shopping_bag", color=MUTED), ft.Text("Agrega productos", color=MUTED)], alignment="center", horizontal_alignment="center"), alignment=ft.alignment.center, padding=pad))
        else:
            for item in state.carrito:
                p = item["product"]; q = item["quantity"]
                cart_col.controls.append(box_container(ft.Row(alignment="spaceBetween", vertical_alignment="center", controls=[
                    ft.Column([ft.Text(p["nombre"], weight="bold", size=14, max_lines=1, overflow="ellipsis"), ft.Text(money(p["precio"]), color=MUTED, size=12)], spacing=2, expand=True),
                    ft.Row(spacing=0, vertical_alignment="center", controls=[
                        ft.IconButton(icon="remove_circle_outline", icon_color=MUTED, icon_size=20, on_click=lambda e, pid=p["id"]: change_qty(pid, -1)),
                        ft.Container(content=ft.Text(str(q), weight="bold", size=14), padding=ft.padding.symmetric(horizontal=8)),
                        ft.IconButton(icon="add_circle_outline", icon_color=BLUE600, icon_size=20, on_click=lambda e, pid=p["id"]: change_qty(pid, 1)),
                        ft.Container(width=5),
                        ft.IconButton(icon="delete_outline", icon_color="#ef4444", icon_size=22, on_click=lambda e, pid=p["id"]: delete_grp(pid))
                    ])
                ]), pad=10))
        page.update()

    def render_menu():
        menu_grid.controls.clear(); sections = {}
        for p in state.menu: sections.setdefault((p.get("seccion") or "Otros").title(), []).append(p)
        for sec, prods in sorted(sections.items()):
            menu_grid.controls.append(ft.Container(ft.Text(sec, size=18, weight="bold"), col={"xs": 12}, padding=ft.padding.only(top=10, bottom=5)))
            for p in prods:
                menu_grid.controls.append(ft.Container(box_container(ft.Column(spacing=10, controls=[
                    ft.Row([ft.Text(p["nombre"], weight="bold", size=15, max_lines=2, overflow="ellipsis", expand=True), tag_chip(p.get("seccion", ""), "#1f2937")], alignment="spaceBetween", vertical_alignment="start"),
                    ft.Text(money(p["precio"]), weight="bold", size=16),
                    ft.Row([
                        ft.OutlinedButton("Detalles", icon="info_outline", style=ft.ButtonStyle(padding=ft.padding.symmetric(6,10)), data=p, on_click=lambda e: (setattr(dlg_info.title, 'value', e.control.data["nombre"]), setattr(dlg_info.content, 'value', e.control.data["descripcion"]), page.open(dlg_info))),
                        ft.IconButton(icon="add_circle", icon_color=BLUE600, icon_size=32, tooltip="Agregar", data=p, on_click=lambda e: change_qty(e.control.data["id"], 1, e.control.data))
                    ], alignment="spaceBetween")
                ]), pad=16), col={"xs": 12, "sm": 6, "md": 6, "lg": 4, "xl": 3}))
        page.update()

    dlg_info = ft.AlertDialog(modal=True, title=ft.Text(""), content=ft.Text(""), actions=[ft.TextButton("Cerrar", on_click=lambda e: page.close(dlg_info))])

    left_p = ft.Container(content=ft.Column([ft.Container(content=ft.Row([ft.Column([ft.Text("Menú", size=24, weight="bold"), ft.Text(f"{current_mode['label']}", color=MUTED)]), ft.TextButton("Cambiar modo", icon="autorenew", on_click=lambda e: (setattr(state, 'modo', None), page.go("/"))) ], alignment="spaceBetween"), padding=ft.padding.only(bottom=10)), ft.Divider(color=BORDER), menu_col], spacing=5), bgcolor=BG, border_radius=10, padding=10)
    right_p = card_container(ft.Column(spacing=15, controls=[ft.Text("Tu pedido", size=20, weight="bold"), ft.Divider(color=BORDER), cart_col, ft.Divider(color=BORDER), ft.Row([ft.Text("Total", size=16), total_text], alignment="spaceBetween"), ft.FilledButton("PAGAR Y ENVIAR PEDIDO", icon="credit_card", bgcolor=GREEN, height=45, on_click=lambda e: page.go("/checkout") if state.carrito else None, width=float("inf")), ft.TextButton("Vaciar carrito", icon="delete_outline", on_click=lambda e: (state.clear_cart(), render_cart(), update_total()), width=float("inf"))]), pad=20)
    
    layout = ft.ResponsiveRow(controls=[ft.Container(left_p, col={"xs": 12, "md": 7, "lg": 8}), ft.Container(right_p, col={"xs": 12, "md": 5, "lg": 4})], spacing=20, run_spacing=20, vertical_alignment="start")
    view = ft.View(route="/menu", padding=pad, bgcolor=BG, scroll=ft.ScrollMode.AUTO, controls=[ft.Column([header, layout], spacing=10)])

    def responsive_update(e=None):
        is_mobile = page.width < 800
        view.scroll = ft.ScrollMode.ADAPTIVE if is_mobile else None
        left_p.height = None if is_mobile else max(500, page.height - 100)
        right_p.height = None if is_mobile else max(500, page.height - 100)
        menu_col.scroll = None if is_mobile else ft.ScrollMode.AUTO
        cart_col.scroll = None if is_mobile else ft.ScrollMode.AUTO
        menu_col.expand = not is_mobile
        cart_col.expand = not is_mobile
        left_p.content.expand = not is_mobile
        right_p.content.expand = not is_mobile
        page.update()

    page.on_resized = responsive_update; page.views.append(view)
    try: state.menu = requests.get(f"{API_URL}/menu", timeout=5).json(); render_menu()
    except: menu_grid.controls.append(ft.Text("Error al cargar menú", color=MUTED)); page.update()
    render_cart(); update_total(); responsive_update()

def CheckoutView(page: ft.Page):
    page.appbar = None; page.scroll = ft.ScrollMode.AUTO; pad = adaptive_padding(page)
    if not state.carrito: page.go("/menu"); return
    
    header = top_bar(page, "Piko", nav_controls=[])
    current_mode = mode_meta(state.modo)

    lista_items = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    for item in state.carrito:
        p = item["product"]; q = item["quantity"]
        lista_items.controls.append(ft.Container(bgcolor="#1f2937", padding=10, border_radius=8, content=ft.Row([ft.Text(f"{q} x {p['nombre']}", weight="500", size=14), ft.Text(money(float(p["precio"])*q), color=MUTED, size=14)], alignment="spaceBetween")))

    main_card = ft.Container(bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=20, padding=30, width=500)

    def show_success():
        main_card.content = ft.Column([ft.Icon("check_circle", color=GREEN, size=120), ft.Text("¡Pedido Exitoso!", size=30, weight="bold", color=GREEN), ft.Text("Enviado a cocina.", color=MUTED, size=16), ft.Text("Redirigiendo...", color=MUTED, italic=True)], alignment="center", horizontal_alignment="center", spacing=20)
        page.update(); time.sleep(2.5); state.clear_cart(); page.go("/")

    def procesar_pago(metodo):
        dlg = ft.AlertDialog(modal=True, content=ft.Row([ft.ProgressRing(), ft.Text("Procesando...")], alignment="center", spacing=20))
        page.open(dlg); time.sleep(1.5)
        
        prod_ids = []
        for item in state.carrito: prod_ids.extend([item["product"]["id"]] * item["quantity"])
        
        payload = {"productos": prod_ids, "total": state.total(), "estado": "pendiente", "modo": f"{current_mode['label']} - {metodo}"}
        try:
            r = requests.post(f"{API_URL}/pedidos", json=payload, timeout=10)
            page.close(dlg)
            if r.status_code == 200: show_success()
            else: page.snack_bar = ft.SnackBar(ft.Text("Error al enviar."), open=True); page.update()
        except:
            page.close(dlg)
            # GUARDAR OFFLINE
            async def save_local():
                success = await save_order_offline(page, payload)
                if success:
                    main_card.content = ft.Column([ft.Icon("wifi_off", color="#f59e0b", size=100), ft.Text("Sin Conexión", size=30, weight="bold"), ft.Text("Pedido guardado en dispositivo.", size=16), ft.Text("Se enviará al recuperar conexión.", color=MUTED)], alignment="center", horizontal_alignment="center", spacing=20)
                    page.update()
                    time.sleep(3); state.clear_cart(); page.go("/")
                else: page.snack_bar = ft.SnackBar(ft.Text("Error crítico local."), open=True); page.update()
            page.run_task(save_local)

    def btn_pago(txt, icon, col):
        return ft.Container(bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=10, padding=20, ink=True, on_click=lambda e: procesar_pago(txt), content=ft.Row([ft.Icon(icon, color=col, size=30), ft.Text(txt, size=18, weight="bold")], alignment="center"))

    main_card.content = ft.Column(controls=[
        ft.Text("Confirmar Pedido", size=28, weight="bold"), ft.Text("Revisa tu orden antes de pagar", color=MUTED), ft.Divider(color=BORDER, height=20),
        ft.Text("Resumen", size=18, weight="bold"),
        ft.Container(content=lista_items, height=300, border=ft.border.all(1, BORDER), border_radius=10, padding=10),
        ft.Row([ft.Text("Total a Pagar", size=20, weight="bold"), ft.Text(money(state.total()), size=22, color=GREEN, weight="bold")], alignment="spaceBetween"),
        ft.Divider(color=BORDER, height=30), ft.Text("Selecciona Método de Pago", size=18, weight="bold"),
        ft.Column(spacing=15, controls=[btn_pago("Efectivo", "attach_money", GREEN), btn_pago("Tarjeta", "credit_card", BLUE600)]),
        ft.Container(height=10), ft.TextButton("Volver al menú", icon="arrow_back", on_click=lambda e: page.go("/menu"), style=ft.ButtonStyle(color=MUTED))
    ], horizontal_alignment="center")

    page.views.append(ft.View(route="/checkout", bgcolor=BG, padding=pad, vertical_alignment="center", horizontal_alignment="center", scroll=ft.ScrollMode.AUTO, controls=[ft.Column([header, ft.Container(content=main_card, alignment=ft.alignment.center, expand=True)], expand=True)]))

def BaristaView(page: ft.Page):
    page.appbar = None; page.scroll = ft.ScrollMode.ADAPTIVE; pad = adaptive_padding(page)
    list_view = ft.ListView(spacing=pad, expand=True, padding=ft.padding.only(top=pad, bottom=pad), scroll_direction=ft.ScrollDirection.HORIZONTAL)
    header = top_bar(page, "Panel del barista", nav_controls=[ft.TextButton("Menú", on_click=lambda e: page.go("/menu"))])

    def update_est(pid, est):
        try: requests.put(f"{API_URL}/pedidos/{pid}/estado", json={"estado": est}, timeout=5); poll_task.cancel(); page.run_task(poll)
        except: pass

    def render():
        list_view.controls.clear()
        filtrados = [p for p in state.pedidos if p.get("estado") != "confirmado"]
        if not filtrados: list_view.controls.append(ft.Container(ft.Text("Sin pedidos.", color=MUTED), alignment=ft.alignment.center, padding=30)); page.update(); return
        
        for p in sorted(filtrados, key=lambda x: x["id"]):
            pid = p["id"]; est = p.get("estado", "pendiente").lower()
            btn = ft.Container()
            if est == "pendiente": btn = ft.FilledButton("INICIAR", on_click=lambda e, id=pid: update_est(id, "preparando"), bgcolor=BLUE600, width=float("inf"))
            elif est == "preparando": btn = ft.FilledButton("LISTO", on_click=lambda e, id=pid: update_est(id, "listo"), bgcolor=GREEN, width=float("inf"))
            elif est == "listo": btn = ft.OutlinedButton("ENTREGAR", on_click=lambda e, id=pid: update_est(id, "confirmado"), width=float("inf"))
            
            prods = ft.Column([ft.Text(f"• {n}", size=14, color=WHITE, max_lines=1, overflow="ellipsis") for n in p.get("productos_nombres", [])], spacing=4, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
            
            card = ft.Container(
                content=card_container(ft.Column([
                    ft.Row([ft.Text(f"#{str(pid).zfill(3)}", weight="bold", size=24), tag_chip(est, state_color(est))], alignment="spaceBetween"),
                    ft.Text(p["modo"], color=MUTED), ft.Text(money(p['total']), size=18, weight="bold"),
                    ft.Divider(color=BORDER, height=10), ft.Text("Productos:", weight="bold"),
                    ft.Container(content=prods, expand=True, padding=ft.padding.only(bottom=10)), btn
                ], spacing=10, expand=True), pad=20, expand=True),
                width=300, height=page.height*0.75
            )
            list_view.controls.append(card)
        page.update()

    page.views.append(ft.View(route="/barista", controls=[ft.Container(content=ft.Column([header, ft.Container(list_view, expand=True)], spacing=16, expand=True), padding=pad, expand=True, bgcolor=BG)]))
    
    running = True
    async def poll():
        while running:
            try: r = requests.get(f"{API_URL}/pedidos", timeout=5); 
            except: pass
            else: 
                if r.status_code==200: state.pedidos = r.json(); render()
            try: await asyncio.sleep(POLL_SECONDS)
            except: running = False
    poll_task = page.run_task(poll); page.views[-1].on_dispose = lambda e: setattr(poll, 'running', False)

def PantallaView(page: ft.Page):
    page.appbar = None; page.scroll = ft.ScrollMode.ADAPTIVE; pad = adaptive_padding(page)
    col_p = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True); col_l = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)
    
    def render():
        col_p.controls.clear(); col_l.controls.clear()
        pp = [p for p in state.pedidos if p.get("estado")=="preparando"]; pl = [p for p in state.pedidos if p.get("estado")=="listo"]
        for p in sorted(pp, key=lambda x: x["id"])[:6]: col_p.controls.append(box_container(ft.Row([ft.Text(f"#{str(p['id']).zfill(3)}", size=24, weight="bold"), ft.Text(p["modo"], color=MUTED, size=18)], alignment="spaceBetween"), pad=15))
        for p in sorted(pl, key=lambda x: x["id"])[:6]: col_l.controls.append(box_container(ft.Row([ft.Text(f"#{str(p['id']).zfill(3)}", size=24, weight="bold"), ft.Text(p["modo"], color=MUTED, size=18)], alignment="spaceBetween"), pad=15))
        page.update()

    grid = ft.ResponsiveRow(controls=[
        ft.Container(card_container(ft.Column([ft.Text("Preparando", size=24, weight="bold", color=BLUE600), ft.Divider(color=BORDER), col_p], expand=True), expand=True), col={"xs":12, "md":6}, height=page.height*0.8),
        ft.Container(card_container(ft.Column([ft.Text("Listos", size=24, weight="bold", color=GREEN), ft.Divider(color=BORDER), col_l], expand=True), expand=True), col={"xs":12, "md":6}, height=page.height*0.8)
    ], spacing=pad)
    
    page.views.append(ft.View(route="/pantalla", controls=[ft.Container(content=ft.Column([ft.Row([ft.Text("Pedidos en Curso", size=adaptive_text_size(page, 32), weight="bold"), ft.TextButton("Menú", on_click=lambda e: page.go("/menu"))], alignment="spaceBetween"), grid], spacing=pad), padding=pad, expand=True, bgcolor=BG)]))
    
    running = True
    async def poll():
        while running:
            try: state.pedidos = requests.get(f"{API_URL}/pedidos", timeout=5).json(); render()
            except: pass
            try: await asyncio.sleep(POLL_SECONDS)
            except: running = False
    page.run_task(poll); page.views[-1].on_dispose = lambda e: setattr(poll, 'running', False)

def main(page: ft.Page):
    page.title = "Piko - PWA"; page.theme_mode = ft.ThemeMode.DARK; page.bgcolor = BG; page.fonts = {"Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap"}
    page.vertical_alignment = "start"; page.horizontal_alignment = "start"
    page.assets_dir = "assets"
    state.clear_cart()
    page.run_task(sync_offline_orders, page) # CORREGIDO: Pasamos 'page'

    def route_change(route):
        page.views.clear()
        if page.route == "/": StartView(page)
        elif page.route == "/menu": MenuView(page)
        elif page.route == "/checkout": CheckoutView(page)
        elif page.route == "/barista": BaristaView(page)
        elif page.route == "/pantalla": PantallaView(page)
        page.update()

    def view_pop(view):
        if len(page.views) > 1: page.views.pop(); page.go(page.views[-1].route)

    page.on_route_change = route_change; page.on_view_pop = view_pop; page.go(page.route if page.route != "/" else "/")

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, port=8080)