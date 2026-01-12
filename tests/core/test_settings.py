# tests/core/test_settings.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Testes do módulo de settings (core/settings.py)
# -----------------------------------------------------------------------------
# Este arquivo valida o comportamento do módulo de settings de forma isolada:
# - helpers internos (deep_get, normalize_path_for_toml, atomic_write_text, etc.)
# - round-trip com tomlkit (parse, ensure_toml_table, set_value_by_path, apply_state_to_document)
# - aplicação de settings em um estado em memória (apply_settings_to_state)
# - fluxos de I/O (load_settings / save_settings), incluindo escrita atômica
#
# Decisão de teste:
# - Usamos um estado fake (_FakeAppState) para evitar dependência do AppState real.
# - Isso mantém o teste focado no contrato do módulo de settings e reduz acoplamento.
# - Quando a função espera AppState, usamos cast apenas nos testes.
# -----------------------------------------------------------------------------

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, cast

import pytest
import tomlkit
from tomlkit.items import Table
from tomlkit.toml_document import TOMLDocument

from nicegui_app_template.core import settings as settings_module
from nicegui_app_template.core.state import AppState

# -----------------------------------------------------------------------------
# Estados mínimos para testes
# -----------------------------------------------------------------------------
# Estes dataclasses reproduzem apenas os campos que o módulo de settings acessa.
# A intenção é validar parsing, defaults e fallback sem depender do AppState real.
# -----------------------------------------------------------------------------


@dataclass
class _MetaState:
    name: str = "MyApp"
    version: str = "0.0.0"
    language: str = "pt-BR"
    first_run: bool = True
    native_mode: bool = True
    port: int = 8080


@dataclass
class _WindowState:
    x: int = 100
    y: int = 100
    width: int = 800
    height: int = 600
    maximized: bool = False
    fullscreen: bool = False
    monitor: int = 0
    storage_key: str = "nicegui_window_state_spa"


@dataclass
class _UiState:
    theme: str = "dark"
    font_scale: float = 1.0
    dense_mode: bool = False
    accent_color: str = "#0057B8"


@dataclass
class _LogState:
    path: Path = Path("logs/app.log")
    level: str = "INFO"
    console: bool = True
    buffer_capacity: int = 500
    rotation: str = "5 MB"
    retention: int = 7


@dataclass
class _BehaviorState:
    auto_save: bool = False


class _FakeAppState:
    """
    Estado mínimo para testes.

    Motivo:
    - Os testes não devem depender do estado real do app para validar o módulo de settings
    - Mantém foco em comportamento (I/O, parsing, defaults e fallback)
    """

    def __init__(self) -> None:
        self.meta = _MetaState()
        self.window = _WindowState()
        self.ui = _UiState()
        self.log = _LogState()
        self.behavior = _BehaviorState()

        self.settings_file_path: Path | None = None
        self.last_error: str | None = None
        self.last_load_ok: bool = False
        self.last_save_ok: bool = False


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture()
def fake_state() -> _FakeAppState:
    """Fornece um estado fake novo para cada teste."""
    return _FakeAppState()


@pytest.fixture()
def test_logger() -> logging.Logger:
    """
    Cria um logger real para os testes.

    Motivo:
    - Permite validar comportamento com logger injetado
    - Facilita inspeção de mensagens via caplog
    """
    logger = logging.getLogger("test_settings_logger")
    logger.setLevel(logging.DEBUG)
    return logger


# -----------------------------------------------------------------------------
# Testes: helpers internos
# -----------------------------------------------------------------------------


def test_deep_get_returns_value_when_present() -> None:
    """Garante que _deep_get retorna o valor quando a chave existe."""
    raw: Mapping[str, Any] = {"app": {"window": {"width": 123}}}
    assert settings_module._deep_get(raw, "app.window.width", 999) == 123


def test_deep_get_returns_default_when_missing() -> None:
    """Garante que _deep_get retorna o default quando a chave não existe."""
    raw: Mapping[str, Any] = {"app": {"window": {}}}
    assert settings_module._deep_get(raw, "app.window.height", 777) == 777


