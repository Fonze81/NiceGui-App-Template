# Project Structure

Este documento explica a **estrutura de pastas e arquivos** do projeto
**NiceGui-App-Template**.

O objetivo desta organização é:

- Facilitar o entendimento do projeto
- Evitar código desorganizado conforme o projeto cresce
- Separar claramente responsabilidades
- Ajudar iniciantes a saber **onde colocar cada coisa**

O foco é **Windows** e aplicações **desktop/web com NiceGUI**.

---

## Visão geral da estrutura

```

NiceGui-App-Template/
├─ .vscode/
├─ docs/
├─ assets/
├─ src/
├─ tests/
├─ README.md
├─ requirements.txt
└─ pyproject.toml

```

Cada pasta tem um propósito bem definido, descrito abaixo.

---

## 📁 `.vscode/`

Contém configurações específicas do **Visual Studio Code**.

- `extensions.json`
  Lista de extensões recomendadas para o projeto.

- `settings.json`
  Ajustes do editor (formatação, Ruff, Python, etc.).

Esses arquivos ajudam a garantir um ambiente de desenvolvimento consistente
entre diferentes pessoas.

---

## 📁 `docs/`

Documentação do projeto.

Aqui ficam arquivos que explicam **como o projeto funciona**, sem misturar
documentação com código.

Arquivos iniciais:

- `development-environment.md` → ambiente de desenvolvimento
- `run-the-app.md` → como executar o projeto
- `project-structure.md` → este documento

---

## 📁 `assets/`

Recursos visuais e estáticos do projeto.

Esses arquivos **não são código Python**, mas fazem parte da interface.

### `assets/css/`

- Arquivos de estilo (CSS)
- Usados para customização visual futura

### `assets/icons/`

- Ícones da aplicação
- Inclui o ícone principal do app (`.ico`), usado no Windows

### `assets/images/`

- Imagens gerais (logos, banners, screenshots, etc.)

---

## 📁 `src/`

Contém **todo o código Python da aplicação**.

O código fica dentro de um pacote real (`nicegui_app_template`), o que:

- Evita imports soltos
- Facilita testes
- Ajuda no empacotamento futuro

---

## 📦 `src/nicegui_app_template/`

Pacote principal da aplicação.

### `app.py`

Ponto de entrada do aplicativo.

Responsável por:

- Inicializar o NiceGUI
- Configurar execução (web ou desktop)
- Chamar a montagem da interface

---

### `settings.py`

Arquivo de configurações da aplicação.

Usado para:

- Ajustes gerais
- Flags de comportamento
- Centralizar configurações simples

---

## 📁 `core/`

Infraestrutura central da aplicação.

Aqui ficam elementos que **todo o app pode usar**, mas que não são UI.

### `state.py`

Estado compartilhado da aplicação.

Usado para:

- Compartilhar dados entre páginas
- Evitar variáveis globais soltas
- Manter informações simples (status, flags, mensagens)

Não é um sistema complexo de estado — apenas um ponto central organizado.

---

### `logger.py`

Configuração do logger da aplicação.

Usado para:

- Padronizar logs
- Evitar uso de `print`
- Facilitar evolução futura (arquivos, níveis, etc.)

---

## 📁 `ui/`

Tudo relacionado à **interface do usuário** (NiceGUI).

### `index.py`

Arquivo responsável por montar a interface.

Normalmente:

- Aplica tema e CSS
- Monta layout global
- Registra páginas (SPA)

---

### 📁 `ui/theme/`

Customização visual da aplicação.

Usado para:

- Aplicar CSS global
- Registrar ícones e assets
- Centralizar decisões visuais

Arquivos:

- `custom_css.py` → aplicação de CSS
- `assets.py` → caminhos e registro de ícones/imagens

---

### 📁 `ui/layout/`

Estrutura fixa da interface.

Aqui ficam componentes reutilizáveis como:

- Navbar
- Drawer (menu lateral)
- Footer

Esses elementos aparecem em várias páginas.

---

### 📁 `ui/pages/`

Conteúdo das páginas da aplicação.

Cada arquivo representa uma página, por exemplo:

- `home.py`
- `hello.py`
- `about.py`

Essas páginas são usadas pelo sistema de navegação SPA do NiceGUI.

---

## 📁 `services/`

Camada reservada para **integrações e serviços externos**.

Exemplos futuros:

- Banco de dados
- APIs
- Integrações com sistemas externos

No início, pode ficar vazia. Ela existe para evitar misturar essas responsabilidades
com UI ou lógica central.

---

## 📁 `utils/`

Funções utilitárias e helpers.

Usado para:

- Funções auxiliares
- Código reutilizável que não pertence ao core

Exemplo:

- `window_state.py` → persistência de posição e tamanho da janela

---

## 📁 `tests/`

Testes automatizados do projeto.

Mesmo que o projeto comece simples, essa pasta já existe para incentivar
boas práticas desde o início.

---

## 🧠 Resumo

Essa estrutura foi pensada para:

- Ser fácil de entender
- Evitar crescimento desorganizado
- Funcionar bem com NiceGUI
- Preparar o projeto para aplicações desktop no Windows

Você não precisa usar tudo desde o primeiro dia.
A estrutura existe para **acompanhar o crescimento do projeto**, não para complicar.
