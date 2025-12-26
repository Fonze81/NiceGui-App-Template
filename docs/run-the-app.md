# Run the App (Windows)

Este documento mostra como executar o **NiceGui-App-Template** no Windows pela primeira vez.

O objetivo é ser direto e funcionar mesmo para iniciantes.

---

## ✅ Pré-requisitos

Antes de continuar, confirme:

- Você está no **Windows**
- Você instalou o **Python 3.13**
- Você abriu o projeto no **VS Code** (recomendado)

Se quiser conferir a versão do Python:

```powershell
python --version
```

O resultado esperado é:

```powershell
Python 3.13.x
```

---

## 1) Abrir um terminal no diretório do projeto

No VS Code:

- Menu **Terminal** → **New Terminal**

Ou no Windows:

- Abra o PowerShell e navegue até a pasta do projeto

---

## 2) Criar a VENV (somente na primeira vez)

Para garantir que a VENV será criada com o Python 3.13, use:

```powershell
py -3.13 -m venv .venv
```

---

## 3) Ativar a VENV

```powershell
.venv\Scripts\Activate.ps1
```

### Se aparecer erro de Execution Policy

Se você receber um erro dizendo que a execução de scripts está bloqueada, execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Confirme com **Y** e tente ativar novamente:

```powershell
.venv\Scripts\Activate.ps1
```

---

## 4) Instalar as dependências

Com a VENV ativa, instale os pacotes:

```powershell
pip install -r requirements.txt
```

---

## 5) Executar o aplicativo

> Ajuste o comando abaixo caso o ponto de entrada do projeto seja diferente no seu template.

### Opção A (recomendada): executar como módulo

```powershell
python -m nicegui_app_template
```

### Opção B: executar o arquivo diretamente

```powershell
python src\nicegui_app_template\app.py
```

---

## 6) Abrir no navegador

Ao rodar, o terminal mostrará um endereço local, normalmente:

- `http://localhost:8080`

Abra esse endereço no seu navegador.

---

## ✅ Verificação rápida

Se tudo estiver correto, você deve ver:

- A página inicial do template
- Navegação funcionando (SPA)
- Layout com menu/topo/rodapé (se já estiver implementado)

---

## 🛠️ Problemas comuns

### "python não é reconhecido"

- Reinstale o Python 3.13 marcando **Add Python to PATH**
- Feche e reabra o terminal após instalar

### VENV ativa, mas Python não é 3.13

- Remova a `.venv` e recrie garantindo o comando:

```powershell
py -3.13 -m venv .venv
```

### Porta ocupada

Se a porta padrão estiver ocupada, pare o app e ajuste a porta no `settings.py`
(se o template expõe essa configuração).
