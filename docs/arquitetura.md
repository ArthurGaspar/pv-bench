# Arquitetura

O projeto tem duas metades independentes, ligadas por um único arquivo JSON:

```text
data/items.json ──┐
                  ├─ bench.run / bench.lote ──> data/resultados/<modelo>.json   (chama modelos)
bench/tasks.py ───┤  bench.importar ─────────> data/resultados/<modelo>.json   (sem modelo)
                  │
                  └─ bench.build ──> web/public/data/benchmark.json ──> web/ (React) ──> web/dist
```

O harness em Python produz e valida rodadas. O site só lê o JSON que `bench.build` gera. As rodadas são versionadas no git, então o build e o site não precisam de modelo, GPU ou chave de API.

## Princípios

1. **Correção por regra.** Cada tipo de resposta tem um avaliador determinístico. Não há juiz humano nem modelo avaliando modelo; qualquer pessoa chega à mesma nota com o mesmo texto.
2. **O texto bruto é a fonte da verdade.** As rodadas guardam a resposta completa do modelo (`bruto`). `extraido`, `acertou` e `formato_ok` são recalculados sempre que uma rodada é lida pelo build ou pela importação. Corrigir um parser ou um gabarito atualiza todas as notas sem rodar modelo de novo.
3. **Compreensão separada de obediência.** A extração tolera texto em volta da resposta (o acerto mede compreensão); `formato_ok` mede se a resposta veio exatamente no formato pedido.
4. **Recusar em vez de adivinhar.** Rodada de outra versão dos prompts, item desconhecido, tarefa trocada, duplicata ou rodada incompleta não entram no site. Erros são acumulados e mostrados todos de uma vez.

## Módulos do harness (`bench/`)

| Módulo | Responsabilidade | Depende de |
|---|---|---|
| `tasks.py` | `Task` (id, título, descrição, `answer_type`, template, rótulos), o dicionário `TASKS` com as 8 tarefas, `registrar_tarefa`, `DIAS` | nada |
| `avaliadores.py` | classe base `Avaliador`, `Parsed`, registro `AVALIADORES`, `carregar_plugins` | `tasks` (só tipos) |
| `grade.py` | parsers (`parse_numero`, `parse_json`, ...), os 6 avaliadores embutidos, `corrigir(item, bruto)` | `avaliadores`, `tasks` |
| `esquema.py` | esquemas, migração, `impressao`, `conferir_estrutura_rodada`, `conferir_rodada`, `nome_arquivo` | `tasks`, `grade` (import tardio) |
| `dataset.py` | `carregar_conjunto` e `conferir_itens`; `Conjunto` com nome, versão, impressão, itens e plugins | todos acima |
| `run.py` | `chamar` (LiteLLM), `rodar` (paralelismo e checkpoint), `executar` (grava e limpa o parcial), CLI | `dataset`, `esquema`, `grade` |
| `lote.py` | validação da spec de lote, `planejar`, `pronto`, CLI | `run` |
| `importar.py` | leitura de JSON/JSONL/CSV, agrupamento por modelo, validação tudo ou nada, CLI | `esquema`, `run` (caminho de saída) |
| `build.py` | `ler_rodadas`, `preparar_rodadas`, montagem do placar e do JSON do site | `dataset`, `esquema` |

`litellm` é importado só dentro de `run.chamar`: validar, importar, testar e montar o site funcionam sem ele instalado.

### Caminho de uma resposta

1. `Task.render(item)` monta o prompt com `mensagem`, as chaves de `contexto`, os rótulos da tarefa e as alternativas do item.
2. `run.chamar` envia o prompt com temperatura 0 e `max_tokens` 200 (padrão), timeout de 180 s. Falha do provedor devolve `bruto = ""` e uma mensagem de erro; a rodada continua.
3. `grade.corrigir` chama `extrair` e `conferir` do avaliador da tarefa e devolve `extraido`, `acertou`, `formato_ok` e `erro_formato`.
4. A resposta é anexada ao parcial `.jsonl` assim que chega. No fim, a rodada completa é gravada em `data/resultados/` e o parcial é apagado se não houve falha de provedor.
5. `bench.build` relê a rodada, confere com o conjunto atual, recorrige a partir de `bruto` e agrega.

### Extração tolerante e formato limpo

Antes de qualquer parser, `_limpar` remove espaços externos e uma cerca de Markdown. Depois:

| Tipo | Extração | Formato limpo quando |
|---|---|---|
| `numero` | primeiro número após remover `R$`, `reais`, `pila`, `conto` e espaços; aceita `1.234,56`, `1,234.56`, `1,5`, `1.500` (= 1500), `44.91` (= 44,91) | o texto é só o número |
| `json` | trecho entre o primeiro `{` e o último `}`; exige os campos do gabarito | o texto é só o objeto |
| `rotulo` | igualdade sem acento e sem caixa; senão, um único rótulo como palavra no texto | o texto é só o rótulo |
| `data` | primeira data `AAAA-MM-DD` | o texto é só a data |
| `alternativa` | letra isolada A–E presente nas alternativas; senão, o texto de uma alternativa contido na resposta | o texto é só a letra |
| `nome` | primeira palavra alfabética; comparação sem acento e sem caixa | o texto é só o nome |

Respostas JSON com vários campos só acertam se todos baterem. Não há crédito parcial.

## Site (`web/`)

React 19, Vite e TypeScript, sem biblioteca de componentes nem roteador. `App.tsx` faz o roteamento pelo hash (`#/`, `#/respostas`, `#/tarefas`, `#/metodo`) e guarda o tema em `localStorage` (`recado-tema`).

| Arquivo | Papel |
|---|---|
| `dados.ts` | tipos de `benchmark.json`, `carregar()` com cache da promessa, `baixarCSV`, formatação em pt-BR |
| `Placar.tsx` | visão geral: placar e matriz item × modelo |
| `Respostas.tsx` | inspeção com busca e filtros persistidos no hash (`tarefa`, `modelo`, `so`, `q`, `item`), exportação CSV |
| `Tarefas.tsx` | o conjunto, com exemplos e prompts |
| `Metodo.tsx` | critérios de correção e registro das rodadas |
| `ui.tsx` | componentes pequenos compartilhados e o hook `useDados` |
| `styles.css` | tokens de cor e tipografia como variáveis CSS, temas claro e escuro por `data-theme` |

`vite.config.ts` usa `base: "./"`, então o build funciona em qualquer subcaminho do GitHub Pages.

## Integração contínua

`.github/workflows/pages.yml` roda em push para `master`, em pull request e manualmente:

1. Python 3.12, `pip install -r requirements.txt`, `python -m pytest -q`;
2. `python -m bench.build`;
3. Node 22, `npm ci` e `npm run build` em `web/`;
4. fora de PRs, publica `web/dist` no GitHub Pages.

## Testes (`tests/`)

- `test_bench.py`: parsers, correção e coerência do conjunto versionado.
- `test_build.py`: recorreção no build, exclusão de rodada parcial, rejeição de duplicatas e incompatibilidades, preservação do erro do provedor.
- `test_esquema.py`: migração, impressão, estrutura de rodada, nomes de arquivo, plugins, lote com retomada (com `chamar` simulado) e importação.

Nenhum teste chama modelo.
