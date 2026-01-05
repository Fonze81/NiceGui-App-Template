# tests/core/test_settings.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from nicegui_app_template.core import settings as settings_module


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


@pytest.fixture()
def fake_state() -> _FakeAppState:
    return _FakeAppState()


@pytest.fixture()
def test_logger() -> logging.Logger:
    # Um logger real é útil para caplog e para validar que erros são emitidos com logger injetado.
    logger = logging.getLogger("test_settings_logger")
    logger.setLevel(logging.DEBUG)
    return logger


def test_deep_get_returns_value_when_present() -> None:
    raw: Mapping[str, Any] = {"app": {"window": {"width": 123}}}
    assert settings_module._deep_get(raw, "app.window.width", 999) == 123


def test_deep_get_returns_default_when_missing() -> None:
    raw: Mapping[str, Any] = {"app": {"window": {}}}
    assert settings_module._deep_get(raw, "app.window.height", 777) == 777


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1 B", 1),
        ("1 KB", 1024),
        ("2 MB", 2 * 1024**2),
        ("3 GB", 3 * 1024**3),
        ("5mb", 5 * 1024**2),
        (" 10   MB ", 10 * 1024**2),
    ],
)
def test_parse_size_to_bytes_valid(text: str, expected: int) -> None:
    assert settings_module._parse_size_to_bytes(text) == expected


@pytest.mark.parametrize("text", ["", "10", "10 TB", "abc", "10  MB  X", "10MiB"])
def test_parse_size_to_bytes_invalid_returns_none(text: str) -> None:
    assert settings_module._parse_size_to_bytes(text) is None


def test_to_toml_string_minimal_serialization_and_newline() -> None:
    data = {
        "app": {
            "name": "MeuApp",
            "version": "1.0.0",
            "window": {
                "width": 1200,
                "height": 800,
            },
            "log": {
                "path": "logs/app.log",
                "console": True,
            },
        }
    }

    toml_text = settings_module._to_toml_string(data)

    # Garante newline final para compatibilidade com ferramentas e diffs.
    assert toml_text.endswith("\n")

    # Estrutura mínima esperada.
    assert "[app]" in toml_text
    assert 'name = "MeuApp"' in toml_text
    assert "[app.window]" in toml_text
    assert "width = 1200" in toml_text
    assert "[app.log]" in toml_text
    assert 'path = "logs/app.log"' in toml_text
    assert "console = true" in toml_text


def test_to_toml_string_escapes_quotes_and_backslashes() -> None:
    data = {"root": {"text": 'a "b" c', "path": r"C:\temp\file.txt"}}
    toml_text = settings_module._to_toml_string(data)

    # Aspas devem ser escapadas.
    assert 'text = "a \\"b\\" c"' in toml_text

    # Backslashes devem ser preservadas de forma válida em TOML.
    assert 'path = "C:\\\\temp\\\\file.txt"' in toml_text


def test_to_toml_string_raises_for_unsupported_type() -> None:
    data = {"bad": {"items": ["a", "b"]}}  # Arrays não são suportados pelo serializador mínimo.
    with pytest.raises(TypeError):
        settings_module._to_toml_string(data)


def test_loads_toml_parses_basic_document() -> None:
    raw = settings_module._loads_toml(
        """
        [app]
        name = "MeuApp"
        port = 8080

        [app.window]
        width = 1200
        height = 800
        """
    )
    assert raw["app"]["name"] == "MeuApp"
    assert raw["app"]["port"] == 8080
    assert raw["app"]["window"]["width"] == 1200


def test_apply_settings_to_state_applies_values_and_fallbacks(fake_state: _FakeAppState) -> None:
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

    settings_module.apply_settings_to_state(fake_state, raw)

    assert fake_state.meta.name == "X"
    assert fake_state.meta.version == "9.9.9"
    assert fake_state.meta.first_run is False

    # Fallbacks / validações leves
    assert fake_state.meta.port == 8080
    assert fake_state.window.width == 800
    assert fake_state.window.height == 600
    assert fake_state.log.level == "INFO"
    assert fake_state.log.buffer_capacity == 50
    assert fake_state.log.rotation == "5 MB"
    assert fake_state.log.retention == 3

    # Casting/atribuição
    assert fake_state.log.path == Path("logs/x.log")
    assert fake_state.behavior.auto_save is True


def test_build_raw_from_state_contains_only_persistent_fields(fake_state: _FakeAppState) -> None:
    fake_state.meta.name = "MeuApp"
    fake_state.log.path = Path(r"logs\app.log")

    raw = settings_module.build_raw_from_state(fake_state)

    # Deve conter apenas "app" e seus filhos, sem flags runtime do state.
    assert list(raw.keys()) == ["app"]
    assert raw["app"]["name"] == "MeuApp"

    # Path deve ser persistido como string com separador normalizado.
    assert raw["app"]["log"]["path"] == "logs/app.log"

    # Flags runtime não devem ser persistidas.
    assert "last_error" not in raw["app"]


