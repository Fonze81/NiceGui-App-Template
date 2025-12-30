# src/nicegui_app_template/core/logger.py
#
# Este módulo implementa o sistema de logging do template.
#
# Objetivos principais:
# - Registrar logs desde o início da execução do aplicativo
# - Evitar perda de logs antes do arquivo de log estar pronto
# - Centralizar logs em um único logger raiz da aplicação
# - Ser seguro no Windows, evitando arquivos de log bloqueados
#
# Observação importante:
# - O módulo logging do Python é global e mantém loggers em cache por nome
# - Por isso, este módulo evita "desconfigurar" um logger que já foi inicializado
#
# Nota sobre logs internos de DEBUG:
# - Para que os próprios logs internos do logger apareçam, precisamos ter handlers
# - Portanto, os handlers (MemoryHandler/console/arquivo) são anexados antes dos logger.debug()


from __future__ import annotations

# =============================================================================
# Imports - bibliotecas padrão do Python
# =============================================================================
import logging
import sys
from dataclasses import dataclass
from logging.handlers import MemoryHandler, RotatingFileHandler
from pathlib import Path
from typing import Optional

# =============================================================================
# Estado interno do módulo - controle do nome do logger raiz
# =============================================================================

_DEFAULT_ROOT_LOGGER_NAME = "nicegui_app_template"
_root_logger_name: str = _DEFAULT_ROOT_LOGGER_NAME


def _set_root_logger_name(name: str) -> None:
    """
    Define o nome do logger raiz do aplicativo.

    Motivo:
    - Permitir que LogConfig(name="...") funcione corretamente
    - Garantir que loggers filhos saibam para onde propagar mensagens
    """
    global _root_logger_name
    _root_logger_name = name or _DEFAULT_ROOT_LOGGER_NAME


# =============================================================================
# Configuração - parâmetros de logging
# =============================================================================


@dataclass(frozen=True)
class LogConfig:
    """
    Configuração mínima de logging do template.

    Motivo:
    - Centralizar parâmetros de logging
    - Facilitar manutenção e evolução futura
    """

    name: str = _DEFAULT_ROOT_LOGGER_NAME
    level: int = logging.INFO
    console: bool = True

    buffer_capacity: int = 500

    file_path: Path = Path("logs/app.log")

    rotate_max_bytes: int = 5 * 1024 * 1024
    rotate_backup_count: int = 3


# =============================================================================
# Helpers internos - funções utilitárias do módulo
# =============================================================================


