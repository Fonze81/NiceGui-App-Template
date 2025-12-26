# NiceGui-App-Template

Este repositório é um **template inicial** para criar aplicações **desktop ou web**
utilizando **NiceGUI** com Python, **com foco exclusivo no Windows**.

O objetivo é facilitar o início de novos projetos, oferecendo uma base organizada,
padronizada e fácil de entender, preparada principalmente para **aplicações
desktop nativas no Windows**.

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

Após a instalação, verifique no **PowerShell**:

```powershell
python --version
```

O resultado esperado é algo como:

```text
Python 3.13.x
```

---

## 🧪 Criação do Ambiente Virtual (VENV)

É altamente recomendado criar um **ambiente virtual Python** para este projeto.

### Usando explicitamente o Python 3.13

Em sistemas Windows, é comum ter mais de uma versão do Python instalada.
Para garantir que a VENV seja criada **com Python 3.13**, utilize o Python Launcher:

```powershell
py -3.13 -m venv .venv
```

---

## ⚠️ PowerShell: Política de Execução (Importante)

Ao ativar a VENV pela primeira vez, pode aparecer um erro informando que
a execução de scripts está bloqueada.

Isso é uma configuração de segurança padrão do Windows.

### Como resolver

No PowerShell (usuário normal), execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Confirme com **Y** quando solicitado.

Essa configuração:

- Afeta apenas o usuário atual
- É necessária apenas uma vez
- Não compromete a segurança do sistema

---

## ▶️ Ativando a VENV (Windows)

```powershell
.venv\Scripts\Activate.ps1
```

Após a ativação, verifique:

```powershell
python --version
```

Resultado esperado:

```text
Python 3.13.x
```

---

## 📦 Instalação dos Pacotes Python

Todas as dependências do projeto estão listadas no arquivo:

```
requirements.txt
```

Com a VENV ativa, instale os pacotes executando:

```powershell
pip install -r requirements.txt
```

---

## 📦 Sobre os pacotes instalados

Este template utiliza os seguintes pacotes principais:

- **nicegui**
  Framework principal da interface gráfica.

- **pywebview**
  Permite executar a aplicação como um **aplicativo desktop nativo no Windows**.

- **pythonnet**
  Necessário para integração com componentes nativos do Windows.

- **pytest**
  Ferramenta para testes automatizados.

- **ruff**
  Ferramenta para análise e correção automática do código.

- **pyinstaller**
  Utilizado **somente** para gerar o executável (`.exe`).
  Não é necessário para rodar o projeto durante o desenvolvimento.

---

## 📌 Observação importante

- ❌ Não execute o `pyinstaller` agora
- ✅ Primeiro, execute e entenda o projeto
- ✅ O empacotamento será tratado em uma etapa futura

---

## 🔜 Próximos conteúdos (em evolução)

Este template será expandido gradualmente para incluir:

- Como executar o projeto pela primeira vez
- Estrutura de pastas
- Conceitos básicos de SPA com NiceGUI
- Exemplos práticos de uso
- Geração de aplicativo desktop (`.exe`) no Windows

---

## 📄 Licença

Projeto pessoal de **Afonso Gilmar Krüger**.
Uso livre para fins de estudo e projetos pessoais.
