"""Execução em lote: vários modelos, cada um com sua configuração, a partir de um arquivo.

    python -m bench.lote lotes/exemplo.json
    python -m bench.lote lotes/exemplo.json --so-validar   # confere a especificação e para
    python -m bench.lote lotes/exemplo.json --do-zero      # ignora parciais

Especificação (JSON):

    {
      "esquema": 1,
      "tarefas": ["valor", "contagem"],          # opcional; sem ela, o conjunto todo
      "padrao": {"paralelo": 1, "max_tokens": 200},
      "plugins": ["meu_pacote.avaliadores"],     # opcional
      "modelos": [
        "ollama/qwen2.5:7b",
        {"modelo": "openai/gpt-4o-mini", "paralelo": 4},
        {"modelo": "ollama/llama3.1:8b", "api_base": "http://outra-maquina:11434"}
      ]
    }

Um modelo que falha não derruba o lote: os outros seguem, e o resumo no fim
diz o que faltou. Cada modelo tem checkpoint próprio, então rodar o mesmo lote
de novo retoma só o que não terminou. Use `--pular-prontos` para não refazer
modelos que já têm resultado completo no conjunto atual.
"""

import argparse
import json
import sys
import traceback
from pathlib import Path

from .dataset import Conjunto, carregar_conjunto
from .esquema import migrar_rodada, nome_arquivo
from .run import MAX_TOKENS, SAIDA, executar, filtrar

ESQUEMA_LOTE = 1
OPCOES = {"paralelo": int, "max_tokens": int, "api_base": str}


def conferir_spec(spec) -> list[str]:
    if not isinstance(spec, dict):
        return ["a especificação deveria ser um objeto"]
    erros = []
    if spec.get("esquema", ESQUEMA_LOTE) != ESQUEMA_LOTE:
        erros.append(f"esquema {spec.get('esquema')!r} não suportado (esperado {ESQUEMA_LOTE})")
    desconhecidos = set(spec) - {"esquema", "descricao", "tarefas", "padrao", "plugins", "modelos"}
    if desconhecidos:
        erros.append(f"campos desconhecidos: {', '.join(sorted(desconhecidos))}")
    tarefas = spec.get("tarefas")
    if tarefas is not None and (not isinstance(tarefas, list) or not all(isinstance(t, str) for t in tarefas)):
        erros.append("'tarefas' deveria ser uma lista de ids de tarefa")
    plugins = spec.get("plugins", [])
    if not isinstance(plugins, list) or not all(isinstance(p, str) for p in plugins):
        erros.append("'plugins' deveria ser uma lista de nomes de módulo")
    erros += [f"padrao: {e}" for e in _conferir_opcoes(spec.get("padrao", {}))]
    modelos = spec.get("modelos")
    if not isinstance(modelos, list) or not modelos:
        erros.append("'modelos' deveria ser uma lista não vazia")
        return erros
    vistos = set()
    for n, entrada in enumerate(modelos):
        if isinstance(entrada, str):
            entrada = {"modelo": entrada}
        if not isinstance(entrada, dict) or not isinstance(entrada.get("modelo"), str) or not entrada["modelo"]:
            erros.append(f"modelos[{n}]: deveria ser um nome ou um objeto com 'modelo'")
            continue
        nome = entrada["modelo"]
        if nome_arquivo(nome) in vistos:
            erros.append(f"modelos[{n}]: {nome} repetido (gravaria no mesmo arquivo)")
        vistos.add(nome_arquivo(nome))
        opcoes = {k: v for k, v in entrada.items() if k != "modelo"}
        erros += [f"modelos[{n}] ({nome}): {e}" for e in _conferir_opcoes(opcoes)]
    return erros


def _conferir_opcoes(opcoes) -> list[str]:
    if not isinstance(opcoes, dict):
        return ["deveria ser um objeto"]
    erros = []
    for chave, valor in opcoes.items():
        tipo = OPCOES.get(chave)
        if tipo is None:
            erros.append(f"opção desconhecida {chave!r}")
        elif not isinstance(valor, tipo) or isinstance(valor, bool):
            erros.append(f"{chave} deveria ser {tipo.__name__}")
        elif tipo is int and valor < 1:
            erros.append(f"{chave} deveria ser pelo menos 1")
    return erros


