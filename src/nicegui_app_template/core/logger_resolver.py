# src/nicegui_app_template/core/logger_resolver.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Logger Resolver — Boundary entre Estado e Infraestrutura de Logging
# -----------------------------------------------------------------------------
# Este módulo é responsável por **converter o estado da aplicação (AppState)**
# em uma configuração técnica consumível pelo sistema de logging.
#
# Papel arquitetural:
# - Atuar como boundary explícito entre:
#   * Estado (valores humanos / UI-friendly)
#   * Infraestrutura (logging do Python, handlers, constantes numéricas)
#
# Decisões importantes:
# - O AppState NÃO deve armazenar valores técnicos (ex.: logging.INFO, bytes)
# - O settings.toml permanece legível e editável por humanos
# - Toda conversão técnica acontece neste resolver
#
# Este módulo:
# - Não realiza I/O
# - Não modifica o estado recebido
# - Não depende do ciclo de vida do logger (bootstrap/shutdown)
# - É determinístico e facilmente testável
# -----------------------------------------------------------------------------

from typing import Final

from .helpers import parse_size_to_bytes
from .logger import DEFAULT_LOG_LEVEL, LogConfig, resolve_log_level
from .state import AppState

# -----------------------------------------------------------------------------
# Constantes de conversão
# -----------------------------------------------------------------------------

# Tamanho padrão de rotação (em bytes) utilizado como fallback seguro.
DEFAULT_ROTATE_MAX_BYTES: Final[int] = 5 * 1024 * 1024


# -----------------------------------------------------------------------------
# Resolver principal
# -----------------------------------------------------------------------------


def resolve_log_config_from_state(state: AppState) -> LogConfig:
    """
    Constrói um LogConfig técnico a partir do estado da aplicação.

    Esta função converte valores armazenados no AppState, que são mantidos
    propositalmente em formato amigável para humanos, em valores técnicos
    exigidos pelo sistema de logging do Python.

    Conversões realizadas:
        - level: str ("INFO", "DEBUG", ...) -> int (logging.INFO, logging.DEBUG)
        - rotation: str ("5 MB") -> int (bytes)

    Regras:
        - Valores inválidos nunca geram exceção
        - Fallbacks seguros são aplicados quando necessário
        - O estado não é alterado

    Args:
        state: Instância do AppState contendo a configuração de logging
            em formato humano.

    Returns:
        Uma instância de LogConfig pronta para ser aplicada ao logger.
    """

    # -------------------------------------------------------------------------
    # Level: str -> int
    # -------------------------------------------------------------------------
    # A resolução do nível textual é um detalhe específico do domínio de logging,
    # por isso o helper vive no módulo logger e é chamado aqui pelo boundary.
    level: int = resolve_log_level(state.log.level, default=DEFAULT_LOG_LEVEL)

    # -------------------------------------------------------------------------
    # Rotation: str -> bytes
    # -------------------------------------------------------------------------
    # A rotação é mantida como string no estado para facilitar edição manual
    # e exibição em UI. Aqui ocorre a conversão técnica final.
    rotate_max_bytes: int = (
        parse_size_to_bytes(state.log.rotation) or DEFAULT_ROTATE_MAX_BYTES
    )

    # -------------------------------------------------------------------------
    # Construção final do LogConfig
    # -------------------------------------------------------------------------
    return LogConfig(
        name="nicegui_app_template",
        level=level,
        console=state.log.console,
        file_path=state.log.path,
        rotate_max_bytes=rotate_max_bytes,
        rotate_backup_count=state.log.retention,
    )
