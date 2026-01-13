# ▶️ Run the App (Windows)

Este documento descreve **o procedimento para executar o NiceGui-App-Template no Windows**, conforme definido no README principal do projeto.

Ele cobre:

- criação do ambiente virtual **fixado em Python 3.13**
- instalação correta para projetos com **src layout**
- execução, testes e debug **sem configuração manual**

---

## 📌 Premissas do Projeto

Este projeto adota oficialmente as seguintes premissas:

- **Python 3.13 é obrigatório**
- O sistema pode ter **múltiplas versões do Python instaladas**
- O projeto **sempre roda dentro de uma venv**
- O layout do projeto é **src/**
- O pacote **deve ser instalado em modo editável**
- O aplicativo é executado **oficialmente como módulo**
  (execuções como script são restritas ao modo de desenvolvimento)
- O **debug já está configurado no repositório**

---

## ✅ Pré-requisitos

Antes de iniciar, confirme:

- Windows
- Python **3.13 instalado** (não precisa ser a versão padrão do sistema)
- PowerShell
- Acesso à raiz do projeto (`pyproject.toml`, `requirements.txt`)

> ℹ️ Nota
> Mesmo que o sistema tenha Python 3.10, 3.11 ou 3.12, **a venv deste projeto deve usar exclusivamente Python 3.13**.

---

## 1️⃣ Verificar as versões de Python disponíveis

Liste as versões instaladas no sistema:

```powershell
py -0p
```

Exemplo:

```text
 -3.10   C:\Python310\python.exe
 -3.12   C:\Python312\python.exe
 -3.13   C:\Python313\python.exe
```

Confirme que o **Python 3.13 está disponível**.

---

## 2️⃣ Criar a venv com Python 3.13

A criação da venv **deve fixar explicitamente a versão**:

```powershell
py -3.13 -m venv .venv
```

---

## 3️⃣ Ativar a venv

```powershell
.venv\Scripts\Activate.ps1
```

Valide:

```powershell
python --version
```

Esperado:

```text
Python 3.13.x
```

---

## 4️⃣ Instalar dependências

```powershell
pip install -r requirements.txt
```

---

## 5️⃣ Instalar o projeto em modo editável

```powershell
pip install -e .
```

---

## 6️⃣ Executar o aplicativo

```powershell
python -m nicegui_app_template
```

---

## 🚫 Execuções não suportadas

❌ Não execute:

```powershell
python src\nicegui_app_template\app.py
```

---

## 7️⃣ Executar os testes

```powershell
pytest
```

---

## 🐞 Debug no VS Code

O repositório **já inclui um `launch.json` funcional**.

Para debugar:

1. Run and Debug
2. Debug NiceGUI (src layout)
3. F5

---

## 🧠 Fluxo oficial (resumo)

```text
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
python -m nicegui_app_template
pytest
```

---

## 🔄 Modos de Execução do Aplicativo

O NiceGUI App Template suporta **dois modos de execução**, cada um com um objetivo específico.

Essa separação é **intencional** e existe para lidar corretamente com as
limitações do Windows, do `multiprocessing` e do auto-reload do NiceGUI.

---

### ▶️ Execução Oficial (modo estável)

```powershell
python -m nicegui_app_template
```

**Características:**

- Executa o aplicativo como **pacote**
- Utiliza o entrypoint oficial (`__main__.py`)
- Auto-reload **desativado**
- Modo mais estável e previsível

**Quando usar:**

- Uso normal do template
- Testes manuais
- Execução empacotada (PyInstaller)
- Ambientes onde estabilidade é prioridade

---

### 🛠️ Execução em Modo Desenvolvimento (com reload)

```powershell
python dev_run.py
```

> ℹ️ Nota
> Este modo existe exclusivamente para permitir auto-reload no Windows
> e **não substitui o fluxo oficial de execução do template**.

**Características:**

- Executa o aplicativo como **script**
- Auto-reload **ativado**
- Reinicia automaticamente ao alterar arquivos
- Entrada compatível com `multiprocessing` no Windows

**Quando usar:**

- Desenvolvimento ativo
- Ajustes frequentes em UI e layout
- Iterações rápidas

---

## ❓ Por que existem dois modos?

O auto-reload do NiceGUI utiliza **multiprocessing**.

No Windows, esse mecanismo funciona no modo **spawn**, o que significa que
o processo filho **reexecuta o ponto de entrada** da aplicação.

Quando o aplicativo é iniciado como módulo:

```powershell
python -m nicegui_app_template
```

com `reload=True`, o processo filho **nem sempre consegue reencontrar**
o ponto onde `ui.run()` é chamado, resultando no erro:

```
RuntimeError:
You must call ui.run() to start the server.
```

Por esse motivo, o template separa explicitamente:

- **Execução oficial** → sem reload (máxima estabilidade)
- **Execução de desenvolvimento** → com reload, via script dedicado

Essa abordagem evita erros intermitentes e mantém o comportamento previsível.

Esse comportamento é uma limitação conhecida da combinação atual entre
Windows, multiprocessing e auto-reload do NiceGUI, e **não representa
um erro de arquitetura do template**.

---

## 📌 Resumo rápido

```text
Execução oficial (sem reload):
    python -m nicegui_app_template

Execução de desenvolvimento (com reload):
    python dev_run.py
```
