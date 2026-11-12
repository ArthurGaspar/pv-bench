"""Esquemas versionados do conjunto de itens e dos arquivos de rodada.

Conjunto (`data/items.json`), esquema 1:

    {"esquema": 1, "nome": "recado", "versao": "1.0.0",
     "plugins": ["modulo.opcional"], "itens": [...]}

O formato antigo, uma lista solta de itens, é lido como esquema 0 e migrado em
memória.

Rodada (`data/resultados/*.json`), esquema 1:

    {"esquema": 1, "modelo": "...", "rodadoEm": "ISO 8601", "segundos": 12.3,
     "conjunto": {"nome": "recado", "versao": "1.0.0", "impressao": "sha256:..."},
     "origem": {"tipo": "local" | "importado", ...},
     "config": {...},
     "respostas": [{"id", "task", "bruto", "segundos", ...}]}

Rodadas sem `esquema` são do formato anterior: valem como esquema 1 sem
`conjunto`, e por isso só passam pela conferência item a item.

A `impressao` é o hash dos prompts montados (id, tarefa e texto exato enviado
ao modelo). Gabarito e `pega` ficam de fora de propósito: corrigir um gabarito
não invalida as respostas, porque as notas sempre são recalculadas a partir do
texto bruto. Mudar uma mensagem ou um template, sim.
"""

import hashlib
import json
import re
from datetime import datetime

ESQUEMA_CONJUNTO = 1
ESQUEMA_RODADA = 1
TIPOS_ORIGEM = ("local", "importado")


def _versao(dados: dict, atual: int, oque: str) -> int:
    esquema = dados.get("esquema", 0)
    if not isinstance(esquema, int) or isinstance(esquema, bool) or esquema < 0:
        raise ValueError(f"{oque}: 'esquema' deveria ser um inteiro, veio {esquema!r}")
    if esquema > atual:
        raise ValueError(f"{oque}: esquema {esquema} é mais novo que o suportado ({atual}); atualize o harness")
    return esquema


# --- conjunto -----------------------------------------------------------------


def migrar_conjunto(dados) -> dict:
    """Devolve o conjunto no esquema atual, sem alterar `dados`."""
    if isinstance(dados, list):
        return {"esquema": ESQUEMA_CONJUNTO, "nome": "recado", "versao": "0", "plugins": [], "itens": dados}
    if not isinstance(dados, dict):
        raise ValueError("conjunto: esperava um objeto com 'itens' ou uma lista de itens")
    _versao(dados, ESQUEMA_CONJUNTO, "conjunto")
    return {"plugins": [], **dados, "esquema": ESQUEMA_CONJUNTO}


def conferir_envelope(dados: dict) -> list[str]:
    erros = []
    for campo in ("nome", "versao"):
        if not isinstance(dados.get(campo), str) or not dados[campo].strip():
            erros.append(f"'{campo}' deveria ser um texto não vazio")
    if not isinstance(dados.get("itens"), list):
        erros.append("'itens' deveria ser uma lista")
    elif not all(isinstance(i, dict) for i in dados["itens"]):
        erros.append("todo item deveria ser um objeto")
    plugins = dados.get("plugins", [])
    if not isinstance(plugins, list) or not all(isinstance(p, str) for p in plugins):
        erros.append("'plugins' deveria ser uma lista de nomes de módulo")
    desconhecidos = set(dados) - {"esquema", "nome", "versao", "descricao", "plugins", "itens"}
    if desconhecidos:
        erros.append(f"campos desconhecidos no cabeçalho: {', '.join(sorted(desconhecidos))}")
    return erros


