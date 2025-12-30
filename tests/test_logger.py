# tests/test_logger.py
#
# Testes automatizados do módulo de logging do template.
#
# Objetivos gerais:
# - Validar o ciclo de vida completo do logger (bootstrap -> arquivo -> shutdown)
# - Garantir propagação correta entre logger raiz e loggers filhos
# - Garantir idempotência (não duplicar handlers)
# - Garantir flush do buffer em memória (MemoryHandler)
# - Garantir encerramento limpo (evitar lock de arquivo no Windows)
# - Validar que mensagens internas de DEBUG do próprio logger são gravadas
#
# Conceitos importantes para iniciantes:
# - Idempotência: chamar uma função várias vezes não deve causar efeitos colaterais
# - Flakiness: testes que falham às vezes por timing, buffer ou I/O
# - logging é global: loggers ficam em cache por nome dentro do processo Python


from __future__ import annotations

# =============================================================================
# Imports
# =============================================================================
import logging
from logging.handlers import MemoryHandler, RotatingFileHandler
from pathlib import Path
from uuid import uuid4

import pytest

from nicegui_app_template.core.logger import LogConfig, create_bootstrapper, get_logger

# =============================================================================
# Helpers
# =============================================================================


def _unique_logger_name(prefix: str = "nicegui_app_template") -> str:
    """
    Gera um nome único de logger para evitar interferência entre testes.

    Motivo:
    - O módulo logging é global e reaproveita loggers pelo nome
    - Usar nomes únicos evita vazamento de estado entre testes
    """
    return f"{prefix}.{uuid4().hex}"


def _read_text(path: Path) -> str:
    """
    Lê o conteúdo de um arquivo de texto.

    Retorna string vazia se o arquivo não existir.
    """
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_log_with_backups(base_log_file: Path, backup_count: int) -> str:
    """
    Lê o log principal e todos os arquivos de backup gerados pela rotação.

    Motivo:
    - RotatingFileHandler pode mover logs antigos para .1, .2, etc.
    - O arquivo principal pode conter apenas as últimas linhas
    - Para evitar flakiness, consideramos todos os arquivos
    """
    parts: list[str] = []

    # Arquivo principal (ex.: app.log)
    parts.append(_read_text(base_log_file))

    # Backups (ex.: app.log.1, app.log.2, ...)
    for i in range(1, backup_count + 1):
        parts.append(_read_text(base_log_file.with_name(f"{base_log_file.name}.{i}")))

    return "\n".join(p for p in parts if p)


def _count_handlers(logger: logging.Logger, handler_type: type[logging.Handler]) -> int:
    """
    Conta quantos handlers de um determinado tipo existem no logger.
    """
    return sum(1 for h in logger.handlers if isinstance(h, handler_type))


def _flush_all_handlers(logger: logging.Logger) -> None:
    """
    Força flush de todos os handlers do logger.

    Motivo:
    - Garantir que os dados já foram gravados em disco antes da leitura
    - Reduz flakiness em testes envolvendo I/O
    """
    for handler in list(logger.handlers):
        try:
            handler.flush()
        except Exception:
            pass


def _cleanup_logger_by_name(logger_name: str) -> None:
    """
    Remove e fecha todos os handlers de um logger pelo nome.

    Motivo:
    - logging é global e pode manter handlers abertos se um teste falhar
    - No Windows, isso pode causar lock de arquivos temporários
    """
    logger = logging.getLogger(logger_name)

    for handler in list(logger.handlers):
        try:
            logger.removeHandler(handler)
        except Exception:
            pass

        try:
            handler.close()
        except Exception:
            pass

    logger.propagate = True
    logger.setLevel(logging.NOTSET)


def _make_config(
    *,
    name: str,
    log_file: Path,
    level: int = logging.INFO,
    console: bool = False,
) -> LogConfig:
    """
    Cria uma configuração de logger adequada para testes.
    """
    return LogConfig(
        name=name,
        level=level,
        console=console,
        buffer_capacity=200,
        file_path=log_file,
        rotate_max_bytes=800,  # pequeno para facilitar rotação em testes
        rotate_backup_count=2,
    )


# =============================================================================
# Fixture
# =============================================================================


