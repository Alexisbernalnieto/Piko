# fronted/main.py
import flet as ft
import requests
import asyncio
from typing import List, Dict, Any, Optional
from flet.core.page import PageDisconnectedException

API_URL = "http://127.0.0.1:9000/api"
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
def build_appbar(page: ft.Page, cart_badge: Optional[ft.Control] = None):
    # icono estado conexión
    dot = ft.Container(width=10, height=10, border_radius=999, bgcolor="#22c55e")
    ws_label = ft.Text("Conectado", color=MUTED)

    # navegación
    def go_menu(e): page.go("/menu")
    def go_wall(e): page.go("/pantalla")
    def go_bar(e):  page.go("/barista")

    nav_buttons = ft.Row(
        spacing=10,
        controls=[
            ft.TextButton("Pantalla de pedidos", on_click=go_wall),
            ft.TextButton("Panel del barista", on_click=go_bar),
        ],
    )

    title_row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Piko", size=22, weight=ft.FontWeight.W_700),
                    cart_badge or ft.Container(),
                ],
            ),
            nav_buttons,
            ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Text("Conectado", color=MUTED), dot],
            ),
        ],
    )

    page.appbar = ft.AppBar(
        bgcolor=PANEL,
        toolbar_height=64,
        title=title_row,
        center_title=False,
    )


def MenuView(page: ft.Page):
    # ---------- Header badge ---------- #
    cart_badge = ft.Container(
        content=ft.Text("0 productos", size=12, color="#cbd5e1"),
        bgcolor=BADGE,
        padding=ft.padding.symmetric(5, 10),
        border_radius=999,
    )
    build_appbar(page, cart_badge)

    # ---------- Carrito ---------- #
    cart_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    total_text = ft.Text("$0.00", weight=ft.FontWeight.W_800)

    def update_badges_and_total():
        cart_badge.content = ft.Text(
            f"{len(state.carrito)} producto{'s' if len(state.carrito) != 1 else ''}",
            size=12,
            color="#cbd5e1",
        )
        total_text.value = money(state.total())
        page.update()

    def render_cart():
        cart_list.controls.clear()
        if not state.carrito:
            cart_list.controls.append(
                ft.Container(
                    content=ft.Text("Agrega productos del menú", color=MUTED),
                    padding=10,
                    alignment=ft.alignment.center,
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
                                ft.Text(p["nombre"], weight=ft.FontWeight.W_600),
                                ft.Text(money(p["precio"]), color=MUTED),
                                ft.TextButton(
                                    "Quitar",
                                    style=ft.ButtonStyle(color="#fca5a5"),
                                    on_click=lambda e, i=idx: remove_from_cart(i),
                                ),
                            ],
                        ),
                        pad=10,
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
    menu_grid = ft.ResponsiveRow(run_spacing=14, spacing=14)

    def render_menu():
        menu_grid.controls.clear()
        for p in state.menu:
            card = box_container(
                ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(p["nombre"], weight=ft.FontWeight.W_600, size=16),
                        ft.Text(money(p["precio"]), weight=ft.FontWeight.W_700),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.END,
                            controls=[
                                ft.FilledButton(
                                    "Agregar",
                                    icon="add_rounded",
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        bgcolor={"": BLUE600, "hovered": BLUE700},
                                        color=WHITE,
                                    ),
                                    on_click=lambda e, prod=p: add_to_cart(prod),
                                )
                            ],
                        ),
                    ],
                ),
                pad=20,
            )
            menu_grid.controls.append(
                ft.Container(card, col={"xs": 12, "md": 6, "lg": 4})
            )
        page.update()

    # ---------- Cards ---------- #
    menu_card = card_container(
        ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(12, 16),
                    border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Menú", size=18, weight=ft.FontWeight.W_700),
                            tag_chip("elige tus productos", BADGE),
                        ],
                    ),
                ),
                ft.Container(menu_grid, padding=16),
            ],
        )
    )

    cart_card = ft.Container(
        bgcolor=PANEL,
        border=ft.border.all(1, BORDER),
        border_radius=14,
        padding=14,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text("Tu pedido", size=18, weight=ft.FontWeight.W_700),
                ft.Container(content=cart_list, height=320),
                ft.Container(
                    border=ft.border.only(top=ft.BorderSide(1, BORDER)),
                    padding=ft.padding.only(top=8),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[ft.Text("Total", color=MUTED), total_text],
                    ),
                ),
                ft.FilledButton(
                    "Enviar pedido",
                    icon="send_rounded",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10),
                                        bgcolor=GREEN,
                                        color=WHITE),
                    on_click=lambda e: enviar_pedido(),
                ),
                ft.OutlinedButton(
                    "Vaciar",
                    icon="delete_outline",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, BORDER),
                        color="#cbd5e1",
                    ),
                    on_click=clear_cart,
                ),
                ft.Text(
                    "Al enviar, te llevamos a la pantalla de estado.",
                    color=MUTED,
                    size=12,
                ),
            ],
        ),
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

    wrapper = ft.Container(layout, expand=True, bgcolor=BG, padding=16)

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
            "modo": "",  # podrías agregar "para llevar" / "comer aquí" si quieres
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

    page.views.append(ft.View(route="/menu", controls=[wrapper]))


