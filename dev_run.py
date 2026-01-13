# dev_run.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Entrypoint de Desenvolvimento (com reload=True)
# -----------------------------------------------------------------------------
# Motivo:
# - O reload do NiceGUI cria processos adicionais e pode falhar quando o app é
#   invocado como módulo (`python -m ...`) em alguns cenários.
# - Rodar como script reduz ambiguidades do multiprocessing no Windows.
#
# Como usar:
#   (.venv) PS> python dev_run.py
# -----------------------------------------------------------------------------

from nicegui_app_template.app import main


def _run() -> None:
    """
    Executa o aplicativo em modo de desenvolvimento com reload ativo.
    """
    main(reload=True)


# IMPORTANTE:
# - Em Windows, spawn pode usar "__mp_main__" para processos filhos.
# - Este guard garante que o processo filho também alcance ui.run().
if __name__ in {"__main__", "__mp_main__"}:
    _run()
