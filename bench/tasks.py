"""As tarefas do benchmark: o que se pergunta ao modelo e como a resposta é cobrada.

Cada tarefa tem um tipo de resposta com um corretor objetivo: ou bate, ou não
bate. Não existe nota de júri nem modelo avaliando modelo, então a correção é
determinística e qualquer pessoa pode repetir e chegar ao mesmo número.

Os prompts são em português porque o benchmark mede compreensão de português.
Todos exigem resposta curta e em formato fixo, e a conformidade com o formato é
medida à parte do acerto: um modelo pode entender a mensagem e mesmo assim
perder o ponto por enfeitar a resposta.
"""

from dataclasses import dataclass
from typing import Literal

AnswerType = Literal["json", "numero", "rotulo", "data", "alternativa", "nome"]

FORMATO = "Responda APENAS com {formato}, sem explicação, sem comentário e sem markdown."


@dataclass(frozen=True)
class Task:
    id: str
    titulo: str
    descricao: str
    answer_type: AnswerType
    prompt: str
    rotulos: tuple[str, ...] = ()

    def render(self, item: dict) -> str:
        campos = {"mensagem": item["mensagem"], **item.get("contexto", {})}
        if self.rotulos:
            campos["rotulos"] = ", ".join(self.rotulos)
        if item.get("alternativas"):
            campos["alternativas"] = "\n".join(f"{letra}) {texto}" for letra, texto in item["alternativas"].items())
        return self.prompt.format(**campos)


TASKS: dict[str, Task] = {
    "compromisso": Task(
        id="compromisso",
        titulo="Combinar um encontro",
        descricao="A mensagem marca dia e hora de um jeito torto. Extrair a data e a hora exatas.",
        answer_type="json",
        prompt=(
            "Hoje é {hoje} ({diadasemana}).\n"
            "Quando a mensagem disser \"que vem\", considere a próxima ocorrência daquele dia.\n\n"
            "Mensagem recebida:\n\"\"\"{mensagem}\"\"\"\n\n"
            "Qual dia e hora ficou combinado?\n"
            + FORMATO.format(formato='o JSON {{"data": "AAAA-MM-DD", "hora": "HH:MM"}} em formato 24 horas')
        ),
    ),
    "valor": Task(
        id="valor",
        titulo="Entender o valor",
        descricao="Dinheiro e quantidade escritos como brasileiro escreve: vírgula decimal, 'k', 'pila', conta pela metade.",
        answer_type="numero",
        prompt=(
            "Mensagem recebida:\n\"\"\"{mensagem}\"\"\"\n\n"
            "{pergunta}\n"
            + FORMATO.format(formato="o número, usando ponto como separador decimal (exemplo: 1234.56)")
        ),
    ),
    "intencao": Task(
        id="intencao",
        titulo="Para que serve a mensagem",
        descricao="Classificar a intenção de quem mandou, escolhendo um rótulo fechado.",
        answer_type="rotulo",
        rotulos=("convite", "cobranca", "cancelamento", "confirmacao", "favor", "spam", "reclamacao", "desabafo"),
        prompt=(
            "Mensagem recebida:\n\"\"\"{mensagem}\"\"\"\n\n"
            "Qual a intenção de quem mandou? Escolha exatamente um destes rótulos: {rotulos}.\n"
            + FORMATO.format(formato="o rótulo")
        ),
    ),
    "resposta": Task(
        id="resposta",
        titulo="Aceitou ou enrolou",
        descricao="Convite feito, resposta recebida. Descobrir se é sim, não ou talvez, mesmo quando vem de ironia.",
        answer_type="rotulo",
        rotulos=("aceitou", "recusou", "talvez"),
        prompt=(
            "Você convidou alguém para isto: {convite}\n\n"
            "A pessoa respondeu:\n\"\"\"{mensagem}\"\"\"\n\n"
            "A pessoa aceitou, recusou ou ficou de talvez? Escolha um: {rotulos}.\n"
            + FORMATO.format(formato="o rótulo")
        ),
    ),
    "pedido": Task(
        id="pedido",
        titulo="O que ela quer de verdade",
        descricao="Pedido indireto: ninguém pede nada com todas as letras, mas está pedindo.",
        answer_type="alternativa",
        prompt=(
            "Situação: {situacao}\n\n"
            "A pessoa falou:\n\"\"\"{mensagem}\"\"\"\n\n"
            "O que ela quer na verdade?\n{alternativas}\n"
            + FORMATO.format(formato="a letra da alternativa")
        ),
    ),
    "data_relativa": Task(
        id="data_relativa",
        titulo="Que dia é esse",
        descricao="Resolver expressões de tempo relativas a partir de uma data de referência.",
        answer_type="data",
        prompt=(
            "Hoje é {hoje} ({diadasemana}).\n"
            "Quando a mensagem disser \"que vem\", considere a próxima ocorrência daquele dia.\n\n"
            "Mensagem recebida:\n\"\"\"{mensagem}\"\"\"\n\n"
            "{pergunta}\n"
            + FORMATO.format(formato="a data no formato AAAA-MM-DD")
        ),
    ),
    "quem": Task(
        id="quem",
        titulo="Quem ficou de fazer",
        descricao="Conversa de grupo com gente demais falando. Descobrir a quem o pronome se refere.",
        answer_type="nome",
        prompt=(
            "Conversa no grupo:\n\"\"\"{mensagem}\"\"\"\n\n"
            "{pergunta}\n"
            + FORMATO.format(formato="o primeiro nome da pessoa")
        ),
    ),
    "contagem": Task(
        id="contagem",
        titulo="A conta no meio da conversa",
        descricao="Uma continha simples enterrada em mensagem de grupo, com informação que não serve para nada no meio.",
        answer_type="numero",
        prompt=(
            "Mensagem recebida:\n\"\"\"{mensagem}\"\"\"\n\n"
            "{pergunta}\n"
            + FORMATO.format(formato="o número, usando ponto como separador decimal se precisar")
        ),
    ),
}

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