def test_normalize_path_for_toml_replaces_backslashes() -> None:
    """Garante que _normalize_path_for_toml produz '/' para reduzir ruído no TOML."""
    assert (
        settings_module._normalize_path_for_toml(Path(r"C:\temp\file.log"))
        == "C:/temp/file.log"
    )


def test_get_logger_returns_null_logger_when_none() -> None:
    """
    Garante que _get_logger(None) retorne um logger silencioso e seguro.

    Motivo:
    - Permite que o módulo opere antes do logger principal estar configurado
    - Evita warnings do logging quando nenhum handler está presente
    """
    log = settings_module._get_logger(None)

    assert isinstance(log, logging.Logger)
    assert any(isinstance(h, logging.NullHandler) for h in log.handlers)


def test_get_logger_returns_injected_logger_when_provided(
    test_logger: logging.Logger,
) -> None:
    """Garante que _get_logger devolve o logger injetado sem substituição."""
    assert settings_module._get_logger(test_logger) is test_logger


def test_atomic_write_text_creates_parent_dir_and_writes_file(tmp_path: Path) -> None:
    """
    Teste direto do helper de escrita atômica.

    Observação:
    - Não é possível provar atomicidade real em todas as plataformas num teste unitário
    - Aqui validamos efeitos esperados: cria diretório e usa arquivo final com conteúdo correto
    """
    file_path = tmp_path / "a" / "b" / "settings.toml"
    settings_module._atomic_write_text(file_path, "x=1\n")

    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == "x=1\n"

    tmp_candidate = file_path.with_suffix(file_path.suffix + ".tmp")
    assert not tmp_candidate.exists()


# -----------------------------------------------------------------------------
# Testes: resolução de root por env
# -----------------------------------------------------------------------------


def test_resolve_app_root_uses_env_when_defined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Garante que APP_ROOT define a raiz do app quando presente."""
    monkeypatch.setenv("APP_ROOT", str(tmp_path))
    assert settings_module._resolve_app_root() == tmp_path.resolve()


def test_resolve_app_root_falls_back_to_cwd_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garante fallback para cwd quando APP_ROOT não está definido."""
    monkeypatch.delenv("APP_ROOT", raising=False)
    assert settings_module._resolve_app_root() == Path.cwd().resolve()


# -----------------------------------------------------------------------------
# Testes: round-trip TOML (tomlkit)
# -----------------------------------------------------------------------------


def test_parse_toml_document_parses_basic_document() -> None:
    """Garante que o parser baseado em tomlkit lê um documento básico."""
    document = settings_module._parse_toml_document(
        """
        # comment
        [app]
        name = "MyApp"
        [app.log]
        path = "logs/app.log"
        """
    )

    assert isinstance(document, TOMLDocument)

    app_table = document.get("app")
    assert isinstance(app_table, Table)

    assert app_table.get("name") == "MyApp"

    log_table = app_table.get("log")
    assert isinstance(log_table, Table)

    assert log_table.get("path") == "logs/app.log"


def test_ensure_toml_table_creates_missing_table() -> None:
    """Garante que _ensure_toml_table cria a tabela quando a chave não existe."""
    document = tomlkit.document()
    table = settings_module._ensure_toml_table(document, "app")
    assert isinstance(table, Table)
    assert isinstance(document["app"], Table)


def test_ensure_toml_table_replaces_non_table_value() -> None:
    """Garante que valores inválidos sejam substituídos por Table para manter salvamento possível."""
    document = tomlkit.document()
    document["app"] = "invalid"
    table = settings_module._ensure_toml_table(document, "app")
    assert isinstance(table, Table)
    assert isinstance(document["app"], Table)


def test_set_toml_value_by_path_creates_tables_and_sets_value() -> None:
    """Garante que _set_toml_value_by_path cria hierarquia e define valor."""
    document = tomlkit.document()
    settings_module._set_toml_value_by_path(document, "app.log.level", "INFO")

    app_table = document.get("app")
    assert isinstance(app_table, Table)

    log_table = app_table.get("log")
    assert isinstance(log_table, Table)

    assert log_table.get("level") == "INFO"


