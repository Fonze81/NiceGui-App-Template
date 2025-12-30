# src/nicegui_app_template/app.py
from __future__ import annotations

#  Imports
# =============================================================================
from pathlib import Path

from nicegui_app_template.core.logger import LogConfig, create_bootstrapper, get_logger


def add(a: int, b: int) -> int:
    """
    Soma dois números inteiros.

    Função propositalmente simples para validar
    a configuração e execução do pytest.
    """
    return a + b


#  Inicialização do Logger (bootstrap)
# =============================================================================

# A configuração é criada aqui para manter o controle no ponto de entrada do app.
# No futuro, isso pode ser carregado a partir de settings.toml.
log_config = LogConfig(
    name="nicegui_app_template",
    file_path=Path("logs/app.log"),
    level=10,
)

# Criamos explicitamente o bootstrapper para evitar side effects em imports.
logger_bootstrapper = create_bootstrapper(log_config)

# Ativamos o modo inicial de logging (console + buffer em memória).
# Isso deve acontecer o mais cedo possível para capturar logs precoces.
logger_bootstrapper.bootstrap()

# Logger raiz do aplicativo.
log = get_logger()


# Função principal
# =============================================================================


def main() -> None:
    """
    Ponto principal de inicialização do aplicativo.

    Responsabilidades:
    - Ativar logging em arquivo (flush do buffer)
    - Montar a interface do usuário
    - Registrar shutdown limpo do logger
    - Iniciar o NiceGUI
    """
    log.info("Application starting")

    # Agora que o app já iniciou, ativamos o logging em arquivo.
    # Isso garante que logs anteriores (buffer) sejam persistidos.
    logger_bootstrapper.enable_file_logging()


# Execução direta
# =============================================================================

if __name__ == "__main__":
    main()