def StatusView(page: ft.Page, pedido_id: int):
    build_appbar(page)

    estado_text = ft.Text("Estado: —", size=20, weight=ft.FontWeight.W_700)
    estado_chip = tag_chip("—", "#374151")
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
                content=ft.Column([info_card, hint], spacing=12),
                padding=16,
                expand=True,
                bgcolor=BG,
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
    build_appbar(page)

    def chip_estado(e: str):
        return tag_chip((e or "").lower(), state_color(e))

    def pill(text: str):
        return ft.Container(
            content=ft.Text(text, size=12, color="#cbd5e1"),
            bgcolor=BADGE,
            padding=ft.padding.symmetric(5, 10),
            border_radius=999,
        )

    show_ready = ft.Switch(label="Mostrar listos", value=True)
    count_badge = pill("0 pedidos")

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("Pedidos en curso", size=20, weight=ft.FontWeight.W_700),
            ft.Row(
                spacing=12,
                controls=[
                    count_badge,
                    show_ready,
                ],
            ),
        ],
    )

    list_view = ft.ListView(expand=True, spacing=10, auto_scroll=False)

    root = ft.Container(
        content=ft.Column(
            [
                header,
                ft.Container(
                    content=list_view,
                    expand=True,
                    bgcolor=PANEL,
                    border=ft.border.all(1, BORDER),
                    border_radius=14,
                    padding=12,
                ),
            ],
            expand=True,
            spacing=12,
        ),
        expand=True,
        padding=16,
        bgcolor=BG,
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

        left = ft.Column(
            spacing=4,
            controls=[
                ft.Text(str(pid).zfill(3), weight=ft.FontWeight.W_800, size=16),
                ft.Text(prods),
            ],
        )

        middle = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[ft.Text(total, weight=ft.FontWeight.W_700), chip_estado(est)],
        )

        right = ft.Row(
            spacing=8,
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

        return ft.Container(
            bgcolor=BOX,
            border=ft.border.all(1, BORDER),
            border_radius=10,
            padding=12,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[left, middle, right],
            ),
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

        count_badge.content = ft.Text(
            f"{len(items)} pedido{'s' if len(items) != 1 else ''}",
            size=12,
            color="#cbd5e1",
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
    build_appbar(page)

    prep_grid = ft.GridView(
        expand=1, runs_count=4, max_extent=220, child_aspect_ratio=1.6, spacing=12, run_spacing=12
    )
    ready_grid = ft.GridView(
        expand=1, runs_count=4, max_extent=220, child_aspect_ratio=1.6, spacing=12, run_spacing=12
    )

    def make_card(p):
        ready = str(p.get("estado", "")).lower() in ("listo", "confirmado")
        return box_container(
            ft.Container(
                alignment=ft.alignment.center,
                height=86,
                content=ft.Text(
                    str(p["id"]).zfill(3),
                    size=44,
                    weight=ft.FontWeight.W_800,
                    color="#86efac" if ready else "#a5b4fc",
                ),
            ),
            pad=10,
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

    async def load_all():
        try:
            def _do():
                r = requests.get(f"{API_URL}/pedidos", timeout=8)
                r.raise_for_status()
                return r.json()

            data = await asyncio.to_thread(_do)
        except Exception:
            data = []
        render_from_data(data)

    cols = ft.ResponsiveRow(
        controls=[
            ft.Container(
                card_container(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("En preparación", size=20, weight=ft.FontWeight.W_700),
                                    tag_chip("pendiente / preparando", "#1d4ed8"),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(prep_grid, height=520, expand=True),
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
                            ft.Container(ready_grid, height=520, expand=True),
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

    view = ft.View("/pantalla", controls=[ft.Container(content=cols, padding=16, bgcolor=BG)])
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
        if page.route.startswith("/menu") or page.route == "/":
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
            page.go("/menu")
            return
        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/menu")


ft.app(target=app, view=ft.AppView.WEB_BROWSER)
