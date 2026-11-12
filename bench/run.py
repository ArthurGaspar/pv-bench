"""Roda o benchmark em um ou mais modelos.

    python -m bench.run                                  # os modelos padrão
    python -m bench.run --modelos ollama/qwen2.5:7b      # só um
    python -m bench.run --tarefas valor contagem         # só algumas tarefas
    python -m bench.run --modelos openai/gpt-4o-mini --paralelo 4

Qualquer modelo que o LiteLLM atenda serve, inclusive de provedor pago: basta
passar o nome e ter a chave no ambiente. O padrão é Ollama rodando na própria
máquina, porque assim a execução não custa nada.

Cada resposta vai para data/resultados/.parcial/ assim que chega. Se a rodada
for interrompida, o mesmo comando retoma de onde parou; `--do-zero` descarta o
parcial. Para vários modelos com configurações diferentes, veja `bench.lote`.
"""

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .dataset import RAIZ, Conjunto, carregar_conjunto
from .esquema import ESQUEMA_RODADA, nome_arquivo
from .grade import corrigir
from .tasks import TASKS

SAIDA = RAIZ / "data" / "resultados"
PARCIAL = SAIDA / ".parcial"
PADRAO = ["ollama/qwen2.5:7b", "ollama/qwen2.5-coder:7b"]
OLLAMA = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
MAX_TOKENS = 200


def chamar(modelo: str, prompt: str, max_tokens: int = MAX_TOKENS, api_base: str | None = None) -> tuple[str, float, str | None]:
    """Devolve (resposta, segundos, erro). Erro de rede vira resultado errado, não quebra a rodada."""
    import litellm  # só aqui: validar, importar e montar não precisam dele

    litellm.suppress_debug_info = True
    inicio = time.perf_counter()
    try:
        if api_base is None and modelo.startswith("ollama/"):
            api_base = OLLAMA
        extra = {"api_base": api_base} if api_base else {}
        r = litellm.completion(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=max_tokens,
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


def ler_parcial(caminho: Path, impressao: str) -> tuple[str | None, dict[str, dict]]:
    """Respostas já obtidas numa execução interrompida. Falhas do provedor ficam de fora e são refeitas."""
    if not caminho.exists():
        return None, {}
    linhas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not linhas or linhas[0].get("impressao") != impressao:
        return None, {}  # parcial de outra versão do conjunto: não serve
    feitas = {r["id"]: r for r in linhas[1:] if r.get("bruto") or not r.get("erro_formato")}
    return linhas[0].get("rodadoEm"), feitas


def rodar(
    modelo: str,
    itens: list[dict],
    log=print,
    *,
    conjunto: Conjunto | None = None,
    paralelo: int = 1,
    max_tokens: int = MAX_TOKENS,
    api_base: str | None = None,
    parcial: Path | None = None,
) -> dict:
    impressao = conjunto.impressao if conjunto else None
    rodado_em, feitas = ler_parcial(parcial, impressao) if parcial else (None, {})
    ids = {i["id"] for i in itens}
    feitas = {k: v for k, v in feitas.items() if k in ids}
    inicio = rodado_em or datetime.now(timezone.utc).isoformat(timespec="seconds")
    pendentes = [i for i in itens if i["id"] not in feitas]
    if feitas:
        log(f"    retomando: {len(itens) - len(pendentes)} de {len(itens)} já respondidos")

    trava = threading.Lock()
    arquivo = None
    if parcial:
        parcial.parent.mkdir(parents=True, exist_ok=True)
        arquivo = parcial.open("w", encoding="utf-8")
        for linha in [{"modelo": modelo, "impressao": impressao, "rodadoEm": inicio}, *feitas.values()]:
            arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
        arquivo.flush()

    contagem = {"n": len(itens) - len(pendentes), "acertos": sum(r["acertou"] for r in feitas.values())}

    def um(item: dict) -> dict:
        prompt = TASKS[item["task"]].render(item)
        bruto, segundos, erro = chamar(modelo, prompt, max_tokens, api_base)
        resultado = corrigir(item, bruto) if erro is None else {
            "extraido": None, "acertou": False, "formato_ok": False, "erro_formato": erro,
        }
        resposta = {"id": item["id"], "task": item["task"], "bruto": bruto, "segundos": round(segundos, 2), **resultado}
        with trava:
            if arquivo and not arquivo.closed:
                arquivo.write(json.dumps(resposta, ensure_ascii=False) + "\n")
                arquivo.flush()
            contagem["n"] += 1
            contagem["acertos"] += resposta["acertou"]
            if contagem["n"] % 8 == 0 or contagem["n"] == len(itens):
                log(f"    {contagem['n']:3d}/{len(itens)}  acertos {contagem['acertos']}")
        return resposta

    pool = ThreadPoolExecutor(max_workers=max(1, paralelo))
    try:
        novas = list(pool.map(um, pendentes))
        pool.shutdown()
    except BaseException:
        # Ctrl+C: não espera a fila inteira; o que já chegou está no parcial.
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    finally:
        if arquivo:
            arquivo.close()

    por_id = {**feitas, **{r["id"]: r for r in novas}}
    respostas = [por_id[i["id"]] for i in itens]
    return {
        "esquema": ESQUEMA_RODADA,
        "modelo": modelo,
        "rodadoEm": inicio,
        # Soma das latências: não depende de paralelismo nem de retomadas.
        "segundos": round(sum(r["segundos"] for r in respostas), 1),
        "conjunto": conjunto.cabecalho() if conjunto else None,
        "origem": {"tipo": "local"},
        "config": {"temperatura": 0, "max_tokens": max_tokens, "paralelo": paralelo},
        "respostas": respostas,
    }


def executar(
    modelo: str,
    conjunto: Conjunto,
    itens: list[dict],
    *,
    paralelo: int = 1,
    max_tokens: int = MAX_TOKENS,
    api_base: str | None = None,
    do_zero: bool = False,
    log=print,
) -> dict:
    """Roda um modelo com checkpoint, grava o resultado e apaga o parcial."""
    nome = nome_arquivo(modelo)
    parcial = PARCIAL / nome.replace(".json", ".jsonl")
    if do_zero:
        parcial.unlink(missing_ok=True)
    resultado = rodar(
        modelo, itens, log, conjunto=conjunto, paralelo=paralelo, max_tokens=max_tokens, api_base=api_base, parcial=parcial
    )
    descarregar(modelo)
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / nome).write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    falhas = sum(1 for r in resultado["respostas"] if not r["bruto"] and r["erro_formato"])
    if falhas:
        # O parcial fica: a próxima execução refaz só as chamadas que falharam.
        log(f"    {falhas} chamada(s) sem resposta do provedor; rode de novo para refazer só essas")
    else:
        parcial.unlink(missing_ok=True)
    certos = sum(r["acertou"] for r in resultado["respostas"])
    formato = sum(r["formato_ok"] for r in resultado["respostas"])
    log(
        f"    {certos}/{len(itens)} acertos ({certos / len(itens):.0%}), "
        f"formato limpo em {formato / len(itens):.0%}, {resultado['segundos']:.0f}s"
    )
    return resultado


