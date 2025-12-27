from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

from nicegui_app_template.core.logger import LogConfig, create_bootstrapper, get_logger

# Helpers
# =============================================================================


def _unique_logger_name(prefix: str = "ng_template_test") -> str:
    """Gera um nome único de logger para evitar interferência entre testes."""
    return f"{prefix}.{uuid4().hex}"


def _read_text(path: Path) -> str:
    """Lê o conteúdo do arquivo de log com UTF-8 para asserts."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _count_handlers(logger: logging.Logger, handler_type: type[logging.Handler]) -> int:
    """Conta handlers de um tipo específico para validar idempotência."""
    return sum(1 for h in logger.handlers if isinstance(h, handler_type))


def _flush_all_handlers(logger: logging.Logger) -> None:
    """
    Força flush de todos os handlers que suportam flush().

    Motivo: garantir que o conteúdo foi persistido antes de ler o arquivo.
    """
    for handler in list(logger.handlers):
        try:
            handler.flush()
        except Exception:
            pass


def _make_config(name: str, log_file: Path) -> LogConfig:
    """Cria uma configuração de logger adequada para testes."""
    return LogConfig(
        name=name,
        level=logging.INFO,
        console=False,  # evita poluição no output do pytest
        buffer_capacity=200,
        file_path=log_file,
        rotate_max_bytes=1024,  # pequeno para facilitar testes de rotação se necessário
        rotate_backup_count=2,
    )


# Tests
# =============================================================================


def test_child_logger_propagation_rules_are_correct() -> None:
    """
    Valida a regra de propagate:
    - logger raiz do app: propagate=False
    - loggers filhos: propagate=True
    """
    root_name = _unique_logger_name("nicegui_app_template")
    config = LogConfig(name=root_name, console=False)
    bootstrapper = create_bootstrapper(config)

    root_logger = bootstrapper.bootstrap()
    child_logger = get_logger(f"{root_name}.ui.pages.home")

    assert root_logger.propagate is False
    assert child_logger.propagate is True

    bootstrapper.shutdown()


def test_buffered_logs_are_flushed_to_file_after_enable(tmp_path: Path) -> None:
    """
    Logs emitidos antes do enable_file_logging() devem:
    - ir para o buffer (MemoryHandler) no logger raiz
    - e aparecer no arquivo após enable_file_logging()
    """
    root_name = _unique_logger_name("nicegui_app_template")
    log_file = tmp_path / "logs" / "app.log"
    config = _make_config(root_name, log_file)
    bootstrapper = create_bootstrapper(config)

    root_logger = bootstrapper.bootstrap()
    child_logger = get_logger(f"{root_name}.core.some_module")

    child_logger.info("early message before file logging")
    child_logger.info("second early message")

    assert not log_file.exists()

    bootstrapper.enable_file_logging(file_path=log_file)

    _flush_all_handlers(root_logger)
    content = _read_text(log_file)

    assert "early message before file logging" in content
    assert "second early message" in content

    bootstrapper.shutdown()


def test_enable_file_logging_without_bootstrap_still_works(tmp_path: Path) -> None:
    """
    enable_file_logging() deve funcionar mesmo se bootstrap() não foi chamado.
    O bootstrapper deve se auto-inicializar.
    """
    root_name = _unique_logger_name("nicegui_app_template")
    log_file = tmp_path / "logs" / "app.log"
    config = _make_config(root_name, log_file)
    bootstrapper = create_bootstrapper(config)

    child_logger = get_logger(f"{root_name}.ui.pages.about")
    child_logger.info("message before explicit bootstrap")

    bootstrapper.enable_file_logging(file_path=log_file)

    root_logger = logging.getLogger(root_name)
    _flush_all_handlers(root_logger)
    content = _read_text(log_file)

    assert "message before explicit bootstrap" in content

    bootstrapper.shutdown()


def test_enable_file_logging_is_idempotent(tmp_path: Path) -> None:
    """
    enable_file_logging() não deve adicionar múltiplos handlers de arquivo.
    Isso evita logs duplicados.
    """
    root_name = _unique_logger_name("nicegui_app_template")
    log_file = tmp_path / "logs" / "app.log"
    config = _make_config(root_name, log_file)
    bootstrapper = create_bootstrapper(config)

    root_logger = bootstrapper.bootstrap()

    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1

    root_logger.info("one")
    root_logger.info("two")
    _flush_all_handlers(root_logger)

    content = _read_text(log_file)
    assert "one" in content
    assert "two" in content

    bootstrapper.shutdown()


def test_shutdown_detaches_file_handler_to_avoid_windows_locks(tmp_path: Path) -> None:
    """
    shutdown() deve remover o handler de arquivo do logger raiz.

    Motivo: em Windows, isso reduz risco de lock e facilita builds/updates.
    """
    root_name = _unique_logger_name("nicegui_app_template")
    log_file = tmp_path / "logs" / "app.log"
    config = _make_config(root_name, log_file)
    bootstrapper = create_bootstrapper(config)

    root_logger = bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1

    bootstrapper.shutdown()

    assert _count_handlers(root_logger, RotatingFileHandler) == 0


def test_file_rotation_creates_backup_when_size_exceeded(tmp_path: Path) -> None:
    """
    Valida que o RotatingFileHandler cria arquivos de backup quando o tamanho
    excede rotate_max_bytes.

    Observação: como rotate_max_bytes é pequeno na config de teste, é fácil
    forçar rotação escrevendo algumas linhas maiores.
    """
    root_name = _unique_logger_name("nicegui_app_template")
    log_file = tmp_path / "logs" / "app.log"

    config = LogConfig(
        name=root_name,
        level=logging.INFO,
        console=False,
        buffer_capacity=10,
        file_path=log_file,
        rotate_max_bytes=600,  # força rotação rapidamente
        rotate_backup_count=2,
    )
    bootstrapper = create_bootstrapper(config)
    root_logger = bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)

    # Mensagens grandes para ultrapassar o limite rapidamente.
    payload = "X" * 250
    for _ in range(10):
        root_logger.info("rotation-test %s", payload)

    _flush_all_handlers(root_logger)

    # Arquivo principal deve existir.
    assert log_file.exists()

    # Pelo menos um backup deve existir quando a rotação acontece.
    backup_1 = log_file.with_name(f"{log_file.name}.1")
    backup_2 = log_file.with_name(f"{log_file.name}.2")

    assert backup_1.exists() or backup_2.exists()

    bootstrapper.shutdown()