def test_apply_state_to_document_updates_only_known_keys() -> None:
    """
    Garante que o updater altera chaves conhecidas sem apagar o restante.

    Motivo:
    - É a essência do round-trip: atualizar somente o que o template gerencia
    """
    document = settings_module._parse_toml_document(
        """
[app]
name = "Original"
unknown_key = "keep_me"

[custom]
value = 1
""".lstrip()
    )

    state = _FakeAppState()
    state.meta.name = "Changed"

    settings_module._apply_state_to_document(document, cast(AppState, state))
    dumped = tomlkit.dumps(document)

    assert 'name = "Changed"' in dumped
    assert 'unknown_key = "keep_me"' in dumped
    assert "\n[custom]\n" in dumped
    assert "value = 1" in dumped


def test_build_minimal_document_from_state_generates_expected_shape(
    fake_state: _FakeAppState,
) -> None:
    """Garante que o documento mínimo (primeiro save) contém a estrutura base."""
    document = settings_module._build_minimal_document_from_state(
        cast(AppState, fake_state)
    )

    assert isinstance(document, TOMLDocument)
    assert document.get("app") is not None

    app_table = document.get("app")
    assert isinstance(app_table, Table)

    assert app_table.get("log") is not None
    assert app_table.get("window") is not None
    assert app_table.get("ui") is not None


# -----------------------------------------------------------------------------
# Testes: aplicação de settings no estado
# -----------------------------------------------------------------------------


def test_apply_settings_to_state_applies_values_and_fallbacks(
    fake_state: _FakeAppState,
) -> None:
    """
    Valida que apply_settings_to_state aplica valores e executa fallbacks.

    Observação:
    - Alguns campos intencionalmente inválidos devem cair para defaults seguros.
    """
    raw = {
        "app": {
            "name": "X",
            "version": "9.9.9",
            "language": "pt-BR",
            "first_run": False,
            "native_mode": True,
            "port": 99999,  # inválida: deve cair para 8080 (fallback do módulo)
            "window": {
                "x": 10,
                "y": 20,
                "width": 10,  # inválida: deve cair para 800
                "height": 10,  # inválida: deve cair para 600
                "maximized": True,
                "fullscreen": False,
                "monitor": 2,
                "storage_key": "k",
            },
            "ui": {
                "theme": "light",
                "font_scale": 1.25,
                "dense_mode": True,
                "accent_color": "#000000",
            },
            "log": {
                "path": "logs/x.log",
                "level": "INVALID",
                "console": False,
                "buffer_capacity": 1,  # inválido: deve cair para 50
                "rotation": "XYZ",  # inválido: deve cair para 5 MB
                "retention": 0,  # inválido: deve cair para 3
            },
            "behavior": {"auto_save": True},
        }
    }

    settings_module.apply_settings_to_state(cast(AppState, fake_state), raw)

    assert fake_state.meta.name == "X"
    assert fake_state.meta.version == "9.9.9"
    assert fake_state.meta.first_run is False

    assert fake_state.meta.port == 8080
    assert fake_state.window.width == 800
    assert fake_state.window.height == 600
    assert fake_state.log.level == "INFO"
    assert fake_state.log.buffer_capacity == 50
    assert fake_state.log.rotation == "5 MB"
    assert fake_state.log.retention == 3

    assert fake_state.log.path == Path("logs/x.log")
    assert fake_state.behavior.auto_save is True


# -----------------------------------------------------------------------------
# Testes: load_settings (I/O)
# -----------------------------------------------------------------------------


def test_load_settings_returns_false_when_file_missing_sets_state_error(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valida o comportamento quando o arquivo não existe."""
    settings_path = tmp_path / "settings.toml"
    assert not settings_path.exists()

    caplog.set_level(logging.DEBUG)

    ok = settings_module.load_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
        logger=test_logger,
    )
    assert ok is False
    assert fake_state.last_load_ok is False
    assert fake_state.last_error is not None
    assert "Settings file not found" in fake_state.last_error
    assert any("Settings file not found" in rec.getMessage() for rec in caplog.records)


def test_load_settings_returns_false_when_parse_fails(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valida que erros de parse são tratados com retorno False e exception logada."""
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text("this is not = toml ==", encoding="utf-8")

    caplog.set_level(logging.DEBUG)

    ok = settings_module.load_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
        logger=test_logger,
    )

    assert ok is False
    assert fake_state.last_load_ok is False
    assert fake_state.last_error is not None
    assert "Failed to load settings" in fake_state.last_error
    assert any("Failed to load settings" in rec.getMessage() for rec in caplog.records)


