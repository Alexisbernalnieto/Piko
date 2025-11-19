# fronted/main.py
import os
import flet as ft
import requests
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from flet.core.page import PageDisconnectedException

API_URL = os.getenv("API_URL", "http://127.0.0.1:9000/api")
POLL_SECONDS = 3

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


def card_container(content: ft.Control, pad: int = 16):
    return ft.Container(
        bgcolor=PANEL,
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=pad,
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
    if e == "pendiente":   return "#7c5c00"
    if e == "preparando":  return "#1d4ed8"
    if e == "listo":       return GREEN
    if e == "confirmado":  return "#059669"
    return "#374151"


def mode_meta(value: Optional[str]) -> dict:
    key = (value or "").strip().lower()
    if "llevar" in key:
        return MODE_CHOICES["para_llevar"]
    if "aqui" in key or "aquí" in key or "comer" in key:
        return MODE_CHOICES["comer_aqui"]
    return {
        "label": "",
        "tag": "",
        "desc": "",
        "color": "#374151",
        "icon": "info",
    }


def responsive_height(page: ft.Page, large: int, small: int = 320) -> int:
    width = page.window_width or page.width or 0
    return large if width >= 900 else small


# --------------------- Estado app --------------------- #
class AppState:
    def __init__(self):
        self.modo: Optional[str] = None
        self.menu: List[Dict[str, Any]] = []
        self.carrito: List[Dict[str, Any]] = []
        self.pedido_id: Optional[int] = None

    def total(self) -> float:
        return sum(float(p.get("precio", 0)) for p in self.carrito)

    def clear_cart(self):
        self.carrito.clear()


state = AppState()


# --------------------- Vistas --------------------- #
def pill(text: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=12, color="#cbd5e1"),
        bgcolor=BADGE,
        padding=ft.padding.symmetric(5, 10),
        border_radius=999,
    )


def top_bar(
    page: ft.Page,
    title: str,
    *,
    badge: Optional[ft.Control] = None,
    nav_controls: Optional[List[ft.Control]] = None,
) -> ft.Container:
    left_controls = [
        ft.Text(title, size=24, weight=ft.FontWeight.W_700),
    ]
    if badge:
        left_controls.append(badge)

    nav_section: ft.Control
    if nav_controls:
        nav_section = ft.Row(
            wrap=True,
            spacing=12,
            controls=nav_controls,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    else:
        nav_section = ft.Container()

    status = ft.Row(
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("Conectado", color=MUTED),
            ft.Container(width=10, height=10, border_radius=999, bgcolor="#22c55e"),
        ],
    )

    return ft.Container(
        padding=ft.padding.only(bottom=20),
        content=ft.ResponsiveRow(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            run_spacing=12,
            spacing=12,
            columns=12,
            controls=[
                ft.Container(
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=left_controls,
                    ),
                    col={"xs": 12, "md": 5, "lg": 4},
                ),
                ft.Container(nav_section, col={"xs": 12, "md": 5, "lg": 5}),
                ft.Container(status, alignment=ft.alignment.center_right, col={"xs": 12, "md": 2, "lg": 3}),
            ],
        ),
    )


