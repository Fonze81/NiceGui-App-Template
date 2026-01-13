# src/nicegui_app_template/app.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Ponto de Entrada Lógico da Aplicação
# -----------------------------------------------------------------------------
# Este módulo coordena:
# - Bootstrap de infraestrutura (logger, settings, estado)
# - Execução do servidor NiceGUI
# -----------------------------------------------------------------------------

import asyncio

from nicegui import ui

from .core.logger import create_bootstrapper, get_logger
from .core.logger_resolver import resolve_log_config_from_state
from .core.settings import load_settings
from .core.state import AppState, get_app_state


def bootstrap_infrastructure() -> AppState:
    """
    Inicializa a infraestrutura essencial da aplicação.

    Responsabilidades:
    - Inicializar o logger em modo buffer (early logging)
    - Obter o estado central da aplicação
    - Carregar configurações persistentes (settings.toml)
    - Reconfigurar o logger com base no estado carregado
    - Ativar o logging em arquivo

    Returns:
        Instância de AppState inicializada com dados de settings ou defaults.
    """
    logger_bootstrapper = create_bootstrapper()
    logger_bootstrapper.bootstrap()

    log = get_logger()
    log.debug("Application infrastructure bootstrap started")

    state = get_app_state()

    load_ok = load_settings(state=state, logger=log)
    if load_ok:
        log.info("Settings loaded successfully")
    else:
        log.warning("Settings load failed; using default values")

    log_config = resolve_log_config_from_state(state)
    logger_bootstrapper.update_config(log_config)

    try:
        logger_bootstrapper.enable_file_logging()
        log.info("File logging is active")
    except Exception:
        log.exception("Failed to enable file logging")

    return state


def main(*, reload: bool) -> None:
    """
    Ponto de entrada principal da aplicação.

    Args:
        reload: Controla o auto-reload do NiceGUI (recomendado apenas em DEV).

    Observação:
        Capturamos CancelledError/KeyboardInterrupt para reduzir ruído no
        encerramento (Ctrl+C) em Windows + Uvicorn.
    """
    state = bootstrap_infrastructure()

    log = get_logger()
    log.info("Application starting")

    try:
        ui.run(
            title=state.meta.name,
            port=state.meta.port,
            native=state.meta.native_mode,
            reload=reload,
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        # CancelledError pode acontecer durante shutdown do Uvicorn; é esperado.
        log.info("Application shutdown requested")
        return