def test_load_settings_success_applies_settings_and_sets_flags(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valida load_settings em cenário de sucesso."""
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text(
        (
            """
[app]
name = "MeuApp"
port = 8081

[app.window]
width = 1201
height = 801

[app.log]
path = "logs/test.log"
level = "debug"
rotation = "10 MB"
retention = 5
buffer_capacity = 123
console = true

[app.behavior]
auto_save = true
""".strip()
            + "\n"
        ),
        encoding="utf-8",
    )

    caplog.set_level(logging.INFO)

    ok = settings_module.load_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
        logger=test_logger,
    )
    assert ok is True
    assert fake_state.last_load_ok is True
    assert fake_state.last_error is None
    assert fake_state.settings_file_path == settings_path.resolve()

    assert fake_state.meta.name == "MeuApp"
    assert fake_state.meta.port == 8081

    assert fake_state.window.width == 1201
    assert fake_state.window.height == 801

    assert fake_state.log.path == Path("logs/test.log")
    assert fake_state.log.level == "DEBUG"
    assert fake_state.log.rotation == "10 MB"
    assert fake_state.log.retention == 5
    assert fake_state.log.buffer_capacity == 123
    assert fake_state.log.console is True

    assert fake_state.behavior.auto_save is True
    assert any(
        "Settings loaded successfully" in rec.getMessage() for rec in caplog.records
    )


# -----------------------------------------------------------------------------
# Testes: save_settings (I/O)
# -----------------------------------------------------------------------------


def test_save_settings_success_writes_toml_and_sets_flags(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valida save_settings em cenário de sucesso."""
    settings_path = tmp_path / "settings.toml"

    fake_state.meta.name = "MeuApp"
    fake_state.meta.port = 8082
    fake_state.window.width = 1000
    fake_state.window.height = 700
    fake_state.log.path = Path("logs/app.log")
    fake_state.log.level = "INFO"
    fake_state.log.rotation = "5 MB"
    fake_state.log.retention = 7
    fake_state.log.buffer_capacity = 500
    fake_state.behavior.auto_save = True

    caplog.set_level(logging.INFO)

    ok = settings_module.save_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
        logger=test_logger,
    )
    assert ok is True
    assert fake_state.last_save_ok is True
    assert fake_state.last_error is None
    assert fake_state.settings_file_path == settings_path.resolve()

    text = settings_path.read_text(encoding="utf-8")
    assert "[app]" in text
    assert 'name = "MeuApp"' in text
    assert "port = 8082" in text
    assert "[app.window]" in text
    assert "width = 1000" in text
    assert "height = 700" in text
    assert "[app.log]" in text
    assert 'path = "logs/app.log"' in text
    assert "[app.behavior]" in text
    assert "auto_save = true" in text

    tmp_candidate = settings_path.with_suffix(settings_path.suffix + ".tmp")
    assert not tmp_candidate.exists()

    assert any(
        "Settings saved successfully" in rec.getMessage() for rec in caplog.records
    )


def test_save_settings_preserves_comments_and_unknown_keys(
    tmp_path: Path, fake_state: _FakeAppState
) -> None:
    """Garante que save_settings preserva comentários e chaves desconhecidas."""
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text(
        """
# top-level comment

[app]
name = "Original"
version = "0.0.0"
# comment inside app
unknown_key = "keep_me"

[app.log]
path = "C:\\\\temp\\\\old.log"  # keep this comment too
level = "INFO"

[custom]
value = 123
""".lstrip(),
        encoding="utf-8",
    )

    fake_state.meta.name = "UpdatedName"
    fake_state.meta.version = "9.9.9"
    fake_state.log.path = Path(r"C:\logs\app.log")

    ok = settings_module.save_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
    )
    assert ok is True

    saved = settings_path.read_text(encoding="utf-8")

    assert "# top-level comment" in saved
    assert "# comment inside app" in saved
    assert "keep this comment too" in saved

    assert 'unknown_key = "keep_me"' in saved
    assert "\n[custom]\n" in saved
    assert "value = 123" in saved

    assert 'name = "UpdatedName"' in saved
    assert 'version = "9.9.9"' in saved


