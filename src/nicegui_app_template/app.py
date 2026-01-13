# src/nicegui_app_template/app.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Ponto de Entrada Lógico da Aplicação
# -----------------------------------------------------------------------------
# Este módulo coordena:
# - Bootstrap de infraestrutura (logger, settings, estado)
# - Registro de hooks de lifecycle do servidor
# - Execução do servidor NiceGUI
#
# Decisões importantes:
# - O bootstrap de infraestrutura é disparado no startup do servidor para evitar
#   efeitos colaterais durante import e reduzir inicializações redundantes em
#   cenários onde múltiplos processos possam existir.
# - O shutdown do logger é explícito para minimizar locks de arquivo no Windows.
# -----------------------------------------------------------------------------

import asyncio
import os

from nicegui import app, ui

from .core.logger import LoggerBootstrapper, create_bootstrapper, get_logger
from .core.logger_resolver import resolve_log_config_from_state
from .core.settings import load_settings
from .core.state import get_app_state

# -----------------------------------------------------------------------------
# Estado mínimo de runtime (privado ao módulo)
# -----------------------------------------------------------------------------
# Motivo:
# - Precisamos de um guard para evitar reexecução do bootstrap no mesmo processo.
# - Precisamos manter referência ao bootstrapper para shutdown limpo.
# - Isso não pertence ao AppState (estado "puro") e não deve ser persistido.
# -----------------------------------------------------------------------------

_bootstrapper: LoggerBootstrapper | None = None
_started: bool = False
_hooks_registered: bool = False

# -----------------------------------------------------------------------------
# Bootstrap de infraestrutura
# -----------------------------------------------------------------------------
# Motivo:
# - Centralizar a sequência de inicialização (logger buffer -> settings -> logger update -> file).
# - Facilitar testes e manter o fluxo previsível.
# -----------------------------------------------------------------------------


def bootstrap_infrastructure() -> None:
    """
    Inicializa a infraestrutura essencial da aplicação.

    Responsabilidades:
        - Inicializar o logger em modo buffer (early logging)
        - Obter o estado central da aplicação
        - Carregar configurações persistentes (settings.toml)
        - Reconfigurar o logger com base no estado carregado
        - Ativar o logging em arquivo

    Observação:
        Esta função não inicia o servidor; ela apenas prepara infraestrutura.
    """
    global _bootstrapper

    logger_bootstrapper = create_bootstrapper()
    logger_bootstrapper.bootstrap()  # Captura logs antes do caminho do arquivo existir.

    log = get_logger()
    log.debug("Application infrastructure bootstrap started")

    state = get_app_state()  # Singleton explícito do estado da aplicação.

    load_ok = load_settings(
        state=state, logger=log
    )  # Parsing + fallback aplicado no state.
    log.debug("Configuration phase completed: settings_load_ok=%s", load_ok)
    if not load_ok:
        log.warning("Settings load failed; using default values")

    log_config = resolve_log_config_from_state(
        state
    )  # Converte LogState para config técnica do logger.
    logger_bootstrapper.update_config(log_config)

    try:
        logger_bootstrapper.enable_file_logging()  # Anexa file handler e descarrega buffer.
        log.info(
            'Logging ready: file="%s" level="%s" console=%s',
            str(state.log.path.resolve()),
            state.log.level,
            state.log.console,
        )

    except Exception:
        # Falhas aqui não devem impedir o app de subir; buffer/console ainda ajudam.
        log.exception("Failed to enable file logging")

    _bootstrapper = logger_bootstrapper  # Mantém referência para shutdown previsível.


# -----------------------------------------------------------------------------
# Hooks de lifecycle do servidor
# -----------------------------------------------------------------------------
# Motivo:
# - Executar o bootstrap no momento correto de início do servidor.
# - Garantir shutdown limpo para liberar handlers e reduzir locks de arquivo.
# -----------------------------------------------------------------------------


def _on_startup() -> None:
    """
    Hook de startup do servidor.

    Motivo:
        Centraliza a inicialização em um único ponto do lifecycle e impede
        reexecuções no mesmo processo.
    """
    global _started

    if _started:
        log = get_logger()
        log.info("Startup bootstrap skipped (already started): pid=%s", os.getpid())
        return

    bootstrap_infrastructure()

    log = get_logger()

    state = get_app_state()

    log.info(
        "[LIFECYCLE] Application starting: pid=%s port=%s", os.getpid(), state.meta.port
    )

    _started = True


def _on_shutdown() -> None:
    """
    Hook de shutdown do servidor.

    Motivo:
        Encerra handlers gerenciados pelo bootstrapper para reduzir risco de
        locks de arquivo e garantir flush final de logs.
    """
    global _bootstrapper, _started

    log = get_logger()
    log.info("[LIFECYCLE] Application shutdown requested: pid=%s", os.getpid())

    if _bootstrapper is None:
        # Pode ocorrer se o processo encerrar antes do bootstrap completar.
        log.debug("Shutdown called without active bootstrapper")
        return

    try:
        _bootstrapper.shutdown()
    except Exception:
        log.exception("Logger shutdown failed")
    finally:
        _bootstrapper = None
        _started = False


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
# Motivo:
# - Registrar hooks de forma explícita e local ao entry point, evitando efeitos colaterais no import.
# - Executar o servidor e reduzir ruído de encerramento no Windows (Ctrl+C + asyncio).
# -----------------------------------------------------------------------------


def main(*, reload: bool) -> None:
    """
    Ponto de entrada principal da aplicação.

    Args:
        reload: Controla o auto-reload do NiceGUI (recomendado apenas em DEV).

    Observação:
        Capturamos CancelledError/KeyboardInterrupt para reduzir ruído no
        encerramento (Ctrl+C) em Windows + Uvicorn.
    """
    global _hooks_registered

    if not _hooks_registered:
        # Guard garante que main() não registre os mesmos hooks mais de uma vez no mesmo processo.
        app.on_startup(_on_startup)
        app.on_shutdown(_on_shutdown)
        _hooks_registered = True

    try:
        # Usamos o estado atual para parâmetros de ui.run; defaults já existem mesmo sem settings.
        state = get_app_state()

        ui.run(
            title=state.meta.name,
            port=state.meta.port,
            native=state.meta.native_mode,
            reload=reload,
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        # CancelledError pode acontecer durante shutdown do Uvicorn; é esperado.
        log = get_logger()
        log.info("Application shutdown requested (signal)")
        return
