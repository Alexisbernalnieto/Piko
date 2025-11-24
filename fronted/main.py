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

# --- Funciones de Adaptabilidad ---
def adaptive_padding(page: ft.Page, base: int = 20) -> int:
    try:
        width = page.window_width or page.width or 0
    except Exception:
        return base
    if width <= 480:
        return max(8, int(base * 0.6))
    if width <= 820:
        return max(12, int(base * 0.8))
    return base

def adaptive_text_size(page: ft.Page, base: int) -> int:
    try:
        width = page.window_width or page.width or 0
    except Exception:
        return base
    if width <= 480:
        return max(12, int(base * 0.85))
    if width <= 820:
        return max(13, int(base * 0.92))
    return base

def button_padding(page: ft.Page, *, h: int = 14, v: int = 12) -> ft.PaddingValue:
    return ft.padding.symmetric(
        horizontal=adaptive_padding(page, h), vertical=adaptive_padding(page, v)
    )

def money(n) -> str:
    try:
        return f"${float(n or 0):.2f}"
    except Exception:
        return "$0.00"

def tag_chip(text: str, color: str = "#374151"):
    return ft.Container(
        content=ft.Text(text, size=12, color="#e5e7eb"),
        bgcolor=color,
        padding=ft.padding.symmetric(5, 10),
        border_radius=999,
    )

def card_container(content: ft.Control, pad: int = 16, *, height: int | None = None):
    return ft.Container(
        bgcolor=PANEL,
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=pad,
        height=height,
        content=content,
    )

def box_container(content: ft.Control, pad: int = 14):
    return ft.Container(
        bgcolor=BOX,
        border=ft.border.all(1, BORDER),
        border_radius=12,
        padding=pad,
        content=content,
    )

def state_color(estado: str) -> str:
    e = (estado or "").lower()
    if e == "pendiente":  return "#7c5c00"
    if e == "preparando": return "#1d4ed8"
    if e == "listo":      return GREEN
    if e == "confirmado": return "#059669"
    return "#374151"

def mode_meta(value: Optional[str]) -> dict:
    key = (value or "").strip().lower()
    if "llevar" in key:
        return MODE_CHOICES["para_llevar"]
    if "aqui" in key or "aquí" in key or "comer" in key:
        return MODE_CHOICES["comer_aqui"]
    return {"label": "", "tag": "", "desc": "", "color": "#374151", "icon": "info"}

# --------------------- Estado app --------------------- #
class AppState:
    def __init__(self):
        self.modo: Optional[str] = None
        self.menu: List[Dict[str, Any]] = []
        self.carrito: List[Dict[str, Any]] = []
        self.pedido_id: Optional[int] = None
        self.pedidos: List[Dict[str, Any]] = []

    def total(self) -> float:
        return sum(float(p.get("precio", 0)) for p in self.carrito)

    def clear_cart(self):
        self.carrito.clear()

state = AppState()

# --------------------- Componentes Base --------------------- #
def pill(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=12, color="#cbd5e1"),
        bgcolor=BADGE,
        padding=ft.padding.symmetric(5, 10),
        border_radius=999,
    )

