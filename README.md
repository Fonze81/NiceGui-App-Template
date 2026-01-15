# NiceGui-App-Template

![Status](https://img.shields.io/badge/status-alpha-orange)
![Version](https://img.shields.io/github/v/release/Fonze81/NiceGui-App-Template?include_prereleases)

![Python](https://img.shields.io/badge/python-3.13%20only-blue)
![Platform](https://img.shields.io/badge/platform-Windows--first-blue)
![NiceGUI](https://img.shields.io/badge/NiceGUI-3.4+-green)

![Layout](https://img.shields.io/badge/layout-src--layout-informational)
![Code Style](https://img.shields.io/badge/code%20style-ruff-black)
![Tests](https://img.shields.io/badge/tests-pytest-green)

![License](https://img.shields.io/badge/license-MIT-blue)

Este repositório é um **template inicial para criação de aplicações desktop ou web**
utilizando **NiceGUI** com Python, com **foco técnico exclusivo no Windows**.

⚠️ **Status do projeto:**

> Este template encontra-se em estágio **alpha**, sujeito a mudanças estruturais sem aviso prévio.

O objetivo é facilitar o início de novos projetos, oferecendo uma base **organizada,
padronizada e fácil de entender**, preparada principalmente para **aplicações desktop
nativas no Windows**.

---

## 🚀 O que este template oferece

- Estrutura organizada para projetos NiceGUI
- Base preparada para aplicações web e desktop nativas no Windows
- Separação clara entre layout, páginas e infraestrutura
- Ambiente de desenvolvimento padronizado
- Suporte a execução, testes e debug sem configurações manuais
- Estrutura pensada para crescer sem virar bagunça

Este template foi projetado para ser **simples no início** e **evoluir de forma segura**
conforme o projeto cresce.

---

## 📐 Premissas do Template

Este projeto adota decisões técnicas claras, aplicadas de forma consistente em toda a base:

- **Python 3.13** como versão oficial
- Uso de **src layout**
- Execução do aplicativo **como módulo**
- Ambiente sempre isolado em **virtual environment (venv)**
- Foco em aplicações **desktop nativas no Windows**
- Debug e testes integrados desde o início
- Padronização de código com **Ruff**
- Testes automatizados com **Pytest**

Essas decisões não são opcionais e fazem parte do padrão do template.

---

## 🧭 Decisões Arquiteturais

Este template adota decisões arquiteturais **intencionais**, focadas em previsibilidade,
testabilidade e manutenção de longo prazo para aplicações **desktop Windows-first com NiceGUI**.

### Estado (`state`)

O estado da aplicação é **puro** (apenas dados em memória, sem I/O, validações ou dependências
externas) e exposto como **singleton controlado**, adequado para aplicações desktop
single-instance.
➡️ [`state.md`](docs/state.md)

**Trade-off:** validações delegadas às boundaries ou UI; não indicado para cenários
multi-user ou multi-tenant.

---

### Configurações (`settings`)

As configurações persistentes são tratadas como **boundary explícito** entre o estado e o
filesystem (TOML), com round-trip preservando comentários e chaves desconhecidas.
➡️ [`settings.md`](docs/settings.md)

**Trade-off:** mapping manual em troca de controle e segurança.

---

### Logging (`logger`)

O logging possui **lifecycle explícito e idempotente**, com suporte a early logging em memória
e shutdown defensivo.
➡️ [`logger.md`](docs/logger.md)

**Trade-off:** maior complexidade inicial para garantir integridade dos logs.

---

> Estas decisões fazem parte do **contrato arquitetural do template** e não devem ser
> alteradas sem considerar seus impactos.

---

## 🧰 Ambiente de Desenvolvimento

As instruções completas sobre:

- instalação do Python
- editor recomendado
- extensões do VS Code
- ajustes de ambiente no Windows

estão disponíveis em:

➡️ **[Guia de Ambiente de Desenvolvimento](docs/development-environment.md)**

---

## ▶️ Como executar o projeto

Para executar o projeto corretamente no Windows — incluindo:

- criação da venv com Python 3.13
- instalação do projeto em modo editável
- execução do aplicativo
- testes e debug

consulte o guia oficial:

➡️ **[Run the App (Windows)](docs/run-the-app.md)**

Esse documento descreve o **fluxo suportado e validado** para este template.

---

## 🗂️ Estrutura do Projeto

A organização de pastas e arquivos do template é explicada em detalhes em:

➡️ **[Project Structure](docs/project-structure.md)**

Esse guia ajuda a entender:

- onde cada tipo de código deve ficar
- como a interface é organizada
- como separar layout, páginas e infraestrutura
- como o projeto pode crescer de forma sustentável

---

## 📌 Próximas evoluções do template

Este template está em evolução contínua. Entre os próximos passos planejados estão:

- exemplos adicionais de páginas e componentes
- customização visual (CSS, ícones, imagens)
- melhorias para uso como aplicação desktop nativa
- empacotamento do aplicativo em `.exe` no Windows
- consolidação de boas práticas para projetos NiceGUI

A evolução ocorrerá de forma incremental, mantendo a base estável.

---

## 📄 Licença

Projeto pessoal de **Afonso Gilmar Krüger**.
Uso livre para fins de estudo e projetos pessoais.