def StartView(page: ft.Page):
    page.appbar = None

    def select_mode(key: str):
        state.modo = key
        page.go("/menu")

    header = ft.Column(
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            tag_chip("Bienvenido", BLUE700),
            ft.Text("Elige cómo será tu pedido", size=22, weight=ft.FontWeight.W_700),
            ft.Text("¿Consumirás en sala o prefieres llevarlo?", color=MUTED),
        ],
    )

    cards = []
    for key, info in MODE_CHOICES.items():
        btn = ft.FilledButton(
            "Elegir",
            icon="check_circle",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                bgcolor={"": info["color"]},
                color=WHITE,
            ),
            on_click=lambda e, _k=key: select_mode(_k),
        )
        card = ft.Container(
            bgcolor=PANEL,
            border=ft.border.all(1, BORDER),
            border_radius=16,
            padding=20,
            on_click=lambda e, _k=key: select_mode(_k),
            content=ft.Column(
                spacing=16,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Icon(info["icon"], size=48, color=info["color"]),
                    ft.Text(info["label"], size=20, weight=ft.FontWeight.W_700),
                    ft.Text(info["desc"], color=MUTED),
                    btn,
                ],
            ),
        )
        cards.append(ft.Container(card, col={"xs": 12, "sm": 6}))

    grid = ft.ResponsiveRow(controls=cards, spacing=20, run_spacing=20)

    view = ft.View(
        route="/",
        controls=[
            ft.Container(
                bgcolor=BG,
                expand=True,
                padding=20,
                content=ft.Column(
                    controls=[
                        ft.Container(header, width=820, alignment=ft.alignment.center),
                        ft.Container(grid, width=1000),
                    ],
                    spacing=32,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
            )
        ],
    )
    page.views.append(view)


def MenuView(page: ft.Page):
    page.appbar = None
    if not state.modo:
        page.go("/")
        return

    current_mode = mode_meta(state.modo)
    cart_badge = pill("0 productos")
    nav_controls = [
        ft.TextButton("Pantalla de pedidos", on_click=lambda e: page.go("/pantalla")),
        ft.TextButton("Panel del barista", on_click=lambda e: page.go("/barista")),
    ]
    header = top_bar(page, "Piko", badge=cart_badge, nav_controls=nav_controls)

    # ---------- Carrito ---------- #
    cart_list = ft.Column(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)
    total_text = ft.Text("$0.00", size=24, weight=ft.FontWeight.W_800)

    def update_badges_and_total():
        cart_badge.content.value = (
            f"{len(state.carrito)} producto{'s' if len(state.carrito) != 1 else ''}"
        )
        total_text.value = money(state.total())
        page.update()

    def render_cart():
        cart_list.controls.clear()
        if not state.carrito:
            cart_list.controls.append(
                ft.Container(
                    alignment=ft.alignment.center,
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Icon("shopping_bag", color=MUTED),
                            ft.Text("Agrega productos del menú", color=MUTED),
                        ],
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
                                        ft.Text(p["nombre"], weight=ft.FontWeight.W_600),
                                        ft.Text(money(p["precio"]), color=MUTED, size=12),
                                    ],
                                    spacing=2,
                                ),
                                ft.TextButton(
                                    "Quitar",
                                    style=ft.ButtonStyle(color="#fca5a5"),
                                    on_click=lambda e, i=idx: remove_from_cart(i),
                                ),
                            ],
                        ),
                        pad=12,
                    )
                )
        page.update()

    def add_to_cart(prod: Dict[str, Any]):
        state.carrito.append(prod)
        render_cart()
        update_badges_and_total()

    def remove_from_cart(index: int):
        del state.carrito[index]
        render_cart()
        update_badges_and_total()

    def clear_cart(e=None):
        state.clear_cart()
        render_cart()
        update_badges_and_total()

    # ---------- Grid de menú ---------- #
    menu_grid = ft.Column(spacing=18)

    def show_description(prod: dict):
        desc = prod.get("descripcion") or "Sin descripción"

        def close_dialog(e=None):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(prod.get("nombre", "Producto")),
            content=ft.Text(desc),
            actions=[ft.TextButton("Cerrar", on_click=close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def render_menu():
        menu_grid.controls.clear()
        for section in state.menu:
            seccion = section.get("seccion", "")
            productos = section.get("productos", [])

            grid = ft.ResponsiveRow(run_spacing=14, spacing=14)
            for p in productos:
                card = box_container(
                    ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(p["nombre"], weight=ft.FontWeight.W_600, size=16),
                                    tag_chip(money(p.get("precio")), "#0ea5e9"),
                                ],
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(seccion, color=MUTED, size=12),
                                    ft.TextButton(
                                        "Ver descripción",
                                        icon="info_outline",
                                        on_click=lambda e, prod=p: show_description(prod),
                                    ),
                                ],
                            ),
                            ft.ElevatedButton(
                                "Agregar",
                                icon="add_circle",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    bgcolor={"": BLUE600, "hovered": BLUE700},
                                    color=WHITE,
                                ),
                                on_click=lambda e, prod=p: add_to_cart(prod),
                            ),
                        ],
                    ),
                    pad=20,
                )
                grid.controls.append(ft.Container(card, col={"xs": 12, "md": 6, "lg": 4}))

            section_card = card_container(
                ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(seccion, size=18, weight=ft.FontWeight.W_700),
                                tag_chip(f"{len(productos)} opciones", "#1f2937"),
                            ],
                        ),
                        ft.Container(grid, padding=4),
                    ],
                )
            )
            menu_grid.controls.append(section_card)

        page.update()

    # ---------- Cards ---------- #
    def change_mode(e):
        state.modo = None
        page.go("/")

    mode_badge = tag_chip(current_mode["tag"], current_mode["color"])

    menu_card = card_container(
        ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(16, 16),
                    border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                [
                                    ft.Text("Menú", size=20, weight=ft.FontWeight.W_700),
                                    ft.Text(
                                        f"{current_mode['label']} · {current_mode['desc']}",
                                        color=MUTED,
                                        size=12,
                                    ),
                                ],
                                spacing=4,
                            ),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    mode_badge,
                                    ft.TextButton(
                                        "Cambiar",
                                        icon="autorenew",
                                        on_click=change_mode,
                                    ),
                                    ft.TextButton(
                                        "Ver todos los productos",
                                        icon="grid_view",
                                        on_click=lambda e: None,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(menu_grid, padding=20),
            ],
        )
    )

    cart_card = card_container(
        ft.Column(
            spacing=14,
            controls=[
                ft.Text("Tu pedido", size=20, weight=ft.FontWeight.W_700),
                ft.Text("Agrega productos del menú", color=MUTED, size=12),
                ft.Container(
                    content=cart_list,
                    height=responsive_height(page, 360, 240),
                    bgcolor=BOX,
                    border_radius=10,
                    padding=12,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Total", color=MUTED),
                        total_text,
                    ],
                ),
                ft.FilledButton(
                    "Enviar pedido",
                    icon="send_rounded",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        bgcolor=GREEN,
                        color=WHITE,
                        padding=20,
                    ),
                    on_click=lambda e: enviar_pedido(),
                ),
                ft.TextButton(
                    "Vaciar",
                    icon="delete_outline",
                    on_click=clear_cart,
                ),
                ft.Text(
                    "Al enviar, te llevamos a la pantalla de estado.",
                    color=MUTED,
                    size=12,
                ),
            ],
        ),
        pad=18,
    )

    layout = ft.ResponsiveRow(
        controls=[
            ft.Container(menu_card, col={"xs": 12, "md": 12, "lg": 8}),
            ft.Container(cart_card, col={"xs": 12, "md": 12, "lg": 4}),
        ],
        run_spacing=18,
        spacing=18,
        expand=True,
    )

    content = ft.Container(
        bgcolor=BG,
        expand=True,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Container(header, width=1200),
                ft.Container(layout, width=1200),
            ],
            spacing=20,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        alignment=ft.alignment.top_center,
    )

    # ---------- Carga menú ---------- #
    try:
        state.menu = requests.get(f"{API_URL}/menu", timeout=10).json()
    except Exception:
        state.menu = []
        menu_grid.controls.append(ft.Text("No se pudo cargar el menú.", color=MUTED))
        page.update()
    else:
        render_menu()

    render_cart()
    update_badges_and_total()

    # ---------- Enviar pedido ---------- #
    def enviar_pedido():
        if not state.carrito:
            page.snack_bar = ft.SnackBar(ft.Text("Añade al menos un producto."))
            page.snack_bar.open = True
            page.update()
            return

        payload = {
            "productos": [p["id"] for p in state.carrito],
            "total": state.total(),
            "estado": "pendiente",
            "modo": current_mode["label"],
        }

        try:
            r = requests.post(f"{API_URL}/pedidos", json=payload, timeout=10)
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text("Sin conexión. Intenta de nuevo."))
            page.snack_bar.open = True
            page.update()
            return

        if r.status_code == 200:
            data = r.json()
            state.pedido_id = data.get("id")
            state.clear_cart()
            page.go(f"/estado/{state.pedido_id}")
        else:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {r.status_code}"))
            page.snack_bar.open = True
            page.update()

    page.views.append(ft.View(route="/menu", controls=[content]))


