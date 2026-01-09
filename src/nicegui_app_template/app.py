# src/nicegui_app_template/app.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Módulo de entrada do aplicativo
# -----------------------------------------------------------------------------
# Este módulo é o ponto de entrada da aplicação.
#
# Responsabilidades deste arquivo:
# - Orquestrar o ciclo de vida do logger (bootstrap → update → enable → shutdown)
# - Carregar configurações persistentes (settings.toml)
# - Resolver configurações humanas do estado em valores técnicos
# - Garantir que falhas não interrompam o bootstrap da aplicação
#
# Decisões arquiteturais:
# - Nenhuma lógica de negócio deve residir aqui
# - Nenhuma configuração é parseada manualmente
# - O estado é tratado como fonte de verdade em runtime
# - Conversões técnicas são delegadas a resolvers explícitos
# -----------------------------------------------------------------------------

from .core.logger import create_bootstrapper, get_logger
from .core.logger_resolver import resolve_log_config_from_state
from .core.settings import load_settings
from .core.state import get_app_state


def main() -> None:
    """
    Inicializa e orquestra o bootstrap da aplicação.

    Esta função executa a sequência completa de inicialização do aplicativo,
    garantindo que:
    - O logger seja iniciado em modo buffered
    - As configurações persistentes sejam carregadas no estado
    - A configuração técnica do logger seja resolvida a partir do estado
    - O logging em arquivo seja habilitado de forma segura
    - Recursos do logger sejam finalizados corretamente ao final

    A função não retorna valores e não lança exceções intencionalmente,
    permitindo que o aplicativo siga com defaults mesmo em cenários de falha.
    """

    # -------------------------------------------------------------------------
    # Bootstrap inicial do logger (modo buffer)
    # -------------------------------------------------------------------------
    # O logger é inicializado antes de qualquer outra operação para capturar
    # mensagens iniciais, mesmo antes do caminho de arquivo estar resolvido.
    logger_bootstrapper = create_bootstrapper()
    logger_bootstrapper.bootstrap()
    log = get_logger()

    # -------------------------------------------------------------------------
    # Inicialização do estado da aplicação
    # -------------------------------------------------------------------------
    # O estado central é obtido como fonte única de verdade em runtime.
    state = get_app_state()

    # -------------------------------------------------------------------------
    # Carregamento das configurações persistentes
    # -------------------------------------------------------------------------
    # Passar explicitamente state e logger evita uso de logger nulo e melhora
    # rastreabilidade em caso de falha no carregamento.
    load_ok = load_settings(state=state, logger=log)

    if load_ok:
        log.info("Settings loaded successfully")
    else:
        # O load_settings já registra o erro detalhado; aqui apenas explicitamos
        # que o aplicativo seguirá com valores default.
        log.warning("Settings load failed; defaults are being used")

    # -------------------------------------------------------------------------
    # Resolução da configuração técnica do logger
    # -------------------------------------------------------------------------
    # Converte valores humanos do estado (ex.: 'INFO', '5 MB') em valores técnicos
    # exigidos pelo sistema de logging do Python.
    log_config = resolve_log_config_from_state(state)
    logger_bootstrapper.update_config(log_config)

    try:
        # ---------------------------------------------------------------------
        # Ativação do logging em arquivo
        # ---------------------------------------------------------------------
        # A partir deste ponto, o logger tenta persistir mensagens em disco.
        log.debug("Application starting (buffered)")

        try:
            logger_bootstrapper.enable_file_logging()
            log.info("File logging is active")
        except Exception:
            # Falhas aqui costumam estar relacionadas a permissões ou paths
            # inválidos. A aplicação não deve quebrar por isso.
            log.exception("Failed to enable file logging")

        # ---------------------------------------------------------------------
        # Bootstrap real da aplicação (UI, rotas, serviços, etc.)
        # ---------------------------------------------------------------------
        # Este é o ponto onde a inicialização do NiceGUI ou outros subsistemas
        # deve ocorrer. Mantido fora deste exemplo por clareza.
    finally:
        # ---------------------------------------------------------------------
        # Finalização controlada do logger
        # ---------------------------------------------------------------------
        # Garante flush de buffers e liberação correta de handlers.
        logger_bootstrapper.shutdown()


if __name__ == "__main__":
    main()
