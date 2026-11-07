"""Junta os resultados num JSON só, para o site ler.

    python -m bench.build

Offline: lê data/items.json e data/resultados/*.json, que são versionados, e
escreve web/public/data. É o passo que o CI roda, já que o CI não tem modelo.
"""

import json
from datetime import datetime, timezone

from .dataset import RAIZ, carregar
from .grade import corrigir
from .tasks import TASKS

RESULTADOS = RAIZ / "data" / "resultados"
SAIDA = RAIZ / "web" / "public" / "data"


def preparar_rodadas(rodadas: list[dict], itens: list[dict]) -> list[dict]:
    por_id = {i["id"]: i for i in itens}
    modelos: set[str] = set()
    completas = []
    for rodada in rodadas:
        modelo = rodada["modelo"]
        if modelo in modelos:
            raise ValueError(f"modelo repetido: {modelo}")
        modelos.add(modelo)
        vistos: set[str] = set()
        respostas = []
        for resposta in rodada["respostas"]:
            id_ = resposta["id"]
            if id_ in vistos:
                raise ValueError(f"{modelo}: item repetido {id_}")
            vistos.add(id_)
            if id_ not in por_id:
                raise ValueError(f"{modelo}: item desconhecido {id_}")
            item = por_id[id_]
            if resposta["task"] != item["task"]:
                raise ValueError(f"{modelo}: tarefa inconsistente em {id_}")
            resultado = corrigir(item, resposta["bruto"])
            if not resposta["bruto"] and resposta.get("erro_formato"):
                resultado["erro_formato"] = resposta["erro_formato"]
            respostas.append({**resposta, **resultado})
        if vistos == set(por_id):
            completas.append({**rodada, "respostas": respostas})
    return completas


def escrever(nome: str, dados) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = SAIDA / nome
    caminho.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {caminho.relative_to(RAIZ)} ({caminho.stat().st_size / 1024:.0f} KB)")


def main() -> None:
    itens = carregar()
    arquivos = sorted(RESULTADOS.glob("*.json"))
    if not arquivos:
        raise SystemExit("Sem resultados em data/resultados; rode `python -m bench.run` primeiro.")
    rodadas = [json.loads(f.read_text(encoding="utf-8")) for f in arquivos]
    completas = preparar_rodadas(rodadas, itens)
    if not completas:
        raise SystemExit("Nenhuma rodada cobriu todos os itens; rode `python -m bench.run` sem --tarefas.")

    placar = []
    for r in completas:
        placar.append(
            {
                "modelo": r["modelo"],
                "rodadoEm": r["rodadoEm"],
                "segundos": r["segundos"],
                "acertos": sum(x["acertou"] for x in r["respostas"]),
                "total": len(r["respostas"]),
                "formatoOk": sum(x["formato_ok"] for x in r["respostas"]),
                "segundosPorItem": round(r["segundos"] / max(1, len(r["respostas"])), 2),
            }
        )
    placar.sort(key=lambda p: (-p["acertos"], p["segundosPorItem"]))

    respostas = []
    for r in completas:
        for resposta in r["respostas"]:
            respostas.append({"modelo": r["modelo"], **resposta})

    escrever(
        "benchmark.json",
        {
            "geradoEm": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tarefas": [
                {"id": t.id, "titulo": t.titulo, "descricao": t.descricao, "tipo": t.answer_type, "rotulos": list(t.rotulos)}
                for t in TASKS.values()
            ],
            "itens": [
                {
                    "id": i["id"],
                    "task": i["task"],
                    "mensagem": i["mensagem"],
                    "contexto": {k: v for k, v in i["contexto"].items() if k != "diadasemana"},
                    "alternativas": i.get("alternativas"),
                    "gabarito": i["gabarito"],
                    "pega": i["pega"],
                    "prompt": TASKS[i["task"]].render(i),
                }
                for i in itens
            ],
            "placar": placar,
            "respostas": respostas,
        },
    )
    for p in placar:
        print(f"  {p['modelo']:28s} {p['acertos']:3d}/{p['total']} ({p['acertos'] / p['total']:.0%})  formato {p['formatoOk'] / p['total']:.0%}")


if __name__ == "__main__":
    main()
