"""Junta os resultados num JSON só, para o site ler.

    python -m bench.build

Offline: lê data/items.json e data/resultados/*.json, que são versionados, e
escreve web/public/data. É o passo que o CI roda, já que o CI não tem modelo.
"""

import json
from datetime import datetime, timezone

from .dataset import RAIZ, carregar_conjunto
from .esquema import conferir_estrutura_rodada, conferir_rodada, migrar_rodada
from .tasks import TASKS

RESULTADOS = RAIZ / "data" / "resultados"
SAIDA = RAIZ / "web" / "public" / "data"


def preparar_rodadas(rodadas: list[dict], itens: list[dict], conjunto: dict | None = None) -> list[dict]:
    modelos: set[str] = set()
    completas = []
    for rodada in rodadas:
        rodada = migrar_rodada(rodada)
        modelo = rodada.get("modelo")
        if modelo in modelos:
            raise ValueError(f"modelo repetido: {modelo}")
        modelos.add(modelo)
        respostas, faltando = conferir_rodada(rodada, itens, conjunto)
        if not faltando:
            completas.append({**rodada, "respostas": respostas})
    return completas


def ler_rodadas(arquivos) -> list[dict]:
    rodadas, erros = [], []
    for f in arquivos:
        try:
            rodada = migrar_rodada(json.loads(f.read_text(encoding="utf-8")))
        except ValueError as e:
            erros.append(f"{f.name}: {e}")
            continue
        erros += [f"{f.name}: {e}" for e in conferir_estrutura_rodada(rodada)]
        rodadas.append(rodada)
    if erros:
        raise ValueError("rodadas com estrutura inválida:\n  " + "\n  ".join(erros))
    return rodadas


def escrever(nome: str, dados) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = SAIDA / nome
    caminho.write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  {caminho.relative_to(RAIZ)} ({caminho.stat().st_size / 1024:.0f} KB)")


def main() -> None:
    conjunto = carregar_conjunto()
    itens = conjunto.itens
    arquivos = sorted(RESULTADOS.glob("*.json"))
    if not arquivos:
        raise SystemExit("Sem resultados em data/resultados; rode `python -m bench.run` primeiro.")
    completas = preparar_rodadas(ler_rodadas(arquivos), itens, conjunto.cabecalho())
    if not completas:
        raise SystemExit("Nenhuma rodada cobriu todos os itens; rode `python -m bench.run` sem --tarefas.")

    placar = []
    for r in completas:
        placar.append(
            {
                "modelo": r["modelo"],
                "rodadoEm": r["rodadoEm"],
                "segundos": r["segundos"],
                "origem": r["origem"]["tipo"],
                "acertos": sum(x["acertou"] for x in r["respostas"]),
                "total": len(r["respostas"]),
                "formatoOk": sum(x["formato_ok"] for x in r["respostas"]),
                "segundosPorItem": None if r["segundos"] is None else round(r["segundos"] / max(1, len(r["respostas"])), 2),
            }
        )
    placar.sort(key=lambda p: (-p["acertos"], p["segundosPorItem"] is None, p["segundosPorItem"] or 0))

    respostas = []
    for r in completas:
        for resposta in r["respostas"]:
            respostas.append({"modelo": r["modelo"], **resposta})

    escrever(
        "benchmark.json",
        {
            "geradoEm": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "conjunto": conjunto.cabecalho(),
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
