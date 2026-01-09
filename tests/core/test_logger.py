# tests/core/test_logger.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Testes do módulo de logging (core/logger.py)
# -----------------------------------------------------------------------------
# Este módulo valida o comportamento do sistema de logging do template,
# cobrindo o ciclo de vida do logger:
#
# - Bootstrap inicial com buffer em memória
# - Propagação correta entre logger raiz e loggers filhos
# - Ativação do logging em arquivo (RotatingFileHandler)
# - Idempotência (não duplicar handlers)
# - Flush correto do MemoryHandler
# - Encerramento limpo (evitar lock de arquivos no Windows)
# - Registro de mensagens internas do próprio logger (DEBUG)
# - Aplicação de update_config (nível e console) após bootstrap
# - Robustez: enable_file_logging() defensivo (sem bootstrap prévio)
# - Shutdown fecha apenas handlers gerenciados pelo bootstrapper
# - Segurança: get_logger() antes do bootstrap não gera warnings (NullHandler)
# - Atualização de níveis em handlers (MemoryHandler / RotatingFileHandler)
# - Idempotência de arquivo preservada mesmo após update_config()
#
# Observações importantes:
# - O módulo logging é global no processo Python
# - Loggers são cacheados por nome
# - Falhas de limpeza podem causar flakiness ou lock de arquivos no Windows
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import logging
from logging.handlers import MemoryHandler, RotatingFileHandler
from pathlib import Path
from uuid import uuid4

import pytest

from nicegui_app_template.core.logger import LogConfig, create_bootstrapper, get_logger

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _unique_logger_name(prefix: str = "nicegui_app_template") -> str:
    """Gera um nome único de logger para cada teste.

    Args:
        prefix: Prefixo base para agrupar o namespace do logger.

    Returns:
        Nome único para uso como logger raiz em testes.

    Notes:
        - O logging reutiliza loggers pelo nome em nível global.
        - Nomes únicos evitam vazamento de handlers e estado entre testes.
    """
    return f"{prefix}.{uuid4().hex}"


def _read_text(path: Path) -> str:
    """Lê o conteúdo de um arquivo de texto.

    Args:
        path: Caminho do arquivo.

    Returns:
        Conteúdo do arquivo em UTF-8, ou string vazia se não existir.

    Notes:
        - Simplifica leitura de logs sem precisar tratar exceções no chamador.
    """
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_log_with_backups(base_log_file: Path, backup_count: int) -> str:
    """Lê o arquivo de log principal e todos os backups gerados pela rotação.

    Args:
        base_log_file: Arquivo principal de log (ex.: app.log).
        backup_count: Quantidade de backups a considerar (ex.: app.log.1, app.log.2).

    Returns:
        Conteúdo concatenado do log principal e backups existentes.

    Notes:
        - RotatingFileHandler pode mover mensagens antigas para arquivos .1, .2, etc.
        - Considerar todos os arquivos reduz flakiness em testes com rotação.
    """
    parts: list[str] = []
    parts.append(_read_text(base_log_file))

    for i in range(1, backup_count + 1):
        parts.append(_read_text(base_log_file.with_name(f"{base_log_file.name}.{i}")))

    return "\n".join(p for p in parts if p)


def _count_handlers(logger: logging.Logger, handler_type: type[logging.Handler]) -> int:
    """Conta quantos handlers de um determinado tipo existem no logger.

    Args:
        logger: Logger alvo.
        handler_type: Tipo do handler a contar.

    Returns:
        Número de handlers do tipo informado no logger.

    Notes:
        - Facilita validação de idempotência sem duplicar lógica em testes.
    """
    return sum(1 for h in logger.handlers if isinstance(h, handler_type))


def _count_console_handlers(logger: logging.Logger) -> int:
    """Conta quantos StreamHandlers "de console" existem no logger.

    Args:
        logger: Logger alvo.

    Returns:
        Número de handlers de console anexados.

    Notes:
        - Consideramos "console" como StreamHandler que não seja NullHandler.
    """
    return sum(
        1
        for h in logger.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.NullHandler)
    )


def _has_null_handler(logger: logging.Logger) -> bool:
    """Indica se o logger possui NullHandler anexado.

    Args:
        logger: Logger alvo.

    Returns:
        True se existir ao menos um NullHandler.
    """
    return any(isinstance(h, logging.NullHandler) for h in logger.handlers)