def top_bar(page: ft.Page, title: str, *, badge: Optional[ft.Control] = None, nav_controls: Optional[List[ft.Control]] = None) -> ft.Container:
    pad = adaptive_padding(page)
    left_controls = [ft.Text(title, size=adaptive_text_size(page, 24), weight=ft.FontWeight.W_700)]
    if badge: left_controls.append(badge)

    nav_section = ft.Row(spacing=12, controls=nav_controls, alignment=ft.MainAxisAlignment.CENTER) if nav_controls else ft.Container()

    status = ft.Row(
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("Conectado", color=MUTED),
            ft.Container(width=10, height=10, border_radius=999, bgcolor="#22c55e"),
        ],
    )

    return ft.Container(
        padding=ft.padding.only(bottom=pad),
        content=ft.ResponsiveRow(
            controls=[
                ft.Container(ft.Row(spacing=12, controls=left_controls, vertical_alignment=ft.CrossAxisAlignment.CENTER), col={"xs": 12, "md": 5, "lg": 6}, alignment=ft.alignment.center_left),
                ft.Container(nav_section, col={"xs": 12, "md": 4}, alignment=ft.alignment.center),
                ft.Container(status, col={"xs": 12, "md": 3, "lg": 2}, alignment=ft.alignment.center_right),
            ],
            spacing=12, run_spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

# --------------------- Vistas de la App --------------------- #

def StartView(page: ft.Page):
    page.appbar = None
    page.scroll = None
    pad = adaptive_padding(page)

    def select_mode(key: str):
        state.modo = key
        page.go("/menu")

    header = ft.Column(
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            tag_chip("Bienvenido", BLUE700),
            ft.Text("Elige cómo será tu pedido", size=adaptive_text_size(page, 22), weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
            ft.Text("¿Consumirás en sala o prefieres llevarlo?", color=MUTED, size=adaptive_text_size(page, 14), text_align=ft.TextAlign.CENTER),
        ],
    )

    cards = []
    for key, info in MODE_CHOICES.items():
        btn = ft.FilledButton("Elegir", icon="check_circle", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), bgcolor={"": info["color"]}, color=WHITE, padding=button_padding(page, h=16, v=12)), on_click=lambda e, _k=key: select_mode(_k))
        card = ft.Container(
            bgcolor=PANEL, border=ft.border.all(1, BORDER), border_radius=16, padding=adaptive_padding(page, 18),
            on_click=lambda e, _k=key: select_mode(_k),
            content=ft.Column(spacing=16, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Icon(info["icon"], size=48, color=info["color"]), ft.Text(info["label"], size=adaptive_text_size(page, 20), weight=ft.FontWeight.W_700), ft.Text(info["desc"], color=MUTED, size=adaptive_text_size(page, 14), text_align=ft.TextAlign.CENTER), btn]),
        )
        cards.append(ft.Container(card, col={"xs": 12, "sm": 6}))

    grid = ft.ResponsiveRow(controls=cards, spacing=adaptive_padding(page, 20), run_spacing=adaptive_padding(page, 20))

    content_block = ft.Column(
        controls=[
            ft.Container(header, width=800, alignment=ft.alignment.center),
            ft.Container(grid, width=800, alignment=ft.alignment.center),
        ],
        spacing=40,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.views.append(
        ft.View(
            route="/",
            scroll=None,
            padding=0, 
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=content_block,
                    bgcolor=BG,
                    expand=True,
                    padding=pad,
                    alignment=ft.alignment.center
                )
            ],
        )
    )