def impressao(itens: list[dict]) -> str:
    from .tasks import TASKS

    canonico = [[i["id"], i["task"], TASKS[i["task"]].render(i)] for i in sorted(itens, key=lambda i: i["id"])]
    texto = json.dumps(canonico, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(texto.encode("utf-8")).hexdigest()


# --- rodada -------------------------------------------------------------------


def migrar_rodada(dados) -> dict:
    if not isinstance(dados, dict):
        raise ValueError("rodada: esperava um objeto")
    if _versao(dados, ESQUEMA_RODADA, "rodada") == 0:
        return {"conjunto": None, "origem": {"tipo": "local"}, **dados, "esquema": ESQUEMA_RODADA}
    return dict(dados)


def _numero(v, nulo: bool = False) -> bool:
    if v is None:
        return nulo
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0


def conferir_estrutura_rodada(r: dict) -> list[str]:
    """Tipos e campos obrigatórios. Não olha o conjunto; isso é com `conferir_rodada`."""
    erros = []
    if not isinstance(r.get("modelo"), str) or not r["modelo"].strip():
        erros.append("'modelo' deveria ser um texto não vazio")
    try:
        datetime.fromisoformat(str(r.get("rodadoEm")))
    except ValueError:
        erros.append(f"'rodadoEm' deveria ser uma data ISO 8601, veio {r.get('rodadoEm')!r}")
    if not _numero(r.get("segundos"), nulo=True):
        erros.append("'segundos' deveria ser um número não negativo ou null")
    conjunto = r.get("conjunto")
    if conjunto is not None and not (
        isinstance(conjunto, dict) and all(isinstance(conjunto.get(c), str) for c in ("nome", "versao", "impressao"))
    ):
        erros.append("'conjunto' deveria ter 'nome', 'versao' e 'impressao' como texto")
    origem = r.get("origem")
    if not isinstance(origem, dict) or origem.get("tipo") not in TIPOS_ORIGEM:
        erros.append(f"'origem.tipo' deveria ser um de {', '.join(TIPOS_ORIGEM)}")
    respostas = r.get("respostas")
    if not isinstance(respostas, list) or not respostas:
        erros.append("'respostas' deveria ser uma lista não vazia")
        return erros
    for n, resp in enumerate(respostas):
        onde = f"respostas[{n}]"
        if not isinstance(resp, dict):
            erros.append(f"{onde}: deveria ser um objeto")
            continue
        onde = f"{onde} ({resp.get('id', 'sem id')})"
        for campo in ("id", "task", "bruto"):
            if not isinstance(resp.get(campo), str):
                erros.append(f"{onde}: '{campo}' deveria ser texto")
        if not _numero(resp.get("segundos"), nulo=True):
            erros.append(f"{onde}: 'segundos' deveria ser um número não negativo ou null")
    return erros


def conferir_rodada(rodada: dict, itens: list[dict], conjunto: dict | None = None) -> tuple[list[dict], set[str]]:
    """Confere uma rodada contra o conjunto e recorrige cada resposta a partir do texto bruto.

    Devolve as respostas corrigidas e os ids que faltaram. Levanta ValueError
    com todos os problemas encontrados, não só o primeiro.
    """
    from .grade import corrigir

    modelo = rodada.get("modelo", "<sem modelo>")
    erros = []
    feita_com = rodada.get("conjunto")
    if conjunto and feita_com:
        if feita_com.get("nome") != conjunto["nome"]:
            erros.append(f"rodada do conjunto {feita_com.get('nome')!r}, não de {conjunto['nome']!r}")
        elif feita_com.get("impressao") != conjunto["impressao"]:
            erros.append(
                f"prompts diferentes dos atuais (rodada na versão {feita_com.get('versao')}, "
                f"conjunto na {conjunto['versao']}); rode o modelo de novo"
            )
    por_id = {i["id"]: i for i in itens}
    vistos: set[str] = set()
    respostas = []
    for resposta in rodada["respostas"]:
        id_ = resposta["id"]
        if id_ in vistos:
            erros.append(f"item repetido {id_}")
            continue
        vistos.add(id_)
        item = por_id.get(id_)
        if item is None:
            erros.append(f"item desconhecido {id_}")
            continue
        if resposta["task"] != item["task"]:
            erros.append(f"tarefa inconsistente em {id_}")
            continue
        resultado = corrigir(item, resposta["bruto"])
        if not resposta["bruto"] and resposta.get("erro_formato"):
            # Falha do provedor: guarda o motivo registrado na execução.
            resultado["erro_formato"] = resposta["erro_formato"]
        respostas.append({**resposta, **resultado})
    if erros:
        raise ValueError(f"{modelo}: " + f"\n  {modelo}: ".join(erros))
    return respostas, set(por_id) - vistos


def nome_arquivo(modelo: str) -> str:
    """ollama/qwen2.5:7b -> ollama__qwen2.5_7b.json; nada de barra, espaço ou caminho relativo."""
    base = re.sub(r"[^A-Za-z0-9._-]", "_", modelo.replace("/", "__"))
    base = re.sub(r"\.{2,}", "_", base).lstrip(".")
    return (base or "modelo") + ".json"
