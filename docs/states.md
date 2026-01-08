# Módulo `state`

## Visão Geral

O módulo `state` define o **estado central da aplicação** em tempo de execução.
Ele representa a **fonte única de verdade (Single Source of Truth)** para todos os
parâmetros carregados a partir de configurações persistentes ou alterados pela UI.

Este módulo é intencionalmente **puro**.

Isso significa que ele:

- Não realiza leitura ou escrita de arquivos
- Não conhece TOML, JSON ou qualquer formato de serialização
- Não depende de UI (NiceGUI) nem de infraestrutura (logger)
- Não executa validações de entrada
- Não contém lógica de negócio

Seu papel é **representar dados**, não interpretá-los.

---

## Objetivos do Design

Os principais objetivos deste módulo são:

1. **Desacoplamento**

   - Separar completamente dados em memória de I/O e frameworks externos.

2. **Previsibilidade**

   - O estado deve ser simples, explícito e fácil de inspecionar em runtime.

3. **Testabilidade**

   - Qualquer teste pode instanciar o estado sem mocks ou dependências externas.

4. **Evolução controlada**
   - Novos campos podem ser adicionados sem quebrar contratos existentes.

---

## Estrutura do Estado

O estado é dividido em **subestados coesos**, cada um responsável por um domínio
específico da aplicação.

### `AppMetaState`

Metadados globais do aplicativo.

Responsabilidades típicas:

- Nome e versão do aplicativo
- Idioma padrão
- Flags de primeiro uso
- Modo nativo (desktop)
- Porta de execução do NiceGUI

Consumido principalmente no **bootstrap da aplicação**.

---

### `WindowState`

Estado relacionado à janela da aplicação em modo desktop.

Campos comuns:

- Posição (x, y)
- Dimensões (width, height)
- Flags de maximizado / fullscreen
- Monitor ativo
- Chave de persistência para frontend (SPA)

Este estado é usado tanto por argumentos de inicialização quanto por scripts
de persistência via frontend.

---

### `UiState`

Preferências visuais da interface.

Exemplos:

- Tema (dark / light)
- Escala de fonte
- Modo denso
- Cor de destaque

Este subestado é **consumido pela UI**, normalmente através de um ViewModel
com binding do NiceGUI.

---

### `LogState`

Configuração de logging em alto nível.

Características importantes:

- `path` é do tipo `Path` (infraestrutura)
- Níveis e rotação são representados como strings amigáveis
- Não há parsing nem validação neste módulo

O mapeamento de `LogState` para `LogConfig` ocorre em um **módulo de ponte**
(`logger_settings.py`).

---

### `BehaviorState`

Flags comportamentais do aplicativo.

Usado para:

- Habilitar ou desabilitar salvamento automático
- Controlar fluxos futuros de automação

Este subestado evita o uso de flags globais espalhadas pelo código.

---

## `AppState` — Estado Central

A classe `AppState` agrega todos os subestados e adiciona **campos de runtime**
que não devem ser persistidos.

Campos de runtime incluem:

- `settings_file_path`
- `last_load_ok`
- `last_save_ok`
- `last_error`

Esses campos existem para **diagnóstico e UI**, não para persistência.

---

## Singleton Pragmatico

O módulo expõe a função:

```python
get_app_state() -> AppState
```

Essa função implementa um singleton simples e controlado, adequado para aplicações desktop.

Justificativa:

Há apenas um processo

Há apenas um estado global

Evita injeção excessiva de dependências

Mantém acesso explícito (não mágico)

O singleton é lazy, ou seja, só é criado quando solicitado.

---

Relação com Outros Módulos

settings.py

Lê settings.toml

Faz parsing, validação leve e fallback

Aplica valores no AppState

Persiste novamente apenas campos configuráveis

O state não conhece o settings.

---

ViewModels da UI

Convertem tipos de infraestrutura (Path) para tipos editáveis (str)

Realizam validação de entrada

Aplicam alterações de volta ao AppState de forma explícita

O state não conhece a UI.

---

Logger

O logger consome dados do LogState

A conversão para LogConfig ocorre em um módulo intermediário

O state não conhece handlers, níveis internos nem rotação

---

Regras de Evolução (Importantes)

Ao adicionar um novo campo persistente:

1. Adicionar o campo no subestado apropriado em state.py

2. Ler o campo em settings.apply_settings_to_state

3. Persistir o campo em settings.build_raw_from_state

Esse é um contrato explícito, adotado para manter controle total sobre persistência e compatibilidade.

---

O que não fazer neste módulo

Não adicionar lógica de UI

Não adicionar parsing de arquivos

Não adicionar validações complexas

Não acessar variáveis de ambiente

Não importar NiceGUI ou bibliotecas externas

Se alguma dessas necessidades surgir, ela pertence a outro módulo.

---

Conclusão

O módulo state é o coração do aplicativo.

Ele foi projetado para ser:

Simples

Explícito

Desacoplado

Testável

Sustentável a longo prazo

Qualquer complexidade adicional deve existir ao redor do estado, nunca dentro dele.
