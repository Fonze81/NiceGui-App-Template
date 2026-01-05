# src/nicegui_app_template/core/state.py

from __future__ import annotations

# =============================================================================
# Estado da Aplicação
# =============================================================================
# Este módulo define o estado central do aplicativo de forma "pura".
# "Puro" aqui significa: sem dependências de UI, sem leitura/escrita de arquivos,
# sem acoplamento ao logger e sem regras de validação. Essa decisão mantém o
# estado testável e reaproveitável em qualquer contexto de execução.

from dataclasses import dataclass, field  # dataclasses reduzem boilerplate e deixam o estado explícito.
from pathlib import Path  # Path é usado no core para representar caminhos de forma robusta no SO.
from typing import Optional  # Optional explicita campos que podem não estar disponíveis em runtime.


# =============================================================================
# Subestados — domínios lógicos do aplicativo
# =============================================================================
# A separação em subestados evita um "Config" monolítico e favorece manutenção
# incremental. Cada grupo concentra atributos com coesão forte (mesma motivação).


@dataclass(slots=True)
class AppMetaState:
    """
    Metadados gerais do aplicativo.

    Motivo de existir:
    - Concentrar informações globais do app
    - Facilitar uso no bootstrap (ex.: ui.run) sem espalhar constantes
    """

    # Nome lógico do aplicativo (usado em título e para identificar recursos).
    name: str = "nicegui_app_template"

    # Versão do aplicativo (informativa; útil para diagnóstico e suporte).
    version: str = "0.0.0"

    # Idioma padrão da interface (controle centralizado evita divergências).
    language: str = "pt-BR"

    # Flag típica para onboarding, migrações e ajustes iniciais.
    first_run: bool = True

    # Indica se o app roda em modo desktop nativo (impacta reload/frameless etc.).
    native_mode: bool = True

    # Porta HTTP usada pelo NiceGUI (parametrizável por settings).
    port: int = 8080


@dataclass(slots=True)
class WindowState:
    """
    Estado persistente relacionado à janela do aplicativo.

    Motivo de existir:
    - Lembrar posição e tamanho entre execuções
    - Centralizar parâmetros usados por window_args e persistência via frontend
    """

    # Posição horizontal da janela (coordenada de tela).
    x: int = 100

    # Posição vertical da janela (coordenada de tela).
    y: int = 100

    # Largura atual/padrão da janela (deve ser validada no boundary).
    width: int = 800

    # Altura atual/padrão da janela (deve ser validada no boundary).
    height: int = 600

    # Indica se a janela inicia maximizada (estado do SO).
    maximized: bool = False

    # Indica se a janela inicia em fullscreen (estado do SO).
    fullscreen: bool = False

    # Índice do monitor em setups multi-monitor (persistência e restauração).
    monitor: int = 0

    # Chave de persistência para uso em storage (SPA / frontend).
    storage_key: str = "nicegui_window_state_spa"


@dataclass(slots=True)
class UiState:
    """
    Estado de preferências visuais da interface.

    Motivo de existir:
    - Centralizar preferências de aparência
    - Facilitar binding em ViewModels sem acoplar o core à UI
    """

    # Tema visual (ex.: "dark" / "light"); interpretação é responsabilidade da UI.
    theme: str = "dark"

    # Escala de fonte global; a UI decide como aplicar (classes, CSS etc.).
    font_scale: float = 1.0

    # Modo de densidade reduzida; útil para telas menores e maior produtividade.
    dense_mode: bool = False

    # Cor de destaque; formato e aplicação ficam a cargo da UI.
    accent_color: str = "#0057B8"


