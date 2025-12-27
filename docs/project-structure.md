# Project Structure

Este documento descreve a **estrutura atual do repositório**
**NiceGui-App-Template** e explica o papel de cada pasta e arquivo.

A estrutura foi pensada para:

- funcionar corretamente no Windows
- suportar `src` layout sem hacks
- permitir execução, debug e testes de forma consistente
- crescer de forma controlada

---

## Visão geral

```

NiceGui-App-Template/
├─ .vscode/
├─ docs/
├─ assets/
├─ src/
├─ tests/
├─ pyproject.toml
├─ requirements.txt
└─ README.md

```

---

## 📁 `.vscode/`

Configurações do **Visual Studio Code** para padronizar o ambiente.

- `extensions.json`
  Extensões recomendadas para o projeto.

- `settings.json`
  Ajustes do editor (Python, Ruff, formatação, etc.).

- `launch.json`
  Configuração de debug que executa o aplicativo como **módulo**
  (`python -m nicegui_app_template`).

---

## 📁 `docs/`

Documentação do projeto.

- `development-environment.md`
  Como preparar o ambiente de desenvolvimento no Windows.

- `run-the-app.md`
  Como executar, debugar e testar o aplicativo usando `src` layout.

- `project-structure.md`
  Este documento.

---

## 📁 `assets/`

Arquivos estáticos e recursos visuais.

- `assets/css/`
  CSS global e customizações futuras.

- `assets/icons/`
  Ícones do aplicativo (ex.: `.ico` para Windows).

- `assets/images/`
  Imagens gerais (logos, screenshots, etc.).

---

## 📁 `src/`

Todo o código Python do projeto fica dentro da pasta `src`.
Este padrão evita imports acidentais e prepara o projeto para empacotamento.

### 📦 `src/nicegui_app_template/`

Pacote principal da aplicação.

```

src/nicegui_app_template/
├─ **init**.py
├─ **main**.py
├─ app.py
└─ ui/
├─ **init**.py
└─ index.py

```

### `__main__.py`

Permite executar o aplicativo como módulo:

```powershell
python -m nicegui_app_template
```

Este é o **modo correto** de execução em projetos com `src` layout.

---

### `app.py`

Ponto de entrada lógico do aplicativo.

Responsabilidades atuais:

- conter a função `main()`
- chamar a montagem da UI
- incluir funções simples de exemplo (ex.: `add`) para validação de testes

Neste estágio, o arquivo é mantido propositalmente simples.

---

### `ui/index.py`

Responsável por montar a interface do usuário.

Atualmente contém:

- um Hello World básico com NiceGUI

No futuro, este módulo evolui para:

- layout
- páginas
- navegação
- temas

---

## 📁 `tests/`

Testes automatizados usando **pytest**.

```
tests/
├─ test_smoke.py
└─ test_math.py
```

### Características importantes

- Não existe `conftest.py`
- Não há manipulação manual de `sys.path`
- Os testes dependem do projeto estar instalado em modo editável

Isso é intencional e garante que:

- os testes refletem o uso real do pacote
- erros de import não sejam mascarados

---

### `test_smoke.py`

Teste de fumaça simples para validar:

- imports do pacote
- estrutura básica do projeto

---

### `test_math.py`

Teste propositalmente simples para validar:

- funcionamento do pytest
- descoberta de testes
- imports corretos no `src` layout

Usa uma função pura (`add`) definida em `app.py`.

---

## 📄 `pyproject.toml`

Arquivo central de configuração do projeto.

Responsável por:

- definir o pacote Python
- configurar o `src` layout
- permitir instalação editável (`pip install -e .`)
- configurar o pytest

Este arquivo é essencial para que:

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

- evita ajustes manuais de PYTHONPATH
- facilita debug
- prepara o projeto para crescer
- reduz problemas para iniciantes

---
