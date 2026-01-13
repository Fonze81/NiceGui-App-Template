# src/nicegui_app_template/__main__.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Entrypoint oficial do pacote
# -----------------------------------------------------------------------------
# Execução oficial:
#   python -m nicegui_app_template
#
# Observação:
# - Em Windows, o encerramento via Ctrl+C dispara KeyboardInterrupt.
# - Uvicorn/NiceGUI pode emitir CancelledError durante shutdown.
# - Capturamos KeyboardInterrupt aqui para evitar stacktrace ruidoso no terminal.
# -----------------------------------------------------------------------------

from .app import main


def _run() -> None:
    """
    Executa o aplicativo via entrypoint do pacote.

    Motivo:
        Centralizar o tratamento de encerramento (Ctrl+C) e manter o entrypoint
        previsível para execução via `python -m`.
    """
    try:
        main(reload=False)
    except KeyboardInterrupt:
        # Encerramento esperado (Ctrl+C). Evita stacktrace ruidoso no terminal.
        return


if __name__ in {"__main__", "__mp_main__"}:
    _run()