def test_save_settings_normalizes_log_path_to_forward_slashes(
    tmp_path: Path, fake_state: _FakeAppState
) -> None:
    """Garante que o path de log é persistido com '/' (para diffs limpos)."""
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text(
        """
[app]
name = "X"
version = "0.0.0"

[app.log]
path = "logs/app.log"
level = "INFO"
""".lstrip(),
        encoding="utf-8",
    )

    fake_state.log.path = Path(r"C:\temp\file.log")

    ok = settings_module.save_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
    )
    assert ok is True

    saved = settings_path.read_text(encoding="utf-8")
    assert 'path = "C:/temp/file.log"' in saved


def test_save_settings_returns_false_when_write_fails(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Garante que falhas de escrita são tratadas e reportadas."""
    settings_path = tmp_path / "settings.toml"

    def _raise(*_: Any, **__: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(settings_module, "_atomic_write_text", _raise)

    caplog.set_level(logging.DEBUG)

    ok = settings_module.save_settings(
        settings_path=settings_path,
        state=cast(AppState, fake_state),
        logger=test_logger,
    )

    assert ok is False
    assert fake_state.last_save_ok is False
    assert fake_state.last_error is not None
    assert "Failed to save settings" in fake_state.last_error
    assert any("Failed to save settings" in rec.getMessage() for rec in caplog.records)


def test_save_settings_uses_state_last_loaded_path_when_settings_path_not_provided(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
) -> None:
    """Valida que save_settings usa o último path conhecido no state quando omitido."""
    settings_path = tmp_path / "settings.toml"
    fake_state.settings_file_path = settings_path

    ok = settings_module.save_settings(
        state=cast(AppState, fake_state), logger=test_logger
    )
    assert ok is True
    assert settings_path.exists()


# -----------------------------------------------------------------------------
# Testes: caminhos padrão e fallback de dependências (monkeypatch)
# -----------------------------------------------------------------------------


def test_load_settings_uses_default_settings_path_when_no_path_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
) -> None:
    """Valida o fluxo default: sem settings_path, deve usar default_settings_path()."""
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text('[app]\nname = "MeuApp"\n', encoding="utf-8")

    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)

    ok = settings_module.load_settings(
        state=cast(AppState, fake_state), logger=test_logger
    )
    assert ok is True
    assert fake_state.meta.name == "MeuApp"
    assert fake_state.settings_file_path == settings_path.resolve()


def test_save_settings_uses_default_settings_path_when_no_path_and_no_state_file_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
) -> None:
    """Valida fallback para default_settings_path quando não há path disponível."""
    settings_path = tmp_path / "settings.toml"
    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)

    fake_state.settings_file_path = None

    ok = settings_module.save_settings(
        state=cast(AppState, fake_state), logger=test_logger
    )
    assert ok is True
    assert settings_path.exists()


def test_load_settings_uses_get_app_state_when_state_not_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_logger: logging.Logger,
) -> None:
    """Valida o comportamento padrão: state None usa get_app_state()."""
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text('[app]\nname = "MeuApp"\n', encoding="utf-8")

    st = _FakeAppState()

    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)
    monkeypatch.setattr(settings_module, "get_app_state", lambda: st)

    ok = settings_module.load_settings(logger=test_logger)
    assert ok is True
    assert st.meta.name == "MeuApp"


def test_save_settings_uses_get_app_state_when_state_not_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_logger: logging.Logger,
) -> None:
    """Valida que save_settings usa get_app_state() quando state não é informado."""
    settings_path = tmp_path / "settings.toml"
    st = _FakeAppState()

    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)
    monkeypatch.setattr(settings_module, "get_app_state", lambda: st)

    ok = settings_module.save_settings(logger=test_logger)
    assert ok is True
    assert settings_path.exists()