@pytest.fixture
def logger_ctx(tmp_path: Path):
    """
    Fixture que cria um ambiente isolado para cada teste.

    Entrega:
    - bootstrapper
    - root_name
    - log_file
    - root_logger

    Garante shutdown e limpeza mesmo se o teste falhar.
    """
    root_name = _unique_logger_name()
    log_file = tmp_path / "logs" / "app.log"

    config = _make_config(
        name=root_name,
        log_file=log_file,
        level=logging.DEBUG,
        console=False,
    )

    bootstrapper = create_bootstrapper(config)
    root_logger = logging.getLogger(root_name)

    try:
        yield bootstrapper, root_name, log_file, root_logger
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


# =============================================================================
# Tests
# =============================================================================


def test_bootstrap_attaches_memory_handler(logger_ctx) -> None:
    """
    bootstrap() deve anexar exatamente um MemoryHandler.
    """
    bootstrapper, _root_name, _log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    assert _count_handlers(root_logger, MemoryHandler) == 1


def test_child_loggers_propagate_to_configured_root_name(logger_ctx) -> None:
    """
    Loggers filhos devem propagar mensagens para o logger raiz configurado.
    """
    bootstrapper, root_name, _log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    child_logger = get_logger(f"{root_name}.ui.pages.home")

    assert root_logger.propagate is False
    assert child_logger.propagate is True


def test_get_logger_returns_root_when_called_without_name(logger_ctx) -> None:
    """
    get_logger() sem argumentos deve retornar o logger raiz atual do app.
    """
    bootstrapper, root_name, _log_file, _root_logger = logger_ctx

    bootstrapper.bootstrap()

    log = get_logger()
    assert log.name == root_name


def test_buffered_logs_are_flushed_to_file_after_enable(logger_ctx) -> None:
    """
    Logs emitidos antes do enable_file_logging devem aparecer no arquivo.
    """
    bootstrapper, root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    child_logger = get_logger(f"{root_name}.core.some_module")
    child_logger.info("early message before file logging")
    child_logger.info("second early message")

    assert not log_file.exists()

    bootstrapper.enable_file_logging(file_path=log_file)

    _flush_all_handlers(root_logger)
    content = _read_log_with_backups(log_file, backup_count=2)

    assert "early message before file logging" in content
    assert "second early message" in content


def test_enable_file_logging_is_idempotent(logger_ctx) -> None:
    """
    enable_file_logging() deve ser idempotente.

    Chamar várias vezes não deve criar handlers duplicados.
    """
    bootstrapper, _root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1


def test_shutdown_detaches_file_handler_to_avoid_windows_locks(logger_ctx) -> None:
    """
    shutdown() deve remover o handler de arquivo.

    Motivo:
    - Evitar lock de arquivos no Windows
    """
    bootstrapper, _root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1

    bootstrapper.shutdown()

    assert _count_handlers(root_logger, RotatingFileHandler) == 0


def test_internal_debug_messages_are_written_when_level_is_debug(logger_ctx) -> None:
    """
    Quando o nível é DEBUG, o próprio logger deve registrar mensagens internas.

    Valida mensagens de:
    - bootstrap
    - enable_file_logging
    - shutdown
    """
    bootstrapper, _root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.shutdown()

    _flush_all_handlers(root_logger)

    content = _read_log_with_backups(log_file, backup_count=2)

    assert "Logger bootstrap started" in content
    assert "Logger bootstrap completed" in content
    assert "Enabling file logging" in content
    assert "File handler attached" in content
    assert "Logger shutdown started" in content
    assert "Logger shutdown completed" in content


def test_enable_file_logging_flushes_memory_buffer(logger_ctx) -> None:
    """
    enable_file_logging() deve descarregar o buffer em memória e removê-lo.
    """
    bootstrapper, root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    child_logger = get_logger(f"{root_name}.core.buffer_test")
    child_logger.info("buffer-message-1")

    assert _count_handlers(root_logger, MemoryHandler) == 1

    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, MemoryHandler) == 0

    _flush_all_handlers(root_logger)
    content = _read_log_with_backups(log_file, backup_count=2)

    assert "buffer-message-1" in content
