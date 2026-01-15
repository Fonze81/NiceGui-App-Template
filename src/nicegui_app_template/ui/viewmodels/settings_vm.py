from __future__ import annotations

# -----------------------------------------------------------------------------
# Settings ViewModel
# -----------------------------------------------------------------------------
# Este módulo define um ViewModel "puro" para a tela de settings.
#
# Decisão:
# - UI trabalha com tipos simples (str/int/bool/float).
# - Conversões para tipos do core (Path) e aplicação no AppState acontecem aqui.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from pathlib import Path

from ...core.state import AppState


@dataclass(slots=True)
class SettingsFormData:
    """
    Representa os campos editáveis da tela de settings.

    Observação:
        Manter tipos simples facilita binding na UI e evita conversões espalhadas.
    """

    # Meta (alguns read-only)
    app_name: str
    app_version: str
    port: int
    native_mode: bool

    # Window
    window_x: int
    window_y: int
    window_width: int
    window_height: int
    window_maximized: bool
    window_fullscreen: bool
    window_monitor: int
    window_storage_key: str

    # UI
    ui_theme: str
    ui_font_scale: float
    ui_dense_mode: bool
    ui_accent_color: str

    # Log
    log_path: str
    log_level: str
    log_console: bool
    log_buffer_capacity: int
    log_rotation: str
    log_retention: int

    # Behavior
    behavior_auto_save: bool

    def update_from(self, other: "SettingsFormData") -> None:
        """
        Atualiza este formulário a partir de outro objeto.

        Motivo:
            A UI mantém referência para este objeto; atualizar in-place evita
            recriar bindings e simplifica a atualização visual.
        """
        for field_name in self.__dataclass_fields__.keys():  # type: ignore[attr-defined]
            setattr(self, field_name, getattr(other, field_name))


class SettingsViewModel:
    """
    Orquestra conversões entre AppState e SettingsFormData.

    Este ViewModel é intencionalmente simples e focado no contrato da tela.
    """

    def defaults(self) -> SettingsFormData:
        """
        Cria um formulário baseado nos defaults do AppState.

        Returns:
            Uma instância de SettingsFormData com valores padrão.
        """
        default_state = AppState()
        return self.from_state(default_state)

    def from_state(self, state: AppState) -> SettingsFormData:
        """
        Constrói um formulário a partir do AppState.

        Args:
            state: Estado atual do aplicativo.

        Returns:
            Formulário com campos preenchidos.
        """
        return SettingsFormData(
            app_name=state.meta.name,
            app_version=state.meta.version,
            port=state.meta.port,
            native_mode=state.meta.native_mode,
            window_x=state.window.x,
            window_y=state.window.y,
            window_width=state.window.width,
            window_height=state.window.height,
            window_maximized=state.window.maximized,
            window_fullscreen=state.window.fullscreen,
            window_monitor=state.window.monitor,
            window_storage_key=state.window.storage_key,
            ui_theme=state.ui.theme,
            ui_font_scale=state.ui.font_scale,
            ui_dense_mode=state.ui.dense_mode,
            ui_accent_color=state.ui.accent_color,
            log_path=str(state.log.path),
            log_level=state.log.level,
            log_console=state.log.console,
            log_buffer_capacity=state.log.buffer_capacity,
            log_rotation=state.log.rotation,
            log_retention=state.log.retention,
            behavior_auto_save=state.behavior.auto_save,
        )

    def apply_to_state(self, *, state: AppState, form: SettingsFormData) -> None:
        """
        Aplica os valores do formulário no AppState.

        Args:
            state: Estado a ser atualizado (em memória).
            form: Dados do formulário (tipos simples).

        Observação:
            Validações profundas não acontecem aqui; a regra do template é:
            - settings.py aplica fallback ao carregar
            - UI deve manter entradas razoáveis
            - defaults continuam sendo um escape seguro
        """
        state.meta.port = int(form.port)
        state.meta.native_mode = bool(form.native_mode)

        state.window.x = int(form.window_x)
        state.window.y = int(form.window_y)
        state.window.width = int(form.window_width)
        state.window.height = int(form.window_height)
        state.window.maximized = bool(form.window_maximized)
        state.window.fullscreen = bool(form.window_fullscreen)
        state.window.monitor = int(form.window_monitor)
        state.window.storage_key = str(form.window_storage_key)

        state.ui.theme = str(form.ui_theme)
        state.ui.font_scale = float(form.ui_font_scale)
        state.ui.dense_mode = bool(form.ui_dense_mode)
        state.ui.accent_color = str(form.ui_accent_color)

        state.log.path = Path(str(form.log_path))
        state.log.level = str(form.log_level).strip().upper()
        state.log.console = bool(form.log_console)
        state.log.buffer_capacity = int(form.log_buffer_capacity)
        state.log.rotation = str(form.log_rotation)
        state.log.retention = int(form.log_retention)

        state.behavior.auto_save = bool(form.behavior_auto_save)

    def requires_restart(self, _form: SettingsFormData) -> bool:
        """
        Indica se alterações exigem reinício do aplicativo.

        Returns:
            True quando alterações podem exigir reinício (conservador).
        """
        return True
