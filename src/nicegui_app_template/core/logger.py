# src/nicegui_app_template/core/logger.py
#
# Este módulo implementa o sistema de logging do template.
#
# Objetivos principais:
# - Permitir registrar logs desde o início da execução do aplicativo
# - Evitar perda de mensagens antes do arquivo de log existir
# - Centralizar toda a escrita de log em um único logger raiz
# - Ser seguro para Windows (evitar arquivos de log bloqueados)
# - Ser simples de usar em módulos comuns (get_logger)
#
# Conceitos importantes usados neste módulo:
# - Logger raiz: logger principal da aplicação, responsável por concentrar handlers
# - Logger filho: logger usado em módulos, que propaga mensagens para o logger raiz
# - Buffer em memória: mensagens ficam temporariamente na memória antes de irem para o arquivo
# - Idempotência: funções podem ser chamadas várias vezes sem criar efeitos colaterais
#
# Este código foi escrito de forma explícita e defensiva para facilitar
# entendimento e manutenção por desenvolvedores iniciantes.


from __future__ import annotations

# =============================================================================
# Imports - bibliotecas padrão do Python
# =============================================================================

import logging  # Sistema padrão de logging do Python
import sys  # Usado para direcionar logs de console para stdout
from dataclasses import dataclass  # Facilita criação de classes de configuração
from logging.handlers import MemoryHandler, RotatingFileHandler  # Handlers especiais de logging
from pathlib import Path  # Manipulação segura de caminhos (especialmente no Windows)
from typing import Optional  # Tipagem opcional para parâmetros


# =============================================================================
# Configuração - definição dos parâmetros de logging
# =============================================================================


@dataclass(frozen=True)
class LogConfig:
    """
    Configuração mínima de logging do template.

    Motivo:
    - Centralizar parâmetros de logging em um único lugar
    - Facilitar ajustes futuros (ex.: ler de arquivo TOML)
    - Evitar valores "espalhados" pelo código
    """

    name: str = "nicegui_app_template"  # Nome do logger raiz da aplicação
    level: int = logging.INFO  # Nível mínimo de log a ser registrado
    console: bool = True  # Define se logs devem aparecer no console

    buffer_capacity: int = 500  # Quantidade máxima de mensagens mantidas em memória

    file_path: Path = Path("logs/app.log")  # Caminho padrão do arquivo de log

    rotate_max_bytes: int = 5 * 1024 * 1024  # Tamanho máximo do arquivo antes da rotação (5 MB)
    rotate_backup_count: int = 3  # Quantidade de arquivos de backup mantidos


# =============================================================================
# Helpers internos - funções de apoio usadas apenas neste módulo
# =============================================================================