def _ensure_parent_dir(file_path: Path) -> None:
    """
    Garante que o diretório do arquivo de log exista.

    Motivo:
    - Evitar falha ao criar o arquivo de log
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _make_console_formatter() -> logging.Formatter:
    """
    Cria o formatter usado para logs no console.
    """
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _make_file_formatter() -> logging.Formatter:
    """
    Cria o formatter usado para logs em arquivo.
    """
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    )


def _get_silent_logger(name: str) -> logging.Logger:
    """
    Retorna um logger seguro para uso em qualquer ponto do aplicativo.

    Regras:
    - Logger raiz do app não propaga para o root logger do Python
    - Loggers filhos propagam para o logger raiz
    - Antes do bootstrap, adiciona NullHandler para evitar warnings
    - Após o bootstrap, não altera handlers nem níveis
    """
    logger = logging.getLogger(name)

    if name == _root_logger_name:
        logger.propagate = False
    else:
        logger.propagate = True

    bootstrapped = bool(getattr(logger, LoggerBootstrapper._BOOTSTRAPPED_ATTR, False))
    if not bootstrapped:
        if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
            logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.NOTSET)

    return logger


# =============================================================================
# Bootstrapper - gerencia o ciclo de vida do logger
# =============================================================================


class LoggerBootstrapper:
    """
    Controla o ciclo de vida do logger da aplicação.

    Fluxo:
    1) bootstrap() - console + buffer em memória
    2) enable_file_logging() - arquivo + flush do buffer
    3) shutdown() - fechamento limpo dos handlers
    """

    _MEMORY_HANDLER_ATTR = "_ng_template_memory_handler"
    _FILE_HANDLER_ATTR = "_ng_template_file_handler"
    _BOOTSTRAPPED_ATTR = "_ng_template_bootstrapped"

    def __init__(self, config: LogConfig):
        self._config = config
        _set_root_logger_name(self._config.name)

    def bootstrap(self) -> logging.Logger:
        """
        Inicializa o logger com buffer em memória e, opcionalmente, console.

        Ponto importante:
        - Para que os logs internos de DEBUG sejam capturados, precisamos anexar
          pelo menos um handler antes de emitir logger.debug(...)
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        if getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            logger.debug("Logger bootstrap skipped - already initialized")
            return logger

        logger.setLevel(self._config.level)

        if not any(isinstance(h, MemoryHandler) for h in logger.handlers):
            memory_handler = MemoryHandler(
                capacity=self._config.buffer_capacity,
                target=None,
                flushLevel=logging.CRITICAL,
            )
            memory_handler.setLevel(self._config.level)
            logger.addHandler(memory_handler)
            setattr(logger, self._MEMORY_HANDLER_ATTR, memory_handler)

        logger.debug("Logger bootstrap started")

        if self._config.console:
            if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(_make_console_formatter())
                console_handler.setLevel(self._config.level)
                logger.addHandler(console_handler)
                logger.debug("Console handler attached")

        setattr(logger, self._BOOTSTRAPPED_ATTR, True)
        logger.debug("Logger bootstrap completed")
        return logger

    def enable_file_logging(
        self, *, file_path: Optional[Path] = None
    ) -> logging.Logger:
        """
        Ativa logging em arquivo e descarrega o buffer em memória.

        Idempotência:
        - múltiplas chamadas não duplicam handlers
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        if not getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            self.bootstrap()

        logger.debug("Enabling file logging")

        if isinstance(getattr(logger, self._FILE_HANDLER_ATTR, None), logging.Handler):
            logger.debug("File logging already enabled - skipping")
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
            logger.debug("Flushing memory buffer to file")
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

        logger.debug("File handler attached")
        logger.info("File logging enabled: %s", str(target_path))
        return logger

    def shutdown(self) -> None:
        """
        Fecha handlers do logger de forma segura.

        Correção importante:
        - "Logger shutdown completed" precisa ser emitido antes de fechar/remover
          o handler de arquivo, senão essa mensagem não entra no log.
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        logger.debug("Logger shutdown started")

        memory_handler = getattr(logger, self._MEMORY_HANDLER_ATTR, None)
        if isinstance(memory_handler, MemoryHandler):
            logger.debug("Closing memory handler")
            logger.removeHandler(memory_handler)
            try:
                memory_handler.close()
            except Exception:
                pass
            setattr(logger, self._MEMORY_HANDLER_ATTR, None)

        file_handler = getattr(logger, self._FILE_HANDLER_ATTR, None)
        if isinstance(file_handler, logging.Handler):
            logger.debug("Closing file handler")

        # Emite a mensagem final enquanto o handler de arquivo ainda existe.
        logger.debug("Logger shutdown completed")

        # Faz flush explícito para reduzir flakiness e garantir escrita no Windows.
        for handler in list(logger.handlers):
            try:
                handler.flush()
            except Exception:
                pass

        if isinstance(file_handler, logging.Handler):
            logger.removeHandler(file_handler)
            try:
                file_handler.close()
            except Exception:
                pass
            setattr(logger, self._FILE_HANDLER_ATTR, None)

        setattr(logger, self._BOOTSTRAPPED_ATTR, False)


# =============================================================================
# API pública
# =============================================================================


def get_logger(name: str = "") -> logging.Logger:
    """
    Retorna um logger pronto para uso.

    Uso:
    - get_logger() retorna o logger raiz do app
    - get_logger(__name__) retorna um logger filho
    """
    resolved_name = name or _root_logger_name
    return _get_silent_logger(resolved_name)


def create_bootstrapper(config: Optional[LogConfig] = None) -> LoggerBootstrapper:
    """
    Cria o bootstrapper do logger.
    """
    return LoggerBootstrapper(config=config or LogConfig())
