"""Correção objetiva: a resposta do modelo bate com o gabarito ou não bate.

Duas coisas são medidas, e de propósito separadas:

- **acerto**: a resposta, depois de extraída do texto, é igual ao gabarito.
- **formato**: a resposta já veio exatamente no formato pedido, sem enfeite.

Um modelo pode entender a mensagem e ainda assim escrever "Claro! O valor é
R$ 1.500,00 😊". A extração é tolerante para não confundir compreensão com
obediência, mas o relatório mostra as duas colunas.
"""

import json
import re
import unicodedata
from dataclasses import dataclass

from .tasks import TASKS, Task

MOEDA = re.compile(r"(?i)\b(r\$|reais?|pila|conto)\b|\s")
NUMERO = re.compile(r"-?\d[\d.,]*")
DATA = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
LETRA = re.compile(r"(?i)\b([a-e])\b")


@dataclass
class Parsed:
    valor: object | None
    formato_ok: bool  # a saída já era exatamente o formato pedido
    erro: str | None = None


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    return sem_acento(texto).casefold().strip(" \t\n\r.,;:!?\"'`*-_")


def _limpar(bruto: str) -> str:
    """Tira cercas de markdown e espaços, que quase todo modelo coloca."""
    texto = bruto.strip()
    cerca = re.match(r"^```[a-z]*\s*\n?(.*?)\n?```$", texto, re.S)
    return (cerca.group(1) if cerca else texto).strip()


def parse_numero(bruto: str) -> Parsed:
    texto = _limpar(bruto)
    achado = NUMERO.search(MOEDA.sub("", texto))
    if not achado:
        return Parsed(None, False, "sem número na resposta")
    cru = achado.group(0).rstrip(".,")
    tem_ponto, tem_virgula = "." in cru, "," in cru
    if tem_ponto and tem_virgula:
        # O separador decimal é o que aparece por último: 1.234,56 ou 1,234.56
        decimal = "," if cru.rfind(",") > cru.rfind(".") else "."
        milhar = "." if decimal == "," else ","
        cru = cru.replace(milhar, "").replace(decimal, ".")
    elif tem_virgula:
        cru = cru.replace(",", ".")
    elif tem_ponto and re.search(r"\.\d{3}$", cru):
        # 1.500 é mil e quinhentos em português; 44.91 continua sendo decimal.
        cru = cru.replace(".", "")
    try:
        valor = float(cru)
    except ValueError:
        return Parsed(None, False, f"número ilegível: {achado.group(0)!r}")
    return Parsed(valor, texto == achado.group(0))


def parse_json(bruto: str, campos: list[str]) -> Parsed:
    texto = _limpar(bruto)
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fim < inicio:
        return Parsed(None, False, "sem objeto JSON na resposta")
    trecho = texto[inicio : fim + 1]
    try:
        obj = json.loads(trecho)
    except json.JSONDecodeError as e:
        return Parsed(None, False, f"JSON inválido: {e.msg}")
    if not isinstance(obj, dict):
        return Parsed(None, False, "o JSON não é um objeto")
    faltando = [c for c in campos if c not in obj]
    if faltando:
        return Parsed(None, trecho == texto, f"faltou o campo {', '.join(faltando)}")
    return Parsed({c: obj[c] for c in campos}, trecho == texto)


def parse_rotulo(bruto: str, rotulos: tuple[str, ...]) -> Parsed:
    texto = _limpar(bruto)
    alvo = normalizar(texto)
    for r in rotulos:
        if alvo == normalizar(r):
            return Parsed(r, True)
    # O rótulo certo pode vir no meio de uma frase.
    achados = [r for r in rotulos if re.search(rf"\b{re.escape(normalizar(r))}\b", normalizar(texto))]
    if len(achados) == 1:
        return Parsed(achados[0], False)
    if len(achados) > 1:
        return Parsed(None, False, "mais de um rótulo na resposta")
    return Parsed(None, False, "nenhum rótulo conhecido na resposta")


def parse_data(bruto: str) -> Parsed:
    texto = _limpar(bruto)
    achado = DATA.search(texto)
    if not achado:
        return Parsed(None, False, "sem data AAAA-MM-DD na resposta")
    return Parsed(achado.group(0), texto == achado.group(0))


def parse_alternativa(bruto: str, alternativas: dict) -> Parsed:
    texto = _limpar(bruto)
    achado = LETRA.search(texto)
    if achado and achado.group(1).upper() in alternativas:
        return Parsed(achado.group(1).upper(), normalizar(texto) == normalizar(achado.group(1)))
    # Alguns modelos devolvem o texto da alternativa em vez da letra.
    for letra, opcao in alternativas.items():
        if normalizar(opcao) in normalizar(texto):
            return Parsed(letra, False)
    return Parsed(None, False, "sem alternativa reconhecível na resposta")


def parse_nome(bruto: str) -> Parsed:
    texto = _limpar(bruto)
    achado = re.search(r"[A-Za-zÀ-ÿ]+", texto)
    if not achado:
        return Parsed(None, False, "sem nome na resposta")
    return Parsed(achado.group(0), texto == achado.group(0))


def extrair(task: Task, item: dict, bruto: str) -> Parsed:
    if task.answer_type == "numero":
        return parse_numero(bruto)
    if task.answer_type == "json":
        return parse_json(bruto, list(item["gabarito"].keys()))
    if task.answer_type == "rotulo":
        return parse_rotulo(bruto, task.rotulos)
    if task.answer_type == "data":
        return parse_data(bruto)
    if task.answer_type == "alternativa":
        return parse_alternativa(bruto, item["alternativas"])
    return parse_nome(bruto)


def conferir(task: Task, item: dict, valor: object) -> bool:
    gabarito = item["gabarito"]
    if task.answer_type == "numero":
        return isinstance(valor, float) and abs(valor - float(gabarito)) < 1e-6
    if task.answer_type == "json":
        return isinstance(valor, dict) and all(str(valor.get(c, "")).strip() == str(v) for c, v in gabarito.items())
    if task.answer_type in ("rotulo", "data", "alternativa"):
        return str(valor) == str(gabarito)
    return normalizar(str(valor)) == normalizar(str(gabarito))


def corrigir(item: dict, bruto: str) -> dict:
    """Devolve o resultado de um item: o que foi extraído, se acertou e se o formato veio limpo."""
    task = TASKS[item["task"]]
    p = extrair(task, item, bruto)
    acertou = p.valor is not None and conferir(task, item, p.valor)
    return {
        "extraido": p.valor,
        "acertou": acertou,
        "formato_ok": p.formato_ok and p.erro is None,
        "erro_formato": p.erro,
    }
