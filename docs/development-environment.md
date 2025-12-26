# Ambiente de Desenvolvimento

Este documento explica como preparar o ambiente de desenvolvimento recomendado
para trabalhar com o **NiceGui-App-Template**.

O objetivo é garantir que qualquer pessoa consiga abrir o projeto e começar a
desenvolver com o mínimo de configuração manual.

---

## 🧰 Editor de Código (IDE)

O editor recomendado é o **Visual Studio Code (VS Code)**.

Você pode baixá-lo gratuitamente em:
https://code.visualstudio.com/

O VS Code é indicado porque:

- É fácil de usar
- Funciona em Windows, Linux e macOS
- Possui excelente suporte para Python
- Permite instalar extensões para melhorar a produtividade

---

## 🧩 Extensões do VS Code

Este repositório contém o arquivo:

```

.vscode/extensions.json

```

Ao abrir o projeto no VS Code, ele irá **sugerir automaticamente** a instalação
das extensões recomendadas.

Essas extensões ajudam com:

- Organização do código
- Correção automática de erros simples
- Padronização entre diferentes computadores
- Documentação e testes

### Extensões utilizadas

- **Python**: suporte completo ao desenvolvimento em Python
- **Ruff**: verifica e corrige problemas no código automaticamente
- **Prettier**: formatação de arquivos JSON e Markdown
- **Git Graph**: visualização do histórico do Git
- **Bookmarks**: marca trechos importantes do código
- **Todo Tree**: lista comentários como TODO e FIXME
- **EditorConfig**: mantém o mesmo estilo de código em diferentes ambientes
- **Path Intellisense**: ajuda com caminhos de arquivos
- **Markdown All in One**: facilita a edição de arquivos Markdown

> Não é necessário entender todas as extensões agora.
> Elas funcionam automaticamente e ajudam a manter o projeto organizado.

---

## ⚙️ Ajustes do VS Code

O projeto inclui o arquivo:

```

.vscode/settings.json

```

Esse arquivo configura o VS Code para:

- Formatar o código automaticamente ao salvar
- Organizar imports sem intervenção manual
- Manter um estilo de código consistente
- Melhorar a legibilidade do código

Esses ajustes evitam problemas comuns como:

- Código com estilos diferentes
- Imports desorganizados
- Erros simples que passam despercebidos

---

## 🐍 Ambiente Python

É recomendado criar um **ambiente virtual Python** dentro do projeto,
normalmente chamado de:

```

.venv

```

Isso ajuda a:

- Isolar dependências do projeto
- Evitar conflitos com outros projetos Python
- Facilitar a reprodução do ambiente em outra máquina

O VS Code já está configurado para tentar usar esse ambiente automaticamente,
caso ele exista.

---

## 📌 Observações

- As configurações fazem parte do template
- Você não precisa alterar nada para começar
- Ajustes pessoais podem ser feitos localmente, sem alterar o projeto
