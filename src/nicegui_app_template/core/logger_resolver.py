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

import logging
from typing import Final

from .logger import LogConfig
from .helpers import parse_size_to_bytes
from .state import AppState


# -----------------------------------------------------------------------------
# Constantes e mapas de conversão
# -----------------------------------------------------------------------------

# Nível de log padrão utilizado quando o valor no estado é inválido ou desconhecido.
DEFAULT_LOG_LEVEL: Final[int] = logging.INFO

# Tamanho padrão de rotação (em bytes) utilizado como fallback seguro.
DEFAULT_ROTATE_MAX_BYTES: Final[int] = 5 * 1024 * 1024

# Mapeamento explícito entre níveis textuais e constantes do módulo logging.
# Este mapa evita uso de getattr/reflection e mantém comportamento previsível.
_LOG_LEVEL_MAP: Final[dict[str, int]] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,  # Alias comum aceito para compatibilidade.
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


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

    Design rationale:
        - Mantém o AppState limpo e independente de detalhes de infraestrutura
        - Centraliza toda a lógica de conversão em um único ponto
        - Facilita testes, manutenção e futuras mudanças no backend de logging
    """

    # -------------------------------------------------------------------------
    # Level: str -> int
    # -------------------------------------------------------------------------
    # Normalizamos a string para evitar problemas com case ou espaços acidentais.
    level_str = state.log.level.upper().strip()

    # O uso de um mapa explícito evita reflexão dinâmica e torna o fallback claro.
    level: int = _LOG_LEVEL_MAP.get(level_str, DEFAULT_LOG_LEVEL)

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
    # A partir deste ponto, todos os valores são técnicos e compatíveis
    # com o módulo logging e seus handlers.
    return LogConfig(
        name="nicegui_app_template",
        level=level,
        console=state.log.console,
        file_path=state.log.path,
        rotate_max_bytes=rotate_max_bytes,
        rotate_backup_count=state.log.retention,
    )
