# src/nicegui_app_template/ui/index.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# SPA Router (NiceGUI) — ui.sub_pages
# -----------------------------------------------------------------------------
# Este módulo define o ponto central de roteamento da aplicação no padrão SPA
# (Single Page Application) utilizando ui.sub_pages (NiceGUI 3.4+).
#
# Responsabilidade:
# - Registrar a página raiz ("root page") da aplicação
# - Definir um catch-all para suportar navegação direta por URL
# - Orquestrar a renderização das subpages sem recriar o layout
#
# Decisões arquiteturais:
# - O layout (header + container) é persistente; apenas o conteúdo interno
#   muda conforme a rota ativa.
# - As páginas reais são builders puros (funções) localizados em ui/pages/,
#   sem decorators @ui.page, para evitar acoplamento com o roteador.
# - O registro de rotas é explicitamente controlado por register_routes()
#   e não ocorre em import-time, garantindo previsibilidade no bootstrap.
# -----------------------------------------------------------------------------

from nicegui import ui

from .pages.home_page import render_home_page
from .pages.settings_page import render_settings_page

# Flag de controle para garantir idempotência no registro das rotas.
# Isso evita erros e comportamento indefinido em cenários de reload
# (especialmente no modo de desenvolvimento).
_routes_registered = False


def register_routes() -> None:
    """
    Registra as rotas da aplicação no padrão SPA usando ui.sub_pages.

    Esta função deve ser chamada **antes** de `ui.run()`, pois o NiceGUI
    inicializa e congela o roteamento durante o bootstrap do servidor.
    Registrar rotas após esse ponto resulta em subpages não resolvidas
    ou falhas silenciosas de navegação.

    A função é idempotente por design: múltiplas chamadas não geram
    registros duplicados, o que é essencial em cenários de reload
    ou inicialização condicional.

    Returns:
        None
    """
    global _routes_registered

    # Evita múltiplos registros de rotas em reload/dev ou chamadas repetidas.
    if _routes_registered:
        return

    _routes_registered = True

    # A página raiz captura tanto "/" quanto qualquer outra rota.
    # O catch-all garante que acessos diretos (ex.: /settings) não
    # quebrem o SPA e sejam resolvidos corretamente pelo ui.sub_pages.
    @ui.page("/")
    @ui.page("/{_:path}")
    def _spa_root() -> None:
        """
        Página raiz do SPA.

        Esta função define o layout persistente da aplicação (header e
        container principal). O conteúdo interno é delegado ao
        ui.sub_pages, que renderiza dinamicamente a subpage ativa
        conforme a rota.
        """
        # Remove espaçamentos padrão para controle total do layout.
        ui.context.client.content.classes("p-0 gap-0")

        # ---------------------------------------------------------------------
        # Header persistente
        # ---------------------------------------------------------------------
        with ui.header().classes("w-full items-center justify-between px-4 py-2"):
            ui.label("NiceGUI App Template").classes("text-lg font-bold")

            # Navegação SPA baseada em links internos.
            with ui.row().classes("gap-2"):
                ui.link("Início", "/")
                ui.link("Configurações", "/settings")

        # ---------------------------------------------------------------------
        # Container principal de conteúdo (subpages)
        # ---------------------------------------------------------------------
        with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
            ui.sub_pages(
                {
                    "/": render_home_page,
                    "/settings": render_settings_page,
                },
                show_404=True,
            ).classes("w-full")