def MenuView(page: ft.Page):
    page.appbar = None
    page.scroll = None 
    
    if not state.modo:
        page.go("/")
        return

    pad = adaptive_padding(page)
    current_mode = mode_meta(state.modo)
    
    nav_controls = [
        ft.TextButton("Pantalla de pedidos", on_click=lambda e: page.go("/pantalla")),
        ft.TextButton("Panel del barista", on_click=lambda e: page.go("/barista")),
    ]
    header = top_bar(page, "Piko", nav_controls=nav_controls)

    cart_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    total_text = ft.Text("$0.00", size=24, weight=ft.FontWeight.W_800)

    def update_total():
        total_text.value = money(state.total())
        page.update()

    def render_cart():
        cart_list.controls.clear()
        if not state.carrito:
            cart_list.controls.append(
                ft.Container(
                    alignment=ft.alignment.center,
                    padding=pad,
                    content=ft.Column(
                        [ft.Icon("shopping_bag", color=MUTED), ft.Text("Agrega productos", color=MUTED)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                )
            )
        else:
            for idx, p in enumerate(state.carrito):
                cart_list.controls.append(
                    box_container(
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Column(
                                    [
                                        ft.Text(p["nombre"], weight=ft.FontWeight.W_600, size=14),
                                        ft.Text(money(p["precio"]), color=MUTED, size=12),
                                    ],
                                    spacing=2,
                                    expand=True 
                                ),
                                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color="#fca5a5", on_click=lambda e, i=idx: remove_from_cart(i)),
                            ],
                        ),
                        pad=10,
                    )
                )
        page.update()

    def add_to_cart(e):
        prod = e.control.data
        state.carrito.append(prod)
        render_cart()
        update_total()

    def remove_from_cart(index):
        del state.carrito[index]
        render_cart()
        update_total()

    def clear_cart(e=None):
        state.clear_cart()
        render_cart()
        update_total()

    def queue_offline_order(payload):
        page.snack_bar = ft.SnackBar(ft.Text("Sin conexión. Pedido guardado localmente.")); page.snack_bar.open = True; page.update()

    menu_grid = ft.ResponsiveRow(run_spacing=15, spacing=15)

    # --- SOLUCIÓN DEFINITIVA DEL DIALOGO ---
    def show_details(e):
        # Recuperar la data del botón (Esto NO falla)
        prod_data = e.control.data
        
        print(f"Abriendo detalles de: {prod_data['nombre']}") # MIRA TU CONSOLA SI NO ABRE

        # Función para cerrar
        def close_dlg(e):
            page.close(dlg) # Usamos page.close() moderno

        # Creamos el dialogo DENTRO de la función
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(prod_data.get("nombre", "Producto"), weight=ft.FontWeight.BOLD),
            content=ft.Text(prod_data.get("descripcion", "Sin descripción disponible."), width=400),
            actions=[
                ft.TextButton("Cerrar", on_click=close_dlg)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Usamos page.open() que es la forma nueva y segura
        page.open(dlg)

    def render_menu():
        menu_grid.controls.clear()
        secciones = {}
        for p in state.menu:
            sec = (p.get("seccion") or "Otros").title()
            secciones.setdefault(sec, []).append(p)

        for seccion, productos in sorted(secciones.items()):
            menu_grid.controls.append(
                ft.Container(
                    ft.Text(seccion, size=18, weight=ft.FontWeight.W_700),
                    col={"xs": 12},
                    padding=ft.padding.only(top=10, bottom=5),
                )
            )
            for p in productos:
                card_content = ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Text(p["nombre"], weight=ft.FontWeight.W_700, size=15, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                                tag_chip(p.get("seccion", ""), "#1f2937"),
                            ],
                        ),
                        ft.Text(money(p["precio"]), weight=ft.FontWeight.W_700, size=16),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                # --- AQUÍ ESTÁ LA MAGIA ---
                                ft.OutlinedButton(
                                    "Detalles", 
                                    icon=ft.Icons.INFO_OUTLINE, 
                                    style=ft.ButtonStyle(padding=5), 
                                    data=p, # Guardamos los datos en el botón
                                    on_click=show_details # Llamamos a la función
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ADD_CIRCLE, 
                                    icon_color=BLUE600, 
                                    icon_size=32, 
                                    tooltip="Agregar", 
                                    data=p, 
                                    on_click=add_to_cart
                                ),
                            ],
                        ),
                    ],
                )
                menu_grid.controls.append(
                    ft.Container(
                        box_container(card_content, pad=16),
                        col={"xs": 12, "sm": 6, "md": 6, "lg": 4, "xl": 3},
                    )
                )
        page.update()

    def enviar_pedido():
        if not state.carrito:
            page.snack_bar = ft.SnackBar(ft.Text("El carrito está vacío.")); page.snack_bar.open = True; page.update(); return
        
        payload = {"productos": [p["id"] for p in state.carrito], "total": state.total(), "estado": "pendiente", "modo": current_mode["label"]}
        try:
            r = requests.post(f"{API_URL}/pedidos", json=payload, timeout=10)
            if r.status_code == 200:
                state.pedido_id = r.json().get("id")
                state.clear_cart()
                page.go(f"/estado/{state.pedido_id}")
            else: raise Exception
        except: queue_offline_order(payload)

    left_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column([ft.Text("Menú", size=24, weight="bold"), ft.Text(f"{current_mode['label']}", color=MUTED)]),
                            ft.TextButton("Cambiar modo", icon=ft.Icons.AUTORENEW, on_click=lambda e: (setattr(state, 'modo', None), page.go("/")))
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    padding=ft.padding.only(bottom=10)
                ),
                ft.Divider(color=BORDER),
                ft.Column([menu_grid], scroll=ft.ScrollMode.AUTO, expand=True), 
            ],
            spacing=5,
            expand=True,
        ),
        bgcolor=BG,
        border_radius=10,
        padding=10,
        expand=True 
    )

    right_panel = card_container(
        ft.Column(
            spacing=15,
            expand=True,
            controls=[
                ft.Text("Tu pedido", size=20, weight="bold"),
                ft.Divider(color=BORDER),
                cart_list, 
                ft.Divider(color=BORDER),
                ft.Row([ft.Text("Total", size=16), total_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.FilledButton("Enviar pedido", icon=ft.Icons.SEND_ROUNDED, bgcolor=GREEN, height=45, on_click=lambda e: enviar_pedido(), width=float("inf")),
                ft.TextButton("Vaciar carrito", icon=ft.Icons.DELETE_OUTLINE, on_click=clear_cart, width=float("inf")),
            ],
        ),
        pad=20,
        height=None 
    )

    layout = ft.ResponsiveRow(
        controls=[
            ft.Container(left_panel, col={"xs": 12, "md": 7, "lg": 8}), 
            ft.Container(right_panel, col={"xs": 12, "md": 5, "lg": 4}, height=600), 
        ],
        expand=True,
        spacing=20,
        run_spacing=20,
        vertical_alignment=ft.CrossAxisAlignment.START
    )

    page.views.append(
        ft.View(
            route="/menu",
            padding=pad,
            bgcolor=BG,
            controls=[
                ft.Column(
                    controls=[
                        header,
                        ft.Container(layout, expand=True)
                    ],
                    expand=True,
                    spacing=10
                )
            ]
        )
    )

    try:
        state.menu = requests.get(f"{API_URL}/menu", timeout=5).json()
        render_menu()
    except:
        menu_grid.controls.append(ft.Text("Error al cargar menú", color=MUTED))
        page.update()
        
    render_cart()
    update_total()

def StatusView(page: ft.Page, pedido_id: int):
    page.appbar = None; page.scroll = ft.ScrollMode.ADAPTIVE; pad = adaptive_padding(page)
    nav_controls = [ft.TextButton("Ir al menú", on_click=lambda e: page.go("/menu")), ft.TextButton("Pantalla de pedidos", on_click=lambda e: page.go("/pantalla"))]
    header = top_bar(page, "Seguimiento", badge=pill(f"#{str(pedido_id).zfill(3)}"), nav_controls=nav_controls)
    estado_text = ft.Text("Estado: —", size=20, weight="bold"); prods_list = ft.Column()
    
    info_card = card_container(ft.Column(spacing=10, controls=[ft.Row([ft.Text("Estado", size=18, weight="bold"), estado_text], alignment="spaceBetween"), box_container(prods_list, pad=10)]), pad=14)
    view = ft.View(route=f"/estado/{pedido_id}", controls=[ft.Container(content=ft.Column([header, ft.ResponsiveRow(controls=[ft.Container(info_card, col={"xs": 12, "md": 6}, alignment=ft.alignment.center)], alignment="center")], spacing=16), padding=pad, expand=True, bgcolor=BG)])
    page.views.append(view)

    running = True
    async def poll_status():
        nonlocal running
        while running:
            try:
                r = requests.get(f"{API_URL}/pedidos/{pedido_id}", timeout=5)
                if r.status_code == 200:
                    p = r.json()
                    est = p.get("estado", "pendiente")
                    if est == "listo" and estado_text.value != "Estado: Listo":
                         page.snack_bar = ft.SnackBar(ft.Text("¡PEDIDO LISTO! Recógelo."), bgcolor=GREEN, open=True); page.update()
                    estado_text.value = f"Estado: {est.capitalize()}"; estado_text.color = state_color(est)
                    prods_list.controls = [ft.Text(f"• {n}") for n in p.get("productos_nombres", [])]
                    page.update()
            except: pass
            await asyncio.sleep(POLL_SECONDS)
    
    view.on_dispose = lambda e: setattr(poll_status, 'running', False) # Hacky stop
    page.run_task(poll_status)

def BaristaView(page: ft.Page):
    page.appbar = None; page.scroll = ft.ScrollMode.ADAPTIVE; pad = adaptive_padding(page)
    header = top_bar(page, "Panel del barista", nav_controls=[ft.TextButton("Menú", on_click=lambda e: page.go("/menu"))])
    list_view = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def update_estado(e, pid, est):
        try: requests.put(f"{API_URL}/pedidos/{pid}/estado", json={"estado": est}, timeout=5)
        except: pass

    def render_pedidos():
        list_view.controls.clear()
        filtrados = [p for p in state.pedidos if p.get("estado") != "confirmado"]
        for p in sorted(filtrados, key=lambda x: x["id"]):
            est = p.get("estado", "pendiente")
            btn = ft.Container()
            if est == "pendiente": btn = ft.FilledButton("Iniciar", on_click=lambda e, pid=p["id"]: update_estado(e, pid, "preparando"), bgcolor=BLUE600)
            elif est == "preparando": btn = ft.FilledButton("Listo", on_click=lambda e, pid=p["id"]: update_estado(e, pid, "listo"), bgcolor=GREEN)
            elif est == "listo": btn = ft.TextButton("Entregado", on_click=lambda e, pid=p["id"]: update_estado(e, pid, "confirmado"))
            
            list_view.controls.append(box_container(ft.Row(controls=[ft.Text(f"#{str(p['id']).zfill(3)}", weight="bold"), ft.Text(p["modo"]), tag_chip(est, state_color(est)), btn], alignment="spaceBetween"), pad=10))
        page.update()

    view = ft.View(route="/barista", controls=[ft.Container(content=ft.Column([header, card_container(list_view, expand=True)], spacing=16), padding=pad, expand=True, bgcolor=BG)])
    page.views.append(view)

    running = True
    async def poll_pedidos():
        while running:
            try: state.pedidos = requests.get(f"{API_URL}/pedidos", timeout=5).json(); render_pedidos()
            except: pass
            await asyncio.sleep(POLL_SECONDS)
    
    view.on_dispose = lambda e: setattr(poll_pedidos, 'running', False)
    page.run_task(poll_pedidos)

def PantallaView(page: ft.Page):
    page.appbar = None; page.scroll = ft.ScrollMode.ADAPTIVE; pad = adaptive_padding(page)
    col_prep, col_listo = ft.Column(), ft.Column()
    
    def render():
        col_prep.controls.clear(); col_listo.controls.clear()
        for p in state.pedidos:
            card = box_container(ft.Row([ft.Text(f"#{str(p['id']).zfill(3)}", size=24, weight="bold"), ft.Text(p["modo"])], alignment="spaceBetween"), pad=15)
            if p["estado"] == "preparando": col_prep.controls.append(card)
            elif p["estado"] == "listo": col_listo.controls.append(card)
        page.update()

    grid = ft.ResponsiveRow(controls=[
        ft.Container(card_container(ft.Column([ft.Text("Preparando", size=24, color=BLUE600), ft.Divider(), col_prep]), height=500), col={"md": 6}),
        ft.Container(card_container(ft.Column([ft.Text("Listos", size=24, color=GREEN), ft.Divider(), col_listo]), height=500), col={"md": 6})
    ])
    
    view = ft.View(route="/pantalla", controls=[ft.Container(content=ft.Column([ft.Text("Pedidos en Curso", size=32, weight="bold"), grid], spacing=20), padding=pad, expand=True, bgcolor=BG)])
    page.views.append(view)

    running = True
    async def poll():
        while running:
            try: state.pedidos = requests.get(f"{API_URL}/pedidos", timeout=5).json(); render()
            except: pass
            await asyncio.sleep(POLL_SECONDS)
            
    view.on_dispose = lambda e: setattr(poll, 'running', False)
    page.run_task(poll)

# --------------------- Función Principal --------------------- #
def main(page: ft.Page):
    page.title = "Piko - PWA"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG
    page.fonts = {"Roboto": "https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap"}
    
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def route_change(route):
        page.views.clear()
        if page.route == "/": StartView(page)
        elif page.route == "/menu": MenuView(page)
        elif page.route.startswith("/estado/"): StatusView(page, int(page.route.split("/")[-1]))
        elif page.route == "/barista": BaristaView(page)
        elif page.route == "/pantalla": PantallaView(page)
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)

if __name__ == "__main__":
    ft.app(target=main, view=ft.WEB_BROWSER, port=8080)