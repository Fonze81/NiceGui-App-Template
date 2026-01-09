# src/nicegui_app_template/core/helpers.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Helpers — Utilidades Genéricas do Core
# -----------------------------------------------------------------------------
# Este módulo concentra funções auxiliares puras, reutilizáveis por múltiplos
# módulos do core (settings, logger, resolvers, etc.).
#
# Princípios de design:
# - Sem dependência de estado global
# - Sem dependência de I/O
# - Sem dependência de frameworks externos (NiceGUI, logging, etc.)
# - Funções pequenas, previsíveis e facilmente testáveis
#
# Objetivo arquitetural:
# - Evitar duplicação de lógica
# - Evitar importação de funções privadas entre módulos
# - Manter boundaries limpos entre settings, estado e infraestrutura
#
# Este módulo:
# - Não conhece AppState
# - Não conhece settings.toml
# - Não conhece LogConfig
# - Apenas transforma dados
# -----------------------------------------------------------------------------

import re
from typing import Optional


# -----------------------------------------------------------------------------
# Parsing de tamanhos (human-readable -> bytes)
# -----------------------------------------------------------------------------


def parse_size_to_bytes(value: str) -> Optional[int]:
    """
    Converte uma expressão textual de tamanho em bytes.

    A função aceita valores escritos de forma amigável para humanos,
    normalmente utilizados em arquivos de configuração ou UI, e os converte
    para um valor técnico em bytes, adequado para uso em APIs de baixo nível
    (ex.: logging, buffers, limites de memória).

    Formatos suportados:
        - "5 MB"
        - "10KB"
        - "1 GB"
        - "512 B"

    Regras:
        - Espaço entre número e unidade é opcional
        - Unidades aceitas: B, KB, MB, GB
        - Case-insensitive
        - Apenas valores inteiros são suportados

    Args:
        value: String representando o tamanho em formato humano.

    Returns:
        O valor convertido em bytes quando o formato é válido.
        Retorna None quando o formato é inválido ou não reconhecido.

    Design rationale:
        - Configurações devem ser legíveis e editáveis por humanos.
        - Infraestrutura exige valores técnicos precisos.
        - A conversão deve ocorrer em um helper neutro e reutilizável,
          evitando acoplamento entre settings, estado e infraestrutura.
    """
    # Normalização simples reduz variações de escrita e simplifica o parsing.
    raw = value.strip().upper()

    # Regex intencionalmente restrita:
    # - evita floats (ex.: "1.5 MB")
    # - evita unidades ambíguas ou não suportadas
    match = re.match(r"^(\d+)\s*(B|KB|MB|GB)$", raw)
    if not match:
        return None

    size = int(match.group(1))
    unit = match.group(2)

    # Multiplicadores explícitos evitam ambiguidades e mantêm previsibilidade.
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
        "GB": 1024**3,
    }

    return size * multipliers[unit]
