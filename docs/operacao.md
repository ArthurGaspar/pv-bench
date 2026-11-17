# Operação

## Ambiente

- Python 3.12 com `pip install -r requirements.txt` (`litellm`, `pytest`).
- Node.js 22 para o site.
- Para rodar modelos locais: [Ollama](https://ollama.com) com o modelo baixado (`ollama pull qwen2.5:7b`). O endereço vem de `OLLAMA_API_BASE` (padrão `http://localhost:11434`).
- Para provedores remotos: a variável de chave que o LiteLLM espera (por exemplo, `OPENAI_API_KEY`). **Isso gera cobrança.**

Testes, validação, importação e build não chamam modelo e não precisam de `litellm` em tempo de execução.

## Rodar um modelo: `bench.run`

```powershell
python -m bench.run                                   # modelos padrão: ollama/qwen2.5:7b e ollama/qwen2.5-coder:7b
python -m bench.run --modelos ollama/qwen2.5:7b
python -m bench.run --modelos openai/gpt-4o-mini --paralelo 4
python -m bench.run --tarefas valor contagem          # rodada parcial; fica fora do placar
```

| Opção | Padrão | Efeito |
|---|---|---|
| `--modelos` | os dois Qwen locais | nomes no formato do LiteLLM |
| `--tarefas` | todas | limita a execução a essas tarefas |
| `--paralelo N` | 1 | chamadas simultâneas por modelo |
| `--max-tokens` | 200 | limite de tokens da resposta |
| `--do-zero` | desligado | descarta o parcial e recomeça |
| `--plugins` | nenhum | módulos extras ([plugins.md](plugins.md)) |

Toda chamada usa temperatura 0, uma tentativa por item, timeout de 180 s. Ao terminar um modelo do Ollama, o harness pede para descarregá-lo da memória antes do próximo.

O resultado vai para `data/resultados/<modelo>.json` e **substitui** a rodada anterior do mesmo modelo.

### Interrupção e retomada

Cada resposta é anexada a `data/resultados/.parcial/<modelo>.jsonl` assim que chega. Depois de `Ctrl+C`, queda de energia ou erro, o mesmo comando retoma:

- respostas já obtidas são reaproveitadas;
- chamadas que falharam no provedor (resposta vazia com erro) são refeitas;
- um parcial feito com outros prompts (impressão diferente) é ignorado.

Se a rodada termina com falhas de provedor, o arquivo final é gravado com essas respostas marcadas como erro e o parcial é mantido; rodar de novo refaz só elas. Sem falhas, o parcial é apagado.

## Vários modelos: `bench.lote`

```powershell
python -m bench.lote lotes/exemplo.json --so-validar     # confere spec e conjunto, sem chamar modelo
python -m bench.lote lotes/exemplo.json                  # roda todos
python -m bench.lote lotes/exemplo.json --pular-prontos  # pula quem já tem rodada completa com os prompts atuais
python -m bench.lote lotes/exemplo.json --do-zero        # ignora parciais
```

Formato da especificação em [formatos.md](formatos.md#especificação-de-lote-lotesjson). Um modelo que falha não interrompe os outros; o resumo no fim lista o estado de cada um. Código de saída: 0 se todos terminaram, 1 se algum falhou ou foi interrompido, 2 se a especificação é inválida.

## Respostas geradas fora do harness: `bench.importar`

```powershell
python -m bench.importar respostas.jsonl --modelo provedor/modelo --so-validar
python -m bench.importar respostas.jsonl --modelo provedor/modelo
python -m bench.importar export.csv                      # CSV do site, com coluna modelo
python -m bench.importar rodada.json --substituir
```

| Opção | Efeito |
|---|---|
| `--formato json\|jsonl\|csv` | força o formato; o padrão vem da extensão |
| `--modelo` | nome do modelo; obrigatório se o arquivo não tiver a coluna `modelo` |
| `--substituir` | permite sobrescrever uma rodada existente do mesmo modelo |
| `--so-validar` | mostra o relatório sem gravar |
| `--plugins` | módulos extras |

Comportamento:

- notas vindas de fora não são aceitas: tudo é recorrigido a partir do texto bruto, e acertos declarados que divergem viram aviso;
- **tudo ou nada**: item desconhecido, tarefa trocada, duplicata, campo com tipo errado, impressão diferente da atual ou destino já existente sem `--substituir` impedem a gravação de todas as rodadas do arquivo;
- sem impressão no arquivo, a importação avisa que não pode garantir que os prompts eram os atuais;
- rodadas parciais podem ser importadas, mas ficam fora do placar.

Código de saída: 0 sucesso, 1 erros de validação, 2 arquivo ilegível.

## Montar e publicar o site

```powershell
python -m pytest -q
python -m bench.build        # escreve web/public/data/benchmark.json
cd web
npm ci
npm run dev                  # servidor local do Vite
npm run build                # tsc --noEmit + vite build -> web/dist
npm run preview              # serve o build
```

`bench.build` falha (e o CI junto) se alguma rodada tiver estrutura inválida, for de outro conjunto, tiver prompts diferentes dos atuais, itens desconhecidos, tarefas trocadas ou duplicatas, ou se dois arquivos forem do mesmo modelo. Rodadas válidas mas incompletas são simplesmente omitidas; se nenhuma for completa, o build para com erro.

O deploy é automático: cada push para `master` roda testes, build e publica no GitHub Pages. Pull requests só validam.

## Fluxo típico para publicar uma rodada nova

1. `python -m bench.run --modelos <modelo>` (ou um lote).
2. `python -m pytest -q` e `python -m bench.build`; confira o placar impresso.
3. `cd web; npm run dev` e revise as respostas no site.
4. Commit de `data/resultados/<modelo>.json`. Se a rodada traz achados novos, atualize a tabela de rodadas no `README.md`.
