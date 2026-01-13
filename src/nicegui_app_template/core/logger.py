# src/nicegui_app_template/core/logger.py
#
from __future__ import annotations

# -----------------------------------------------------------------------------
# Logger da Aplicação
# -----------------------------------------------------------------------------
# Este módulo implementa o sistema de logging do template.
#
# Objetivos principais:
# - Registrar logs desde o início da execução do aplicativo (early logging).
# - Evitar perda de logs antes do arquivo de log estar disponível.
# - Centralizar o logging em um único logger raiz da aplicação.
# - Garantir segurança no Windows, evitando bloqueios de arquivos de log.
#
# Observações importantes:
# - O módulo logging do Python é global e mantém loggers em cache por nome.
# - Por esse motivo, este módulo evita reconfigurar loggers já inicializados.
# - A escrita em arquivo ocorre exclusivamente após a chamada de
#   enable_file_logging().
#
# Nota sobre logs internos do próprio logger:
# - Para que mensagens internas (logger.debug) sejam registradas corretamente,
#   handlers (MemoryHandler, console ou arquivo) precisam estar anexados antes
#   da emissão desses logs.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Imports - bibliotecas padrão do Python
# -----------------------------------------------------------------------------
import logging
import sys
from dataclasses import dataclass
from logging.handlers import MemoryHandler, RotatingFileHandler
from pathlib import Path
from typing import Final, Optional

# -----------------------------------------------------------------------------
# Estado interno do módulo - controle do nome do logger raiz
# -----------------------------------------------------------------------------

_DEFAULT_ROOT_LOGGER_NAME = "nicegui_app_template"
_root_logger_name: str = _DEFAULT_ROOT_LOGGER_NAME


def _set_root_logger_name(name: str) -> None:
    """Define o nome do logger raiz da aplicação.

    Esta função centraliza a definição do nome do logger raiz utilizado
    pelo aplicativo, garantindo consistência na hierarquia de loggers.

    Args:
        name: Nome lógico do logger raiz.

    Notes:
        - O nome do logger é global dentro do processo Python.
        - Alterações após o bootstrap não são recomendadas, pois o módulo
          logging mantém loggers em cache por nome.
        - Esta função permite que LogConfig(name="...") funcione corretamente
          e que loggers filhos saibam para onde propagar mensagens.
    """
    global _root_logger_name
    _root_logger_name = name or _DEFAULT_ROOT_LOGGER_NAME


# -----------------------------------------------------------------------------
# Helpers internos - resolução de nível (texto -> logging int)
# -----------------------------------------------------------------------------
# Esta conversão é um detalhe específico do domínio de logging e tende a ser
# reutilizada por adaptadores (ex.: logger_resolver) sem exigir que o logger
# conheça AppState, settings ou UI.

DEFAULT_LOG_LEVEL: Final[int] = logging.INFO

_LOG_LEVEL_MAP: Final[dict[str, int]] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,  # Alias comum aceito para compatibilidade.
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def resolve_log_level(level: str, *, default: int = DEFAULT_LOG_LEVEL) -> int:
    """Resolve um nível textual para a constante do módulo logging.

    Args:
        level: Nível em formato humano (ex.: "INFO", "debug", " warn ").
        default: Valor técnico utilizado como fallback se o texto for inválido.

    Returns:
        Constante do módulo logging correspondente ao nível informado.

    Notes:
        - Esta função é pura e determinística.
        - Não lança exceções; sempre retorna um int válido para o logging.
    """
    normalized = (level or "").upper().strip()
    return _LOG_LEVEL_MAP.get(normalized, default)


