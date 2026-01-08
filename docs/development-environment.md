# Ambiente de Desenvolvimento

Este documento descreve o **ambiente de desenvolvimento recomendado**
para trabalhar com o **NiceGui-App-Template**, conforme as decisões técnicas
definidas no projeto.

O objetivo é garantir que qualquer pessoa consiga **abrir o projeto no VS Code
e começar a desenvolver imediatamente**, com o mínimo de configuração manual.

---

## 📌 Premissas do Ambiente

Este template **adota como padrão técnico**:

- Desenvolvimento focado em **Windows**
- **Python 3.13 obrigatório** (restrição técnica do projeto)
- Execução do projeto sempre dentro de uma **virtual environment**
- **Visual Studio Code** como editor principal recomendado

Essas decisões fazem parte do design do template e **não são opcionais**,
salvo indicação explícita em documentação futura.

---

## 🧰 Editor de Código (IDE)

O editor recomendado é o **Visual Studio Code (VS Code)**.

Download oficial:
https://code.visualstudio.com/

O VS Code foi escolhido porque:

- Possui excelente suporte para Python
- Integra-se bem com ambientes virtuais
- Oferece debug, linting e formatação integrados
- Funciona bem com projetos estruturados em `src/`

Outros editores podem ser usados, mas **o template é otimizado para VS Code**.

---

## 🧩 Extensões do VS Code

Este repositório inclui o arquivo:

```
.vscode/extensions.json
```

Ao abrir o projeto no VS Code, o editor **sugerirá automaticamente**
a instalação das extensões recomendadas.

Essas extensões ajudam com:

- padronização de código
- formatação automática
- organização do projeto
- navegação e leitura do código
- documentação e testes

### Extensões utilizadas

As extensões abaixo são recomendadas automaticamente pelo VS Code ao abrir o projeto.
Elas foram escolhidas para melhorar a produtividade, padronizar o ambiente e facilitar
a leitura, execução e manutenção do código.

- **Python** (`ms-python.python`)  
  Suporte principal ao desenvolvimento em Python.

- **Python Debugger** (`ms-python.debugpy`)  
  Integração do debug Python com o VS Code.

- **Ruff** (`charliermarsh.ruff`)  
  Linting e formatação de código conforme o padrão do projeto.

- **Python Test Adapter** (`littlefoxteam.vscode-python-test-adapter`)  
  Integração do pytest com o Test Explorer.

- **Test Explorer UI** (`hbenl.vscode-test-explorer`)  
  Interface visual para execução e acompanhamento de testes.

- **Prettier** (`esbenp.prettier-vscode`)  
  Formatação de arquivos Markdown, JSON e outros arquivos de apoio.

- **Even Better TOML** (`tamasfe.even-better-toml`)  
  Suporte avançado a arquivos TOML (`pyproject.toml`, `settings.toml`).

- **EditorConfig** (`editorconfig.editorconfig`)  
  Garantia de estilo consistente entre diferentes máquinas e editores.

- **Git Graph** (`mhutchie.git-graph`)  
  Visualização gráfica do histórico de commits.

- **Todo Tree** (`gruntfuggly.todo-tree`)  
  Organização visual de comentários TODO e FIXME.

- **Bookmarks** (`alefragnani.bookmarks`)  
  Marcação de pontos importantes no código.

- **Trailing Spaces** (`shardulm94.trailing-spaces`)  
  Identificação e remoção de espaços em branco desnecessários.

- **Path Intellisense** (`christian-kohler.path-intellisense`)  
  Autocomplete para caminhos de arquivos.

- **Markdown All in One** (`yzhang.markdown-all-in-one`)  
  Facilita a edição e navegação em arquivos Markdown.

- **Dracula Theme** (`dracula-theme.theme-dracula`)  
  Tema visual recomendado (opcional).

- **FiraCode** (`seyyedkhandon.firacode`)  
  Fonte com ligaduras para melhor leitura de código (opcional).

- **Material Icon Theme** (`pkief.material-icon-theme`)  
  Ícones de arquivos e pastas no Explorer do VS Code (opcional).

> As extensões visuais (tema, fonte e ícones) são opcionais,
> mas ajudam a manter uma experiência consistente entre desenvolvedores.

---

## ⚙️ Ajustes do VS Code

O projeto inclui o arquivo:

```
.vscode/settings.json
```

Esse arquivo configura o VS Code para:

- formatar o código automaticamente ao salvar
- organizar imports sem intervenção manual
- aplicar as regras do Ruff
- manter um estilo consistente entre desenvolvedores

Esses ajustes evitam problemas comuns como:

- estilos de código inconsistentes
- imports desorganizados
- correções repetitivas em reviews

---

## 🐍 Ambiente Python

O projeto utiliza um **ambiente virtual Python**, com o nome padrão:

```
.venv
```

Esse ambiente é usado para:

- isolar dependências do projeto
- garantir o uso do **Python 3.13**
- evitar conflitos com outros projetos Python

O VS Code já está configurado para:

- detectar automaticamente a `.venv`
- usar o interpretador correto
- integrar o ambiente ao debug e aos testes

> A criação da venv e a instalação do projeto
> estão documentadas em **Run the App (Windows)**.

---

## 📌 Observações finais

- Todas as configurações fazem parte do template
- Nenhum ajuste manual é necessário para começar
- Configurações pessoais podem ser feitas localmente
- Arquivos dentro de `.vscode/` não devem ser alterados sem necessidade
