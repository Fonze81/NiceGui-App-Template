# tests/core/test_state.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Testes do módulo de estado (core/state.py)
# -----------------------------------------------------------------------------
# Estes testes validam:
# - valores padrão dos dataclasses de estado
# - composição do AppState (subestados corretos e independentes)
# - comportamento do singleton get_app_state (lazy + cache)
# - garantias de imutabilidade estrutural via slots (sem atributos dinâmicos)
#
# Decisão: os testes importam o módulo como `state_module` para facilitar o acesso
# a símbolos internos (ex.: _APP_STATE) quando necessário para isolar cenários.
# -----------------------------------------------------------------------------

from pathlib import Path

import pytest

from nicegui_app_template.core import state as state_module


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _reset_singleton() -> None:
    """
    Reseta o singleton do módulo para garantir isolamento entre testes.

    Como o estado é cacheado em nível de módulo, um teste pode influenciar outro
    se o singleton já estiver inicializado. Ao zerar o cache explicitamente,
    garantimos que cada teste parta de um baseline previsível.
    """
    # Este acesso é intencional: estamos testando o contrato público (`get_app_state`)
    # mas precisamos controlar o cache interno para assegurar isolamento entre casos.
    state_module._APP_STATE = None  # type: ignore[attr-defined]


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_singleton_between_tests() -> None:
    """
    Garante que cada teste rode com singleton limpo.

    Usar autouse evita repetição de boilerplate em todos os testes e reduz o
    risco de esquecer o reset em cenários específicos.
    """
    _reset_singleton()


# -----------------------------------------------------------------------------
# Testes de defaults dos subestados
# -----------------------------------------------------------------------------
def test_app_meta_state_defaults() -> None:
    """
    Valida os valores padrão do AppMetaState.

    Este teste garante que defaults esperados sejam estáveis, pois eles são a
    base para inicialização do aplicativo quando não há settings persistidos.
    """
    meta = state_module.AppMetaState()

    assert meta.name == "nicegui_app_template"
    assert meta.version == "0.0.0"
    assert meta.language == "pt-BR"
    assert meta.first_run is True
    assert meta.native_mode is True
    assert meta.port == 8080


def test_window_state_defaults() -> None:
    """
    Valida os valores padrão do WindowState.

    A configuração de janela impacta diretamente a UX e o modo nativo; manter
    defaults corretos evita inconsistências na primeira execução.
    """
    window = state_module.WindowState()

    assert window.x == 100
    assert window.y == 100
    assert window.width == 800
    assert window.height == 600
    assert window.maximized is False
    assert window.fullscreen is False
    assert window.monitor == 0
    assert window.storage_key == "nicegui_window_state_spa"


def test_ui_state_defaults() -> None:
    """
    Valida os valores padrão do UiState.

    Defaults de UI são usados como baseline quando não existem preferências
    persistidas, garantindo uma aparência inicial consistente.
    """
    ui_state = state_module.UiState()

    assert ui_state.theme == "dark"
    assert ui_state.font_scale == 1.0
    assert ui_state.dense_mode is False
    assert ui_state.accent_color == "#0057B8"


def test_log_state_defaults() -> None:
    """
    Valida os valores padrão do LogState.

    Logging é crítico para diagnóstico; este teste garante que o caminho padrão
    e parâmetros essenciais estejam alinhados ao contrato do template.
    """
    log_state = state_module.LogState()

    assert isinstance(log_state.path, Path)
    assert log_state.path == Path("logs/app.log")
    assert log_state.level == "INFO"
    assert log_state.console is True
    assert log_state.buffer_capacity == 500
    assert log_state.rotation == "5 MB"
    assert log_state.retention == 3


def test_behavior_state_defaults() -> None:
    """
    Valida os valores padrão do BehaviorState.

    O estado de comportamento deve permanecer previsível para evitar efeitos
    colaterais inesperados em automações e rotinas do aplicativo.
    """
    behavior = state_module.BehaviorState()

    assert behavior.auto_save is True