# -----------------------------------------------------------------------------
# Configuração - parâmetros de logging
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class LogConfig:
    """Configuração do sistema de logging do template.

    Esta classe centraliza os parâmetros técnicos do logger já normalizados.

    Observação:
        - O template mantém a conversão State/Settings -> LogConfig fora do logger
          (ex.: logger_resolver). Entretanto, este módulo pode expor helpers
          específicos do domínio de logging (por exemplo, resolução de nível).

    Motivos:
        - Centralizar parâmetros de logging.
        - Facilitar manutenção e evolução futura do sistema de logs.

    Attributes:
        name: Nome do logger raiz da aplicação.
        level: Nível de logging (constante do módulo logging).
        console: Indica se os logs devem ser enviados para stdout.
        buffer_capacity: Capacidade do buffer em memória para logs iniciais.
        file_path: Caminho do arquivo de log.
        rotate_max_bytes: Tamanho máximo do arquivo antes da rotação.
        rotate_backup_count: Quantidade de arquivos de backup mantidos.
    """

    name: str = _DEFAULT_ROOT_LOGGER_NAME
    level: int = logging.INFO
    console: bool = True

    buffer_capacity: int = 500

    file_path: Path = Path("logs/app.log")

    rotate_max_bytes: int = 5 * 1024 * 1024
    rotate_backup_count: int = 3


# -----------------------------------------------------------------------------
# Helpers internos - funções utilitárias do módulo
# -----------------------------------------------------------------------------


