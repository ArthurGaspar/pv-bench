# Formatos de arquivo

Todos os arquivos são UTF-8. A fonte canônica dos esquemas é `bench/esquema.py`; este documento a descreve.

Um arquivo com `esquema` maior que o suportado é recusado com a mensagem "atualize o harness". Um arquivo sem `esquema` é tratado como esquema 0 e migrado em memória; o arquivo em disco não é reescrito.

## Conjunto: `data/items.json`

Esquema 1:

```json
{
  "esquema": 1,
  "nome": "recado",
  "versao": "1.0.0",
  "descricao": "texto livre (opcional)",
  "plugins": ["modulo.opcional"],
  "itens": [ ... ]
}
```

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `esquema` | inteiro | não (0 se ausente) | versão do formato |
| `nome` | texto não vazio | sim | identifica o conjunto; rodadas de outro nome são recusadas |
| `versao` | texto não vazio | sim | rótulo humano; a garantia real é a impressão |
| `descricao` | texto | não | |
| `plugins` | lista de nomes de módulo | não | importados ao carregar o conjunto, inclusive no CI |
| `itens` | lista de objetos | sim | veja [conjunto.md](conjunto.md) |

Qualquer outro campo no cabeçalho é erro. O esquema 0 é uma lista solta de itens; ele migra para `nome: "recado"`, `versao: "0"`.

### Item

```json
{
  "id": "compromisso-01",
  "task": "compromisso",
  "contexto": {"hoje": "2026-03-10"},
  "mensagem": "blz entao fica combinado ne, qui q vem 15h ...",
  "alternativas": {"A": "...", "B": "...", "C": "..."},
  "gabarito": {"data": "2026-03-12", "hora": "15:00"},
  "pega": "por que este item é difícil"
}
```

`alternativas` só existe na tarefa `pedido`. O tipo de `gabarito` depende do avaliador da tarefa (número, texto, objeto). `contexto.diadasemana` é derivado de `contexto.hoje` ao carregar e não deve ser escrito no arquivo.

### Impressão

A impressão identifica exatamente o que foi perguntado ao modelo:

```text
sha256( json([[id, task, prompt_renderizado], ...] ordenado por id, sem espaços, ensure_ascii=False) )
```

Ela muda quando muda um `id`, uma `task`, uma `mensagem`, um valor de `contexto`, as `alternativas`, um template em `bench/tasks.py` ou a lista de rótulos de uma tarefa. Ela **não** muda com `gabarito`, `pega`, `versao` ou `descricao`. O valor tem o prefixo `sha256:`.

## Rodada: `data/resultados/<modelo>.json`

Esquema 1:

```json
{
  "esquema": 1,
  "modelo": "ollama/qwen2.5:7b",
  "rodadoEm": "2026-10-29T13:04:55+00:00",
  "segundos": 310.9,
  "conjunto": {"nome": "recado", "versao": "1.0.0", "impressao": "sha256:..."},
  "origem": {"tipo": "local"},
  "config": {"temperatura": 0, "max_tokens": 200, "paralelo": 1},
  "respostas": [
    {
      "id": "compromisso-01",
      "task": "compromisso",
      "bruto": "{\"data\": \"2026-03-16\", \"hora\": \"15:00\"}",
      "segundos": 29.0,
      "extraido": {"data": "2026-03-16", "hora": "15:00"},
      "acertou": false,
      "formato_ok": true,
      "erro_formato": null
    }
  ]
}
```

| Campo | Tipo | Notas |
|---|---|---|
| `modelo` | texto não vazio | nome no formato do LiteLLM; único entre as rodadas |
| `rodadoEm` | data ISO 8601 | início da rodada; numa retomada, o início original |
| `segundos` | número ≥ 0 ou `null` | soma das latências das respostas, independente de paralelismo e retomadas |
| `conjunto` | objeto ou `null` | `nome`, `versao`, `impressao` do conjunto usado; `null` em rodadas antigas |
| `origem.tipo` | `"local"` ou `"importado"` | importações acrescentam `arquivo`, `formato`, `importadoEm` e, se reimportadas, `anterior` |
| `config` | objeto ou `null` | informativo; não é validado |
| `respostas[].id`, `.task`, `.bruto` | texto | obrigatórios; `bruto` é a resposta integral |
| `respostas[].segundos` | número ≥ 0 ou `null` | latência da chamada |
| `extraido`, `acertou`, `formato_ok`, `erro_formato` | | gravados por conveniência e **sempre recalculados** na leitura |

