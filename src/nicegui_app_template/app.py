# src/nicegui_app_template/app.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Ponto de Entrada Lógico da Aplicação
# -----------------------------------------------------------------------------
# Este módulo orquestra a inicialização e o encerramento da aplicação.
#
# Responsabilidades:
# - Executar o bootstrap de infraestrutura (logger, settings e estado)
# - Registrar hooks de lifecycle do servidor (startup/shutdown)
# - Iniciar o servidor NiceGUI
#
# Decisões arquiteturais importantes:
# - O bootstrap de infraestrutura ocorre explicitamente ANTES de ui.run().
#   Isso é necessário porque parâmetros como porta e modo nativo são consumidos
#   no momento da chamada de ui.run() e dependem de valores carregados via settings.
#
# - app.on_startup não é utilizado para bootstrap, pois é executado após a
#   criação/partida do servidor e não é um ponto confiável para influenciar
#   parâmetros de inicialização.
#
# - O shutdown do logger é explícito e controlado para garantir flush correto
#   e minimizar riscos de locks de arquivo no Windows.
# -----------------------------------------------------------------------------

import asyncio
import os

from nicegui import app, ui

from .core.logger import LoggerBootstrapper, create_bootstrapper, get_logger
from .core.logger_resolver import resolve_log_config_from_state
from .core.settings import load_settings
from .core.state import AppState, get_app_state
from .ui.index import register_routes

# -----------------------------------------------------------------------------
# Estado mínimo de runtime (privado ao módulo)
# -----------------------------------------------------------------------------
# Motivo:
# - Mantém a referência ao bootstrapper ativo no processo atual.
# - Indica que o bootstrap de infraestrutura já foi executado neste processo.
# - Permite um shutdown explícito e seguro dos handlers de logging.
#
# Decisão arquitetural:
# - Este estado é estritamente de runtime.
# - Não pertence ao AppState (que deve permanecer puro e independente de
#   infraestrutura).
# - Não deve ser persistido nem exposto fora deste módulo.
# -----------------------------------------------------------------------------

_bootstrapper: LoggerBootstrapper | None = None

# -----------------------------------------------------------------------------
# Bootstrap de infraestrutura
# -----------------------------------------------------------------------------


def bootstrap_infrastructure() -> AppState:
    """Inicializa a infraestrutura essencial da aplicação.

    Responsabilidades:
        - Inicializar o logger em modo buffer (early logging)
        - Obter o estado central da aplicação
        - Carregar configurações persistentes (settings.toml)
        - Reconfigurar o logger com base no estado carregado
        - Ativar o logging em arquivo

    Observação:
        Esta função não inicia o servidor. Seu papel é preparar a infraestrutura
        necessária antes da chamada de ui.run().

    Returns:
        Instância de AppState inicializada com dados provenientes do
        settings.toml ou com valores padrão.
    """
    global _bootstrapper

    # Evita bootstrap repetido no mesmo processo, preservando idempotência.
    if _bootstrapper is not None:
        return get_app_state()

    logger_bootstrapper = create_bootstrapper()
    logger_bootstrapper.bootstrap()  # Captura logs antes do caminho do arquivo existir.

    log = get_logger()
    log.debug("Application infrastructure bootstrap started")

    state = get_app_state()  # Singleton explícito do estado da aplicação.

    # load_settings aplica parsing + fallback no próprio state.
    load_ok = load_settings(state=state, logger=log)
    log.debug("Configuration phase completed: settings_load_ok=%s", load_ok)
    if not load_ok:
        log.warning("Settings load failed; using default values")

    # Resolve LogConfig técnico com base no estado.
    log_config = resolve_log_config_from_state(state)
    logger_bootstrapper.update_config(log_config)

    try:
        # Ativa escrita em arquivo e flush do buffer.
        logger_bootstrapper.enable_file_logging()
        log.info(
            'Logging ready: file="%s" level="%s" console=%s',
            str(state.log.path.resolve()),
            state.log.level,
            state.log.console,
        )
    except Exception:
        # Fail-safe: o app continua com console/buffer se algo falhar.
        log.exception("Failed to enable file logging")

    # Presença indica bootstrap concluído no processo atual.
    _bootstrapper = logger_bootstrapper
    return state


# -----------------------------------------------------------------------------
# Hooks de lifecycle do servidor
# -----------------------------------------------------------------------------
# Motivo:
# - Registrar pontos explícitos de observabilidade durante o ciclo de vida
#   do servidor (startup e shutdown).
# - Garantir um shutdown limpo para liberar handlers de logging e reduzir
#   riscos de locks de arquivo no Windows.
#
# Observação:
# - O bootstrap de infraestrutura não ocorre nesses hooks.
# - Ele é executado antes de ui.run(), pois parâmetros críticos do servidor
#   dependem de valores previamente carregados no estado.
# -----------------------------------------------------------------------------


def _on_startup() -> None:
    """Executa ações de observabilidade no startup do servidor.

    Observação:
        O bootstrap não ocorre aqui porque ui.run() já consumiu parâmetros
        de inicialização (port/native). Este hook existe para rastreabilidade.
    """
    log = get_logger()
    state = get_app_state()
    log.info(
        "[LIFECYCLE] Server startup: pid=%s port=%s native=%s",
        os.getpid(),
        state.meta.port,
        state.meta.native_mode,
    )


def _on_shutdown() -> None:
    """Executa o shutdown controlado da infraestrutura no encerramento do servidor.

    Motivo:
        Encerrar handlers do logger de forma explícita reduz riscos de locks
        de arquivo no Windows e garante flush final.
    """
    global _bootstrapper

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


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
# Motivo:
# - Centralizar o ponto único de entrada da aplicação por processo.
# - Registrar hooks de lifecycle de forma explícita, evitando efeitos colaterais
#   durante o import de módulos.
# - Executar o servidor NiceGUI após o bootstrap da infraestrutura.
# - Tratar sinais de encerramento (Ctrl+C / CancelledError), reduzindo ruído
#   de exceções no Windows.
# -----------------------------------------------------------------------------


def main(*, reload: bool) -> None:
    """Ponto de entrada principal da aplicação.

    Args:
        reload: Controla o auto-reload do NiceGUI (recomendado apenas em DEV).

    Observação:
        Capturamos CancelledError/KeyboardInterrupt para reduzir ruído no
        encerramento (Ctrl+C) em Windows + Uvicorn.
    """
    # Registro explícito do lifecycle da aplicação.
    # main() deve ser chamado uma única vez por processo.
    # Os hooks são registrados antes de ui.run() para garantir um shutdown limpo
    # e previsível do servidor e do logger.
    app.on_startup(_on_startup)
    app.on_shutdown(_on_shutdown)

    try:
        # Bootstrap antes de ui.run() para garantir state atualizado.
        state = bootstrap_infrastructure()

        # Aviso explícito sobre efeitos colaterais do reload no Windows.
        if reload:
            log = get_logger()
            log.warning(
                "NiceGUI reload=True may start multiple Python processes (watcher/server). "
                "This can cause duplicated log messages and repeated bootstrap side effects. "
                "Use reload only for development and keep production runs with reload=False. "
                "pid=%s",
                os.getpid(),
            )

        # O roteamento SPA é inicializado durante ui.run();
        # por isso as rotas devem ser registradas previamente.
        register_routes()

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
