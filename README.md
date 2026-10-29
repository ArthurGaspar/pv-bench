# Deu pra entender?

Um benchmark de português brasileiro de verdade: testa se um modelo entende mensagem de brasileiro como ela chega no
celular, com abreviação sem vogal, erro de digitação, emoji no lugar de palavra, ironia e pedido que ninguém faz com
todas as letras.

São **64 itens em 8 tarefas**, cada um com **uma resposta certa só, conferida por regra**. Não tem modelo dando nota
para modelo, então a mesma rodada dá sempre o mesmo número e qualquer pessoa pode repetir.

**Site:** https://arthurgaspar.github.io/pv-bench/

![O placar](docs/placar.png)

## O que já deu

Rodado nos dois modelos que eu tinha na máquina, de graça, via Ollama. O benchmark é o produto aqui; estes dois são só
os primeiros em que ele foi apontado.

| Modelo | Acertos | Formato limpo | Seg. por item |
|---|---|---|---|
| qwen2.5-coder:7b | 43/64 (67%) | 88% | 6,0s |
| qwen2.5:7b | 42/64 (66%) | 100% | 4,9s |

O placar quase empata, e o interessante não é ele. É **onde** cada um erra:

| Tarefa | Acertos (os dois somados) |
|---|---|
| O que ela quer de verdade (pedido indireto) | 16/16 (100%) |
| Quem ficou de fazer (resolver pronome) | 16/16 (100%) |
| Para que serve a mensagem | 14/16 (88%) |
| Entender o valor | 13/16 (81%) |
| Aceitou ou enrolou | 11/16 (69%) |
| A conta no meio da conversa | 6/16 (38%) |
| Que dia é esse | 5/16 (31%) |
| Combinar um encontro | 4/16 (25%) |

**Os dois entendem o brasileiro e tropeçam na conta.** Pedido indireto ("nossa que calor né kkkk" dentro do carro) e
pronome perdido no meio do grupo saem perfeitos. Já "depois de amanhã" e "meio dia e meia de quarta" derrubam os dois:
15 dos 64 itens nenhum dos dois acertou, e quase todos são data, hora ou continha.

Dois achados que valem olhar com calma:

- **"fechouuu" foi lido como recusa** pelos dois modelos. É das palavras mais claras de aceite que existem em português
  brasileiro, e nenhum dos dois pegou.
- **O modelo de código acerta um pouco mais e obedece bastante menos.** Ele ganha na continha (4/8 contra 2/8) mas
  entrega o formato pedido em 88% das vezes, contra 100% do modelo geral, que nunca enfeitou uma resposta.

Com 64 itens, cada item vale 1,6 ponto percentual: dá para ver tendência e tropeço, não para cravar ranking.

## Como a correção funciona

Duas coisas são medidas de propósito em colunas separadas:

- **Acerto**: a resposta, depois de extraída do texto, bate com o gabarito. A extração é tolerante porque a pergunta é
  se o modelo entendeu a mensagem, não se ele obedeceu.
- **Formato limpo**: a resposta já veio exatamente como foi pedido, sem frase em volta e sem markdown.

Um detalhe que só aparece em português: **"1.500" é mil e quinhentos e "1,5" é um e meio.** O corretor lê os dois
formatos, o brasileiro e o inglês, decidindo pelo separador que aparece por último. Em item com mais de um campo (dia
*e* hora), acerto exige os dois: não há crédito parcial.

## Rodar nos seus modelos

O runner usa **LiteLLM**, então serve qualquer provedor que ele atenda. O padrão é Ollama na própria máquina, porque
assim rodar não custa nada.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; `source .venv/bin/activate` no resto
pip install -r requirements.txt

python -m bench.run --modelos ollama/llama3.2:3b    # local, de graça
python -m bench.run --tarefas valor contagem        # só algumas tarefas
python -m bench.build                               # monta o JSON do site
python -m pytest                                    # 36 testes do harness

cd web && npm install && npm run dev
```

Para um provedor pago, basta ter a chave no ambiente: `python -m bench.run --modelos gpt-4o-mini`. Cada rodada cai em
`data/resultados/<modelo>.json`, com a resposta crua de cada item.

## Como está organizado

```
bench/tasks.py      as 8 tarefas: o prompt e o tipo de resposta de cada uma
bench/grade.py      o corretor: extrai a resposta do texto e confere com o gabarito
bench/dataset.py    carrega e confere os itens antes de qualquer rodada
bench/run.py        chama o modelo via LiteLLM e grava resposta crua + correção
bench/build.py      junta tudo num JSON para o site (offline, é o que o CI roda)
data/items.json     os 64 itens, versionados
data/resultados/    uma rodada por modelo, versionada
web/                o site: placar, todas as respostas, tarefas e método
```

O conjunto se confere sozinho nos testes: ids únicos, rótulo dentro da lista da tarefa, todo prompt montando, e
**todo gabarito passando pelo próprio corretor**: se eu escrever um gabarito que o corretor não aceita, o teste quebra.
Também testa que as alternativas não ficam todas na mesma letra, senão um modelo que responde sempre "B" gabaritava.

## O que este número não é

- **São itens escritos à mão.** Imitam mensagem real, mas não foram coletados de conversa de ninguém, porque conversa de
  verdade é dado pessoal.
- **Temperatura zero, uma tentativa por item.** Sem média de várias rodadas, um empate técnico pode virar um ponto de
  diferença por acaso.
- **Não mede escrita, só compreensão.** Todas as respostas são curtas e verificáveis.
- **Os itens estão publicados.** Bom para auditar, ruim para o futuro: uma vez na internet, podem acabar em treino de
  alguém e deixar de medir o que mediam.
- **O CI não roda modelo.** Ele roda os testes e monta o site a partir das rodadas versionadas, porque não tem GPU e não
  deve gastar nada.
