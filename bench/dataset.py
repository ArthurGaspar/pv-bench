"""Carrega e confere o conjunto de itens.

A conferência roda nos testes e antes de cada execução: um gabarito com o
formato errado não deve ser descoberto no meio de uma rodada de meia hora.
"""

import datetime
import json
from dataclasses import dataclass
from pathlib import Path

from . import grade  # noqa: F401 - registra os avaliadores embutidos
from .avaliadores import AVALIADORES, carregar_plugins, obter
from .esquema import conferir_envelope, impressao, migrar_conjunto
from .tasks import DIAS, TASKS

RAIZ = Path(__file__).resolve().parent.parent
ITENS = RAIZ / "data" / "items.json"


@dataclass
class Conjunto:
    nome: str
    versao: str
    impressao: str
    itens: list[dict]
    plugins: list[str]

    def cabecalho(self) -> dict:
        """O que cada rodada grava para dizer com que conjunto foi feita."""
        return {"nome": self.nome, "versao": self.versao, "impressao": self.impressao}


def carregar_conjunto(caminho: Path = ITENS, plugins: list[str] | None = None) -> Conjunto:
    dados = migrar_conjunto(json.loads(caminho.read_text(encoding="utf-8")))
    erros = conferir_envelope(dados)
    if erros:
        raise ValueError(f"{caminho.name}: cabeçalho inválido:\n  " + "\n  ".join(erros))
    carregar_plugins([*dados["plugins"], *(plugins or [])])
    itens = dados["itens"]
    for item in itens:
        contexto = item.setdefault("contexto", {})
        if "hoje" in contexto:
            # O dia da semana sai sempre da data, para nunca discordar dela.
            contexto["diadasemana"] = DIAS[datetime.date.fromisoformat(contexto["hoje"]).weekday()]
    conferir_itens(itens)
    return Conjunto(dados["nome"], dados["versao"], impressao(itens), itens, dados["plugins"])


def carregar(caminho: Path = ITENS) -> list[dict]:
    return carregar_conjunto(caminho).itens


def conferir_itens(itens: list[dict]) -> None:
    erros: list[str] = []
    vistos: set[str] = set()
    for item in itens:
        id_ = item.get("id", "<sem id>")
        if id_ in vistos:
            erros.append(f"{id_}: id repetido")
        vistos.add(id_)
        task = TASKS.get(item.get("task", ""))
        if task is None:
            erros.append(f"{id_}: tarefa desconhecida {item.get('task')!r}")
            continue
        if task.answer_type not in AVALIADORES:
            erros.append(f"{id_}: nenhum avaliador para o tipo {task.answer_type!r}; falta carregar um plugin?")
            continue
        if "gabarito" not in item:
            erros.append(f"{id_}: falta o gabarito")
            continue
        erros += [f"{id_}: {e}" for e in obter(task.answer_type).validar_item(item, task)]
        if not item.get("pega"):
            erros.append(f"{id_}: falta o campo 'pega' explicando a dificuldade")
        try:
            task.render(item)
        except KeyError as e:
            erros.append(f"{id_}: o prompt pede {e} e o item não tem")
    if erros:
        raise ValueError("itens inválidos:\n  " + "\n  ".join(erros))