def _ensure_parent_dir(file_path: Path) -> None:
    """
    Garante que a pasta do arquivo de log exista.

    Motivo:
    - Evitar erro ao tentar criar o arquivo de log
    - Criar diretórios automaticamente melhora a experiência do usuário
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _make_console_formatter() -> logging.Formatter:
    """
    Cria o formatter usado no console.

    Motivo:
    - Logs de console devem ser curtos e fáceis de ler
    - Informações detalhadas ficam reservadas para o arquivo
    """
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _make_file_formatter() -> logging.Formatter:
    """
    Cria o formatter usado no arquivo de log.

    Motivo:
    - Arquivo de log é usado para diagnóstico
    - Inclui nome do arquivo e linha para facilitar rastreamento
    """
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    )


def _get_silent_logger(name: str) -> logging.Logger:
    """
    Retorna um logger com fallback silencioso.

    Regras adotadas:
    - Logger raiz do app não propaga mensagens
    - Loggers filhos propagam para o logger raiz
    - Um NullHandler é adicionado para evitar erros antes do bootstrap

    Motivo:
    - Permitir uso seguro de get_logger() em qualquer ponto do código
    - Evitar exceções caso o logging ainda não tenha sido inicializado
    """
    logger = logging.getLogger(name)

    # Apenas o logger raiz centraliza handlers
    if name == "nicegui_app_template":
        logger.propagate = False
    else:
        logger.propagate = True

    # Adiciona um handler silencioso se nenhum existir
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())

    # Nível NOTSET permite que o logger herde o nível efetivo do logger raiz
    logger.setLevel(logging.NOTSET)
    return logger


# =============================================================================
# Bootstrapper - controla o ciclo de vida do logging
# =============================================================================


class LoggerBootstrapper:
    """
    Gerencia o ciclo de vida do logger da aplicação.

    Fluxo esperado:
    1) bootstrap() - ativa console e buffer em memória
    2) enable_file_logging() - cria arquivo e grava mensagens pendentes
    3) shutdown() - fecha handlers e libera recursos

    Motivo:
    - Separar inicialização de logging da lógica da aplicação
    - Permitir ativação progressiva do logging
    """

    _MEMORY_HANDLER_ATTR = "_ng_template_memory_handler"  # Atributo interno para guardar o MemoryHandler
    _FILE_HANDLER_ATTR = "_ng_template_file_handler"  # Atributo interno para guardar o FileHandler
    _BOOTSTRAPPED_ATTR = "_ng_template_bootstrapped"  # Marca se o logger já foi inicializado

    def __init__(self, config: LogConfig):
        self._config = config  # Guarda a configuração usada pelo bootstrapper

    def bootstrap(self) -> logging.Logger:
        """
        Inicializa o logger raiz com console e buffer em memória.

        Motivo:
        - Permitir registrar logs antes do arquivo existir
        - Evitar perda de mensagens no início da aplicação
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        # Evita inicialização duplicada (idempotência)
        if getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            return logger

        logger.setLevel(self._config.level)

        # Configura handler de console, se habilitado
        if self._config.console:
            if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(_make_console_formatter())
                console_handler.setLevel(self._config.level)
                logger.addHandler(console_handler)

        # Configura buffer em memória para logs iniciais
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
        Ativa logging em arquivo e grava mensagens que estavam no buffer.

        Conceito de idempotência:
        - Chamar esta função várias vezes não deve criar múltiplos handlers
        - O estado final do logger deve ser sempre consistente
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        # Garante que o bootstrap ocorreu
        if not getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            self.bootstrap()

        # Se o handler de arquivo já existe, não faz nada
        if isinstance(getattr(logger, self._FILE_HANDLER_ATTR, None), logging.Handler):
            return logger

        target_path = file_path or self._config.file_path
        _ensure_parent_dir(target_path)

        # Cria handler de arquivo com rotação
        file_handler = RotatingFileHandler(
            filename=str(target_path),
            maxBytes=self._config.rotate_max_bytes,
            backupCount=self._config.rotate_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(_make_file_formatter())
        file_handler.setLevel(self._config.level)

        # Se existir buffer em memória, faz flush para o arquivo
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
        """
        Fecha handlers controlados pelo bootstrapper.

        Motivo:
        - Liberar arquivos no Windows
        - Evitar locks durante builds ou encerramento do app
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        # Remove e fecha buffer em memória
        memory_handler = getattr(logger, self._MEMORY_HANDLER_ATTR, None)
        if isinstance(memory_handler, MemoryHandler):
            logger.removeHandler(memory_handler)
            try:
                memory_handler.close()
            except Exception:
                pass
            setattr(logger, self._MEMORY_HANDLER_ATTR, None)

        # Remove e fecha handler de arquivo
        file_handler = getattr(logger, self._FILE_HANDLER_ATTR, None)
        if isinstance(file_handler, logging.Handler):
            logger.removeHandler(file_handler)
            try:
                file_handler.close()
            except Exception:
                pass
            setattr(logger, self._FILE_HANDLER_ATTR, None)

        setattr(logger, self._BOOTSTRAPPED_ATTR, False)


# =============================================================================
# API pública - funções expostas para o restante da aplicação
# =============================================================================


def get_logger(name: str = "nicegui_app_template") -> logging.Logger:
    """
    Retorna um logger pronto para uso.

    Uso recomendado:
    - get_logger() para obter o logger raiz
    - get_logger(__name__) dentro de módulos

    Motivo:
    - Padronizar o acesso ao logging
    - Evitar criação manual de loggers espalhados pelo código
    """
    return _get_silent_logger(name or "nicegui_app_template")


def create_bootstrapper(config: Optional[LogConfig] = None) -> LoggerBootstrapper:
    """
    Cria uma instância do LoggerBootstrapper.

    Motivo:
    - Centralizar a criação do bootstrapper
    - Facilitar futuras extensões (ex.: integração com settings.toml)
    """
    return LoggerBootstrapper(config=config or LogConfig())
