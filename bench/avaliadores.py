"""Interface dos avaliadores: como extrair a resposta do texto e compará-la ao gabarito.

Cada tarefa declara um tipo de resposta (`Task.answer_type`), e cada tipo tem um
avaliador registrado aqui. Os seis tipos do conjunto vêm de `bench.grade`; um
plugin acrescenta outros com `registrar_avaliador` e, se quiser, tarefas novas
com `bench.tasks.registrar_tarefa`.

Um plugin é um módulo Python comum, carregado de três jeitos:

- listado em `plugins` no cabeçalho de `data/items.json`;
- passado em `--plugins modulo.caminho` para `bench.run`, `bench.lote` ou `bench.importar`;
- publicado por um pacote no grupo de entry points `recado_bench.avaliadores`.

Veja `exemplos/plugin_hora.py`. A regra continua a mesma dos embutidos: correção
determinística, sem modelo avaliando modelo.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tasks import Task

GRUPO_ENTRY_POINTS = "recado_bench.avaliadores"


@dataclass
class Parsed:
    valor: object | None
    formato_ok: bool  # a saída já era exatamente o formato pedido
    erro: str | None = None


class Avaliador:
    """Base dos avaliadores. `extrair` e `conferir` são obrigatórios."""

    nome: str = ""

    def extrair(self, bruto: str, item: dict, task: Task) -> Parsed:
        raise NotImplementedError

    def conferir(self, valor: object, item: dict, task: Task) -> bool:
        raise NotImplementedError

    def validar_item(self, item: dict, task: Task) -> list[str]:
        """Problemas do gabarito, conferidos ao carregar o conjunto. Cada string vira um erro."""
        return []

    def gabarito_como_texto(self, item: dict, task: Task) -> str:
        """O gabarito escrito como o modelo deveria escrever; os testes exigem que ele passe."""
        return str(item["gabarito"])


AVALIADORES: dict[str, Avaliador] = {}
_carregados: set[str] = set()


def registrar_avaliador(avaliador: Avaliador, substituir: bool = False) -> Avaliador:
    if not avaliador.nome:
        raise ValueError(f"{type(avaliador).__name__}: avaliador sem nome")
    for metodo in ("extrair", "conferir"):
        if getattr(type(avaliador), metodo) is getattr(Avaliador, metodo):
            raise TypeError(f"avaliador {avaliador.nome!r} não implementa {metodo}")
    if avaliador.nome in AVALIADORES and not substituir:
        raise ValueError(f"avaliador {avaliador.nome!r} já registrado")
    AVALIADORES[avaliador.nome] = avaliador
    return avaliador


def obter(nome: str) -> Avaliador:
    try:
        return AVALIADORES[nome]
    except KeyError:
        raise KeyError(f"nenhum avaliador para o tipo {nome!r}; falta carregar um plugin?") from None


def carregar_plugins(modulos: list[str] | None = None) -> None:
    """Importa os plugins pedidos, os de `RECADO_PLUGINS` e os de entry points. Repetir não recarrega."""
    nomes = list(modulos or [])
    nomes += [m for m in os.environ.get("RECADO_PLUGINS", "").replace(";", ",").split(",") if m.strip()]
    for nome in nomes:
        nome = nome.strip()
        if nome not in _carregados:
            importlib.import_module(nome)
            _carregados.add(nome)
    for ep in entry_points(group=GRUPO_ENTRY_POINTS):
        chave = f"ep:{ep.value}"
        if chave not in _carregados:
            ep.load()
            _carregados.add(chave)
