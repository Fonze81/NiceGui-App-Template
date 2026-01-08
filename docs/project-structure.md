# Project Structure

Este documento descreve a **estrutura atual do repositório**
**NiceGui-App-Template** e explica o papel de cada pasta e arquivo.

A estrutura foi pensada para:

- funcionar corretamente no **Windows**
- suportar **`src` layout** sem hacks
- permitir **execução, debug e testes** de forma consistente
- crescer de forma controlada e sustentável

---

## Visão geral

```text
NiceGui-App-Template/
├─ assets/
├─ docs/
├─ src/
├─ tests/
├─ pyproject.toml
├─ requirements.txt
└─ README.md
```

---

## 📁 `.vscode/`

Configurações do **Visual Studio Code** para padronizar o ambiente de desenvolvimento.

Arquivos incluídos:

- `extensions.json`
  Lista de extensões recomendadas para o projeto.

- `settings.json`
  Ajustes do editor (Python, Ruff, formatação, testes, etc.).

- `launch.json`
  Configuração de debug que executa o aplicativo como **módulo**
  (`python -m nicegui_app_template`).

Esses arquivos evitam configuração manual e garantem consistência entre máquinas.

---

## 📁 `docs/`

Documentação do projeto.

Arquivos principais:

- `development-environment.md`
  Como preparar o ambiente de desenvolvimento no Windows.

- `run-the-app.md`
  Como criar a venv, instalar dependências, executar, debugar e testar o app.

- `project-structure.md`
  Este documento.

- `logger.md`
  Documentação do sistema de logging.

- `settings.md`
  Documentação do módulo de settings.

- `states.md`
  Documentação do estado da aplicação.

---

## 📁 `assets/`

Arquivos estáticos e recursos visuais.

- `assets/css/`
  CSS global e customizações visuais.

- `assets/icons/`
  Ícones do aplicativo (ex.: `.ico` para Windows).

- `assets/images/`
  Imagens gerais (logos, screenshots, etc.).

Esses arquivos não contêm lógica Python.

---

## 📁 `src/`

Todo o código Python do projeto fica dentro da pasta `src`.

Esse padrão:

- evita imports acidentais
- elimina dependência de `PYTHONPATH`
- prepara o projeto para empacotamento
- reflete o uso real do pacote em produção

---

## 📦 `src/nicegui_app_template/`

Pacote principal da aplicação.

```text
src/nicegui_app_template/
├─ app.py
├─ __main__.py
├─ core/
├─ services/
├─ ui/
└─ utils/
```

---

### `__main__.py`

Permite executar o aplicativo como **módulo Python**:

```powershell
python -m nicegui_app_template
```

Este é o **modo correto** de execução em projetos com `src` layout.

O arquivo é propositalmente pequeno e apenas delega para `app.main()`.

---

### `app.py`

Ponto de entrada lógico do aplicativo.

Responsabilidades:

- definir a função `main()`
- inicializar logger e estado
- carregar settings
- montar a UI
- iniciar o servidor NiceGUI

Este arquivo coordena o bootstrap do app, mas não contém lógica de negócio.

---

## 📁 `core/`

Infraestrutura central do aplicativo.

- `logger.py`
  Sistema de logging com buffer em memória, rotação de arquivos e shutdown limpo.

- `settings.py`
  Leitura, escrita e aplicação de configurações via `settings.toml`.

- `state.py`
  Estado central da aplicação, implementado como dataclasses puras.

Esses módulos não dependem da UI.

---

## 📁 `ui/`

Camada de interface do usuário (NiceGUI).

```text
ui/
├─ index.py
├─ layout/
├─ pages/
└─ theme/
```

- `index.py`
  Monta o layout principal e registra páginas.

### `layout/`

Componentes estruturais reutilizáveis:

- navbar
- drawer
- footer
- menu

### `pages/`

Páginas da aplicação:

- home
- hello
- about

### `theme/`

Customizações visuais:

- assets
- CSS customizado
- integração com o tema do NiceGUI

---

## 📁 `services/`

Camada reservada para **serviços e integrações externas**.

Exemplos futuros:

- integração com SAP
- acesso a banco de dados
- chamadas REST
- automações

Atualmente pode estar vazia ou conter apenas documentação.

---

## 📁 `utils/`

Utilitários auxiliares e código de apoio.

- `window_state.py`
  Persistência e restauração do estado da janela (posição, tamanho, monitor).

---

## 📁 `tests/`

Testes automatizados usando **pytest**.

```text
tests/
└─ core/
   ├─ test_logger.py
   ├─ test_settings.py
   └─ test_state.py
```

Características importantes:

- Não há manipulação manual de `sys.path`
- Os testes dependem do projeto estar instalado em modo editável
- O layout de testes reflete a estrutura real do código

Isso garante que:

- os testes simulam o uso real do pacote
- erros de import não sejam mascarados
- o projeto permaneça saudável ao crescer

---

## 📄 `pyproject.toml`

Arquivo central de configuração do projeto.

Responsável por:

- definir o pacote Python
- configurar o `src` layout
- definir dependências
- configurar o pytest
- configurar o Ruff

Este arquivo é essencial para que:

- `pip install -e .` funcione
- `python -m nicegui_app_template` funcione
- debug no VS Code funcione
- pytest funcione sem hacks

---

## 🧠 Resumo

O fluxo correto do projeto é:

```text
pip install -e .
python -m nicegui_app_template
pytest
```

Essa estrutura:

- evita ajustes manuais de `PYTHONPATH`
- facilita debug
- melhora testabilidade
- prepara o projeto para longo prazo
- reduz problemas para iniciantes