def test_load_settings_returns_false_when_file_missing_sets_state_error(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings_path = tmp_path / "settings.toml"
    assert not settings_path.exists()

    caplog.set_level(logging.DEBUG)

    ok = settings_module.load_settings(settings_path=settings_path, state=fake_state, logger=test_logger)
    assert ok is False
    assert fake_state.last_load_ok is False
    assert fake_state.last_error is not None
    assert "Settings file not found" in fake_state.last_error

    # Com logger injetado, esperamos um erro registrado.
    assert any("Settings file not found" in rec.getMessage() for rec in caplog.records)


def test_load_settings_success_applies_settings_and_sets_flags(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text(
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
        + "\n",
        encoding="utf-8",
    )

    caplog.set_level(logging.INFO)

    ok = settings_module.load_settings(settings_path=settings_path, state=fake_state, logger=test_logger)
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

    assert any("Settings loaded successfully" in rec.getMessage() for rec in caplog.records)


def test_save_settings_success_writes_toml_and_sets_flags(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings_path = tmp_path / "settings.toml"

    # Forçar alguns valores para validar persistência.
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

    ok = settings_module.save_settings(settings_path=settings_path, state=fake_state, logger=test_logger)
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

    # Deve gravar como string normalizada para facilitar edição e portabilidade.
    assert "[app.log]" in text
    assert 'path = "logs/app.log"' in text

    # Arquivo temporário não deve sobrar após replace.
    tmp_candidate = settings_path.with_suffix(settings_path.suffix + ".tmp")
    assert not tmp_candidate.exists()

    assert any("Settings saved successfully" in rec.getMessage() for rec in caplog.records)


def test_save_settings_uses_state_last_loaded_path_when_settings_path_not_provided(
    tmp_path: Path,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
) -> None:
    # Simula que o app já carregou de um path específico.
    settings_path = tmp_path / "settings.toml"
    fake_state.settings_file_path = settings_path

    ok = settings_module.save_settings(state=fake_state, logger=test_logger)
    assert ok is True
    assert settings_path.exists()


def test_load_settings_uses_default_settings_path_when_no_path_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
) -> None:
    """
    Valida o fluxo default: sem settings_path, deve usar default_settings_path().

    Motivo:
    - Bootstrap do app normalmente chama load_settings() sem passar path explícito
    - O módulo deve ser testável sem depender de Path.cwd()
    """
    settings_path = tmp_path / "settings.toml"
    settings_path.write_text('[app]\nname = "MeuApp"\n', encoding="utf-8")

    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)

    ok = settings_module.load_settings(state=fake_state, logger=test_logger)
    assert ok is True
    assert fake_state.meta.name == "MeuApp"
    assert fake_state.settings_file_path == settings_path.resolve()


def test_save_settings_uses_default_settings_path_when_no_path_and_no_state_file_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_state: _FakeAppState,
    test_logger: logging.Logger,
) -> None:
    settings_path = tmp_path / "settings.toml"
    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)

    fake_state.settings_file_path = None

    ok = settings_module.save_settings(state=fake_state, logger=test_logger)
    assert ok is True
    assert settings_path.exists()


def test_load_settings_uses_get_app_state_when_state_not_provided(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_logger: logging.Logger,
) -> None:
    """
    Valida o comportamento padrão: state None usa get_app_state().

    Motivo:
    - Facilita bootstrap do app sem precisar plugar explicitamente o estado
    - Mantém compatibilidade com o template
    """
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
    settings_path = tmp_path / "settings.toml"
    st = _FakeAppState()

    monkeypatch.setattr(settings_module, "default_settings_path", lambda: settings_path)
    monkeypatch.setattr(settings_module, "get_app_state", lambda: st)

    ok = settings_module.save_settings(logger=test_logger)
    assert ok is True
    assert settings_path.exists()


def test_get_logger_returns_null_logger_when_none() -> None:
    log = settings_module._get_logger(None)

    # Deve ser um logger funcional e silencioso (sem handlers de console).
    assert isinstance(log, logging.Logger)

    # Deve ter pelo menos um handler NullHandler para evitar warnings.
    assert any(isinstance(h, logging.NullHandler) for h in log.handlers)


def test_atomic_write_text_creates_parent_dir_and_is_atomic_like(tmp_path: Path) -> None:
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

    # Arquivo temporário não deve ficar no disco ao final.
    tmp_candidate = file_path.with_suffix(file_path.suffix + ".tmp")
    assert not tmp_candidate.exists()