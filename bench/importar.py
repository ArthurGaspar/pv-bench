"""Importa respostas geradas fora deste harness, conferindo tudo antes de gravar.

    python -m bench.importar rodada.json
    python -m bench.importar respostas.jsonl --modelo provedor/modelo-x
    python -m bench.importar export.csv --so-validar
    python -m bench.importar rodada.json --substituir     # sobrescreve um resultado existente

Formatos aceitos, escolhidos pela extensão (ou por `--formato`):

- **json**: um arquivo de rodada deste projeto, de qualquer esquema suportado,
  ou uma lista de respostas.
- **jsonl**: uma resposta por linha.
- **csv**: com cabeçalho. É o mesmo formato do "Exportar CSV" do site.

Cada resposta precisa de `id` (ou `item`) e `bruto` (ou `resposta`), o texto
exato que o modelo devolveu. `modelo`, `task`/`tarefa` e `segundos` são
opcionais; um arquivo com vários modelos vira uma rodada por modelo.

Nada que venha de fora é aceito como nota: acerto, formato e valor extraído
são recalculados pelo corretor deste projeto, e divergências com o que o
arquivo dizia aparecem como aviso. A importação é tudo ou nada: com qualquer
erro, nenhum arquivo é gravado.
"""

import argparse
import csv
import io
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .dataset import Conjunto, carregar_conjunto
from .esquema import ESQUEMA_RODADA, conferir_estrutura_rodada, conferir_rodada, migrar_rodada, nome_arquivo
from .run import SAIDA

FORMATOS = ("json", "jsonl", "csv")
ALIASES = {"id": ("id", "item"), "bruto": ("bruto", "resposta"), "task": ("task", "tarefa")}
VERDADEIRO = {"true", "1", "sim", "verdadeiro"}


@dataclass
class Relatorio:
    modelo: str
    rodada: dict | None = None
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _campo(linha: dict, nome: str):
    for chave in ALIASES.get(nome, (nome,)):
        if chave in linha:
            return linha[chave]
    return None


def _segundos(v):
    if v is None or v == "":
        return None
    if isinstance(v, str):
        try:
            return float(v.replace(",", "."))
        except ValueError:
            return v  # a conferência de estrutura aponta o erro
    return v


def _acertou_declarado(v):
    if isinstance(v, str):
        return v.strip().casefold() in VERDADEIRO if v.strip() else None
    return v if isinstance(v, bool) else None


def ler_linhas(texto: str, formato: str) -> tuple[dict | None, list[dict]]:
    """Devolve (rodada nativa ou None, linhas de resposta)."""
    if formato == "json":
        dados = json.loads(texto)
        if isinstance(dados, dict):
            return dados, []
        if not isinstance(dados, list):
            raise ValueError("o JSON deveria ser uma rodada (objeto) ou uma lista de respostas")
        return None, dados
    if formato == "jsonl":
        linhas = []
        for n, linha in enumerate(texto.splitlines(), start=1):
            if linha.strip():
                try:
                    linhas.append(json.loads(linha))
                except json.JSONDecodeError as e:
                    raise ValueError(f"linha {n}: JSON inválido ({e.msg})") from None
        return None, linhas
    try:
        dialeto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t")
    except csv.Error:
        dialeto = csv.excel
    return None, list(csv.DictReader(io.StringIO(texto), dialect=dialeto))


def agrupar(linhas: list, modelo_forcado: str | None) -> tuple[dict[str, list[dict]], list[str]]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    erros = []
    for n, linha in enumerate(linhas, start=1):
        if not isinstance(linha, dict):
            erros.append(f"linha {n}: deveria ser um objeto")
            continue
        modelo = modelo_forcado or linha.get("modelo")
        if not isinstance(modelo, str) or not modelo.strip():
            erros.append(f"linha {n}: sem modelo; passe --modelo")
            continue
        grupos[modelo.strip()].append(linha)
    return grupos, erros


def montar_rodada(modelo: str, linhas: list[dict]) -> dict:
    respostas = []
    for linha in linhas:
        resposta = {"id": _campo(linha, "id"), "task": _campo(linha, "task") or None, "bruto": _campo(linha, "bruto"), "segundos": _segundos(linha.get("segundos"))}
        declarado = _acertou_declarado(linha.get("acertou"))
        if declarado is not None:
            resposta["_acertou_declarado"] = declarado
        respostas.append(resposta)
    tempos = [r["segundos"] for r in respostas]
    total = round(sum(tempos), 1) if tempos and all(isinstance(t, (int, float)) for t in tempos) else None
    return {"esquema": ESQUEMA_RODADA, "modelo": modelo, "rodadoEm": None, "segundos": total, "conjunto": None, "respostas": respostas}


