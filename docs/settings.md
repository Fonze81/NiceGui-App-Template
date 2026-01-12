# Módulo `settings` – NiceGUI App Template

## 📌 Visão Geral

O módulo `settings` é responsável por **gerenciar configurações persistentes**
do aplicativo por meio de um arquivo `settings.toml`.

Ele atua como um **boundary explícito** entre:

- o mundo externo (arquivo de texto, encoding, disco),
- e o mundo interno da aplicação (`AppState`).

Este módulo **não contém lógica de UI**, **não define estado em memória**
e **não configura o logger**.
Seu papel é exclusivamente **I/O, conversão e fallback**.

---

## 🧭 Responsabilidades Principais

O módulo `settings` é responsável por:

1. Resolver a localização do arquivo `settings.toml`
2. Ler e interpretar seu conteúdo (TOML)
3. Aplicar valores válidos no `AppState`
4. Persistir o estado configurável de volta ao arquivo
5. Preservar comentários, ordem e estilo do arquivo existente
6. Garantir robustez em caso de erro, corrupção ou campos ausentes

---

## 🏗️ Princípios de Design

### Boundary explícito

Este módulo concentra **todas as interações com o mundo externo**, incluindo:

- `str` ↔ `Path`
- parsing de números e booleanos
- normalização de caminhos
- fallback para valores padrão
- leitura e escrita em disco

O `AppState` permanece **completamente puro**, sem parsing, sem I/O e sem dependências externas.

---

### Falha segura (Fail-safe)

Erros de leitura ou escrita **não devem derrubar a aplicação**.

Decisões adotadas:

- Operações retornam `False` em falha
- Exceções não escapam do fluxo normal
- Detalhes ficam registrados em `AppState.last_error`
- Valores inválidos sofrem fallback para defaults seguros

---

### Persistência com Round-Trip (tomlkit)

A persistência utiliza **round-trip real via `tomlkit`**.

Isso significa que:

- O arquivo `settings.toml` existente é **editado in-place**
- Comentários, ordem e espaçamento são preservados
- Apenas **chaves conhecidas pelo template** são atualizadas
- Chaves desconhecidas permanecem intactas

O módulo **não regenera** o arquivo se ele já existir.

---

## 📦 Dependências

- **Python**: 3.13+
- **TOML**: `tomlkit`

A dependência de `tomlkit` é **intencional** e **confinada ao módulo `settings`**.

---

## 📁 Localização do Arquivo `settings.toml`

Por padrão, o arquivo é procurado em:

```
<diretório de execução>/settings.toml
```

### Exemplos

**Desenvolvimento**

```
project_root/
 ├── settings.toml
 └── logs/
```

**Produção (desktop)**

```
MyApp/
 ├── MyApp.exe
 ├── settings.toml
 └── logs/
```

O caminho pode ser sobrescrito via variável de ambiente:

```
APP_ROOT=/caminho/customizado
```

---

## 📖 Leitura de Configurações

### `load_settings(...)`

Responsável por:

- Resolver o caminho do arquivo
- Ler o conteúdo TOML
- Aplicar valores no `AppState`
- Atualizar flags de runtime (`last_load_ok`, `last_error`)

Comportamento em falha:

- Arquivo inexistente → retorna `False`
- TOML inválido → retorna `False`
- O aplicativo continua com defaults

O módulo **não cria automaticamente** o arquivo ausente.

---

## 💾 Escrita de Configurações

### `save_settings(...)`

Responsável por:

- Atualizar apenas chaves conhecidas no documento TOML
- Preservar comentários e chaves externas
- Escrever o arquivo de forma atômica
- Atualizar flags de runtime (`last_save_ok`, `last_error`)

---

### Escrita Atômica

A escrita ocorre em três passos:

1. Gravação em arquivo temporário (`.tmp`)
2. Escrita completa do conteúdo
3. Substituição do arquivo original

Isso reduz o risco de corrupção do arquivo em cenários de falha.

---

## 🧠 Aplicação dos Dados no Estado

### `apply_settings_to_state(...)`

Função responsável por:

- Ler valores por caminho lógico (`app.window.width`)
- Fazer casting leve (`int`, `bool`, `float`, `str`)
- Aplicar defaults do próprio estado
- Executar validações mínimas com fallback

Exemplos de validações leves:

- Porta fora do intervalo → fallback
- Tamanho de janela inválido → mínimos seguros
- Nível de log desconhecido → `INFO`
- Rotação inválida → `"5 MB"`

Validações complexas **não pertencem a este módulo**.

---

## 🧹 Persistência e Normalização

- `Path` é persistido como **string**
- Separadores são normalizados para `/`
- Diferenças de SO não vazam para o arquivo

---

## ⏱️ Campos Persistentes vs Runtime

Somente campos **explicitamente mapeados** são persistidos.

Campos de runtime **nunca são gravados**, como:

- `last_error`
- `last_load_ok`
- `last_save_ok`
- `settings_file_path`

---

## 🔗 Relação com Outros Módulos

### `state.py`

- Define a estrutura do estado
- Não conhece TOML nem disco
- Não depende de `settings`

---

### UI / ViewModels

- Validam entrada do usuário
- Atualizam o `AppState`
- Chamam `save_settings(...)` explicitamente

---

### Logger

- O `settings` apenas popula `LogState`
- A configuração efetiva ocorre em módulo intermediário

---

## 📐 Regra de Evolução

Ao adicionar um novo campo persistente:

1. Adicionar no subestado correspondente em `state.py`
2. Ler em `apply_settings_to_state(...)`
3. Persistir no updater TOML (`_apply_state_to_document`)

Essa regra garante evolução previsível e compatível.

---

## 🚫 O que não fazer neste módulo

- Não adicionar lógica de UI
- Não importar NiceGUI
- Não executar validações complexas
- Não acessar logger global
- Não persistir campos de runtime
- Não expor estruturas internas do TOML

---

## ✅ Conclusão

O módulo `settings` existe para **proteger o núcleo da aplicação**.

Ele garante que:

- Configurações externas não contaminem o estado
- O aplicativo seja resiliente a falhas
- A persistência seja legível e previsível
- Comentários e ajustes manuais sejam respeitados

Toda a complexidade de I/O, parsing, round-trip e fallback
permanece **estritamente confinada a este módulo**.