def _get_first_handler(
    logger: logging.Logger, handler_type: type[logging.Handler]
) -> logging.Handler | None:
    """Retorna o primeiro handler do tipo informado, se existir.

    Args:
        logger: Logger alvo.
        handler_type: Tipo do handler desejado.

    Returns:
        Handler encontrado ou None.
    """
    for handler in logger.handlers:
        if isinstance(handler, handler_type):
            return handler
    return None


def _flush_all_handlers(logger: logging.Logger) -> None:
    """Força flush de todos os handlers associados ao logger.

    Args:
        logger: Logger alvo.

    Notes:
        - Garante que dados já foram gravados em disco antes da leitura.
        - Reduz flakiness em testes que envolvem I/O.
    """
    for handler in list(logger.handlers):
        try:
            handler.flush()
        except Exception:
            # Em testes, falhas de flush não devem quebrar o fluxo.
            pass


def _cleanup_logger_by_name(logger_name: str) -> None:
    """Remove e fecha todos os handlers de um logger identificado pelo nome.

    Args:
        logger_name: Nome do logger a limpar.

    Notes:
        - logging é global e pode manter handlers abertos após falha de testes.
        - No Windows, handlers de arquivo abertos causam lock em diretórios temporários.
        - Esta função tenta retornar o logger para um estado neutro.
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
    rotate_max_bytes: int = 800,
    rotate_backup_count: int = 2,
) -> LogConfig:
    """Cria uma configuração de logger adequada para testes.

    Args:
        name: Nome do logger raiz.
        log_file: Caminho do arquivo de log.
        level: Nível de logging.
        console: Indica se StreamHandler deve ser anexado.
        rotate_max_bytes: Tamanho máximo do arquivo antes da rotação.
        rotate_backup_count: Quantidade de backups mantidos.

    Returns:
        Instância de LogConfig para uso em testes.

    Notes:
        - Centraliza parâmetros comuns.
        - Usa limites pequenos por padrão para facilitar testes de rotação.
    """
    return LogConfig(
        name=name,
        level=level,
        console=console,
        buffer_capacity=200,
        file_path=log_file,
        rotate_max_bytes=rotate_max_bytes,
        rotate_backup_count=rotate_backup_count,
    )


# -----------------------------------------------------------------------------
# Fixture
# -----------------------------------------------------------------------------


@pytest.fixture
def logger_ctx(tmp_path: Path):
    """Cria um contexto isolado de logger para cada teste.

    Args:
        tmp_path: Fixture do pytest para diretório temporário do teste.

    Yields:
        Tupla contendo:
            - bootstrapper
            - root_name
            - log_file
            - root_logger

    Notes:
        - Garante isolamento por teste.
        - Executa shutdown e limpeza mesmo em caso de falha.
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


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_bootstrap_attaches_memory_handler(logger_ctx) -> None:
    """bootstrap() deve anexar exatamente um MemoryHandler ao logger raiz."""
    bootstrapper, _root_name, _log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    assert _count_handlers(root_logger, MemoryHandler) == 1


def test_bootstrap_is_idempotent(logger_ctx) -> None:
    """bootstrap() não deve duplicar handlers quando chamado múltiplas vezes."""
    bootstrapper, _root_name, _log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()
    bootstrapper.bootstrap()
    bootstrapper.bootstrap()

    assert _count_handlers(root_logger, MemoryHandler) == 1
    assert _count_console_handlers(root_logger) == 0


def test_child_loggers_propagate_to_configured_root_name(logger_ctx) -> None:
    """Loggers filhos devem propagar mensagens para o logger raiz configurado."""
    bootstrapper, root_name, _log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    child_logger = get_logger(f"{root_name}.ui.pages.home")

    assert root_logger.propagate is False
    assert child_logger.propagate is True


def test_get_logger_returns_root_when_called_without_name(logger_ctx) -> None:
    """get_logger() sem argumentos deve retornar o logger raiz atual do app."""
    bootstrapper, root_name, _log_file, _root_logger = logger_ctx

    bootstrapper.bootstrap()

    log = get_logger()
    assert log.name == root_name


