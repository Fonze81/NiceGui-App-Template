# src/nicegui_app_template/app.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Módulo de entrada do aplicativo
# -----------------------------------------------------------------------------
# Este módulo define o ponto de entrada lógico do aplicativo.
#
# Objetivos principais:
# - Demonstrar o ciclo de vida completo do sistema de logging
# - Garantir que mensagens sejam efetivamente gravadas em arquivo no Windows
# - Servir como base simples e previsível para evolução futura do app
#
# Problema comum em exemplos simples de logging:
# - O arquivo de log é criado, mas permanece vazio
#
# Causas frequentes:
# - O processo termina logo após habilitar o handler de arquivo
# - Não há nenhuma mensagem registrada após a ativação do handler
# - Handlers não são fechados corretamente (especialmente no Windows)
#
# Decisão adotada neste template:
# - Habilitar explicitamente o logging em arquivo com path conhecido
# - Registrar mensagens antes e depois da ativação do arquivo
# - Garantir shutdown em bloco finally para flush e fechamento dos handlers
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import logging  # Usado apenas para constantes de nível (DEBUG, INFO, etc.)
from pathlib import Path  # Representação robusta de caminhos de arquivo

from .core.logger import LogConfig, create_bootstrapper, get_logger

# -----------------------------------------------------------------------------
# Função principal
# -----------------------------------------------------------------------------


def main() -> None:
    """
    Inicializa o sistema de logging e registra mensagens de exemplo.

    Esta função é propositalmente simples e síncrona para:
    - facilitar validação em ambiente Windows
    - evitar dependências de UI neste estágio
    - servir como base clara para o bootstrap do aplicativo
    """
    # Definição explícita do caminho do arquivo de log.
    #
    # Motivo:
    # - Evita ambiguidades sobre onde o log será gravado
    # - Facilita debug e inspeção manual durante desenvolvimento
    log_file_path = Path("logs/app.log")

    # Construção da configuração do logger.
    #
    # Decisões:
    # - Nome fixo do logger raiz do aplicativo
    # - Nível DEBUG para máxima visibilidade durante desenvolvimento
    # - Console habilitado para feedback imediato
    log_config = LogConfig(
        name="nicegui_app_template",
        file_path=log_file_path,
        level=logging.DEBUG,
        console=True,
    )

    # Criação do bootstrapper responsável por gerenciar o ciclo de vida do logging.
    #
    # Responsabilidades do bootstrapper:
    # - Inicializar handlers iniciais (console + buffer em memória)
    # - Ativar o logging em arquivo quando solicitado
    # - Garantir flush e fechamento correto dos handlers no shutdown
    logger_bootstrapper = create_bootstrapper(log_config)

    # Inicializa o logging básico (console + buffer em memória).
    #
    # Motivo:
    # - Capturar mensagens emitidas logo no início da execução
    # - Evitar perda de logs antes da ativação do arquivo
    logger_bootstrapper.bootstrap()

    # Recupera o logger raiz do aplicativo.
    #
    # Observação:
    # - Todos os módulos devem obter loggers filhos a partir deste logger raiz
    log = get_logger()

    try:
        # Mensagem registrada antes da ativação do logging em arquivo.
        #
        # Esperado:
        # - Esta mensagem fica temporariamente no buffer em memória
        log.debug("Application starting (buffered)")

        # Ativação explícita do logging em arquivo.
        #
        # Decisão:
        # - Passar o file_path explicitamente evita depender de defaults implícitos
        logger_bootstrapper.enable_file_logging(file_path=log_file_path)

        # Mensagem registrada após a ativação do arquivo.
        #
        # Esperado:
        # - Esta mensagem deve ser escrita diretamente no arquivo de log
        log.error("File logging is active (should be written to disk)")

    finally:
        # Encerramento explícito do sistema de logging.
        #
        # Motivo:
        # - Forçar flush dos buffers
        # - Fechar handlers corretamente
        # - Evitar arquivos vazios ou bloqueados no Windows
        logger_bootstrapper.shutdown()


# -----------------------------------------------------------------------------
# Execução direta
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
