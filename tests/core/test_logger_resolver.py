# tests/core/test_logger_resolver.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Tests — core/logger_resolver.py
# -----------------------------------------------------------------------------
# Este módulo valida o comportamento do resolver de logging, responsável por
# converter valores armazenados no AppState (formato humano) em uma configuração
# técnica (LogConfig) consumível pelo sistema de logging do Python.
#
# O foco destes testes é garantir:
# - Conversão correta de nível de log (str -> int)
# - Conversão correta de rotação (str -> bytes)
# - Aplicação de fallbacks seguros para valores inválidos
# - Preservação de campos não convertidos
# - Ausência de efeitos colaterais (imutabilidade do estado)
# -----------------------------------------------------------------------------

import logging
from pathlib import Path
from typing import Any

import pytest

from nicegui_app_template.core.logger import DEFAULT_LOG_LEVEL, LogConfig
from nicegui_app_template.core.logger_resolver import (
    DEFAULT_ROTATE_MAX_BYTES,
    resolve_log_config_from_state,
)
from nicegui_app_template.core.state import AppState


# -----------------------------------------------------------------------------
# Helpers de teste
# -----------------------------------------------------------------------------


def _make_state(
    *,
    level: str = "INFO",
    rotation: str = "5 MB",
    retention: int = 3,
    console: bool = True,
    path: Path = Path("logs/test.log"),
) -> AppState:
    """
    Cria uma instância de AppState configurada para testes do resolver.

    Apenas os campos relevantes para o logging são ajustados explicitamente,
    mantendo o restante do estado com valores default. Isso mantém os testes
    focados no comportamento do resolver, e não na construção do estado.

    Args:
        level: Nível de log em formato humano.
        rotation: Valor de rotação em formato humano.
        retention: Quantidade de arquivos de backup.
        console: Flag indicando se o log em console está habilitado.
        path: Caminho do arquivo de log.

    Returns:
        Uma instância de AppState pronta para uso nos testes.
    """
    state = AppState()

    # Ajustamos apenas o subestado de logging para manter o teste isolado.
    state.log.level = level
    state.log.rotation = rotation
    state.log.retention = retention
    state.log.console = console
    state.log.path = path

    return state


def _snapshot_log_fields(state: AppState) -> dict[str, Any]:
    """
    Captura um snapshot dos campos relevantes do subestado de logging.

    Este snapshot é usado para verificar que o resolver não modifica o estado
    recebido, reforçando a garantia de que ele atua como uma transformação
    pura (state -> LogConfig).

    Args:
        state: Instância de AppState a ser inspecionada.

    Returns:
        Um dicionário contendo os valores atuais dos campos relevantes.
    """
    return {
        "path": state.log.path,
        "level": state.log.level,
        "console": state.log.console,
        "buffer_capacity": state.log.buffer_capacity,
        "rotation": state.log.rotation,
        "retention": state.log.retention,
    }


# -----------------------------------------------------------------------------
# Conversão de nível de log (str -> int)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_level", "expected_level"),
    [
        ("CRITICAL", logging.CRITICAL),
        ("ERROR", logging.ERROR),
        ("WARNING", logging.WARNING),
        ("WARN", logging.WARNING),
        ("INFO", logging.INFO),
        ("DEBUG", logging.DEBUG),
        ("NOTSET", logging.NOTSET),
        # Normalização de case e espaços deve ser tolerada no boundary.
        (" info ", logging.INFO),
        ("DeBuG", logging.DEBUG),
    ],
)
def test_resolve_log_config_maps_level_string_to_logging_int(
    input_level: str,
    expected_level: int,
) -> None:
    """
    Valida a conversão de níveis textuais do estado para constantes do logging.

    Args:
        input_level: Nível em formato humano armazenado no estado.
        expected_level: Constante esperada do módulo logging.
    """
    state = _make_state(level=input_level)

    config = resolve_log_config_from_state(state)

    assert isinstance(config, LogConfig)
    assert config.level == expected_level


def test_resolve_log_config_uses_default_level_on_unknown_value() -> None:
    """
    Garante que um nível textual inválido resulte em fallback seguro.

    O resolver não deve lançar exceção nem propagar valores inválidos para
    a infraestrutura de logging.
    """
    state = _make_state(level="INVALID_LEVEL")

    config = resolve_log_config_from_state(state)

    assert config.level == DEFAULT_LOG_LEVEL


# -----------------------------------------------------------------------------
# Conversão de rotação (human-readable -> bytes)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rotation", "expected_bytes"),
    [
        ("1 B", 1),
        ("1 KB", 1024),
        ("2 MB", 2 * 1024**2),
        ("3 GB", 3 * 1024**3),
        # Normalização de espaços e case deve ser tolerada.
        ("  5   mb ", 5 * 1024**2),
        ("10KB", 10 * 1024),
    ],
)
def test_resolve_log_config_converts_rotation_to_bytes(
    rotation: str,
    expected_bytes: int,
) -> None:
    """
    Valida a conversão correta de valores textuais de rotação para bytes.

    Args:
        rotation: Valor de rotação em formato humano.
        expected_bytes: Valor esperado em bytes.
    """
    state = _make_state(rotation=rotation)

    config = resolve_log_config_from_state(state)

    assert config.rotate_max_bytes == expected_bytes


@pytest.mark.parametrize(
    "rotation",
    [
        "",
        "   ",
        "5",
        "MB",
        "1.5 MB",
        "-5 MB",
        "5 TB",
        "5 MiB",
        "5MB extra",
    ],
)
def test_resolve_log_config_uses_default_rotate_bytes_on_invalid_rotation(
    rotation: str,
) -> None:
    """
    Garante fallback seguro quando o valor de rotação não pode ser convertido.

    Valores inválidos não devem quebrar o bootstrap do logger nem gerar exceções.
    """
    state = _make_state(rotation=rotation)

    config = resolve_log_config_from_state(state)

    assert config.rotate_max_bytes == DEFAULT_ROTATE_MAX_BYTES


# -----------------------------------------------------------------------------
# Propagação de campos não convertidos e imutabilidade do estado
# -----------------------------------------------------------------------------


def test_resolve_log_config_preserves_non_converted_fields() -> None:
    """
    Valida que campos não sujeitos a conversão sejam propagados corretamente.

    Apenas level e rotation devem ser transformados pelo resolver.
    """
    custom_path = Path("logs/custom.log")
    state = _make_state(
        level="INFO",
        rotation="5 MB",
        retention=7,
        console=False,
        path=custom_path,
    )

    config = resolve_log_config_from_state(state)

    assert config.console is False
    assert config.file_path == custom_path
    assert config.rotate_backup_count == 7
    assert config.name == "nicegui_app_template"


def test_resolve_log_config_does_not_mutate_state() -> None:
    """
    Garante que o resolver não modifica o estado recebido.

    Mesmo que o resolver normalize internamente valores como nível e rotação,
    o AppState deve permanecer exatamente como estava antes da chamada.
    """
    state = _make_state(level="  debug  ", rotation=" 10 KB ")
    before = _snapshot_log_fields(state)

    _ = resolve_log_config_from_state(state)

    after = _snapshot_log_fields(state)

    assert after == before
