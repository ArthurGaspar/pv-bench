# CLAUDE.md

Benchmark de compreensão de mensagens informais em português brasileiro. Harness em Python (`bench/`) que roda modelos via LiteLLM e corrige por regra; site estático em React (`web/`) que mostra as rodadas versionadas. Documentação de referência em `docs/` (comece por `docs/README.md`).

## Comandos

```powershell
pip install -r requirements.txt          # litellm + pytest
python -m pytest -q                      # testes; não chamam modelo
python -m bench.build                    # data/ -> web/public/data/benchmark.json (offline)
cd web; npm ci; npm run dev              # site local; precisa do build acima antes
cd web; npm run build                    # tsc --noEmit + vite build -> web/dist

python -m bench.run --modelos ollama/qwen2.5:7b [--tarefas valor contagem] [--paralelo N]
python -m bench.lote lotes/exemplo.json [--so-validar] [--pular-prontos] [--do-zero]
python -m bench.importar arquivo.{json,jsonl,csv} --modelo provedor/nome [--so-validar] [--substituir]
```

`bench.run`/`bench.lote` chamam modelos de verdade (Ollama local por padrão; provedores pagos custam dinheiro). Não rode sem o usuário pedir. Para validar mudanças, use `pytest` e `bench.build`, como o CI faz.

## Arquitetura em uma tela

- `bench/tasks.py`: as 8 tarefas (`Task`), cada uma com template de prompt e `answer_type`. `registrar_tarefa` para plugins.
- `bench/avaliadores.py`: classe `Avaliador` (`extrair`, `conferir`, `validar_item`, `gabarito_como_texto`), registro e `carregar_plugins`.
- `bench/grade.py`: os 6 avaliadores embutidos (`numero`, `json`, `rotulo`, `data`, `alternativa`, `nome`) e `corrigir(item, bruto)`. Importar `grade` registra os embutidos.
- `bench/esquema.py`: esquemas versionados do conjunto e da rodada, migração, `impressao` (hash dos prompts), `conferir_rodada`, `nome_arquivo`.
- `bench/dataset.py`: `carregar_conjunto()` lê `data/items.json`, carrega plugins, deriva `diadasemana` de `hoje`, valida todos os itens.
- `bench/run.py`: execução com checkpoint em `data/resultados/.parcial/*.jsonl` e retomada. `bench/lote.py`: vários modelos a partir de uma spec. `bench/importar.py`: importação validada, tudo ou nada.
- `bench/build.py`: recorrige todas as rodadas e escreve o único JSON que o site lê.
- `web/src/dados.ts`: tipos do `benchmark.json` e helpers. Páginas: `Placar`, `Respostas` (filtros no hash: `tarefa`, `modelo`, `so`, `q`, `item`), `Tarefas`, `Metodo`. Roteamento por hash em `App.tsx`.

## Invariantes (não quebre)

- **Correção determinística.** Nada de LLM avaliando LLM. Todo avaliador é regra pura.
- **Notas nunca são confiadas.** `acertou`, `extraido`, `formato_ok` são sempre recalculados a partir de `bruto`, no build e na importação. O texto bruto do modelo é preservado integralmente.
- **Acerto e formato são medidas separadas.** A extração é tolerante (acha o valor no meio do texto); `formato_ok` só é verdadeiro quando a saída limpa (sem espaços externos nem cerca markdown) é exatamente o formato pedido.
- **Impressão do conjunto.** É o sha256 de `[id, task, prompt renderizado]` dos itens. Mudar mensagem, contexto ou template de prompt muda a impressão e invalida as rodadas existentes (o build as recusa). Mudar `gabarito` ou `pega` não muda. Se for alterar prompts, avise que todas as rodadas em `data/resultados/` precisarão ser refeitas, e suba `versao` em `data/items.json`.
- **Só rodadas completas entram no site.** Rodada que não cobre todos os itens é descartada no build. Duplicatas de item ou de modelo são erro.
- **Plugins usados pelo conjunto vão no cabeçalho** (`"plugins"` em `data/items.json`): o CI roda `bench.build` sem argumentos.
- Falha do provedor vira resposta com `bruto: ""` e `erro_formato` preenchido; conta como erro, e a retomada refaz só essas.

## Ao editar o conjunto (`data/items.json`)

Cada item precisa de `id` único, `task` existente, `mensagem`, `contexto` com as chaves que o template pede, `gabarito` válido para o avaliador e `pega` (por que o item é difícil). Os testes exigem que o gabarito escrito como resposta (`gabarito_como_texto`) seja corrigido como acerto, que todas as tarefas tenham itens, que todos os rótulos de `intencao` e `resposta` apareçam como gabarito e que nenhuma letra seja a correta em mais da metade dos itens de `pedido`. Não preencha `diadasemana`: ele é derivado de `hoje`. Detalhes em `docs/conjunto.md`.

## Convenções

- Tudo em português: identificadores, mensagens de erro, docstrings, commits (`tipo(escopo): descrição`, ex.: `feat(bench): ...`, `feat(web): ...`).
- Python 3.12, só biblioteca padrão no harness além do `litellm` (importado preguiçosamente dentro de `chamar`). Sem formatter configurado; siga o estilo do arquivo (linhas longas são aceitas, comentários explicam o porquê).
- Erros de validação são acumulados e reportados juntos (`list[str]` de erros, depois um `ValueError` com todos), não o primeiro.
- Arquivos JSON lidos e escritos com `encoding="utf-8"` e `ensure_ascii=False`.
- Web: React 19 + Vite + TypeScript estrito, sem bibliotecas de UI; estilos em `web/src/styles.css` com variáveis CSS e temas claro/escuro via `data-theme`.
- `web/public/data/` e `data/resultados/.parcial/` são gerados e ignorados pelo git. `data/resultados/*.json` são versionados e são a fonte do site.

## CI

`.github/workflows/pages.yml`: em push para `master`, roda `pytest`, `bench.build`, `npm ci && npm run build` e publica `web/dist` no GitHub Pages. Em PR, só valida. Não há modelo no CI.