# -----------------------------------------------------------------------------
# Testes de composição do AppState
# -----------------------------------------------------------------------------
def test_app_state_defaults_and_composition() -> None:
    """
    Valida a composição do AppState e seus valores padrão.

    Este teste assegura que o estado raiz agregue corretamente todos os
    subestados e que campos de runtime iniciem em valores seguros.
    """
    app_state = state_module.AppState()

    assert isinstance(app_state.meta, state_module.AppMetaState)
    assert isinstance(app_state.window, state_module.WindowState)
    assert isinstance(app_state.ui, state_module.UiState)
    assert isinstance(app_state.log, state_module.LogState)
    assert isinstance(app_state.behavior, state_module.BehaviorState)

    assert app_state.settings_file_path is None
    assert app_state.last_load_ok is False
    assert app_state.last_save_ok is False
    assert app_state.last_error is None


def test_app_state_default_factories_create_distinct_instances() -> None:
    """
    Garante que os default factories não compartilham instâncias.

    Como os subestados são mutáveis por design (estado em runtime), qualquer
    compartilhamento acidental entre AppState diferentes seria um bug grave.
    """
    a = state_module.AppState()
    b = state_module.AppState()

    assert a.meta is not b.meta
    assert a.window is not b.window
    assert a.ui is not b.ui
    assert a.log is not b.log
    assert a.behavior is not b.behavior


# -----------------------------------------------------------------------------
# Testes do singleton get_app_state
# -----------------------------------------------------------------------------
def test_get_app_state_returns_singleton_instance() -> None:
    """
    Verifica que get_app_state retorna sempre a mesma instância.

    Este é o contrato do singleton: chamadas repetidas devem compartilhar a
    mesma referência, evitando estados divergentes no aplicativo.
    """
    first = state_module.get_app_state()
    second = state_module.get_app_state()

    assert first is second
    assert isinstance(first, state_module.AppState)


def test_get_app_state_is_lazy_initialized() -> None:
    """
    Verifica que o singleton é inicializado sob demanda (lazy).

    A inicialização lazy é importante para:
    - reduzir custo de import
    - permitir testes mais previsíveis
    - facilitar bootstrap com logging/configurações em fases
    """
    assert state_module._APP_STATE is None  # type: ignore[attr-defined]

    instance = state_module.get_app_state()

    assert state_module._APP_STATE is instance  # type: ignore[attr-defined]


def test_singleton_reset_allows_new_instance() -> None:
    """
    Garante que é possível reinicializar o singleton em ambiente de teste.

    Embora em produção o singleton não seja resetado, a capacidade de reset em
    testes é necessária para isolamento e reprodutibilidade.
    """
    first = state_module.get_app_state()
    _reset_singleton()

    second = state_module.get_app_state()

    assert first is not second


# -----------------------------------------------------------------------------
# Testes de campos de runtime e restrições de slots
# -----------------------------------------------------------------------------
def test_app_state_runtime_fields_can_be_set() -> None:
    """
    Valida que campos de runtime do AppState são configuráveis.

    Esses campos refletem resultados de carregamento/salvamento e devem ser
    mutáveis durante a execução, sem exigir reconstrução do estado.
    """
    app_state = state_module.AppState()

    app_state.settings_file_path = Path("settings.toml")
    app_state.last_load_ok = True
    app_state.last_save_ok = True
    app_state.last_error = "example error"

    assert app_state.settings_file_path == Path("settings.toml")
    assert app_state.last_load_ok is True
    assert app_state.last_save_ok is True
    assert app_state.last_error == "example error"


def test_slots_prevent_dynamic_attributes() -> None:
    """
    Garante que dataclasses com slots impedem atributos dinâmicos.

    Esta garantia reduz erros de digitação e evita mutações estruturais
    acidentais no estado, mantendo o modelo mais seguro e previsível.
    """
    app_state = state_module.AppState()

    with pytest.raises(AttributeError):
        setattr(app_state, "unexpected_field", 123)
