# src/nicegui_app_template/core/state.py

from __future__ import annotations

# -----------------------------------------------------------------------------
# Estado da Aplicação
# -----------------------------------------------------------------------------
# Este módulo define o estado central do aplicativo de forma "pura".
#
# Definição de "estado puro":
# - Não depende de UI
# - Não executa I/O (arquivos, rede, banco)
# - Não conhece logger, settings ou infraestrutura
# - Não realiza validações ou conversões
#
# Essa separação mantém o estado:
# - Fácil de testar
# - Reutilizável
# - Previsível ao longo do tempo
# -----------------------------------------------------------------------------

from dataclasses import (
    dataclass,
    field,
)  # dataclasses reduzem boilerplate e deixam o estado explícito.
from pathlib import (
    Path,
)  # Path é usado no core para representar caminhos de forma robusta no SO.
from typing import (
    Optional,
)  # Optional explicita campos que podem não estar disponíveis em runtime.

# -----------------------------------------------------------------------------
# Subestados — domínios lógicos do aplicativo
# -----------------------------------------------------------------------------
# Cada subestado representa um domínio coeso do aplicativo.
# Essa divisão evita um objeto monolítico e facilita manutenção incremental.
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class AppMetaState:
    """Metadados globais do aplicativo.

    Este estado concentra informações de identidade e bootstrap do aplicativo,
    evitando o espalhamento de constantes por múltiplos módulos.

    Attributes:
        name: Nome lógico do aplicativo.
        version: Versão informativa do aplicativo.
        language: Idioma padrão da interface.
        first_run: Indica se esta é a primeira execução do app.
        native_mode: Indica se o app roda em modo desktop nativo.
        port: Porta HTTP utilizada pelo NiceGUI.
    """

    name: str = "nicegui_app_template"
    version: str = "0.1.0a2"
    language: str = "pt-BR"
    first_run: bool = True
    native_mode: bool = True
    port: int = 8080


@dataclass(slots=True)
class WindowState:
    """Estado persistente relacionado à janela do aplicativo.

    Este estado centraliza informações necessárias para restaurar posição,
    tamanho e comportamento da janela entre execuções.

    Attributes:
        x: Posição horizontal da janela.
        y: Posição vertical da janela.
        width: Largura da janela.
        height: Altura da janela.
        maximized: Indica se a janela inicia maximizada.
        fullscreen: Indica se a janela inicia em fullscreen.
        monitor: Índice do monitor em ambientes multi-monitor.
        storage_key: Chave usada para persistência no frontend.
    """

    x: int = 100
    y: int = 100
    width: int = 800
    height: int = 600
    maximized: bool = False
    fullscreen: bool = False
    monitor: int = 0
    storage_key: str = "nicegui_window_state_spa"


@dataclass(slots=True)
class UiState:
    """Preferências visuais da interface.

    Este estado representa apenas preferências declarativas.
    A interpretação e aplicação ficam sob responsabilidade da UI.

    Attributes:
        theme: Tema visual da aplicação.
        font_scale: Escala global de fonte.
        dense_mode: Indica uso de layout mais compacto.
        accent_color: Cor de destaque da interface.
    """

    theme: str = "dark"
    font_scale: float = 1.0
    dense_mode: bool = False
    accent_color: str = "#0057B8"


@dataclass(slots=True)
class LogState:
    """Estado declarativo de configuração de logging.

    Este estado descreve preferências e parâmetros de logging, mas não
    executa nenhuma lógica relacionada a handlers ou parsing.

    Attributes:
        path: Caminho do arquivo de log.
        level: Nível de log em formato string.
        console: Indica se logs em console estão habilitados.
        buffer_capacity: Capacidade do buffer de early logging.
        rotation: Política de rotação por tamanho.
        retention: Quantidade de arquivos de backup.
    """

    path: Path = Path("logs/app.log")
    level: str = "INFO"
    console: bool = True
    buffer_capacity: int = 500
    rotation: str = "5 MB"
    retention: int = 3


@dataclass(slots=True)
class BehaviorState:
    """Flags comportamentais do aplicativo.

    Este estado centraliza decisões de fluxo e automações,
    evitando flags globais espalhadas pelo código.

    Attributes:
        auto_save: Indica se o app deve salvar ajustes automaticamente.
    """

    auto_save: bool = True


# -----------------------------------------------------------------------------
# Estado Central — fonte de verdade em runtime
# -----------------------------------------------------------------------------
# O AppState agrega todos os subestados e adiciona campos de runtime
# utilizados para diagnóstico e controle de fluxo.
#
# Observação:
# - Campos de runtime NÃO são persistidos automaticamente
# - Persistência é responsabilidade do módulo de settings
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class AppState:
    """Estado central do aplicativo.

    Este objeto é a fonte de verdade durante a execução do aplicativo.
    Ele é simples, previsível e projetado para ser facilmente testável.

    Não é responsabilidade deste objeto:
    - Ler ou escrever arquivos
    - Validar dados externos
    - Conhecer UI, TOML, JSON ou logging

    Attributes:
        meta: Metadados globais do aplicativo.
        window: Estado persistente da janela.
        ui: Preferências visuais da interface.
        log: Estado declarativo de logging.
        behavior: Flags comportamentais.
        settings_file_path: Caminho efetivo do arquivo de settings carregado.
        last_load_ok: Resultado do último carregamento de settings.
        last_save_ok: Resultado do último salvamento de settings.
        last_error: Última mensagem de erro registrada.
    """

    meta: AppMetaState = field(default_factory=AppMetaState)
    window: WindowState = field(default_factory=WindowState)
    ui: UiState = field(default_factory=UiState)
    log: LogState = field(default_factory=LogState)
    behavior: BehaviorState = field(default_factory=BehaviorState)

    settings_file_path: Optional[Path] = None
    last_load_ok: bool = False
    last_save_ok: bool = False
    last_error: Optional[str] = None


# -----------------------------------------------------------------------------
# Singleton pragmático do estado
# -----------------------------------------------------------------------------
# Justificativa:
# - Aplicações desktop normalmente possuem um único estado global
# - Evita injeção excessiva de dependências
# - Mantém acesso explícito e previsível via função
#
# Importante:
# - Não executa lógica de inicialização complexa
# - Apenas fornece uma instância consistente no processo
# -----------------------------------------------------------------------------

_APP_STATE: Optional[AppState] = None


def get_app_state() -> AppState:
    """Retorna a instância singleton do estado do aplicativo.

    A inicialização é lazy para evitar custo desnecessário em tempo de import
    e permitir que o bootstrap do aplicativo controle o fluxo.

    Returns:
        Instância única de AppState para o processo.
    """
    global _APP_STATE

    if _APP_STATE is None:
        _APP_STATE = AppState()

    return _APP_STATE
