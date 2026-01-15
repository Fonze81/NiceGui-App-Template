from __future__ import annotations

# -----------------------------------------------------------------------------
# Settings Page (SPA subpage)
# -----------------------------------------------------------------------------
# Tela de ajuste de settings:
# - Editar valores
# - Resetar para padrões (defaults do AppState)
# - Cancelar alterações (voltar ao snapshot inicial da tela)
# - Salvar (persistir em settings.toml)
#
# Nota sobre tipagem:
# - Os stubs do NiceGUI podem gerar falsos-positivos no Pylance para ui.select.
# - Runtime do NiceGUI espera "options" como primeiro argumento posicional.
# - Para manter o editor limpo sem alterar comportamento, encapsulamos a chamada
#   em um wrapper que usa Any.
# -----------------------------------------------------------------------------

from typing import Any, Callable, cast

from nicegui import ui

from ...core.logger import get_logger
from ...core.settings import save_settings
from ...core.state import get_app_state
from ..viewmodels.settings_vm import SettingsViewModel


def render_settings_page() -> None:
    """
    Renderiza a subpage de configurações.
    """
    log = get_logger(__name__)
    state = get_app_state()

    vm = SettingsViewModel()

    # Form atual (mutável) usado pela UI.
    form = vm.from_state(state)

    # Snapshot para "Cancelar": baseline do estado ao abrir a tela.
    initial_snapshot = vm.from_state(state)

    def _apply_to_state_from_form() -> None:
        vm.apply_to_state(state=state, form=form)

    def _cancel() -> None:
        form.update_from(initial_snapshot)
        _apply_to_state_from_form()
        ui.notify("Alterações descartadas", type="info", position="top")

    def _reset_to_defaults() -> None:
        defaults = vm.defaults()
        form.update_from(defaults)
        _apply_to_state_from_form()
        ui.notify(
            "Valores resetados para o padrão (ainda não salvo)",
            type="info",
            position="top",
        )

    def _save() -> None:
        _apply_to_state_from_form()

        ok = save_settings(state=state, logger=log)
        if not ok:
            ui.notify(
                state.last_error or "Falha ao salvar settings",
                type="negative",
                position="top",
            )
            return

        # Após salvar, a baseline vira o estado salvo.
        initial_snapshot.update_from(vm.from_state(state))

        if vm.requires_restart(form):
            ui.notify(
                "Configurações salvas. Algumas alterações exigem reinício (porta/modo nativo).",
                type="warning",
                position="top",
            )
        else:
            ui.notify(
                "Configurações salvas com sucesso", type="positive", position="top"
            )

    # -------------------------------------------------------------------------
    # Opções
    # -------------------------------------------------------------------------
    theme_options: list[str] = ["dark", "light"]
    log_level_options: list[str] = [
        "CRITICAL",
        "ERROR",
        "WARNING",
        "INFO",
        "DEBUG",
        "NOTSET",
    ]

    # -------------------------------------------------------------------------
    # Wrapper para ui.select (runtime correto + sem ruído do Pylance)
    # -------------------------------------------------------------------------
    select_any = cast(Any, ui.select)

    def _select(
        *,
        label: str,
        options: list[str],
        value: str,
        on_change: Callable[[Any], None],
    ) -> Any:
        """
        Encapsula ui.select com assinatura compatível com runtime.

        Motivo:
            No runtime, ui.select recebe "options" como primeiro argumento posicional.
            Passar label como posicional pode ser interpretado como options e causar:
            "got multiple values for argument 'options'".
        """
        return select_any(options, label=label, value=value, on_change=on_change)

    with ui.column().classes("w-full gap-4"):
        ui.label("Configurações").classes("text-2xl font-bold")

        with ui.row().classes("w-full items-center gap-2"):
            ui.button("Salvar", on_click=_save).props("color=primary")
            ui.button("Resetar padrão", on_click=_reset_to_defaults).props("outline")
            ui.button("Cancelar", on_click=_cancel).props("outline")

        with ui.card().classes("w-full"):
            ui.label("Aplicativo").classes("text-lg font-semibold")

            with ui.grid(columns=2).classes("w-full gap-4"):
                ui.input("Nome do app", value=form.app_name).props("readonly")
                ui.input("Versão", value=form.app_version).props("readonly")

                ui.input(
                    "Porta",
                    value=str(form.port),
                    on_change=lambda e: setattr(form, "port", int(e.value)),
                ).props("type=number min=1 max=65535")

                ui.switch(
                    "Modo nativo",
                    value=form.native_mode,
                    on_change=lambda e: setattr(form, "native_mode", bool(e.value)),
                )

        with ui.card().classes("w-full"):
            ui.label("Janela").classes("text-lg font-semibold")

            with ui.grid(columns=4).classes("w-full gap-4"):
                ui.input(
                    "X",
                    value=str(form.window_x),
                    on_change=lambda e: setattr(form, "window_x", int(e.value)),
                ).props("type=number")

                ui.input(
                    "Y",
                    value=str(form.window_y),
                    on_change=lambda e: setattr(form, "window_y", int(e.value)),
                ).props("type=number")

                ui.input(
                    "Largura",
                    value=str(form.window_width),
                    on_change=lambda e: setattr(form, "window_width", int(e.value)),
                ).props("type=number min=200")

                ui.input(
                    "Altura",
                    value=str(form.window_height),
                    on_change=lambda e: setattr(form, "window_height", int(e.value)),
                ).props("type=number min=200")

                ui.switch(
                    "Maximizada",
                    value=form.window_maximized,
                    on_change=lambda e: setattr(
                        form, "window_maximized", bool(e.value)
                    ),
                )

                ui.switch(
                    "Tela cheia",
                    value=form.window_fullscreen,
                    on_change=lambda e: setattr(
                        form, "window_fullscreen", bool(e.value)
                    ),
                )

                ui.input(
                    "Monitor",
                    value=str(form.window_monitor),
                    on_change=lambda e: setattr(form, "window_monitor", int(e.value)),
                ).props("type=number min=0")

                ui.input(
                    "Chave de storage",
                    value=form.window_storage_key,
                    on_change=lambda e: setattr(
                        form, "window_storage_key", str(e.value)
                    ),
                )

        with ui.card().classes("w-full"):
            ui.label("Interface").classes("text-lg font-semibold")

            with ui.grid(columns=2).classes("w-full gap-4"):
                _select(
                    label="Tema",
                    options=theme_options,
                    value=form.ui_theme,
                    on_change=lambda e: setattr(form, "ui_theme", str(e.value)),
                )

                ui.input(
                    "Escala de fonte",
                    value=str(form.ui_font_scale),
                    on_change=lambda e: setattr(form, "ui_font_scale", float(e.value)),
                ).props("type=number step=0.05 min=0.75 max=2.0")

                ui.switch(
                    "Modo denso",
                    value=form.ui_dense_mode,
                    on_change=lambda e: setattr(form, "ui_dense_mode", bool(e.value)),
                )

                ui.input(
                    "Cor de destaque (hex)",
                    value=form.ui_accent_color,
                    on_change=lambda e: setattr(form, "ui_accent_color", str(e.value)),
                ).props('placeholder="#0057B8"')

        with ui.card().classes("w-full"):
            ui.label("Logging").classes("text-lg font-semibold")

            with ui.grid(columns=2).classes("w-full gap-4"):
                ui.input(
                    "Caminho do log",
                    value=form.log_path,
                    on_change=lambda e: setattr(form, "log_path", str(e.value)),
                )

                _select(
                    label="Nível",
                    options=log_level_options,
                    value=form.log_level,
                    on_change=lambda e: setattr(form, "log_level", str(e.value)),
                )

                ui.switch(
                    "Console",
                    value=form.log_console,
                    on_change=lambda e: setattr(form, "log_console", bool(e.value)),
                )

                ui.input(
                    "Capacidade do buffer",
                    value=str(form.log_buffer_capacity),
                    on_change=lambda e: setattr(
                        form, "log_buffer_capacity", int(e.value)
                    ),
                ).props("type=number min=50 max=5000")

                ui.input(
                    "Rotação (ex.: 5 MB)",
                    value=form.log_rotation,
                    on_change=lambda e: setattr(form, "log_rotation", str(e.value)),
                )

                with ui.input(
                    "Retenção (backups)",
                    value=str(form.log_retention),
                    on_change=lambda e: setattr(form, "log_retention", int(e.value)),
                ).props("type=number min=1 max=50"):
                    ui.tooltip(
                        "Define a quantidade máxima de backups armazenados antes da exclusão dos mais antigos."
                    )