def test_get_logger_before_bootstrap_is_safe_and_uses_null_handler(
    tmp_path: Path,
) -> None:
    """get_logger() antes do bootstrap deve ser seguro e adicionar NullHandler."""
    root_name = _unique_logger_name()
    log_file = tmp_path / "logs" / "app.log"

    config = _make_config(
        name=root_name, log_file=log_file, level=logging.DEBUG, console=False
    )
    bootstrapper = create_bootstrapper(config)

    try:
        # Não chamamos bootstrap().
        log = get_logger()
        assert log.name == root_name

        # Deve existir ao menos um NullHandler para evitar warnings.
        assert _has_null_handler(log) is True

        # O logger raiz não deve propagar para o root logger global.
        assert log.propagate is False
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_buffered_logs_are_flushed_to_file_after_enable(logger_ctx) -> None:
    """Logs emitidos antes da ativação do arquivo devem ser persistidos após enable."""
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
    """enable_file_logging() deve ser idempotente e não duplicar handlers."""
    bootstrapper, _root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.enable_file_logging(file_path=log_file)
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1


def test_enable_file_logging_flushes_memory_buffer(logger_ctx) -> None:
    """enable_file_logging() deve descarregar o buffer em memória e removê-lo."""
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


def test_enable_file_logging_is_defensive_when_called_before_bootstrap(
    tmp_path: Path,
) -> None:
    """enable_file_logging() deve funcionar mesmo sem bootstrap() explícito."""
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
        bootstrapper.enable_file_logging(file_path=log_file)

        assert _count_handlers(root_logger, RotatingFileHandler) == 1
        content = _read_log_with_backups(log_file, backup_count=2)

        assert "Enabling file logging" in content
        assert "File handler attached" in content
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_update_config_can_attach_console_after_bootstrap(tmp_path: Path) -> None:
    """update_config() deve anexar console após bootstrap quando habilitado."""
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
        bootstrapper.bootstrap()
        assert _count_console_handlers(root_logger) == 0

        new_config = _make_config(
            name=root_name,
            log_file=log_file,
            level=logging.DEBUG,
            console=True,
        )
        bootstrapper.update_config(new_config)

        assert _count_console_handlers(root_logger) == 1
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_update_config_can_detach_console_after_bootstrap(tmp_path: Path) -> None:
    """update_config() deve remover console após bootstrap quando desabilitado."""
    root_name = _unique_logger_name()
    log_file = tmp_path / "logs" / "app.log"

    config = _make_config(
        name=root_name,
        log_file=log_file,
        level=logging.DEBUG,
        console=True,
    )

    bootstrapper = create_bootstrapper(config)
    root_logger = logging.getLogger(root_name)

    try:
        bootstrapper.bootstrap()
        assert _count_console_handlers(root_logger) == 1

        new_config = _make_config(
            name=root_name,
            log_file=log_file,
            level=logging.DEBUG,
            console=False,
        )
        bootstrapper.update_config(new_config)

        assert _count_console_handlers(root_logger) == 0
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_update_config_does_not_change_root_logger_name(tmp_path: Path) -> None:
    """update_config() não deve permitir alteração do nome do logger após bootstrap."""
    root_name = _unique_logger_name()
    other_name = _unique_logger_name(prefix="other")
    log_file = tmp_path / "logs" / "app.log"

    config = _make_config(
        name=root_name, log_file=log_file, level=logging.DEBUG, console=False
    )
    bootstrapper = create_bootstrapper(config)
    root_logger = logging.getLogger(root_name)

    try:
        bootstrapper.bootstrap()

        new_config = _make_config(
            name=other_name,
            log_file=log_file,
            level=logging.DEBUG,
            console=False,
        )
        bootstrapper.update_config(new_config)

        assert root_logger.name == root_name
        assert logging.getLogger(root_name) is root_logger
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)
        _cleanup_logger_by_name(other_name)


def test_update_config_updates_memory_handler_level(logger_ctx) -> None:
    """update_config() deve atualizar o nível do MemoryHandler após bootstrap."""
    bootstrapper, root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()

    memory_handler = _get_first_handler(root_logger, MemoryHandler)
    assert isinstance(memory_handler, MemoryHandler)
    assert memory_handler.level == logging.DEBUG

    new_config = _make_config(
        name=root_name,
        log_file=log_file,
        level=logging.INFO,
        console=False,
    )
    bootstrapper.update_config(new_config)

    memory_handler_after = _get_first_handler(root_logger, MemoryHandler)
    assert isinstance(memory_handler_after, MemoryHandler)
    assert memory_handler_after.level == logging.INFO


