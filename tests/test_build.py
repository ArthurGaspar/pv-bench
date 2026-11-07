"""Integridade das rodadas publicadas, independente dos escores salvos."""

from copy import deepcopy

import pytest

from bench.build import preparar_rodadas


ITENS = [
    {"id": "valor-01", "task": "valor", "gabarito": 80},
    {"id": "valor-02", "task": "valor", "gabarito": 20},
]


def rodada():
    return {"modelo": "teste", "respostas": [
        {"id": "valor-01", "task": "valor", "bruto": "80", "acertou": False},
        {"id": "valor-02", "task": "valor", "bruto": "999", "acertou": True},
    ]}


def test_recalcula_notas_a_partir_do_texto():
    original = rodada()
    copia = deepcopy(original)
    respostas = preparar_rodadas([original], ITENS)[0]["respostas"]
    assert [r["acertou"] for r in respostas] == [True, False]
    assert all(r["formato_ok"] for r in respostas)
    assert original == copia


def test_exclui_rodada_parcial():
    r = rodada()
    r["respostas"].pop()
    assert preparar_rodadas([r], ITENS) == []


def test_rejeita_duplicata_com_contagem_de_rodada_completa():
    r = rodada()
    r["respostas"][1] = r["respostas"][0].copy()
    with pytest.raises(ValueError, match="item repetido"):
        preparar_rodadas([r], ITENS)


@pytest.mark.parametrize("campo,valor,erro", [
    ("id", "inexistente", "item desconhecido"),
    ("task", "contagem", "tarefa inconsistente"),
])
def test_rejeita_resposta_incompativel(campo, valor, erro):
    r = rodada()
    r["respostas"][0][campo] = valor
    with pytest.raises(ValueError, match=erro):
        preparar_rodadas([r], ITENS)


def test_rejeita_modelo_repetido():
    with pytest.raises(ValueError, match="modelo repetido"):
        preparar_rodadas([rodada(), rodada()], ITENS)


def test_preserva_erro_do_provedor_sem_contar_acerto():
    r = rodada()
    r["respostas"][0].update(bruto="", erro_formato="TimeoutError: indisponível")
    resposta = preparar_rodadas([r], ITENS)[0]["respostas"][0]
    assert resposta["erro_formato"] == "TimeoutError: indisponível"
    assert not resposta["acertou"] and not resposta["formato_ok"]
