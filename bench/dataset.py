"""Carrega e confere o conjunto de itens.

A conferência roda nos testes e antes de cada execução: um gabarito com o
formato errado não deve ser descoberto no meio de uma rodada de meia hora.
"""

import datetime
import json
from pathlib import Path

from .tasks import DIAS, TASKS

RAIZ = Path(__file__).resolve().parent.parent
ITENS = RAIZ / "data" / "items.json"


def carregar(caminho: Path = ITENS) -> list[dict]:
    itens = json.loads(caminho.read_text(encoding="utf-8"))
    for item in itens:
        contexto = item.setdefault("contexto", {})
        if "hoje" in contexto:
            # O dia da semana sai sempre da data, para nunca discordar dela.
            contexto["diadasemana"] = DIAS[datetime.date.fromisoformat(contexto["hoje"]).weekday()]
    conferir_itens(itens)
    return itens


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
        gabarito = item.get("gabarito")
        tipo = task.answer_type
        if tipo == "json" and not isinstance(gabarito, dict):
            erros.append(f"{id_}: gabarito deveria ser um objeto")
        if tipo == "numero" and not isinstance(gabarito, (int, float)):
            erros.append(f"{id_}: gabarito deveria ser número")
        if tipo == "rotulo" and gabarito not in task.rotulos:
            erros.append(f"{id_}: rótulo {gabarito!r} fora da lista da tarefa")
        if tipo == "data":
            try:
                datetime.date.fromisoformat(str(gabarito))
            except ValueError:
                erros.append(f"{id_}: data inválida {gabarito!r}")
        if tipo == "alternativa":
            alternativas = item.get("alternativas") or {}
            if gabarito not in alternativas:
                erros.append(f"{id_}: alternativa {gabarito!r} não existe")
            if len(alternativas) < 3:
                erros.append(f"{id_}: precisa de pelo menos 3 alternativas")
        if not item.get("pega"):
            erros.append(f"{id_}: falta o campo 'pega' explicando a dificuldade")
        try:
            task.render(item)
        except KeyError as e:
            erros.append(f"{id_}: o prompt pede {e} e o item não tem")
    if erros:
        raise ValueError("itens inválidos:\n  " + "\n  ".join(erros))
