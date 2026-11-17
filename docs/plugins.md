# Plugins: avaliadores e tarefas novas

Cada tarefa declara um tipo de resposta (`Task.answer_type`), e cada tipo tem um avaliador. Os seis tipos embutidos (`numero`, `json`, `rotulo`, `data`, `alternativa`, `nome`) estão em `bench/grade.py`. Um plugin é um módulo Python comum que registra avaliadores e, se quiser, tarefas.

A regra vale para plugins também: correção determinística, sem modelo avaliando modelo.

## Interface

```python
from bench.avaliadores import Avaliador, Parsed, registrar_avaliador
from bench.tasks import FORMATO, Task, registrar_tarefa


class Hora(Avaliador):
    nome = "hora"                                  # obrigatório; é o answer_type

    def extrair(self, bruto: str, item: dict, task: Task) -> Parsed:
        """Tira o valor do texto do modelo. Obrigatório."""

    def conferir(self, valor, item: dict, task: Task) -> bool:
        """Compara o valor extraído com item["gabarito"]. Obrigatório."""

    def validar_item(self, item: dict, task: Task) -> list[str]:
        """Problemas do gabarito, conferidos ao carregar o conjunto. Opcional."""

    def gabarito_como_texto(self, item: dict, task: Task) -> str:
        """O gabarito escrito como o modelo deveria responder. Opcional; padrão str(gabarito)."""
```

`Parsed(valor, formato_ok, erro=None)`:

- `valor`: o que foi extraído, ou `None` se nada foi encontrado;
- `formato_ok`: a saída já era exatamente o formato pedido;
- `erro`: motivo legível quando a extração falha; com erro, `formato_ok` é tratado como falso.

Use `bench.grade._limpar(bruto)` no começo de `extrair` para remover espaços e cercas de Markdown do mesmo jeito que os embutidos.

O teste `test_gabarito_bate_com_o_proprio_corretor` passa `gabarito_como_texto` pelo avaliador e exige acerto. Se o gabarito não é um texto simples (como o objeto do tipo `json`), sobrescreva esse método.

## Registro

- `registrar_avaliador(avaliador, substituir=False)`: recusa avaliador sem `nome`, sem `extrair` ou `conferir` implementados, ou com nome já registrado.
- `registrar_tarefa(task, substituir=False)`: recusa id de tarefa já existente. O template é um `str.format` que recebe `mensagem`, as chaves de `contexto`, `rotulos` (se a tarefa tiver) e `alternativas` (se o item tiver). Termine com `FORMATO.format(formato="...")` para manter o padrão de instrução.

O avaliador do tipo de cada tarefa só é exigido quando o conjunto é carregado; a mensagem "falta carregar um plugin?" indica que o módulo não foi importado.

## Carga

`carregar_plugins` importa, uma vez cada:

1. os módulos listados em `plugins` no cabeçalho de `data/items.json`;
2. os passados em `--plugins` para `bench.run`, `bench.lote` (campo `plugins` da spec) e `bench.importar`;
3. os listados na variável de ambiente `RECADO_PLUGINS`, separados por vírgula ou ponto e vírgula;
4. os entry points do grupo `recado_bench.avaliadores` de pacotes instalados.

`bench.build` não recebe argumentos, e o CI não define variáveis. **Se o conjunto versionado tem itens de uma tarefa de plugin, o módulo precisa estar no cabeçalho do conjunto**, senão o build falha.

## Exemplo

`exemplos/plugin_hora.py` registra o avaliador `hora` (converte "8h", "20:30", "9 h" para `HH:MM`) e a tarefa `horario`:

```powershell
python -m bench.run --plugins exemplos.plugin_hora --tarefas horario
```

Para usá-lo de verdade:

1. acrescente itens com `"task": "horario"` e gabarito `"HH:MM"` em `data/items.json`;
2. acrescente `"exemplos.plugin_hora"` em `plugins` no cabeçalho;
3. rode `python -m pytest -q`. A impressão muda, então as rodadas existentes precisam ser refeitas ([conjunto.md](conjunto.md#mudanças-e-suas-consequências)).

Para distribuir como pacote:

```toml
[project.entry-points."recado_bench.avaliadores"]
hora = "meu_pacote.hora"
```
