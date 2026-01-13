# src/nicegui_app_template/core/settings.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Settings (TOML) + Integração com Estado
# -----------------------------------------------------------------------------
# Este módulo é responsável por:
# - Ler settings.toml e aplicar os valores no AppState (estado em runtime)
# - Persistir o AppState (somente a parte configurável) novamente em settings.toml
#
# Decisões de arquitetura:
# - O AppState permanece "puro": sem parsing, sem I/O e sem validação pesada
# - Este módulo é o boundary de I/O e conversão (str <-> Path, casting, defaults)
# - Validações são "leves" e orientadas a fallback para manter robustez do app
#
# Compatibilidade:
# - Python 3.13+
# - Round-trip com tomlkit (preserva comentários, ordem e estilo do arquivo)
#
# Observação:
# - A persistência utiliza round-trip via tomlkit: o arquivo TOML existente é
#   editado in-place, atualizando apenas chaves conhecidas e preservando
#   comentários, ordem e estilo originais

import logging  # Logging é injetável e opcional; o módulo não deve depender do bootstrap do logger.
import os  # Permite override de raiz do app via variável de ambiente para empacotamento/atalhos.
from pathlib import (
    Path,
)  # Path é o tipo padrão para caminhos, evitando strings frágeis em múltiplos SOs.
from typing import (
    Any,
    Mapping,
    Optional,
)  # Tipos explícitos facilitam manutenção e testes.

import tomlkit  # tomlkit permite round-trip de TOML preservando comentários e formatação.
from tomlkit.items import (
    Table,
)  # Table representa tabelas TOML internas (usado para criar/garantir hierarquia).
from tomlkit.toml_document import (
    TOMLDocument,
)  # TOMLDocument é a AST mutável do arquivo TOML, preservando estilo.

from .helpers import parse_size_to_bytes
from .state import (
    AppState,
    get_app_state,
)  # O módulo aplica configurações diretamente no estado central.

# -----------------------------------------------------------------------------
# Logger injetável com fallback silencioso
# -----------------------------------------------------------------------------
# O módulo não deve falhar nem emitir prints se o logger ainda não estiver pronto.
# Por isso, aceitamos um logger opcional e usamos um fallback silencioso.


class _NullLogger(logging.Logger):
    """
    Logger nulo para evitar prints e manter o módulo desacoplado.

    Motivo:
    - Settings pode ser carregado antes do bootstrap do logger da aplicação
    - O módulo não deve causar warnings nem efeitos colaterais
    """

    def __init__(self) -> None:
        super().__init__(name="null")
        self.addHandler(logging.NullHandler())


def _get_logger(logger: Optional[logging.Logger]) -> logging.Logger:
    # Mantém API simples: quem não quiser logger passa None, e o módulo segue silencioso.
    return logger if logger is not None else _NullLogger()


# -----------------------------------------------------------------------------
# Helpers: resolução de caminhos e utilidades de parsing
# -----------------------------------------------------------------------------