def StatusView(page: ft.Page, pedido_id: int):
    page.appbar = None

    pedido_badge = pill(f"Pedido #{str(pedido_id).zfill(3)}")
    nav_controls = [
        ft.TextButton("Ir al menú", on_click=lambda e: page.go("/menu")),
        ft.TextButton("Pantalla de pedidos", on_click=lambda e: page.go("/pantalla")),
    ]
    header = top_bar(page, "Seguimiento de pedido", badge=pedido_badge, nav_controls=nav_controls)

    estado_text = ft.Text("Estado: —", size=20, weight=ft.FontWeight.W_700)
    estado_chip = tag_chip("—", "#374151")
    modo_chip = tag_chip("—", "#374151")
    prods_list = ft.Column(spacing=6)
    total_text = ft.Text("$0.00", weight=ft.FontWeight.W_800)

    info_card = card_container(
        ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    [
                        ft.Text("Estado del pedido", weight=ft.FontWeight.W_700, size=18),
                        estado_chip,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                estado_text,
                ft.Row(
                    [ft.Text("Consumo"), modo_chip],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text("Productos", weight=ft.FontWeight.W_700),
                box_container(prods_list, pad=10),
                ft.Row(
                    [ft.Text("Total", color=MUTED), total_text],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
        ),
        pad=14,
    )

    hint = ft.Text(
        "Esta pantalla se actualiza automáticamente.",
        color=MUTED,
        size=12,
    )

    view = ft.View(
        route=f"/estado/{pedido_id}",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(header, width=900),
                        ft.Container(info_card, width=900),
                        ft.Container(hint, width=900),
                    ],
                    spacing=16,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
                expand=True,
                bgcolor=BG,
                alignment=ft.alignment.top_center,
            )
        ],
    )
    page.views.append(view)

    running = True

    async def poll_status():
        nonlocal running
        while running:
            try:
                r = requests.get(f"{API_URL}/pedidos/{pedido_id}", timeout=8)
                if r.status_code == 200:
                    pedido = r.json()
                else:
                    pedido = None

                if pedido:
                    est = str(pedido.get("estado", "pendiente"))
                    estado_text.value = f"Estado: {est.capitalize()}"
                    estado_chip.content = ft.Text(est, size=12, color="#e5e7eb")
                    estado_chip.bgcolor = state_color(est)

                    meta = mode_meta(pedido.get("modo"))
                    modo_chip.content = ft.Text(meta["label"] or "—", size=12, color="#e5e7eb")
                    modo_chip.bgcolor = meta["color"]

                    prods_list.controls.clear()
                    for name in pedido.get("productos_nombres") or []:
                        prods_list.controls.append(ft.Text(f"• {name}"))

                    total_text.value = money(pedido.get("total", 0))
                    page.update()
            except Exception:
                pass

            await asyncio.sleep(POLL_SECONDS)

    def on_dispose(e):
        nonlocal running
        running = False

    view.on_dispose = on_dispose
    page.run_task(poll_status)