def planejar(spec: dict) -> list[dict]:
    """Uma entrada por modelo, com as opções padrão já aplicadas."""
    padrao = {"paralelo": 1, "max_tokens": MAX_TOKENS, "api_base": None, **spec.get("padrao", {})}
    plano = []
    for entrada in spec["modelos"]:
        entrada = {"modelo": entrada} if isinstance(entrada, str) else entrada
        plano.append({**padrao, **entrada})
    return plano


def pronto(modelo: str, conjunto: Conjunto, itens: list[dict]) -> bool:
    """Já existe resultado deste modelo, com os prompts atuais, cobrindo os itens pedidos?"""
    arquivo = SAIDA / nome_arquivo(modelo)
    if not arquivo.exists():
        return False
    try:
        r = migrar_rodada(json.loads(arquivo.read_text(encoding="utf-8")))
    except ValueError:
        return False
    if (r.get("conjunto") or {}).get("impressao") != conjunto.impressao:
        return False
    # Resposta vazia com erro é falha do provedor, não resposta: não conta como pronto.
    ok = {x["id"] for x in r.get("respostas", []) if x.get("bruto") or not x.get("erro_formato")}
    return {i["id"] for i in itens} <= ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path, help="arquivo JSON com a especificação do lote")
    parser.add_argument("--so-validar", action="store_true", help="confere a especificação e o conjunto, sem chamar modelo")
    parser.add_argument("--do-zero", action="store_true", help="ignora respostas parciais de execuções interrompidas")
    parser.add_argument("--pular-prontos", action="store_true", help="não refaz modelos com resultado completo e atual")
    args = parser.parse_args(argv)

    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"não consegui ler {args.spec}: {e}", file=sys.stderr)
        return 2
    erros = conferir_spec(spec)
    if erros:
        print(f"{args.spec}: especificação inválida:\n  " + "\n  ".join(erros), file=sys.stderr)
        return 2

    conjunto = carregar_conjunto(plugins=spec.get("plugins"))
    itens = filtrar(conjunto.itens, spec.get("tarefas"))
    plano = planejar(spec)
    print(f"Lote {args.spec.name}: {len(plano)} modelo(s), {len(itens)} itens do conjunto {conjunto.nome} {conjunto.versao}")
    for p in plano:
        print(f"  {p['modelo']:36s} paralelo {p['paralelo']}, max_tokens {p['max_tokens']}")
    if args.so_validar:
        return 0

    resumo: list[tuple[str, str]] = []
    for p in plano:
        modelo = p["modelo"]
        print(f"\n  {modelo}")
        if args.pular_prontos and pronto(modelo, conjunto, itens):
            print("    já tem resultado completo com os prompts atuais; pulando")
            resumo.append((modelo, "pulado"))
            continue
        try:
            r = executar(
                modelo, conjunto, itens,
                paralelo=p["paralelo"], max_tokens=p["max_tokens"], api_base=p["api_base"], do_zero=args.do_zero,
            )
        except KeyboardInterrupt:
            print("\nInterrompido. Rode o mesmo lote para retomar; as respostas obtidas ficaram salvas.")
            resumo.append((modelo, "interrompido"))
            break
        except Exception as e:  # noqa: BLE001 - um modelo quebrado não derruba os outros
            traceback.print_exc()
            resumo.append((modelo, f"falhou: {type(e).__name__}: {e}"))
            continue
        falhas = sum(1 for x in r["respostas"] if not x["bruto"] and x["erro_formato"])
        certos = sum(x["acertou"] for x in r["respostas"])
        estado = f"{certos}/{len(itens)} acertos"
        if falhas:
            estado += f", {falhas} sem resposta do provedor (rode o lote de novo para refazer só essas)"
        resumo.append((modelo, estado))

    print("\nResumo")
    for modelo, estado in resumo:
        print(f"  {modelo:36s} {estado}")
    return 0 if all(not e.startswith(("falhou", "interrompido")) for _, e in resumo) and len(resumo) == len(plano) else 1


if __name__ == "__main__":
    raise SystemExit(main())
