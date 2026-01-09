# tests/test_helpers.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Testes — core/helpers.py
# -----------------------------------------------------------------------------
# Este arquivo valida o comportamento do módulo helpers, garantindo que:
# - Entradas válidas sejam convertidas corretamente para bytes
# - Entradas inválidas retornem None (falha controlada, sem exceção)
#
# Motivo:
# - helpers é um ponto de reutilização transversal (settings/logger/resolvers)
# - A função deve ser previsível e defensiva, pois recebe valores editáveis
#   manualmente por usuários em settings.toml ou UI.
# -----------------------------------------------------------------------------

import pytest

from nicegui_app_template.core.helpers import parse_size_to_bytes


# -----------------------------------------------------------------------------
# Casos válidos (comportamento esperado)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Casos básicos (com e sem espaço).
        ("5 MB", 5 * 1024**2),
        ("5MB", 5 * 1024**2),
        ("10KB", 10 * 1024),
        ("10 KB", 10 * 1024),
        ("1 GB", 1 * 1024**3),
        ("512 B", 512),
        # Normalização de espaços e tabs.
        ("  5   MB  ", 5 * 1024**2),
        ("5\tMB", 5 * 1024**2),
        # Case-insensitive.
        ("5 mb", 5 * 1024**2),
        ("5 Mb", 5 * 1024**2),
        ("5 mB", 5 * 1024**2),
        # Zero é válido e útil em cenários de configuração.
        ("0 B", 0),
        ("0KB", 0),
        # Valores com zeros à esquerda devem ser aceitos, pois são comuns em edição manual.
        ("001 KB", 1 * 1024),
    ],
)
def test_parse_size_to_bytes_valid_inputs(value: str, expected: int) -> None:
    """
    Valida conversões corretas para entradas válidas.

    Args:
        value: Entrada em formato humano.
        expected: Saída esperada em bytes.
    """
    # Arrange/Act: chamamos diretamente a função, pois ela é pura.
    result = parse_size_to_bytes(value)

    # Assert: a conversão deve ser determinística e retornar int.
    assert result == expected


# -----------------------------------------------------------------------------
# Casos inválidos (falha controlada)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        # String vazia / somente espaços.
        "",
        "   ",
        # Sem unidade ou sem número.
        "5",
        "MB",
        # Unidade não suportada.
        "5 TB",
        "5 MiB",
        "5 MIB",
        # Formatos com caracteres extras.
        "5MBs",
        "5 MB extra",
        "size=5 MB",
        # Valores não inteiros (regex intencionalmente restrita).
        "1.5 MB",
        "5.0 MB",
        # Valores negativos (não fazem sentido para tamanho).
        "-5 MB",
        # Unidades coladas com símbolos inesperados.
        "5-MB",
        "5_MB",
    ],
)
def test_parse_size_to_bytes_invalid_inputs_return_none(value: str) -> None:
    """
    Valida que entradas inválidas retornam None (sem exceções).

    Args:
        value: Entrada em formato humano inválida.
    """
    # Act: o comportamento esperado para erro de formato é retornar None.
    result = parse_size_to_bytes(value)

    # Assert: falha controlada evita quebrar bootstrap/configuração.
    assert result is None


# -----------------------------------------------------------------------------
# Robustez — não deve lançar exceções para strings
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        # Casos estranhos, mas ainda strings; a função deve ser defensiva.
        "\n",
        "\r\n",
        "\t",
        " \t  \n ",
        "999999999999999 GB",  # Pode ser grande, mas não deve lançar exceção ao parse.
    ],
)
def test_parse_size_to_bytes_does_not_raise_for_string_inputs(value: str) -> None:
    """
    Garante robustez defensiva: para entradas do tipo str, a função não deve lançar.

    Args:
        value: String potencialmente problemática.
    """
    # Act/Assert: se falhar, deve falhar retornando None ou um int, nunca via exceção.
    try:
        result = parse_size_to_bytes(value)
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"parse_size_to_bytes raised an exception for '{value!r}': {exc}")

    # Assert: resultado deve ser None ou int (nunca outros tipos).
    assert result is None or isinstance(result, int)