Uma resposta com `bruto: ""` e `erro_formato` preenchido representa falha do provedor: conta como erro, mantém a mensagem registrada e é refeita na retomada.

Rodadas sem `esquema` (esquema 0) migram com `conjunto: null` e `origem: {"tipo": "local"}`. Sem impressão, passam apenas pela conferência item a item (id existente, tarefa correta, sem duplicatas).

### Nome do arquivo

`nome_arquivo(modelo)`: `/` vira `__`, qualquer caractere fora de `[A-Za-z0-9._-]` vira `_`, sequências de pontos viram `_` e pontos iniciais são removidos. `ollama/qwen2.5:7b` → `ollama__qwen2.5_7b.json`. Dois modelos que resultariam no mesmo nome são recusados no lote e na importação.

### Checkpoint: `data/resultados/.parcial/<modelo>.jsonl`

Primeira linha: `{"modelo", "impressao", "rodadoEm"}`. Demais linhas: uma resposta cada, no formato acima. Um parcial com impressão diferente da atual é ignorado. Ignorado pelo git.

## Especificação de lote: `lotes/*.json`

Esquema 1:

```json
{
  "esquema": 1,
  "descricao": "texto livre",
  "tarefas": ["valor", "contagem"],
  "padrao": {"paralelo": 1, "max_tokens": 200},
  "plugins": ["meu_pacote.avaliadores"],
  "modelos": [
    "ollama/qwen2.5:7b",
    {"modelo": "openai/gpt-4o-mini", "paralelo": 4},
    {"modelo": "ollama/llama3.1:8b", "api_base": "http://outra-maquina:11434"}
  ]
}
```

Campos de nível superior aceitos: `esquema`, `descricao`, `tarefas`, `padrao`, `plugins`, `modelos`. Opções por modelo ou em `padrao`: `paralelo` (int ≥ 1), `max_tokens` (int ≥ 1), `api_base` (texto). Qualquer outro campo é erro.

## Importação: JSON, JSONL e CSV

`bench.importar` aceita:

- **JSON**: uma rodada no formato acima (qualquer esquema suportado) ou uma lista de respostas;
- **JSONL**: uma resposta por linha;
- **CSV**: com cabeçalho; delimitador `,`, `;` ou tab detectado automaticamente; BOM aceito.

Campos de cada resposta:

| Campo | Aliases | Obrigatório | Notas |
|---|---|---|---|
| `id` | `item` | sim | id de um item do conjunto |
| `bruto` | `resposta` | sim | texto exato devolvido pelo modelo |
| `modelo` | | sim, ou `--modelo` | um arquivo com vários modelos gera uma rodada por modelo |
| `task` | `tarefa` | não | se ausente, vem do item |
| `segundos` | | não | aceita vírgula decimal |
| `acertou` | | não | só para comparar; divergências viram aviso e vale a recorreção |

Demais colunas são ignoradas. O CSV exportado pelo site tem as colunas `item, tarefa, mensagem, gabarito, modelo, resposta, extraido, acertou, formato_ok, segundos` e pode ser reimportado diretamente.

## JSON do site: `web/public/data/benchmark.json` (interno)

Gerado por `bench.build`, ignorado pelo git. Chaves: `geradoEm`, `conjunto`, `tarefas`, `itens` (com o `prompt` renderizado e sem `diadasemana`), `placar` (ordenado por acertos e depois por tempo por item) e `respostas` (achatadas, com `modelo`). Os tipos estão em `web/src/dados.ts`. Não é contrato público.
