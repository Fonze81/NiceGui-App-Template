# src/nicegui_app_template/core/logger.py

from __future__ import annotations

# Imports
# =============================================================================
import logging
import sys
from dataclasses import dataclass
from logging.handlers import MemoryHandler, RotatingFileHandler
from pathlib import Path
from typing import Optional

#  Configuração
# =============================================================================


@dataclass(frozen=True)
class LogConfig:
    """
    Configuração mínima de logging do template.

    Mantém o logger flexível e evolutivo sem acoplar a um backend específico
    de configuração (ex.: TOML) neste momento.
    """

    name: str = "nicegui_app_template"
    level: int = logging.INFO
    console: bool = True

    buffer_capacity: int = 500

    file_path: Path = Path("logs/app.log")

    rotate_max_bytes: int = 5 * 1024 * 1024  # 5 MB
    rotate_backup_count: int = 3


#  Helpers internos


def _ensure_parent_dir(file_path: Path) -> None:
    """Garante que a pasta do arquivo de log exista."""
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _make_console_formatter() -> logging.Formatter:
    """Formatter compacto para console."""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _make_file_formatter() -> logging.Formatter:
    """Formatter detalhado para arquivo."""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    )


def _get_silent_logger(name: str) -> logging.Logger:
    """
    Retorna um logger com fallback silencioso.

    Regras:
    - Loggers filhos propagam para o logger raiz do app
    - Apenas o logger raiz possui propagate=False
    - Evita exceções caso o bootstrap ainda não tenha ocorrido
    """
    logger = logging.getLogger(name)

    if name == "nicegui_app_template":
        logger.propagate = False
    else:
        logger.propagate = True

    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())

    logger.setLevel(logging.NOTSET)
    return logger


#  Bootstrapper


class LoggerBootstrapper:
    """
    Gerencia o ciclo de vida do logger da aplicação.

    Fluxo esperado:
    1) bootstrap(): ativa console + buffer em memória
    2) enable_file_logging(): ativa arquivo e faz flush do buffer
    3) shutdown(): fecha handlers no encerramento do app
    """

    _MEMORY_HANDLER_ATTR = "_ng_template_memory_handler"
    _FILE_HANDLER_ATTR = "_ng_template_file_handler"
    _BOOTSTRAPPED_ATTR = "_ng_template_bootstrapped"

    def __init__(self, config: LogConfig):
        self._config = config

    def bootstrap(self) -> logging.Logger:
        """Inicializa console e buffer em memória."""
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        if getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            return logger

        logger.setLevel(self._config.level)

        if self._config.console:
            if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(_make_console_formatter())
                console_handler.setLevel(self._config.level)
                logger.addHandler(console_handler)

        if not any(isinstance(h, MemoryHandler) for h in logger.handlers):
            memory_handler = MemoryHandler(
                capacity=self._config.buffer_capacity,
                target=None,
                flushLevel=logging.CRITICAL,
            )
            memory_handler.setLevel(self._config.level)
            logger.addHandler(memory_handler)
            setattr(logger, self._MEMORY_HANDLER_ATTR, memory_handler)

        setattr(logger, self._BOOTSTRAPPED_ATTR, True)
        return logger

    def enable_file_logging(
        self, *, file_path: Optional[Path] = None
    ) -> logging.Logger:
        """
        Ativa logging em arquivo e despeja o buffer de memória.

        É idempotente: múltiplas chamadas não duplicam handlers.
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        if not getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            self.bootstrap()

        if isinstance(getattr(logger, self._FILE_HANDLER_ATTR, None), logging.Handler):
            return logger

        target_path = file_path or self._config.file_path
        _ensure_parent_dir(target_path)

        file_handler = RotatingFileHandler(
            filename=str(target_path),
            maxBytes=self._config.rotate_max_bytes,
            backupCount=self._config.rotate_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(_make_file_formatter())
        file_handler.setLevel(self._config.level)

        memory_handler = getattr(logger, self._MEMORY_HANDLER_ATTR, None)
        if isinstance(memory_handler, MemoryHandler):
            memory_handler.setTarget(file_handler)
            memory_handler.flush()
            logger.removeHandler(memory_handler)
            try:
                memory_handler.close()
            except Exception:
                pass
            setattr(logger, self._MEMORY_HANDLER_ATTR, None)

        logger.addHandler(file_handler)
        setattr(logger, self._FILE_HANDLER_ATTR, file_handler)

        logger.info("File logging enabled: %s", str(target_path))
        return logger

    def shutdown(self) -> None:
        """Fecha handlers controlados pelo bootstrapper."""
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        memory_handler = getattr(logger, self._MEMORY_HANDLER_ATTR, None)
        if isinstance(memory_handler, MemoryHandler):
            logger.removeHandler(memory_handler)
            try:
                memory_handler.close()
            except Exception:
                pass
            setattr(logger, self._MEMORY_HANDLER_ATTR, None)

        file_handler = getattr(logger, self._FILE_HANDLER_ATTR, None)
        if isinstance(file_handler, logging.Handler):
            logger.removeHandler(file_handler)
            try:
                file_handler.close()
            except Exception:
                pass
            setattr(logger, self._FILE_HANDLER_ATTR, None)

        setattr(logger, self._BOOTSTRAPPED_ATTR, False)


#  API pública
# =============================================================================


def get_logger(name: str = "nicegui_app_template") -> logging.Logger:
    """
    Retorna um logger pronto para uso.

    Use:
    - get_logger(__name__) em módulos
    - get_logger() para o logger raiz
    """
    return _get_silent_logger(name or "nicegui_app_template")


def create_bootstrapper(config: Optional[LogConfig] = None) -> LoggerBootstrapper:
    """Cria o bootstrapper do logger."""
    return LoggerBootstrapper(config=config or LogConfig())
