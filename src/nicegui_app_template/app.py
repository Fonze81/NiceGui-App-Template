# src/nicegui_app_template/app.py

from __future__ import annotations

# =============================================================================
# Módulo de entrada do aplicativo - logging e funções simples para testes
# =============================================================================
#
# Problema comum em exemplos simples:
# - o arquivo de log é criado, mas fica vazio
#
# Causas mais frequentes:
# - o processo termina logo após habilitar o arquivo, sem fechar handlers
# - não existe nenhuma mensagem registrada após a ativação do handler de arquivo
#
# Solução:
# - habilitar o arquivo explicitamente com o file_path correto
# - registrar pelo menos uma mensagem depois do enable
# - chamar shutdown() em um bloco finally para garantir flush/close no Windows
# =============================================================================
# Imports - dependências mínimas
# =============================================================================
import logging  # Usado para constantes de nível (DEBUG, INFO, etc.)
from pathlib import Path  # Caminhos de arquivo de forma robusta

from nicegui_app_template.core.logger import LogConfig, create_bootstrapper, get_logger

# =============================================================================
# Função simples - usada pelo pytest para validar execução
# =============================================================================


def add(a: int, b: int) -> int:
    """
    Soma dois números inteiros.

    Função propositalmente simples para validar
    a configuração e execução do pytest.
    """
    return a + b


# =============================================================================
# Função principal - ponto de entrada
# =============================================================================


def main() -> None:
    """
    Inicializa o logger e registra algumas mensagens.

    Este main é propositalmente simples para facilitar validação no Windows.
    """
    # Definimos o arquivo de log explicitamente - assim não há dúvida sobre onde será gravado.
    log_file_path = Path("logs/app1.log")

    # Configuração do logger - usamos logging.DEBUG para ficar legível.
    log_config = LogConfig(
        name="nicegui_app_template",
        file_path=log_file_path,
        level=logging.DEBUG,
        console=True,
    )

    # Criamos o bootstrapper - ele gerencia o ciclo de vida do logging.
    logger_bootstrapper = create_bootstrapper(log_config)

    # Inicializa console e buffer em memória - captura logs bem no começo do app.
    logger_bootstrapper.bootstrap()

    # Logger raiz do aplicativo - centraliza handlers.
    log = get_logger()

    try:
        # Esta mensagem ocorre antes do arquivo existir - deve cair no buffer em memória.
        log.debug("Application starting (buffered)")

        # Ativamos o log em arquivo usando explicitamente o caminho desejado.
        # Isso garante que estamos gravando no app1.log (e não em um default diferente).
        logger_bootstrapper.enable_file_logging(file_path=log_file_path)

        # Esta mensagem ocorre após enable - deve ir direto para o arquivo.
        log.error("File logging is active (should be written to disk)")

    finally:
        # Garante flush e fechamento dos handlers - essencial no Windows para não ficar vazio/bloqueado.
        logger_bootstrapper.shutdown()


# =============================================================================
# Execução direta
# =============================================================================

if __name__ == "__main__":
    main()
