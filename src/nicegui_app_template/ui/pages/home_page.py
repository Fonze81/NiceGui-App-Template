# src/nicegui_app_template/ui/pages/home_page.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Home Page (SPA subpage)
# -----------------------------------------------------------------------------
# Esta página é renderizada dentro do container ui.sub_pages do root SPA.
# -----------------------------------------------------------------------------

from nicegui import ui


def render_home_page() -> None:
    """
    Renderiza a subpage inicial do aplicativo.
    """
    with ui.card().classes("w-full"):
        ui.label("Início").classes("text-2xl font-bold")
        ui.label("Página inicial (placeholder).")