def filtrar(itens: list[dict], tarefas: list[str] | None) -> list[dict]:
    if not tarefas:
        return itens
    desconhecidas = set(tarefas) - set(TASKS)
    if desconhecidas:
        raise SystemExit(f"tarefa desconhecida: {', '.join(sorted(desconhecidas))}")
    return [i for i in itens if i["task"] in tarefas]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelos", nargs="*", default=PADRAO)
    parser.add_argument("--tarefas", nargs="*", help="limita às tarefas indicadas")
    parser.add_argument("--paralelo", type=int, default=1, help="chamadas simultâneas por modelo (padrão 1)")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--do-zero", action="store_true", help="ignora respostas parciais de uma execução interrompida")
    parser.add_argument("--plugins", nargs="*", default=[], help="módulos com avaliadores ou tarefas extras")
    args = parser.parse_args()

    conjunto = carregar_conjunto(plugins=args.plugins)
    itens = filtrar(conjunto.itens, args.tarefas)
    print(f"{len(itens)} itens do conjunto {conjunto.nome} {conjunto.versao}, {len(args.modelos)} modelo(s)")

    for modelo in args.modelos:
        print(f"  {modelo}")
        try:
            executar(modelo, conjunto, itens, paralelo=args.paralelo, max_tokens=args.max_tokens, do_zero=args.do_zero)
        except KeyboardInterrupt:
            raise SystemExit("\nInterrompido. As respostas obtidas ficaram salvas; rode o mesmo comando para retomar.")


if __name__ == "__main__":
    main()