@dataclass(slots=True)
class LogState:
    """
    Estado de configuração de logging.

    Observações importantes:
    - `path` é do tipo Path (infraestrutura do SO)
    - Conversão Path <-> str e validação pertencem ao boundary (settings/UI)
    - O logger consome o estado, mas o estado não conhece o logger
    """

    # Caminho do arquivo de log (infraestrutura); evita strings soltas no core.
    path: Path = Path("logs/app.log")

    # Nível de log como string para facilitar settings e binding (ex.: "INFO").
    level: str = "INFO"

    # Ativa/desativa logs em console; decisão de handler fica no logger.
    console: bool = True

    # Capacidade do buffer em memória antes do flush (bootstrap early logs).
    buffer_capacity: int = 500

    # Rotação por tamanho (ex.: "5 MB"); parse para bytes ocorre no boundary.
    rotation: str = "5 MB"

    # Quantidade de arquivos de backup (mapeia para backupCount quando aplicável).
    retention: int = 3


@dataclass(slots=True)
class BehaviorState:
    """
    Estado para flags comportamentais do aplicativo.

    Motivo de existir:
    - Evitar flags globais espalhadas
    - Centralizar decisões de comportamento para manter previsibilidade
    """

    # Indica se o app deve salvar ajustes automaticamente (quando o fluxo permitir).
    auto_save: bool = True


# =============================================================================
# Estado Central — fonte de verdade em runtime
# =============================================================================
# Esta estrutura agrega os subestados e adiciona campos de runtime para
# diagnóstico (sucesso/erro de load/save). Esses campos não são persistência
# por padrão: persistência é responsabilidade do módulo de settings.


@dataclass(slots=True)
class AppState:
    """
    Estado central do aplicativo.

    Responsabilidades:
    - Agregar todos os subestados
    - Ser a fonte de verdade durante a execução
    - Ser simples, previsível e fácil de testar

    Não é responsabilidade deste objeto:
    - Ler ou escrever arquivos
    - Validar dados recebidos do mundo externo
    - Conhecer UI, TOML, JSON ou handlers de logging
    """

    # Subestado com metadados globais (bootstrap/identidade).
    meta: AppMetaState = field(default_factory=AppMetaState)

    # Subestado com geometria e persistência de janela.
    window: WindowState = field(default_factory=WindowState)

    # Subestado com preferências visuais (aplicadas na UI).
    ui: UiState = field(default_factory=UiState)

    # Subestado de logging (consumido pelo bootstrap do logger).
    log: LogState = field(default_factory=LogState)

    # Subestado de comportamento (flags de fluxo e automações).
    behavior: BehaviorState = field(default_factory=BehaviorState)

    # Caminho efetivo do arquivo de settings carregado (runtime, não persistente).
    settings_file_path: Optional[Path] = None

    # Indica se o último load de settings foi bem-sucedido (runtime).
    last_load_ok: bool = False

    # Indica se o último save de settings foi bem-sucedido (runtime).
    last_save_ok: bool = False

    # Última mensagem de erro (para UI/diagnóstico); evita exceções em cascata.
    last_error: Optional[str] = None


# =============================================================================
# Singleton pragmático
# =============================================================================
# Justificativa:
# - Em aplicações desktop é comum existir uma única instância de estado global
# - Evita injeção excessiva de dependências em módulos pequenos
# - Mantém acesso simples, mas explícito (via função)
#
# Importante:
# - Este singleton não executa lógica de inicialização complexa
# - Ele apenas fornece uma instância consistente para o processo


_APP_STATE: Optional[AppState] = None  # Cache do estado global do processo; evita múltiplas instâncias acidentais.


def get_app_state() -> AppState:
    """
    Retorna a instância singleton do estado do aplicativo.

    Motivo:
    - Simplificar acesso global ao estado
    - Evitar múltiplas instâncias inconsistentes no mesmo processo
    - Manter previsibilidade do fluxo em um app desktop
    """
    global _APP_STATE  # O singleton é controlado por módulo para manter simplicidade e previsibilidade.
    if _APP_STATE is None:  # Inicialização lazy para não impor custo antes de ser necessário.
        _APP_STATE = AppState()  # Instância padrão; será populada pelo módulo settings em seguida.
    return _APP_STATE  # Retorno da instância única para consumo por módulos do app.