def test_update_config_updates_file_handler_level(tmp_path: Path) -> None:
    """update_config() deve atualizar o nível do RotatingFileHandler após enable_file_logging()."""
    root_name = _unique_logger_name()
    log_file = tmp_path / "logs" / "app.log"
    config = _make_config(
        name=root_name, log_file=log_file, level=logging.DEBUG, console=False
    )

    bootstrapper = create_bootstrapper(config)
    root_logger = logging.getLogger(root_name)

    try:
        bootstrapper.bootstrap()
        bootstrapper.enable_file_logging(file_path=log_file)

        file_handler = _get_first_handler(root_logger, RotatingFileHandler)
        assert isinstance(file_handler, RotatingFileHandler)
        assert file_handler.level == logging.DEBUG

        new_config = _make_config(
            name=root_name,
            log_file=log_file,
            level=logging.ERROR,
            console=False,
        )
        bootstrapper.update_config(new_config)

        file_handler_after = _get_first_handler(root_logger, RotatingFileHandler)
        assert isinstance(file_handler_after, RotatingFileHandler)
        assert file_handler_after.level == logging.ERROR
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_enable_file_logging_does_not_duplicate_file_handler_after_update_config(
    tmp_path: Path,
) -> None:
    """enable_file_logging() não deve duplicar file handler mesmo após update_config()."""
    root_name = _unique_logger_name()
    log_file = tmp_path / "logs" / "app.log"
    config = _make_config(
        name=root_name, log_file=log_file, level=logging.DEBUG, console=False
    )

    bootstrapper = create_bootstrapper(config)
    root_logger = logging.getLogger(root_name)

    try:
        bootstrapper.bootstrap()
        bootstrapper.enable_file_logging(file_path=log_file)

        assert _count_handlers(root_logger, RotatingFileHandler) == 1

        new_config = _make_config(
            name=root_name,
            log_file=log_file,
            level=logging.INFO,
            console=False,
        )
        bootstrapper.update_config(new_config)

        bootstrapper.enable_file_logging(file_path=log_file)

        assert _count_handlers(root_logger, RotatingFileHandler) == 1
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_shutdown_detaches_file_handler_to_avoid_windows_locks(logger_ctx) -> None:
    """shutdown() deve remover o handler de arquivo para evitar lock no Windows."""
    bootstrapper, _root_name, log_file, root_logger = logger_ctx

    bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1

    bootstrapper.shutdown()

    assert _count_handlers(root_logger, RotatingFileHandler) == 0


def test_internal_debug_messages_are_written_when_level_is_debug(logger_ctx) -> None:
    """Em nível DEBUG, o logger deve registrar mensagens internas do lifecycle."""
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


def test_shutdown_does_not_close_external_handlers(tmp_path: Path) -> None:
    """shutdown() deve fechar somente handlers gerenciados pelo bootstrapper."""
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

    external_handler = logging.NullHandler()

    try:
        bootstrapper.bootstrap()
        root_logger.addHandler(external_handler)

        bootstrapper.enable_file_logging(file_path=log_file)
        bootstrapper.shutdown()

        assert external_handler in root_logger.handlers
    finally:
        try:
            root_logger.removeHandler(external_handler)
        except Exception:
            pass
        try:
            external_handler.close()
        except Exception:
            pass

        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)


def test_file_rotation_creates_backups(tmp_path: Path) -> None:
    """Rotação deve criar backups quando maxBytes é excedido."""
    root_name = _unique_logger_name()
    log_file = tmp_path / "logs" / "app.log"

    config = _make_config(
        name=root_name,
        log_file=log_file,
        level=logging.DEBUG,
        console=False,
        rotate_max_bytes=250,
        rotate_backup_count=2,
    )

    bootstrapper = create_bootstrapper(config)
    root_logger = logging.getLogger(root_name)

    try:
        bootstrapper.bootstrap()
        bootstrapper.enable_file_logging(file_path=log_file)

        log = get_logger(root_name)
        for _ in range(60):
            log.info("X" * 80)

        _flush_all_handlers(root_logger)

        backup_1 = log_file.with_name(f"{log_file.name}.1")
        assert backup_1.exists()
    finally:
        try:
            bootstrapper.shutdown()
        except Exception:
            pass
        _cleanup_logger_by_name(root_name)
