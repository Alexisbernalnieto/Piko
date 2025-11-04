import flet as ft
import requests

API_URL = "http://127.0.0.1:9000/api"

# --------------------- Estado de la app ---------------------
class AppState:
    def __init__(self):
        self.modo: str = ""
        self.carrito: list = []
        self.menu: list = []
        self.pedido_id: int = None

    def total(self) -> float:
        return sum(float(p["precio"]) for p in self.carrito)

state = AppState()

# --------------------- Vistas ---------------------

def LandingView(page: ft.Page):
    page.appbar = ft.AppBar(
        bgcolor="#111827",
        toolbar_height=64,
        leading=ft.Icon(name="local_cafe_rounded"),
        title=ft.Text("Cafetería Universitaria", weight=ft.FontWeight.W_700),
    )

    def pick(mode: str):
        state.modo = mode
        page.go("/menu")

    def option_card(title: str, desc: str, icon_name: str, on_click):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(name=icon_name, size=64),
                    ft.Text(title, weight=ft.FontWeight.W_700, size=20),
                    ft.Text(desc, color="#9aa3af", size=14, text_align=ft.TextAlign.CENTER),
                    ft.FilledButton("Elegir", on_click=on_click),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#0f172a",
            border_radius=14,
            padding=16,
        )

    content = ft.Column(
        [
            ft.Text("Bienvenido 👋", size=30, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
            ft.Text("Elige cómo será tu pedido:", color="#9aa3af", size=15, text_align=ft.TextAlign.CENTER),
            ft.Row(
                [
                    option_card("Comer aquí", "Prepara tu pedido para consumo en sala.", "restaurant", lambda e: pick("Comer aquí")),
                    option_card("Para llevar", "Empacaremos tu pedido para llevar.", "takeout_dining", lambda e: pick("Para llevar")),
                ],
                spacing=24,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
            ),
        ],
        spacing=22,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.views.append(ft.View(route="/", controls=[content]))


def MenuView(page: ft.Page):
    # Cargar menú de la API
    response = requests.get(f"{API_URL}/menu")
    menu = response.json() if response.ok else []

    state.menu = menu

    # UI para mostrar el carrito
    cart_list = ft.Column(spacing=10)
    total_text = ft.Text("$0.00", weight=ft.FontWeight.W_800)

    def update_cart():
        cart_list.controls.clear()
        for prod in state.carrito:
            cart_list.controls.append(ft.Text(f"{prod['nombre']} - ${prod['precio']}"))

        total_text.value = f"${state.total():.2f}"
        page.update()

    def add_to_cart(product):
        state.carrito.append(product)
        update_cart()

    menu_grid = ft.ResponsiveRow(run_spacing=14, spacing=14)

    for p in menu:
        card = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(p["nombre"], weight=ft.FontWeight.W_600),
                    ft.Text(f"${p['precio']}", weight=ft.FontWeight.W_700),
                    ft.FilledButton("Agregar", on_click=lambda e, prod=p: add_to_cart(prod)),
                ],
                spacing=8,
            ),
            padding=14,
            bgcolor="#1f2937",
            border_radius=10,
        )
        menu_grid.controls.append(ft.Container(card, col={"xs": 12, "md": 6, "lg": 4}))

    layout = ft.ResponsiveRow(
        controls=[ft.Container(menu_grid, col={"xs": 12, "md": 8}), ft.Container(cart_list, col={"xs": 12, "md": 4})],
        run_spacing=18,
        spacing=18,
        expand=True,
    )

    page.views.append(ft.View(route="/menu", controls=[layout]))


# --------------------- Ejecutar aplicación ---------------------

def app(page: ft.Page):
    page.title = "Cafetería Universitaria"
    page.bgcolor = "#0b0f14"
    page.theme_mode = ft.ThemeMode.DARK

    page.on_route_change = route_change
    page.go("/")

    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()
        if page.route == "/":
            LandingView(page)
        elif page.route.startswith("/menu"):
            MenuView(page)
        page.update()

ft.app(target=app)
