# Run the App (Windows)

Este documento explica **como executar o NiceGui-App-Template no Windows**
utilizando o **src layout**.

> ⚠️ Importante
> Quando um projeto usa `src/`, o pacote **precisa ser instalado no ambiente**
> para que o Python consiga encontrá-lo.
> Por isso, o uso de **instalação editável (`pip install -e .`) é obrigatório**.

---

## ✅ Pré-requisitos

Antes de continuar, confirme:

- Windows
- Python **3.13**
- Ambiente virtual (`.venv`) ativo
- Terminal aberto **na raiz do projeto**

---

## 1️⃣ Ativar o ambiente virtual

```powershell
.venv\Scripts\Activate.ps1
```

Confirme:

```powershell
python --version
```

Esperado:

```text
Python 3.13.x
```

---

## 2️⃣ Instalar as dependências

```powershell
pip install -r requirements.txt
```

---

## 3️⃣ Instalar o projeto em modo editável (obrigatório)

Este passo é essencial para projetos com `src/` layout.

```powershell
pip install -e .
```

📌 O ponto (`.`) indica a pasta atual (raiz do projeto).

Após esse comando:

- o pacote `nicegui_app_template` fica disponível no Python
- `python -m nicegui_app_template` passa a funcionar
- pytest encontra os módulos corretamente
- debug no VS Code funciona sem ajustes extras

---

## 4️⃣ Executar o aplicativo

Execute sempre **como módulo**, nunca chamando arquivos dentro de `src/`.

```powershell
python -m nicegui_app_template
```

Se tudo estiver correto, o terminal exibirá algo como:

```text
Running on http://localhost:8080
```

Abra o endereço no navegador.

---

## 🚫 O que **não** fazer (com src layout)

❌ Não execute:

```powershell
python src\nicegui_app_template\app.py
```

Isso **não funciona** em projetos com `src/` layout e causa erros como:

- `ModuleNotFoundError`
- imports quebrados
- comportamento inconsistente

---

## 5️⃣ Executar os testes

Com o projeto instalado em modo editável:

```powershell
pytest
```

Os testes devem ser encontrados automaticamente.

---

## 🐞 Debug no VS Code

Para debugar, use uma configuração que execute o **módulo**, não o arquivo.

Exemplo de `launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug NiceGUI (src layout)",
      "type": "python",
      "request": "launch",
      "module": "nicegui_app_template",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

Depois:

1. Abra **Run and Debug** no VS Code
2. Selecione **Debug NiceGUI (src layout)**
3. Pressione **F5**

---

## 🧠 Resumo rápido

Em projetos com `src/` layout, o fluxo correto é sempre:

```text
pip install -e .
python -m nicegui_app_template
pytest
```

Esse padrão evita:

- problemas de import
- ajustes manuais de PYTHONPATH
- falhas no debug
- testes não encontrados
