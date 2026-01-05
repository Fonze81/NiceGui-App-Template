# Módulo `settings`

## Visão Geral

O módulo `settings` é responsável por **gerenciar configurações persistentes**
do aplicativo por meio de um arquivo `settings.toml`.

Ele atua como um **boundary explícito** entre:

- o mundo externo (arquivo de texto, encoding, disco),
- e o mundo interno da aplicação (`AppState`).

Este módulo **não contém lógica de UI**, **não define estado em memória**
e **não conhece detalhes do logger** além do necessário para relatar erros.

---

## Responsabilidades Principais

O módulo `settings` é responsável por:

1. Localizar o arquivo `settings.toml`
2. Ler e interpretar seu conteúdo (TOML)
3. Aplicar os valores no `AppState`
4. Persistir o estado configurável de volta ao arquivo
5. Garantir robustez em caso de erro, corrupção ou campos ausentes

---

## Princípios de Design

### Boundary explícito

Este módulo concentra **todas as conversões e interações com o mundo externo**:

- `str` ↔ `Path`
- parsing de números e booleanos
- fallback para valores padrão
- escrita em disco

O `AppState` permanece completamente isolado dessas responsabilidades.

---

### Falha segura (Fail-safe)

Erros de leitura ou escrita **não devem derrubar a aplicação**.

Decisões adotadas:

- Falhas retornam `False`, não exceções no fluxo normal
- Detalhes do erro ficam em `AppState.last_error`
- Valores inválidos sofrem fallback para defaults seguros

---

### Zero dependência obrigatória de escrita

- A leitura de TOML usa `tomllib` (Python 3.11+) ou `tomli` (Python 3.10)
- A escrita de TOML é feita por um serializador mínimo próprio
- Não há dependência obrigatória de bibliotecas externas para escrita

Isso mantém o template leve e previsível.

---

## Localização do Arquivo `settings.toml`

Por padrão, o arquivo é procurado em:

**<diretório de execução>**/settings.toml

Exemplos:

- Desenvolvimento:

project_root/settings.toml

- Produção (desktop):

```
MyApp/
 ├── MyApp.exe
 ├── settings.toml
 └── logs/
```

O caminho pode ser sobrescrito via variável de ambiente:

APP_ROOT=/caminho/customizado

---

## Leitura de Configurações

### `load_settings(...)`

Responsável por:

- Localizar o arquivo
- Ler o conteúdo TOML
- Aplicar valores no `AppState`
- Atualizar flags de runtime (`last_load_ok`, `last_error`)

Comportamento em falha:

- Arquivo inexistente → retorna `False`
- TOML inválido → retorna `False`
- O aplicativo pode continuar com defaults

O módulo **não cria automaticamente** o arquivo ausente para evitar mascarar
erros de deploy.

---

## Escrita de Configurações

### `save_settings(...)`

Responsável por:

- Serializar apenas os campos configuráveis do `AppState`
- Escrever o arquivo de forma atômica
- Atualizar flags de runtime (`last_save_ok`, `last_error`)

### Escrita Atômica

A escrita ocorre em três passos:

1. Gravação em arquivo temporário (`.tmp`)
2. Flush completo em disco
3. Substituição do arquivo original

Isso garante que o arquivo final esteja sempre íntegro,
mesmo em caso de falha de energia ou travamento.

---

## Aplicação dos Dados no Estado

### `apply_settings_to_state(...)`

Função responsável por:

- Ler valores do TOML por caminho lógico (`app.window.width`)
- Fazer casting leve (`int`, `bool`, `float`, `str`)
- Aplicar defaults do próprio estado
- Realizar validações mínimas com fallback

Exemplos de validações leves:

- Porta fora do intervalo → volta para padrão
- Tamanho de janela inválido → valores mínimos
- Nível de log desconhecido → `INFO`
- Rotação inválida → `"5 MB"`

Validações complexas **não pertencem a este módulo**.

---

## Serialização TOML

### `_to_toml_string(...)`

O serializador TOML implementado é **intencionalmente mínimo**.

Suporta:

- Tabelas aninhadas (`[a]`, `[a.b]`)
- `str`, `int`, `float`, `bool`
- `Path` convertido para string

Limitações conhecidas:

- Não preserva comentários
- Não preserva ordem original
- Não suporta arrays ou tipos avançados

Essas limitações são aceitáveis para um template base controlado.

---

## Campos Persistentes vs Runtime

Somente campos **explicitamente definidos** em
`build_raw_from_state(...)` são persistidos.

Campos de runtime **nunca são salvos**, como:

- `last_error`
- `last_load_ok`
- `last_save_ok`
- `settings_file_path`

Isso evita vazamento de estado efêmero para o arquivo de configuração.

---

## Relação com Outros Módulos

### `state.py`

- Define a estrutura do estado
- Não conhece TOML nem disco

O `settings` aplica valores **no** estado, mas o estado não depende do `settings`.

---

### ViewModels da UI

- Trabalham com tipos amigáveis (`str`)
- Fazem validação de entrada
- Aplicam alterações explicitamente no `AppState`
- Chamam `save_settings(...)` quando apropriado

---

### Logger

- O `settings` não configura diretamente o logger
- Apenas popula `LogState`
- A conversão para `LogConfig` ocorre em módulo intermediário

---

## Regra de Evolução (Importante)

Ao adicionar um novo campo persistente:

1. Adicionar o campo no subestado correspondente em `state.py`
2. Ler o campo em `apply_settings_to_state(...)`
3. Persistir o campo em `build_raw_from_state(...)`

Essa regra é **intencional** e garante controle total sobre compatibilidade
e persistência.

---

## O que **não** fazer neste módulo

- Não adicionar lógica de UI
- Não importar NiceGUI
- Não executar validações complexas
- Não acessar diretamente o logger global
- Não persistir campos de runtime

---

## Conclusão

O módulo `settings` existe para **proteger o núcleo da aplicação**.

Ele garante que:

- Configurações externas nunca contaminem o estado interno
- Falhas não derrubem o aplicativo
- Persistência seja explícita, controlada e segura

Toda complexidade relacionada a arquivos, parsing e fallback
deve permanecer **neste módulo**, e apenas nele.
