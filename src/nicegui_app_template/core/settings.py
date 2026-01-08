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
# - Python 3.11+: usa tomllib (stdlib)
# - Python 3.10: requer tomli como dependência opcional (somente para leitura)
#
# Observação:
# - Persistência é feita via serialização TOML mínima, sem dependências extras
# - Se você quiser preservar comentários/ordem do TOML, considere tomlkit no futuro

import logging  # Logging é injetável e opcional; o módulo não deve depender do bootstrap do logger.
import os  # Permite override de raiz do app via variável de ambiente para empacotamento/atalhos.
import re  # Usado para parsing leve de tamanhos como "5 MB" para bytes.
from pathlib import (
    Path,
)  # Path é o tipo padrão para caminhos, evitando strings frágeis em múltiplos SOs.
from typing import (
    Any,
    Mapping,
    Optional,
)  # Tipos explícitos facilitam manutenção e testes.

from .state import (
    AppState,
    get_app_state,
)  # O módulo aplica configurações diretamente no estado central.


# -----------------------------------------------------------------------------
# Compat TOML (Python 3.10+)
# -----------------------------------------------------------------------------
# A leitura TOML precisa funcionar em 3.10 (tomli) e 3.11+ (tomllib).
# A escrita TOML será feita por um serializador mínimo próprio (sem dependências).

try:
    import tomllib  # type: ignore  # Python 3.11+
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


def _loads_toml(text: str) -> dict[str, Any]:
    """
    Faz parse do TOML de forma compatível com Python 3.10+.

    Estratégia:
    - Preferir tomllib quando disponível (stdlib)
    - Em 3.10, utilizar tomli (dependência opcional)
    """
    if tomllib is not None:
        return tomllib.loads(text)  # type: ignore[no-any-return]

    # Em Python 3.10, exigimos tomli apenas se o app realmente precisar ler TOML.
    try:
        import tomli  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Python 3.10 requires 'tomli' to parse TOML. Install it with: pip install tomli"
        ) from exc

    return tomli.loads(text)  # type: ignore[no-any-return]


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


