"""Junta os resultados num JSON só, para o site ler.

    python -m bench.build

Offline: lê data/items.json e data/resultados/*.json, que são versionados, e
escreve web/public/data. É o passo que o CI roda, já que o CI não tem modelo.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone

from .dataset import RAIZ, carregar
from .tasks import TASKS

RESULTADOS = RAIZ / "data" / "resultados"
SAIDA = RAIZ / "web" / "public" / "data"


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
    # Uma rodada parcial (só algumas tarefas) não entra no placar, para não inflar porcentagem.
    completas = [r for r in rodadas if len(r["respostas"]) == len(itens)]
    if not completas:
        raise SystemExit("Nenhuma rodada cobriu todos os itens; rode `python -m bench.run` sem --tarefas.")

    placar = []
    for r in completas:
        por_task: dict[str, list[bool]] = defaultdict(list)
        for resposta in r["respostas"]:
            por_task[resposta["task"]].append(resposta["acertou"])
        placar.append(
            {
                "modelo": r["modelo"],
                "rodadoEm": r["rodadoEm"],
                "segundos": r["segundos"],
                "acertos": sum(x["acertou"] for x in r["respostas"]),
                "total": len(r["respostas"]),
                "formatoOk": sum(x["formato_ok"] for x in r["respostas"]),
                "segundosPorItem": round(r["segundos"] / max(1, len(r["respostas"])), 2),
                "porTarefa": {t: {"acertos": sum(v), "total": len(v)} for t, v in sorted(por_task.items())},
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
            "itensPorTarefa": {t: sum(1 for i in itens if i["task"] == t) for t in TASKS},
        },
    )
    for p in placar:
        print(f"  {p['modelo']:28s} {p['acertos']:3d}/{p['total']} ({p['acertos'] / p['total']:.0%})  formato {p['formatoOk'] / p['total']:.0%}")


if __name__ == "__main__":
    main()