def _ensure_parent_dir(file_path: Path) -> None:
    """Garante que o diretório pai do arquivo de log exista.

    Esta função cria o diretório pai do arquivo de log caso ele ainda
    não exista, evitando falhas no momento da criação ou rotação do
    arquivo de log.

    Args:
        file_path: Caminho completo do arquivo de log.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _make_console_formatter() -> logging.Formatter:
    """Cria o formatter utilizado para logs em console."""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _make_file_formatter() -> logging.Formatter:
    """Cria o formatter utilizado para logs em arquivo."""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    )


def _get_silent_logger(name: str) -> logging.Logger:
    """Retorna um logger seguro para uso em qualquer ponto do aplicativo.

    Esta função garante que chamadas de logging possam ocorrer antes do
    bootstrap do sistema de logs, evitando warnings e comportamentos
    inesperados do módulo logging.

    Args:
        name: Nome do logger solicitado.

    Returns:
        Instância de logging.Logger configurada de forma segura, utilizando
        NullHandler quando necessário.

    Notes:
        - O logger raiz do aplicativo não propaga mensagens para o root logger
          global do Python.
        - Loggers filhos propagam mensagens para o logger raiz da aplicação.
        - Antes do bootstrap, um NullHandler é adicionado para evitar warnings.
        - Após o bootstrap, esta função não altera handlers nem níveis já
          configurados.
    """
    logger = logging.getLogger(name)

    # Expressa a regra de hierarquia em uma única atribuição, sem alterar a lógica:
    # - Raiz do app: não propaga para o root logger do Python
    # - Filhos: propagam para o logger raiz do app
    logger.propagate = name != _root_logger_name

    bootstrapped = bool(getattr(logger, LoggerBootstrapper._BOOTSTRAPPED_ATTR, False))
    if not bootstrapped:
        if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
            logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.NOTSET)

    return logger


# -----------------------------------------------------------------------------
# Bootstrapper - gerencia o ciclo de vida do logger
# -----------------------------------------------------------------------------


class LoggerBootstrapper:
    """Gerencia o ciclo de vida do logger da aplicação.

    Esta classe coordena a inicialização, configuração e finalização do
    sistema de logging, garantindo suporte a early logging e escrita
    segura em arquivo.

    Fluxo esperado:
        1. bootstrap() -> inicializa buffer em memória (e console opcional).
        2. update_config() -> aplica a configuração final após settings/state.
        3. enable_file_logging() -> ativa escrita em arquivo e realiza flush do buffer.
        4. shutdown() -> encerra handlers gerenciados de forma segura.
    """

    _MEMORY_HANDLER_ATTR = "_ng_template_memory_handler"
    _CONSOLE_HANDLER_ATTR = "_ng_template_console_handler"
    _FILE_HANDLER_ATTR = "_ng_template_file_handler"
    _BOOTSTRAPPED_ATTR = "_ng_template_bootstrapped"

    def __init__(self, config: LogConfig):
        """Inicializa o bootstrapper com uma configuração base.

        Args:
            config: Configuração inicial do logger.
        """
        self._config = config
        _set_root_logger_name(self._config.name)

    def bootstrap(self) -> logging.Logger:
        """Inicializa o logger com buffer em memória e, opcionalmente, console.

        Esta fase prepara o sistema de logging para capturar mensagens desde o
        início da execução do aplicativo, antes que a escrita em arquivo esteja
        disponível.

        Returns:
            Logger raiz configurado para early logging.

        Notes:
            - Esta fase não escreve em arquivo.
            - O objetivo é capturar logs iniciais com segurança.
            - Para que logs internos em nível DEBUG sejam registrados, ao menos
              um handler deve ser anexado antes da emissão de logger.debug(...).
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        if getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            logger.debug("Logger bootstrap skipped - already initialized")
            return logger

        logger.setLevel(self._config.level)

        # Anexa o buffer antes de qualquer mensagem interna em DEBUG.
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
            # Evita duplicar StreamHandlers e mantém o handler gerenciado registrado.
            console_handler = getattr(logger, self._CONSOLE_HANDLER_ATTR, None)
            if not isinstance(console_handler, logging.StreamHandler):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(_make_console_formatter())
                console_handler.setLevel(self._config.level)
                logger.addHandler(console_handler)
                setattr(logger, self._CONSOLE_HANDLER_ATTR, console_handler)
                logger.debug("Console handler attached")

        setattr(logger, self._BOOTSTRAPPED_ATTR, True)
        logger.debug("Logger bootstrap completed")
        return logger

    def update_config(self, config: LogConfig) -> logging.Logger:
        """Atualiza a configuração do logger após o bootstrap.

        Args:
            config: Configuração final a ser aplicada.

        Returns:
            Logger raiz atualizado.

        Notes:
            - O nome do logger não pode ser alterado após o bootstrap.
            - Esta função não ativa escrita em arquivo.
            - Esta função não cria o buffer nem marca o logger como bootstrapped.
              O app deve chamar bootstrap() antes do ciclo normal de execução.
        """
        # O módulo logging é cacheado por nome; mudar o nome após bootstrap tende
        # a gerar comportamento inesperado. Aqui mantemos o nome original.
        if config.name != self._config.name:
            config = LogConfig(
                name=self._config.name,
                level=config.level,
                console=config.console,
                buffer_capacity=config.buffer_capacity,
                file_path=config.file_path,
                rotate_max_bytes=config.rotate_max_bytes,
                rotate_backup_count=config.rotate_backup_count,
            )

        self._config = config
        _set_root_logger_name(self._config.name)

        logger = logging.getLogger(self._config.name)
        logger.propagate = False
        logger.setLevel(self._config.level)

        # Se ainda não houve bootstrap, evitamos anexar handlers aqui para manter
        # o lifecycle previsível (handlers são responsabilidade do bootstrap()).
        if not getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            return logger

        memory_handler = getattr(logger, self._MEMORY_HANDLER_ATTR, None)
        if isinstance(memory_handler, MemoryHandler):
            memory_handler.setLevel(self._config.level)

        # Aplica a configuração de console de forma consistente e mínima.
        console_handler = getattr(logger, self._CONSOLE_HANDLER_ATTR, None)
        has_console = isinstance(console_handler, logging.StreamHandler)

        if self._config.console and not has_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(_make_console_formatter())
            console_handler.setLevel(self._config.level)
            logger.addHandler(console_handler)
            setattr(logger, self._CONSOLE_HANDLER_ATTR, console_handler)
            logger.debug("Console handler attached (reconfigured)")

        if not self._config.console and has_console:
            if isinstance(console_handler, logging.StreamHandler):
                handler: logging.Handler = (
                    console_handler  # Narrowing explícito para o type checker.
                )
                try:
                    logger.removeHandler(handler)
                except Exception:
                    pass
                try:
                    handler.close()
                except Exception:
                    pass

            setattr(logger, self._CONSOLE_HANDLER_ATTR, None)
            logger.debug("Console handler detached (reconfigured)")

        # Mantém os handlers gerenciados alinhados ao nível final.
        for handler in list(logger.handlers):
            if isinstance(
                handler, (MemoryHandler, RotatingFileHandler, logging.StreamHandler)
            ):
                handler.setLevel(self._config.level)

        return logger

    def enable_file_logging(
        self, *, file_path: Optional[Path] = None
    ) -> logging.Logger:
        """Ativa a escrita em arquivo e descarrega o buffer em memória.

        Este método cria o handler de arquivo, conecta-o ao buffer em memória
        e realiza o flush dos logs acumulados durante a fase de early logging.

        Args:
            file_path: Caminho do arquivo de log. Quando não informado, utiliza
                o caminho definido na configuração atual do logger.

        Returns:
            Logger raiz com o handler de arquivo ativo.

        Notes:
            - O método é idempotente: múltiplas chamadas não duplicam handlers.
            - Após a ativação do arquivo, os logs passam a ser gravados
              diretamente em disco.
            - Este método é defensivo: se o logger ainda não foi bootstrapped,
              ele executa bootstrap() antes de habilitar arquivo.
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        if not getattr(logger, self._BOOTSTRAPPED_ATTR, False):
            self.bootstrap()

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
        logger.debug('File logging enabled: "%s"', str(target_path.resolve()))
        return logger

    def shutdown(self) -> None:
        """Finaliza o logger e fecha os handlers gerenciados de forma segura.

        Este método encerra o ciclo de vida do logger, garantindo que todos
        os handlers gerenciados sejam corretamente flushados e fechados.

        Notes:
            - Mensagens finais de log (por exemplo, indicando conclusão do shutdown)
              devem ser emitidas antes da remoção ou fechamento do handler de arquivo.
              Caso contrário, essas mensagens não serão persistidas no log.
            - Para reduzir efeitos colaterais, este método fecha somente handlers
              gerenciados por este bootstrapper.
        """
        logger = logging.getLogger(self._config.name)
        logger.propagate = False

        logger.debug("Logger shutdown started")
        logger.debug("Logger shutdown completed")

        # Captura handlers gerenciados para evitar fechar handlers externos.
        memory_handler = getattr(logger, self._MEMORY_HANDLER_ATTR, None)
        console_handler = getattr(logger, self._CONSOLE_HANDLER_ATTR, None)
        file_handler = getattr(logger, self._FILE_HANDLER_ATTR, None)

        # Flush dos handlers gerenciados enquanto ainda estão anexados.
        for handler in (memory_handler, console_handler, file_handler):
            if isinstance(handler, logging.Handler):
                try:
                    handler.flush()
                except Exception:
                    pass

        # Remove e fecha buffer primeiro.
        if isinstance(memory_handler, MemoryHandler):
            try:
                logger.removeHandler(memory_handler)
            except Exception:
                pass
            try:
                memory_handler.close()
            except Exception:
                pass
            setattr(logger, self._MEMORY_HANDLER_ATTR, None)

        # Remove e fecha console (se criado por nós).
        if isinstance(console_handler, logging.StreamHandler):
            try:
                logger.removeHandler(console_handler)
            except Exception:
                pass
            try:
                console_handler.close()
            except Exception:
                pass
            setattr(logger, self._CONSOLE_HANDLER_ATTR, None)

        # Remove e fecha arquivo por último (evita perda das mensagens finais).
        if isinstance(file_handler, logging.Handler):
            try:
                logger.removeHandler(file_handler)
            except Exception:
                pass
            try:
                file_handler.close()
            except Exception:
                pass
            setattr(logger, self._FILE_HANDLER_ATTR, None)

        setattr(logger, self._BOOTSTRAPPED_ATTR, False)


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------


def get_logger(name: str = "") -> logging.Logger:
    """Retorna um logger pronto para uso.

    Uso:
        - get_logger() retorna o logger raiz do aplicativo.
        - get_logger(__name__) retorna um logger filho associado ao módulo chamador.

    Args:
        name: Nome do logger desejado. Quando vazio, retorna o logger raiz.

    Returns:
        Instância de logging.Logger configurada ou silenciosa, conforme o estado
        atual do bootstrap do logger.
    """
    resolved_name = name or _root_logger_name
    return _get_silent_logger(resolved_name)


def create_bootstrapper(config: Optional[LogConfig] = None) -> LoggerBootstrapper:
    """Cria uma instância do LoggerBootstrapper.

    Args:
        config: Configuração inicial do logger.

    Returns:
        LoggerBootstrapper inicializado.
    """
    return LoggerBootstrapper(config=config or LogConfig())