def _project_root_from_env() -> Path:
    """
    Resolve uma raiz de projeto simples.

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
    return _project_root_from_env() / "settings.toml"


def _deep_get(mapping: Mapping[str, Any], path: str, default: Any) -> Any:
    """
    Busca um valor por caminho (ex.: 'app.window.width') com fallback.

    Motivo:
    - Evitar blocos try/except em cada leitura
    - Manter comportamento consistente: se faltar, usa default
    """
    cur: Any = mapping
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _parse_size_to_bytes(value: str) -> Optional[int]:
    """
    Converte expressões como '5 MB' em bytes.

    Motivo:
    - RotatingFileHandler trabalha com maxBytes
    - O TOML é mais amigável para humanos com unidades
    """
    raw = value.strip().upper()
    match = re.match(r"^(\d+)\s*(B|KB|MB|GB)$", raw)
    if not match:
        return None

    n = int(match.group(1))
    unit = match.group(2)

    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    return n * multipliers[unit]


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


# -----------------------------------------------------------------------------
# Serialização TOML mínima
# -----------------------------------------------------------------------------
# Este serializador cobre apenas o necessário para o template:
# - tabelas aninhadas [a] e [a.b]
# - tipos escalares: str, int, float, bool
# - Path é convertido para string
#
# Motivo:
# - Evitar dependências extras para o template base
# - Manter arquivo gerado legível e previsível
#
# Limitação:
# - Não preserva comentários nem ordem original
# - Não suporta arrays e tipos especiais (datas etc.)


def _to_toml_string(data: Mapping[str, Any]) -> str:
    """
    Serializa um dict para TOML com suporte mínimo.

    Motivo:
    - Persistir settings sem depender de bibliotecas externas
    - Manter saída consistente para diffs e auditoria
    """

    def fmt_value(v: Any) -> str:
        # O TOML tem representações diferentes por tipo; aqui cobrimos o básico.
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, Path):
            # Converter Path para string é o boundary correto da persistência.
            return f'"{str(v).replace("\\\\", "/")}"'
        if isinstance(v, str):
            # Escape simples para manter string válida em TOML.
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        raise TypeError(f"Unsupported TOML value type: {type(v)}")

    lines: list[str] = []

    # Separar escalares do nível raiz e tabelas ajuda a organizar o arquivo.
    root_scalars: dict[str, Any] = {}
    tables: dict[str, dict[str, Any]] = {}

    for key, value in data.items():
        if isinstance(value, Mapping):
            tables[key] = dict(value)
        else:
            root_scalars[key] = value

    # Primeiro escrevemos escalares no root, se existirem.
    for key, value in root_scalars.items():
        lines.append(f"{key} = {fmt_value(value)}")

    def write_table(prefix: str, table_data: Mapping[str, Any]) -> None:
        # Cada tabela pode conter escalares e tabelas aninhadas.
        scalars: dict[str, Any] = {}
        nested: dict[str, dict[str, Any]] = {}

        for key, value in table_data.items():
            if isinstance(value, Mapping):
                nested[key] = dict(value)
            else:
                scalars[key] = value

        # Linha em branco antes de tabela melhora legibilidade.
        lines.append("")
        lines.append(f"[{prefix}]")

        for key, value in scalars.items():
            lines.append(f"{key} = {fmt_value(value)}")

        # Aninhamento é resolvido por prefixo "a.b".
        for nested_key, nested_value in nested.items():
            write_table(f"{prefix}.{nested_key}", nested_value)

    for table_key, table_value in tables.items():
        write_table(table_key, table_value)

    # Garantir newline final facilita ferramentas e diffs.
    return "\n".join(lines).lstrip("\n").rstrip() + "\n"


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

    if _parse_size_to_bytes(state.log.rotation) is None:
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
# Construção: AppState -> dict TOML (somente persistente)
# -----------------------------------------------------------------------------
# A persistência deve conter apenas campos de configuração, não flags de runtime
# como last_error/last_load_ok. Isso evita "vazar" estados efêmeros para disco.


def build_raw_from_state(state: AppState) -> dict[str, Any]:
    """
    Constrói um dicionário serializável em TOML a partir do estado atual.

    Motivo:
    - Definir explicitamente o que é persistente
    - Evitar acidentalmente salvar campos de runtime
    """
    return {
        "app": {
            "name": state.meta.name,
            "version": state.meta.version,
            "language": state.meta.language,
            "first_run": state.meta.first_run,
            "native_mode": state.meta.native_mode,
            "port": state.meta.port,
            "window": {
                "x": state.window.x,
                "y": state.window.y,
                "width": state.window.width,
                "height": state.window.height,
                "maximized": state.window.maximized,
                "fullscreen": state.window.fullscreen,
                "monitor": state.window.monitor,
                "storage_key": state.window.storage_key,
            },
            "ui": {
                "theme": state.ui.theme,
                "font_scale": state.ui.font_scale,
                "dense_mode": state.ui.dense_mode,
                "accent_color": state.ui.accent_color,
            },
            "log": {
                # Persistimos como string para interoperabilidade e facilidade de edição.
                "path": str(state.log.path).replace("\\", "/"),
                "level": state.log.level,
                "console": state.log.console,
                "buffer_capacity": state.log.buffer_capacity,
                "rotation": state.log.rotation,
                "retention": state.log.retention,
            },
            "behavior": {
                "auto_save": state.behavior.auto_save,
            },
        }
    }


# -----------------------------------------------------------------------------
# API pública: load/save
# -----------------------------------------------------------------------------
# A API retorna bool para facilitar bootstrap do app sem exceções no fluxo normal.
# Em caso de falha, a causa é registrada em state.last_error.


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
        raw = _loads_toml(path.read_text(encoding="utf-8"))
        apply_settings_to_state(st, raw)
        st.last_load_ok = True
        log.info("Settings loaded successfully")
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
        # Persistimos apenas campos configuráveis, deixando runtime fora do arquivo.
        raw = build_raw_from_state(st)
        content = _to_toml_string(raw)
        _atomic_write_text(path, content)
        st.last_save_ok = True
        log.info("Settings saved successfully")
        return True
    except Exception as exc:
        st.last_error = f"Failed to save settings: {exc}"
        log.exception("Failed to save settings")
        return False
