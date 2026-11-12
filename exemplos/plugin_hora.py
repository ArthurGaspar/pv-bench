"""Exemplo de plugin: um avaliador de horário e uma tarefa que o usa.

    python -m bench.run --plugins exemplos.plugin_hora --tarefas horario

Para usar de verdade, acrescente itens com "task": "horario" em data/items.json
e liste o módulo em "plugins" no cabeçalho do conjunto, para que a montagem do
site (que não recebe --plugins) também consiga recorrigir as respostas.
"""

import re

from bench.avaliadores import Avaliador, Parsed, registrar_avaliador
from bench.grade import _limpar
from bench.tasks import FORMATO, Task, registrar_tarefa

HORA = re.compile(r"\b([01]?\d|2[0-3])\s*(?::|h)\s*([0-5]\d)?\b", re.I)


class Hora(Avaliador):
    nome = "hora"

    def extrair(self, bruto, item, task):
        texto = _limpar(bruto)
        achado = HORA.search(texto)
        if not achado:
            return Parsed(None, False, "sem horário na resposta")
        valor = f"{int(achado.group(1)):02d}:{achado.group(2) or '00'}"
        return Parsed(valor, texto == valor)

    def conferir(self, valor, item, task):
        return valor == item["gabarito"]

    def validar_item(self, item, task):
        g = item.get("gabarito")
        if not isinstance(g, str) or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", g):
            return [f"horário {g!r} deveria estar em HH:MM"]
        return []


registrar_avaliador(Hora())
registrar_tarefa(
    Task(
        id="horario",
        titulo="Que horas fica",
        descricao="Converter o horário dito de um jeito informal para HH:MM.",
        answer_type="hora",
        prompt=(
            "Mensagem recebida:\n\"\"\"{mensagem}\"\"\"\n\n"
            "Que horário ficou combinado?\n"
            + FORMATO.format(formato="o horário no formato HH:MM, em 24 horas")
        ),
    )
)
