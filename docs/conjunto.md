# O conjunto de itens

`data/items.json` é escrito à mão. Cada item é uma mensagem curta em português brasileiro informal, uma pergunta com resposta verificável e uma explicação da dificuldade.

## Tarefas

| `task` | Tipo de resposta | Chaves de `contexto` | Gabarito |
|---|---|---|---|
| `compromisso` | `json` | `hoje` | `{"data": "AAAA-MM-DD", "hora": "HH:MM"}` |
| `valor` | `numero` | `pergunta` | número |
| `intencao` | `rotulo` | nenhuma | um de `convite`, `cobranca`, `cancelamento`, `confirmacao`, `favor`, `spam`, `reclamacao`, `desabafo` |
| `resposta` | `rotulo` | `convite` | um de `aceitou`, `recusou`, `talvez` |
| `pedido` | `alternativa` | `situacao` (+ campo `alternativas` no item) | letra da alternativa |
| `data_relativa` | `data` | `hoje`, `pergunta` | `"AAAA-MM-DD"` |
| `quem` | `nome` | `pergunta` | primeiro nome |
| `contagem` | `numero` | `pergunta` | número |

Os templates estão em `bench/tasks.py`. Todos terminam pedindo resposta curta, sem explicação e sem Markdown. Nas tarefas com `hoje`, o prompt inclui o dia da semana e a regra de que "que vem" significa a próxima ocorrência daquele dia.

## Escrevendo um item

```json
{"id": "valor-09", "task": "valor",
 "contexto": {"pergunta": "Quanto a pessoa pagou no total?"},
 "mensagem": "paguei 2k e quinhentos no carro, mais uns 300 conto de documento",
 "gabarito": 2800,
 "pega": "\"2k e quinhentos\" é 2500, e \"conto\" é real"}
```

- `id`: `<tarefa>-<nn>`, único. Mudar um id muda a impressão.
- `mensagem`: escrita como alguém escreveria no celular. Abreviações, falta de acento, emoji e ironia são bem-vindos; o item tem que ter uma resposta inequívoca para um falante nativo.
- `contexto`: exatamente as chaves que o template pede. Chave faltando é erro na carga.
- `gabarito`: no formato da tabela. Para `json`, os valores são comparados como texto (`"09:00"` ≠ `"9:00"`).
- `pega`: obrigatório. Uma frase sobre o que torna o item difícil; aparece no site.
- `alternativas` (só `pedido`): pelo menos 3, com letras de A a E.

## Validação

`carregar_conjunto` roda a validação toda vez que o conjunto é carregado (testes, execução, importação, build) e reporta todos os problemas juntos:

- `id` repetido, tarefa desconhecida, tipo de resposta sem avaliador registrado;
- gabarito ausente ou inválido para o avaliador (número que não é número, rótulo fora da lista, data inválida, alternativa inexistente, menos de 3 alternativas);
- `pega` ausente ou vazio;
- template que pede uma chave que o item não tem.

Os testes acrescentam regras sobre o conjunto como um todo:

- toda tarefa tem pelo menos um item;
- o próprio gabarito, escrito como resposta, é corrigido como acerto;
- em `intencao` e `resposta`, todos os rótulos aparecem como gabarito de algum item;
- em `pedido`, nenhuma letra é a correta em mais da metade dos itens.

Rode `python -m pytest -q` depois de qualquer edição.

## Mudanças e suas consequências

| Mudança | Impressão muda? | Rodadas existentes |
|---|---|---|
| Corrigir `gabarito` ou `pega` | não | continuam válidas; as notas são recalculadas no próximo build |
| Mudar `mensagem`, `contexto`, `alternativas` ou `id` | sim | recusadas pelo build; é preciso rodar os modelos de novo |
| Mudar um template ou os rótulos em `bench/tasks.py` | sim | idem |
| Acrescentar itens | sim | idem |
| Acrescentar uma tarefa | sim | idem; pode exigir um avaliador novo ([plugins.md](plugins.md)) |

Quando a impressão muda, suba `versao` (veja a convenção em [README.md](README.md#o-que-muda-entre-versões-do-conjunto)), refaça as rodadas e substitua os arquivos em `data/resultados/` no mesmo commit, senão o CI falha no build.