def validar(rodada: dict, conjunto: Conjunto, arquivo: str, formato: str, substituir: bool) -> Relatorio:
    rel = Relatorio(str(rodada.get("modelo")))
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if rodada.get("rodadoEm") is None:
        rodada["rodadoEm"] = agora
        rel.avisos.append("sem data da rodada; usando a data da importação")
    if isinstance(rodada.get("respostas"), list):
        for r in rodada["respostas"]:
            if isinstance(r, dict) and r.get("task") is None:
                item = next((i for i in conjunto.itens if i["id"] == r.get("id")), None)
                if item:
                    r["task"] = item["task"]
                elif isinstance(r.get("id"), str):
                    rel.erros.append(f"item desconhecido {r['id']}")
                    r["task"] = ""
    origem_anterior = rodada.get("origem")
    rodada["origem"] = {"tipo": "importado", "arquivo": arquivo, "formato": formato, "importadoEm": agora}
    if isinstance(origem_anterior, dict) and origem_anterior.get("tipo") == "importado":
        rodada["origem"]["anterior"] = origem_anterior

    rel.erros += conferir_estrutura_rodada(rodada)
    if rel.erros:
        return rel
    if rodada.get("conjunto") is None:
        rel.avisos.append("sem impressão do conjunto: não dá para garantir que os prompts eram os atuais")
    declarados = {
        r["id"]: r.get("_acertou_declarado", r.get("acertou"))
        for r in rodada["respostas"]
        if isinstance(r.get("_acertou_declarado", r.get("acertou")), bool)
    }
    try:
        corrigidas, faltando = conferir_rodada(rodada, conjunto.itens, conjunto.cabecalho())
    except ValueError as e:
        rel.erros += [l.split(": ", 1)[-1] for l in str(e).splitlines()]
        return rel

    if any(r.get("segundos") is None for r in corrigidas):
        rel.avisos.append("respostas sem tempo; a coluna de tempo fica vazia")
    divergentes = sorted(r["id"] for r in corrigidas if r["id"] in declarados and declarados[r["id"]] != r["acertou"])
    if divergentes:
        rel.avisos.append(
            f"{len(divergentes)} acerto(s) declarados diferem da recorreção (ex.: {', '.join(divergentes[:5])}); vale a recorreção"
        )
    if faltando:
        rel.avisos.append(f"cobre {len(corrigidas)} de {len(conjunto.itens)} itens; rodada parcial fica fora do placar")
    if (SAIDA / nome_arquivo(rodada["modelo"])).exists() and not substituir:
        rel.erros.append(f"já existe {nome_arquivo(rodada['modelo'])} em data/resultados; use --substituir")

    campos = ("id", "task", "bruto", "segundos")
    ordem = {i["id"]: n for n, i in enumerate(conjunto.itens)}
    respostas = sorted(
        ({**{c: r.get(c) for c in campos}, **{k: r[k] for k in ("extraido", "acertou", "formato_ok", "erro_formato")}} for r in corrigidas),
        key=lambda r: ordem[r["id"]],
    )
    rel.rodada = {
        "esquema": ESQUEMA_RODADA,
        "modelo": rodada["modelo"],
        "rodadoEm": rodada["rodadoEm"],
        "segundos": rodada.get("segundos"),
        "conjunto": rodada.get("conjunto"),
        "origem": rodada["origem"],
        "config": rodada.get("config"),
        "respostas": respostas,
    }
    return rel


def importar(caminho: Path, conjunto: Conjunto, *, formato: str | None = None, modelo: str | None = None,
             substituir: bool = False) -> list[Relatorio]:
    formato = formato or caminho.suffix.lstrip(".").lower()
    if formato not in FORMATOS:
        raise ValueError(f"formato {formato!r} desconhecido; use --formato {'/'.join(FORMATOS)}")
    nativa, linhas = ler_linhas(caminho.read_text(encoding="utf-8-sig"), formato)
    if nativa is not None:
        rodada = migrar_rodada(nativa)
        if modelo:
            rodada["modelo"] = modelo
        rodadas, erros = [rodada], []
    else:
        grupos, erros = agrupar(linhas, modelo)
        rodadas = [montar_rodada(m, ls) for m, ls in grupos.items()]
    if erros or not rodadas:
        return [Relatorio(modelo or "?", erros=erros or ["nenhuma resposta no arquivo"])]
    relatorios = [validar(r, conjunto, caminho.name, formato, substituir) for r in rodadas]
    destinos = defaultdict(list)
    for rel in relatorios:
        destinos[nome_arquivo(rel.modelo)].append(rel)
    for nome, rels in destinos.items():
        if len(rels) > 1:
            for rel in rels:
                rel.erros.append(f"mais de um modelo do arquivo iria para {nome}")
    return relatorios


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("arquivo", type=Path)
    parser.add_argument("--formato", choices=FORMATOS, help="padrão: pela extensão do arquivo")
    parser.add_argument("--modelo", help="nome do modelo; obrigatório se o arquivo não disser")
    parser.add_argument("--substituir", action="store_true", help="sobrescreve resultado existente do mesmo modelo")
    parser.add_argument("--so-validar", action="store_true", help="confere e mostra o relatório, sem gravar")
    parser.add_argument("--plugins", nargs="*", default=[], help="módulos com avaliadores ou tarefas extras")
    args = parser.parse_args(argv)

    conjunto = carregar_conjunto(plugins=args.plugins)
    try:
        relatorios = importar(args.arquivo, conjunto, formato=args.formato, modelo=args.modelo, substituir=args.substituir)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"{args.arquivo}: {e}", file=sys.stderr)
        return 2

    for rel in relatorios:
        estado = "inválida" if rel.erros else "ok"
        resumo = ""
        if rel.rodada:
            r = rel.rodada["respostas"]
            resumo = f"  {sum(x['acertou'] for x in r)}/{len(r)} acertos na recorreção"
        print(f"{rel.modelo}: {estado}{resumo}")
        for e in rel.erros[:30]:
            print(f"  erro: {e}")
        if len(rel.erros) > 30:
            print(f"  ... e mais {len(rel.erros) - 30} erros")
        for a in rel.avisos:
            print(f"  aviso: {a}")

    if any(rel.erros for rel in relatorios):
        print("Nada foi gravado.", file=sys.stderr)
        return 1
    if args.so_validar:
        return 0
    SAIDA.mkdir(parents=True, exist_ok=True)
    for rel in relatorios:
        destino = SAIDA / nome_arquivo(rel.rodada["modelo"])
        destino.write_text(json.dumps(rel.rodada, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  gravado {destino.relative_to(SAIDA.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