def _resolve_app_root() -> Path:
    """
    Resolve a raiz do aplicativo.

    Motivo:
    - Em execução "normal", Path.cwd() é suficiente
    - Em empacotamento/atalhos, pode ser necessário apontar para outra pasta
    """
    override = os.getenv("APP_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd().resolve()


def default_settings_path() -> Path:
    """
    Retorna o caminho padrão do arquivo settings.toml.

    Motivo:
    - Centralizar a convenção do projeto
    - Evitar strings repetidas espalhadas no código
    """
    return _resolve_app_root() / "settings.toml"


def _deep_get(mapping: Mapping[str, Any], path: str, default: Any) -> Any:
    """
    Busca um valor por caminho (ex.: 'app.window.width') com fallback.

    Motivo:
    - Evitar blocos try/except em cada leitura
    - Manter comportamento consistente: se faltar, usa default
    """
    cursor: Any = mapping
    for part in path.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return default
        cursor = cursor[part]
    return cursor


def _ensure_parent_dir(file_path: Path) -> None:
    # Garantir diretório evita falha ao gravar settings.toml em primeiro uso.
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_write_text(file_path: Path, content: str) -> None:
    """
    Escrita atômica para reduzir risco de corrupção do arquivo.

    Motivo:
    - Em caso de crash/queda, é melhor manter o último arquivo íntegro
    - A estratégia .tmp + replace costuma ser suficiente e simples
    """
    _ensure_parent_dir(file_path)
    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(file_path)


def _normalize_path_for_toml(path: Path) -> str:
    """
    Normaliza caminhos para persistência em TOML.

    Motivo:
    - Evitar backslashes (Windows) no arquivo, reduzindo escaping e ruído em diffs
    - Manter compatibilidade: caminhos com "/" funcionam no Windows e Unix
    """
    return str(path).replace("\\", "/")


# -----------------------------------------------------------------------------
# Round-trip TOML (tomlkit)
# -----------------------------------------------------------------------------
# tomlkit trabalha com uma AST mutável (TOMLDocument) e permite:
# - manter comentários
# - manter ordem e espaçamento
# - atualizar apenas chaves específicas sem "regerar" o arquivo


def _parse_toml_document(text: str) -> TOMLDocument:
    """
    Faz parse do TOML preservando comentários/ordem/estilo.

    Motivo:
    - O tomlkit retorna TOMLDocument que contém a estrutura + metadados de formatação
    """
    return tomlkit.parse(text)


def _ensure_toml_table(root: TOMLDocument | Table, key: str) -> Table:
    """
    Garante que a chave exista como tabela TOML.

    Motivo:
    - Arquivo pode estar incompleto (primeiro uso) ou editado manualmente
    - Criamos somente o necessário, preservando o restante do documento
    """
    current = root.get(key)
    if isinstance(current, Table):
        return current

    # Se existir com tipo errado, substituímos para evitar falha ao salvar e restaurar a hierarquia mínima.
    table = tomlkit.table()
    root[key] = table
    return table


def _set_toml_value_by_path(
    document: TOMLDocument, dotted_path: str, value: Any
) -> None:
    """
    Define um valor em caminho pontilhado (ex.: 'app.log.level').

    Motivo:
    - Centraliza escrita no documento e evita duplicação de lógica
    - Garante criação incremental das tabelas sem apagar comentários fora do trecho editado
    """
    parts = dotted_path.split(".")
    if not parts:
        return

    cursor: TOMLDocument | Table = document
    for part in parts[:-1]:
        cursor = _ensure_toml_table(cursor, part)

    cursor[parts[-1]] = value


def _apply_state_to_document(document: TOMLDocument, state: AppState) -> None:
    """
    Atualiza o TOMLDocument com os valores do estado.

    Motivo:
    - Preservar comentários e chaves não gerenciadas pelo template
    - Atualizamos somente o conjunto de chaves conhecidas
    """
    _set_toml_value_by_path(document, "app.name", state.meta.name)
    _set_toml_value_by_path(document, "app.version", state.meta.version)
    _set_toml_value_by_path(document, "app.language", state.meta.language)
    _set_toml_value_by_path(document, "app.first_run", state.meta.first_run)
    _set_toml_value_by_path(document, "app.native_mode", state.meta.native_mode)
    _set_toml_value_by_path(document, "app.port", state.meta.port)

    _set_toml_value_by_path(document, "app.window.x", state.window.x)
    _set_toml_value_by_path(document, "app.window.y", state.window.y)
    _set_toml_value_by_path(document, "app.window.width", state.window.width)
    _set_toml_value_by_path(document, "app.window.height", state.window.height)
    _set_toml_value_by_path(document, "app.window.maximized", state.window.maximized)
    _set_toml_value_by_path(document, "app.window.fullscreen", state.window.fullscreen)
    _set_toml_value_by_path(document, "app.window.monitor", state.window.monitor)
    _set_toml_value_by_path(
        document, "app.window.storage_key", state.window.storage_key
    )

    _set_toml_value_by_path(document, "app.ui.theme", state.ui.theme)
    _set_toml_value_by_path(document, "app.ui.font_scale", state.ui.font_scale)
    _set_toml_value_by_path(document, "app.ui.dense_mode", state.ui.dense_mode)
    _set_toml_value_by_path(document, "app.ui.accent_color", state.ui.accent_color)

    # Persistimos como string para interoperabilidade e facilidade de edição.
    _set_toml_value_by_path(
        document,
        "app.log.path",
        _normalize_path_for_toml(state.log.path),
    )
    _set_toml_value_by_path(document, "app.log.level", state.log.level)
    _set_toml_value_by_path(document, "app.log.console", state.log.console)
    _set_toml_value_by_path(
        document,
        "app.log.buffer_capacity",
        state.log.buffer_capacity,
    )
    _set_toml_value_by_path(document, "app.log.rotation", state.log.rotation)
    _set_toml_value_by_path(document, "app.log.retention", state.log.retention)

    _set_toml_value_by_path(
        document,
        "app.behavior.auto_save",
        state.behavior.auto_save,
    )


def _build_minimal_document_from_state(state: AppState) -> TOMLDocument:
    """
    Cria um documento TOML mínimo baseado no estado.

    Motivo:
    - Permitir persistência no primeiro run mesmo sem arquivo existente
    - Gerar estrutura mínima e previsível do template
    """
    document = tomlkit.document()
    _apply_state_to_document(document, state)
    return document


# -----------------------------------------------------------------------------
# Aplicação ao Estado: TOML -> AppState
# -----------------------------------------------------------------------------
# Nesta etapa, aplicamos:
# - casting leve (int/bool/float/str)
# - defaults do próprio estado
# - validações leves com fallback
#
# Motivo:
# - O estado não deve conter validações nem parsing
# - Evitar travar o app por configuração inválida
# - Garantir consistência mínima dos valores para consumo por UI e logger


def apply_settings_to_state(state: AppState, raw: Mapping[str, Any]) -> None:
    """
    Aplica o conteúdo do TOML ao estado em memória.

    Motivo:
    - Centralizar defaults e casting
    - Evitar que módulos consumidores façam parsing manual
    """
    # -------------------------
    # App (meta)
    # -------------------------
    state.meta.name = str(_deep_get(raw, "app.name", state.meta.name))
    state.meta.version = str(_deep_get(raw, "app.version", state.meta.version))
    state.meta.language = str(_deep_get(raw, "app.language", state.meta.language))
    state.meta.first_run = bool(_deep_get(raw, "app.first_run", state.meta.first_run))
    state.meta.native_mode = bool(
        _deep_get(raw, "app.native_mode", state.meta.native_mode)
    )
    state.meta.port = int(_deep_get(raw, "app.port", state.meta.port))

    # Validação leve para porta; fallback mantém o app executável.
    if state.meta.port < 1 or state.meta.port > 65535:
        state.meta.port = 8080

    # -------------------------
    # Window
    # -------------------------
    state.window.x = int(_deep_get(raw, "app.window.x", state.window.x))
    state.window.y = int(_deep_get(raw, "app.window.y", state.window.y))
    state.window.width = int(_deep_get(raw, "app.window.width", state.window.width))
    state.window.height = int(_deep_get(raw, "app.window.height", state.window.height))
    state.window.maximized = bool(
        _deep_get(raw, "app.window.maximized", state.window.maximized)
    )
    state.window.fullscreen = bool(
        _deep_get(raw, "app.window.fullscreen", state.window.fullscreen)
    )
    state.window.monitor = int(
        _deep_get(raw, "app.window.monitor", state.window.monitor)
    )
    state.window.storage_key = str(
        _deep_get(raw, "app.window.storage_key", state.window.storage_key)
    )

    # Tamanhos mínimos evitam UI inutilizável; valores podem ser ajustados depois.
    if state.window.width < 400:
        state.window.width = 800
    if state.window.height < 300:
        state.window.height = 600

    # -------------------------
    # UI
    # -------------------------
    state.ui.theme = str(_deep_get(raw, "app.ui.theme", state.ui.theme))
    state.ui.font_scale = float(
        _deep_get(raw, "app.ui.font_scale", state.ui.font_scale)
    )
    state.ui.dense_mode = bool(_deep_get(raw, "app.ui.dense_mode", state.ui.dense_mode))
    state.ui.accent_color = str(
        _deep_get(raw, "app.ui.accent_color", state.ui.accent_color)
    )

    # -------------------------
    # Logging
    # -------------------------
    # path entra como string no TOML e vira Path no estado (boundary correto).
    log_path = str(_deep_get(raw, "app.log.path", str(state.log.path)))
    state.log.path = Path(log_path)

    # level é mantido como string para facilitar UI e settings.
    state.log.level = (
        str(_deep_get(raw, "app.log.level", state.log.level)).upper().strip()
    )

    # console é booleano simples.
    state.log.console = bool(_deep_get(raw, "app.log.console", state.log.console))

    # buffer_capacity define o tamanho do MemoryHandler no bootstrap do logger.
    state.log.buffer_capacity = int(
        _deep_get(raw, "app.log.buffer_capacity", state.log.buffer_capacity)
    )

    # rotation/retention são strings/ints amigáveis para humanos e mapeadas em outro módulo.
    state.log.rotation = str(
        _deep_get(raw, "app.log.rotation", state.log.rotation)
    ).strip()
    state.log.retention = int(_deep_get(raw, "app.log.retention", state.log.retention))

    # Validações leves: preferimos fallback a erro duro.
    allowed_levels = {"CRITICAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"}
    if state.log.level not in allowed_levels:
        state.log.level = "INFO"

    if parse_size_to_bytes(state.log.rotation) is None:
        state.log.rotation = "5 MB"

    if state.log.retention < 1:
        state.log.retention = 3

    if state.log.buffer_capacity < 50:
        state.log.buffer_capacity = 50

    # -------------------------
    # Behavior
    # -------------------------
    state.behavior.auto_save = bool(
        _deep_get(raw, "app.behavior.auto_save", state.behavior.auto_save)
    )


# -----------------------------------------------------------------------------
# API pública do módulo
# -----------------------------------------------------------------------------
# - load_settings(...)-> bool
# - save_settings(...)-> bool
#
# Implementação: round-trip via tomlkit (parse → update de chaves conhecidas → dumps).


def load_settings(
    *,
    settings_path: Optional[Path] = None,
    state: Optional[AppState] = None,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    Carrega settings.toml e aplica no estado.

    Retorna:
    - True em sucesso
    - False em falha (detalhes em state.last_error)

    Motivo:
    - Em bootstrap, é comum seguir com defaults caso settings falhe
    - O app pode exibir o erro na UI sem interromper o processo
    """
    log = _get_logger(logger)
    st = state if state is not None else get_app_state()
    path = (settings_path or default_settings_path()).expanduser().resolve()

    # Guardar o path efetivo ajuda suporte e diagnósticos.
    st.settings_file_path = path
    st.last_error = None
    st.last_load_ok = False

    if not path.exists():
        # Não criamos automaticamente para evidenciar problemas de deploy.
        st.last_error = f"Settings file not found: {path}"
        log.error(st.last_error)
        return False

    try:
        document = _parse_toml_document(path.read_text(encoding="utf-8"))
        apply_settings_to_state(st, document)
        st.last_load_ok = True
        log.info('Settings parsed and applied to AppState: path="%s"', str(path))
        return True
    except Exception as exc:
        st.last_error = f"Failed to load settings: {exc}"
        log.exception("Failed to load settings")
        return False


def save_settings(
    *,
    settings_path: Optional[Path] = None,
    state: Optional[AppState] = None,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """
    Persiste o estado atual em settings.toml.

    Retorna:
    - True em sucesso
    - False em falha (detalhes em state.last_error)

    Motivo:
    - Escrita atômica reduz risco de corrupção
    - Falhas não devem derrubar a UI; elas devem ser reportadas
    """
    log = _get_logger(logger)
    st = state if state is not None else get_app_state()

    # O path pode vir explicitamente, do último load, ou do default do projeto.
    path = (
        (settings_path or st.settings_file_path or default_settings_path())
        .expanduser()
        .resolve()
    )

    st.settings_file_path = path
    st.last_error = None
    st.last_save_ok = False

    try:
        if path.exists():
            # Parse do arquivo existente preserva comentários e estilo.
            document = _parse_toml_document(path.read_text(encoding="utf-8"))
        else:
            # Primeiro save: não há comentários a preservar; criamos estrutura mínima.
            document = _build_minimal_document_from_state(st)

        # Atualiza somente chaves conhecidas, preservando chaves extras e comentários.
        _apply_state_to_document(document, st)

        content = tomlkit.dumps(document)
        _atomic_write_text(path, content)

        st.last_save_ok = True
        log.info("Settings saved successfully")
        return True
    except Exception as exc:
        st.last_error = f"Failed to save settings: {exc}"
        log.exception("Failed to save settings")
        return False
