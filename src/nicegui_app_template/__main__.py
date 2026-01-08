# src/nicegui_app_template/__main__.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Ponto de Entrada do Pacote
# -----------------------------------------------------------------------------
# Este módulo define o ponto de entrada oficial do pacote
# `nicegui_app_template` quando o aplicativo é executado como módulo:
#
#     python -m nicegui_app_template
#
# A existência deste arquivo (__main__.py) é obrigatória para permitir a
# execução do pacote via `-m`, conforme documentado no README e no
# run-the-app.md.
#
# Este módulo não contém lógica de negócio.
# Sua única responsabilidade é delegar a execução para a função `main`,
# definida no módulo principal da aplicação.
# -----------------------------------------------------------------------------

from .app import main  # Importação explícita do ponto de inicialização da aplicação


def _run() -> None:
    """
    Executa o ponto de entrada da aplicação.

    Esta função existe apenas para tornar explícito o fluxo de execução
    e facilitar futuras extensões (ex.: instrumentação, profiling ou
    inicialização condicional), sem alterar o contrato do ponto de entrada.
    """
    main()


# -----------------------------------------------------------------------------
# Execução direta do módulo
# -----------------------------------------------------------------------------
# Este bloco garante que a aplicação seja iniciada apenas quando o pacote
# for executado diretamente como módulo, e não quando importado.
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    _run()
