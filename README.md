# NiceGui-App-Template

Este repositório é um **template inicial** para criar aplicações **desktop ou web**
utilizando **NiceGUI** com Python, **com foco exclusivo no Windows**.

O objetivo é facilitar o início de novos projetos, oferecendo uma base organizada,
padronizada e fácil de entender, preparada principalmente para **aplicações nativas
no Windows**.

---

## 🚀 O que este template oferece

- Estrutura básica organizada para projetos NiceGUI
- Base preparada para aplicações web e **desktop nativas no Windows**
- Separação clara entre layout, páginas e utilidades
- Configurações prontas para um ambiente de desenvolvimento consistente no Windows

Este projeto foi pensado para crescer de forma simples, sem complicações desnecessárias.

---

## 🧰 Ambiente de Desenvolvimento

As instruções completas sobre instalação do editor, extensões recomendadas
e ajustes do ambiente de desenvolvimento estão disponíveis no documento:

➡️ **[Guia de Ambiente de Desenvolvimento](docs/development-environment.md)**

---

## 🐍 Instalação do Python (Windows)

### Versão recomendada

Este projeto **utiliza Python 3.13 no Windows**.

🔴 **Importante:**
Apesar de já existir uma versão mais recente do Python (3.14, no momento),
**ela não deve ser utilizada neste projeto**.

### Por que Python 3.13?

Para criar **aplicações desktop nativas no Windows**, algumas bibliotecas são
necessárias. Uma das principais é o **`pythonnet`**.

Atualmente, o `pythonnet` **não é compatível com o Python 3.14**.
Isso impede a criação de aplicações nativas no Windows quando essa versão é usada.

Por esse motivo, o template foi padronizado para **Python 3.13**, garantindo:

- Compatibilidade com bibliotecas essenciais
- Funcionamento correto em modo desktop
- Menos problemas durante o desenvolvimento

---

### Download do Python 3.13

Baixe o instalador oficial do Python para Windows em:

https://www.python.org/downloads/

Durante a instalação:

- Marque a opção **“Add Python to PATH”**
- Utilize as opções padrão do instalador

Após a instalação, verifique no **Prompt de Comando** ou **PowerShell**:

```powershell
python --version
```

````

O resultado esperado é algo como:

```text
Python 3.13.x
```

---

## 🧪 Criação do Ambiente Virtual (VENV)

É altamente recomendado criar um **ambiente virtual Python** para este projeto.

Isso permite:

- Isolar dependências do projeto
- Evitar conflitos com outros projetos Python
- Garantir que o ambiente funcione corretamente no Windows

### Criando a VENV

Na pasta raiz do projeto, execute:

```powershell
py -3.13 -m venv .venv
```

---

## ⚠️ PowerShell: Política de Execução (Importante)

Ao tentar ativar a VENV no Windows, **usuários iniciantes frequentemente encontram um erro**
relacionado à **política de execução do PowerShell**.

### Erro comum

Ao executar:

```powershell
.venv\Scripts\Activate.ps1
```

Pode aparecer uma mensagem semelhante a:

> _"A execução de scripts foi desabilitada neste sistema."_

Isso **não é um erro do Python nem do projeto**.
É uma configuração de segurança padrão do Windows.

---

### Como resolver (recomendado)

Abra o **PowerShell como usuário normal** (não precisa ser administrador) e execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Quando solicitado, confirme com **Y**.

✅ Essa configuração:

- Afeta **somente o usuário atual**
- Permite executar scripts locais (como a VENV)
- Mantém a segurança do sistema

---

### Ativando a VENV após o ajuste

Depois disso, ative normalmente:

```powershell
.venv\Scripts\Activate.ps1
```

O terminal indicará que o ambiente virtual está ativo.

---

## 🧠 Observação importante

Essa configuração é necessária **apenas uma vez por usuário**.
Após ajustada, você não precisará repetir esse passo em outros projetos Python.

---

### Integração com o VS Code

O VS Code está configurado para:

- Detectar automaticamente a pasta `.venv`
- Utilizar o interpretador correto
- Aplicar lint, formatação e organização de código automaticamente

Caso o VS Code solicite a seleção do interpretador Python,
escolha o Python localizado dentro da pasta `.venv`.

---

## 📌 Próximos conteúdos (em evolução)

Este template será expandido gradualmente para incluir:

- Como executar o projeto no Windows
- Estrutura de pastas
- Conceitos básicos de SPA com NiceGUI
- Exemplos práticos de uso
- Uso como aplicação desktop nativa no Windows

---

## 📄 Licença

Projeto pessoal de **Afonso Gilmar Krüger**.
Uso livre para fins de estudo e projetos pessoais.
````
