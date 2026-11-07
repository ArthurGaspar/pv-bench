"""Roda o benchmark em um ou mais modelos.

    python -m bench.run                                  # os modelos padrão
    python -m bench.run --modelos ollama/qwen2.5:7b      # só um
    python -m bench.run --tarefas valor contagem         # só algumas tarefas

Qualquer modelo que o LiteLLM atenda serve, inclusive de provedor pago: basta
passar o nome e ter a chave no ambiente. O padrão é Ollama rodando na própria
máquina, porque assim a execução não custa nada.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone

import litellm

from .dataset import RAIZ, carregar
from .grade import corrigir
from .tasks import TASKS

litellm.suppress_debug_info = True
SAIDA = RAIZ / "data" / "resultados"
PADRAO = ["ollama/qwen2.5:7b", "ollama/qwen2.5-coder:7b"]
OLLAMA = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
MAX_TOKENS = 200


def chamar(modelo: str, prompt: str) -> tuple[str, float, str | None]:
    """Devolve (resposta, segundos, erro). Erro de rede vira resultado errado, não quebra a rodada."""
    inicio = time.perf_counter()
    try:
        extra = {"api_base": OLLAMA} if modelo.startswith("ollama/") else {}
        r = litellm.completion(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=MAX_TOKENS,
            timeout=180,
            **extra,
        )
        return (r.choices[0].message.content or "").strip(), time.perf_counter() - inicio, None
    except Exception as e:  # noqa: BLE001 - qualquer falha do provedor é registrada e segue
        return "", time.perf_counter() - inicio, f"{type(e).__name__}: {e}"[:300]


def descarregar(modelo: str) -> None:
    """Libera a memória do Ollama antes do próximo modelo; numa máquina pequena isso importa."""
    if not modelo.startswith("ollama/"):
        return
    import urllib.request

    pedido = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=json.dumps({"model": modelo.split("/", 1)[1], "keep_alive": 0}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(pedido, timeout=30).read()
    except Exception:  # noqa: BLE001 - descarregar é otimização, não requisito
        pass


def rodar(modelo: str, itens: list[dict], log=print) -> dict:
    respostas = []
    acertos = 0
    inicio = datetime.now(timezone.utc)
    for n, item in enumerate(itens, start=1):
        prompt = TASKS[item["task"]].render(item)
        bruto, segundos, erro = chamar(modelo, prompt)
        resultado = corrigir(item, bruto) if erro is None else {
            "extraido": None, "acertou": False, "formato_ok": False, "erro_formato": erro,
        }
        acertos += resultado["acertou"]
        respostas.append({"id": item["id"], "task": item["task"], "bruto": bruto, "segundos": round(segundos, 2), **resultado})
        if n % 8 == 0 or n == len(itens):
            log(f"    {n:3d}/{len(itens)}  acertos {acertos}")
    return {
        "modelo": modelo,
        "rodadoEm": inicio.isoformat(timespec="seconds"),
        "segundos": round((datetime.now(timezone.utc) - inicio).total_seconds(), 1),
        "respostas": respostas,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelos", nargs="*", default=PADRAO)
    parser.add_argument("--tarefas", nargs="*", help="limita às tarefas indicadas")
    args = parser.parse_args()

    itens = carregar()
    if args.tarefas:
        desconhecidas = set(args.tarefas) - set(TASKS)
        if desconhecidas:
            raise SystemExit(f"tarefa desconhecida: {', '.join(sorted(desconhecidas))}")
        itens = [i for i in itens if i["task"] in args.tarefas]
    SAIDA.mkdir(parents=True, exist_ok=True)
    print(f"{len(itens)} itens, {len(args.modelos)} modelo(s)")

    for modelo in args.modelos:
        print(f"  {modelo}")
        resultado = rodar(modelo, itens)
        descarregar(modelo)
        arquivo = SAIDA / (modelo.replace("/", "__").replace(":", "_") + ".json")
        arquivo.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
        certos = sum(r["acertou"] for r in resultado["respostas"])
        formato = sum(r["formato_ok"] for r in resultado["respostas"])
        print(
            f"    {certos}/{len(itens)} acertos ({certos / len(itens):.0%}), "
            f"formato limpo em {formato / len(itens):.0%}, {resultado['segundos']:.0f}s"
        )


if __name__ == "__main__":
    main()