def BaristaView(page: ft.Page):
    page.appbar = None

    def chip_estado(e: str):
        label = (e or "").strip().lower()
        return tag_chip(label.capitalize() or "—", state_color(label))

    def chip_modo(m: str):
        meta = mode_meta(m)
        if meta["label"]:
            return tag_chip(meta["label"], meta["color"])
        return ft.Container()

    show_ready = ft.Switch(label="Mostrar listos", value=True)
    count_badge = pill("0 pedidos")

    nav_controls = [
        ft.TextButton("Ir al menú", on_click=lambda e: page.go("/menu")),
        ft.TextButton("Pantalla de pedidos", on_click=lambda e: page.go("/pantalla")),
    ]
    header = top_bar(page, "Panel del barista", nav_controls=nav_controls)

    section_header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("Pedidos en curso", size=22, weight=ft.FontWeight.W_700),
            ft.Row(spacing=10, controls=[count_badge, show_ready]),
        ],
    )

    columns = [
        ("ID", 1, ft.alignment.center_left),
        ("Productos", 4, ft.alignment.center_left),
        ("Total", 1, ft.alignment.center_right),
        ("Estado", 1, ft.alignment.center),
        ("Acciones", 2, ft.alignment.center_right),
    ]

    header_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                content=ft.Text(label, weight=ft.FontWeight.W_600, color=MUTED),
                alignment=align,
                expand=flex,
            )
            for label, flex, align in columns
        ],
    )

    table_header = ft.Container(
        bgcolor=BOX,
        border=ft.border.all(1, BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(12, 16),
        content=header_row,
    )

    list_view = ft.Column(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)

    table_card = card_container(
        ft.Column(
            spacing=16,
            controls=[
                section_header,
                table_header,
                ft.Container(
                    content=list_view,
                    height=responsive_height(page, 520, 360),
                    padding=4,
                ),
            ],
        ),
        pad=20,
    )

    root = ft.Container(
        content=ft.Column(
            [
                ft.Container(header, width=1200),
                ft.Container(table_card, width=1200),
            ],
            spacing=20,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        expand=True,
        padding=20,
        bgcolor=BG,
        alignment=ft.alignment.top_center,
    )

    view = ft.View("/barista", controls=[root])
    page.views.append(view)

    # ---------- API helpers ---------- #
    def api_get_pedidos() -> list[dict]:
        try:
            r = requests.get(f"{API_URL}/pedidos", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return []

    def api_put_estado(pid: int, estado: str) -> bool:
        try:
            r = requests.put(
                f"{API_URL}/pedidos/{pid}/estado",
                json={"estado": estado},
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False

    # ---------- Acciones ---------- #
    def set_preparando(pid: int):
        if not api_put_estado(pid, "preparando"):
            page.snack_bar = ft.SnackBar(ft.Text("No se pudo poner en PREPARANDO."))
            page.snack_bar.open = True
        reload()

    def set_listo(pid: int):
        def close():
            dlg.open = False
            page.update()

        def do_listo(e):
            ok = api_put_estado(pid, "listo")
            close()
            if not ok:
                page.snack_bar = ft.SnackBar(ft.Text("No se pudo poner en LISTO."))
                page.snack_bar.open = True
            reload()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar"),
            content=ft.Text(f"¿Notificar al cliente que el pedido #{pid} está LISTO?"),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: close()),
                ft.FilledButton("Sí, notificar", icon="check_circle", on_click=do_listo),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ---------- Render ---------- #
    current: list[dict] = []

    def make_row(p: dict) -> ft.Control:
        pid = int(p["id"])
        prods = ", ".join(p.get("productos_nombres") or [])
        total = money(p.get("total", 0))
        est = (p.get("estado") or "pendiente").lower()

        products_column = ft.Column(
            spacing=6,
            controls=[
                ft.Text(prods or "—", max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                chip_modo(p.get("modo")),
            ],
        )

        actions = ft.Row(
            spacing=8,
            alignment=ft.MainAxisAlignment.END,
            controls=[
                ft.FilledTonalButton(
                    "Preparando",
                    icon="coffee",
                    on_click=lambda e, _pid=pid: set_preparando(_pid),
                ),
                ft.FilledTonalButton(
                    "Listo",
                    icon="check_circle",
                    on_click=lambda e, _pid=pid: set_listo(_pid),
                ),
            ],
        )

        row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Text(str(pid).zfill(3), weight=ft.FontWeight.W_800),
                    alignment=ft.alignment.center_left,
                    expand=1,
                ),
                ft.Container(products_column, alignment=ft.alignment.center_left, expand=4),
                ft.Container(
                    content=ft.Text(total, weight=ft.FontWeight.W_600),
                    alignment=ft.alignment.center_right,
                    expand=1,
                ),
                ft.Container(chip_estado(est), alignment=ft.alignment.center, expand=1),
                ft.Container(actions, alignment=ft.alignment.center_right, expand=2),
            ],
        )

        return ft.Container(
            bgcolor=BOX,
            border=ft.border.all(1, BORDER),
            border_radius=12,
            padding=ft.padding.symmetric(12, 16),
            content=row,
        )

    def render(data: list[dict]):
        items = data
        if not show_ready.value:
            items = [
                x for x in data if x.get("estado", "").lower() not in ("listo", "confirmado")
            ]

        list_view.controls.clear()
        for p in items:
            list_view.controls.append(make_row(p))

        count_badge.content.value = (
            f"{len(items)} pedido{'s' if len(items) != 1 else ''}"
        )
        page.update()

    def reload():
        nonlocal current
        current = api_get_pedidos()
        render(current)

    show_ready.on_change = lambda e: render(current)
    reload()

    # auto-refresh
    running = True

    async def loop_refresh():
        nonlocal running
        while running:
            await asyncio.sleep(POLL_SECONDS)
            try:
                reload()
            except PageDisconnectedException:
                break

    def on_dispose(e):
        nonlocal running
        running = False

    view.on_dispose = on_dispose
    page.run_task(loop_refresh)


def WallboardView(page: ft.Page):
    page.appbar = None

    nav_controls = [
        ft.TextButton("Ir al menú", on_click=lambda e: page.go("/menu")),
        ft.TextButton("Panel del barista", on_click=lambda e: page.go("/barista")),
    ]
    header = top_bar(page, "Pantalla de pedidos", nav_controls=nav_controls)

    prep_grid = ft.GridView(
        expand=1, runs_count=4, max_extent=220, child_aspect_ratio=1.6, spacing=12, run_spacing=12
    )
    ready_grid = ft.GridView(
        expand=1, runs_count=4, max_extent=220, child_aspect_ratio=1.6, spacing=12, run_spacing=12
    )

    def make_card(p):
        ready = str(p.get("estado", "")).lower() in ("listo", "confirmado")
        return ft.Container(
            bgcolor=BOX,
            border=ft.border.all(1, BORDER),
            border_radius=16,
            alignment=ft.alignment.center,
            height=100,
            content=ft.Text(
                str(p["id"]).zfill(3),
                size=40,
                weight=ft.FontWeight.W_800,
                color="#86efac" if ready else "#a5b4fc",
            ),
        )

    def render_from_data(data: list[dict]):
        prep_grid.controls.clear()
        ready_grid.controls.clear()
        for p in sorted(data, key=lambda x: int(x["id"]), reverse=True):
            target = (
                ready_grid
                if str(p.get("estado", "")).lower() in ("listo", "confirmado")
                else prep_grid
            )
            target.controls.append(make_card(p))
        page.update()

    last_updated = ft.Text("Última actualización: —", color=MUTED, size=12)

    async def load_all():
        try:
            def _do():
                r = requests.get(f"{API_URL}/pedidos", timeout=8)
                r.raise_for_status()
                return r.json()

            data = await asyncio.to_thread(_do)
            last_updated.value = (
                f"Última actualización: {datetime.now().strftime('%H:%M:%S')} h"
            )
        except Exception:
            data = []
            last_updated.value = "Última actualización: sin conexión"
        render_from_data(data)
        page.update()

    cols = ft.ResponsiveRow(
        controls=[
            ft.Container(
                card_container(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("En preparación", size=20, weight=ft.FontWeight.W_700),
                                    tag_chip("pendiente", "#1d4ed8"),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(prep_grid, height=responsive_height(page, 520, 320), expand=True),
                        ]
                    )
                ),
                col={"xs": 12, "md": 6},
            ),
            ft.Container(
                card_container(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("Para retirar", size=20, weight=ft.FontWeight.W_700),
                                    tag_chip("listo", GREEN),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(ready_grid, height=responsive_height(page, 520, 320), expand=True),
                        ]
                    )
                ),
                col={"xs": 12, "md": 6},
            ),
        ],
        run_spacing=16,
        spacing=16,
        expand=True,
    )

    body = ft.Container(
        bgcolor=BG,
        padding=20,
        expand=True,
        content=ft.Column(
            controls=[
                ft.Container(header, width=1200),
                ft.Container(cols, width=1200),
                ft.Container(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[last_updated],
                    ),
                    width=1200,
                ),
            ],
            spacing=20,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        alignment=ft.alignment.top_center,
    )

    view = ft.View("/pantalla", controls=[body])
    page.views.append(view)

    running = True

    async def loop_refresh():
        nonlocal running
        while running:
            await load_all()
            await asyncio.sleep(POLL_SECONDS)

    def on_dispose(e):
        nonlocal running
        running = False

    view.on_dispose = on_dispose
    page.run_task(loop_refresh)


# --------------------- Router --------------------- #
def app(page: ft.Page):
    page.title = "Piko - Cafetería Universitaria"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG

    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()
        if page.route == "/":
            StartView(page)
        elif page.route.startswith("/menu"):
            if not state.modo:
                page.go("/")
                return
            MenuView(page)
        elif page.route.startswith("/pantalla"):
            WallboardView(page)
        elif page.route.startswith("/barista"):
            BaristaView(page)
        elif page.route.startswith("/estado/"):
            try:
                pedido_id = int(page.route.split("/estado/")[1])
            except Exception:
                pedido_id = state.pedido_id or 0
            StatusView(page, pedido_id)
        else:
            page.go("/")
            return
        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/")


ft.app(target=app, view=ft.AppView.WEB_BROWSER)
