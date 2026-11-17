# Documentação do Recado bench

O [README](../README.md) apresenta o projeto e os resultados. Estes documentos descrevem como ele funciona e quais contratos são estáveis.

| Documento | Para quem | Conteúdo |
|---|---|---|
| [arquitetura.md](arquitetura.md) | quem vai mexer no código | módulos, fluxo de dados, decisões de projeto |
| [formatos.md](formatos.md) | quem produz ou consome arquivos | esquemas do conjunto, da rodada, do lote, do JSON do site e do CSV |
| [conjunto.md](conjunto.md) | quem vai escrever ou corrigir itens | campos por tarefa, regras de validação, versionamento |
| [operacao.md](operacao.md) | quem vai rodar modelos ou publicar | execução, retomada, lotes, importação, build e deploy |
| [plugins.md](plugins.md) | quem quer novos tipos de resposta ou tarefas | interface `Avaliador`, registro e carga de plugins |

## O que é estável

Mudanças nestes pontos exigem subir o número de esquema e escrever migração em `bench/esquema.py`:

- formato de `data/items.json` (esquema do conjunto, hoje 1);
- formato de `data/resultados/*.json` (esquema da rodada, hoje 1);
- formato da especificação de lote (esquema do lote, hoje 1);
- a interface `Avaliador` e as funções `registrar_avaliador`, `registrar_tarefa` e `carregar_plugins`;
- as opções de linha de comando de `bench.run`, `bench.lote`, `bench.importar` e `bench.build`;
- as colunas do CSV exportado pelo site, que `bench.importar` lê de volta.

O formato de `web/public/data/benchmark.json` é interno: é gerado e consumido no mesmo build, e pode mudar junto com `web/src/dados.ts`.

## O que muda entre versões do conjunto

A `versao` em `data/items.json` segue a ideia de versionamento semântico aplicada ao conjunto:

- **major**: itens removidos ou trocados, ou tarefas novas; rodadas antigas deixam de ser comparáveis;
- **minor**: itens novos ou prompts alterados; exige rodar os modelos de novo;
- **patch**: correções de `gabarito` ou `pega`; as rodadas continuam válidas, porque as notas são recalculadas.

A garantia mecânica não depende do número: o build recusa qualquer rodada cuja impressão (hash dos prompts) difere da do conjunto atual. Veja [formatos.md](formatos.md#impressão).
