"""Testes do harness. O que importa aqui é o corretor: se ele erra, o benchmark inteiro mente."""

import json
from pathlib import Path

import pytest

from bench.avaliadores import obter
from bench.dataset import ITENS, carregar, conferir_itens
from bench.grade import corrigir, normalizar, parse_alternativa, parse_data, parse_json, parse_numero, parse_rotulo
from bench.tasks import TASKS

RAIZ = Path(__file__).resolve().parent.parent


class TestNumero:
    @pytest.mark.parametrize(
        "bruto, esperado",
        [
            ("1500", 1500.0),
            ("1500.00", 1500.0),
            ("1.500", 1500.0),  # ponto de milhar à brasileira
            ("1.234,56", 1234.56),  # o formato que o Brasil escreve
            ("1,234.56", 1234.56),  # e o que o inglês escreve
            ("44,91", 44.91),
            ("R$ 52,50", 52.5),
            ("  87.90  ", 87.9),
            ("O total é R$ 1.234,56 😊", 1234.56),  # resposta enfeitada
            ("```\n60\n```", 60.0),
            ("-5", -5.0),
        ],
    )
    def test_formatos_aceitos(self, bruto, esperado):
        assert parse_numero(bruto).valor == pytest.approx(esperado)

    def test_formato_limpo_so_quando_e_so_o_numero(self):
        assert parse_numero("1500.00").formato_ok
        assert not parse_numero("O valor é 1500.00").formato_ok

    def test_sem_numero(self):
        p = parse_numero("não consegui descobrir")
        assert p.valor is None and p.erro


class TestRotulo:
    rotulos = ("convite", "cobranca", "spam")

    def test_aceita_com_e_sem_acento(self):
        assert parse_rotulo("cobrança", self.rotulos).valor == "cobranca"
        assert parse_rotulo("COBRANCA", self.rotulos).valor == "cobranca"

    def test_encontra_no_meio_da_frase_mas_marca_formato_sujo(self):
        p = parse_rotulo("A intenção é claramente um convite.", self.rotulos)
        assert p.valor == "convite" and not p.formato_ok

    def test_recusa_resposta_ambigua(self):
        p = parse_rotulo("pode ser convite ou spam", self.rotulos)
        assert p.valor is None and "mais de um" in p.erro

    def test_recusa_rotulo_inventado(self):
        assert parse_rotulo("propaganda", self.rotulos).valor is None


class TestOutrosTipos:
    def test_json_exige_os_campos(self):
        assert parse_json('{"data": "2026-03-12", "hora": "15:00"}', ["data", "hora"]).valor == {"data": "2026-03-12", "hora": "15:00"}
        assert parse_json('{"data": "2026-03-12"}', ["data", "hora"]).erro == "faltou o campo hora"

    def test_json_dentro_de_cerca_markdown(self):
        p = parse_json('```json\n{"data": "2026-03-12", "hora": "15:00"}\n```', ["data", "hora"])
        assert p.valor["hora"] == "15:00" and p.formato_ok

    def test_json_com_texto_em_volta_nao_e_formato_limpo(self):
        p = parse_json('Claro! {"data": "2026-03-12", "hora": "15:00"}', ["data", "hora"])
        assert p.valor is not None and not p.formato_ok

    def test_data(self):
        assert parse_data("2026-03-12").valor == "2026-03-12"
        assert parse_data("A data é 2026-03-12.").valor == "2026-03-12"
        assert parse_data("12/03/2026").valor is None  # o formato pedido foi ISO

    def test_alternativa_por_letra_ou_por_texto(self):
        alternativas = {"A": "Elogiar o clima", "B": "Pedir para ligar o ar"}
        assert parse_alternativa("B", alternativas).valor == "B"
        assert parse_alternativa("Resposta: B) Pedir para ligar o ar", alternativas).valor == "B"
        p = parse_alternativa("Pedir para ligar o ar", alternativas)
        assert p.valor == "B" and not p.formato_ok


class TestCorrigir:
    def item(self, task, gabarito, **extra):
        return {"id": "x", "task": task, "mensagem": "m", "gabarito": gabarito, "pega": "p", **extra}

    def test_acerto_e_erro_de_numero(self):
        assert corrigir(self.item("valor", 80), "80")["acertou"]
        assert not corrigir(self.item("valor", 80), "800")["acertou"]

    def test_json_precisa_bater_em_todos_os_campos(self):
        item = self.item("compromisso", {"data": "2026-03-12", "hora": "15:00"})
        assert corrigir(item, '{"data":"2026-03-12","hora":"15:00"}')["acertou"]
        assert not corrigir(item, '{"data":"2026-03-12","hora":"15:30"}')["acertou"]

    def test_nome_ignora_caixa_e_acento(self):
        assert corrigir(self.item("quem", "Natalia"), "natália")["acertou"]

    def test_resposta_vazia_nao_acerta(self):
        r = corrigir(self.item("valor", 80), "")
        assert not r["acertou"] and not r["formato_ok"] and r["erro_formato"]

    def test_acerto_com_formato_sujo_ainda_e_acerto(self):
        r = corrigir(self.item("valor", 80), "O valor que falta é R$ 80,00.")
        assert r["acertou"] and not r["formato_ok"]


def test_normalizar():
    assert normalizar("  Cobrança! ") == "cobranca"


class TestConjunto:
    """O conjunto versionado precisa continuar coerente consigo mesmo."""

    itens = carregar()

    def test_tem_itens_para_todas_as_tarefas(self):
        tarefas = {i["task"] for i in self.itens}
        assert tarefas == set(TASKS), f"faltam itens para {set(TASKS) - tarefas}"

    def test_ids_unicos(self):
        ids = [i["id"] for i in self.itens]
        assert len(ids) == len(set(ids))

    def test_todo_prompt_monta(self):
        for item in self.itens:
            prompt = TASKS[item["task"]].render(item)
            assert item["mensagem"] in prompt

    def test_gabarito_bate_com_o_proprio_corretor(self):
        """Escrever o gabarito como o modelo escreveria tem que dar acerto."""
        for item in self.itens:
            task = TASKS[item["task"]]
            texto = obter(task.answer_type).gabarito_como_texto(item, task)
            assert corrigir(item, texto)["acertou"], f"{item['id']}: o próprio gabarito não passa"

    def test_alternativas_nao_ficam_todas_na_mesma_letra(self):
        """Senão um modelo que responde sempre a mesma letra gabarita a tarefa."""
        letras = [i["gabarito"] for i in self.itens if i["task"] == "pedido"]
        assert max(letras.count(l) for l in set(letras)) <= len(letras) // 2

    def test_rotulos_cobrem_a_lista(self):
        for tarefa in ("intencao", "resposta"):
            usados = {i["gabarito"] for i in self.itens if i["task"] == tarefa}
            assert usados == set(TASKS[tarefa].rotulos), f"{tarefa}: rótulos sem item {set(TASKS[tarefa].rotulos) - usados}"

    def test_conferencia_pega_item_quebrado(self):
        with pytest.raises(ValueError, match="rótulo"):
            conferir_itens([{"id": "a", "task": "intencao", "mensagem": "m", "gabarito": "inexistente", "pega": "p"}])

    def test_arquivo_versionado_e_json_valido(self):
        json.loads(ITENS.read_text(encoding="utf-8"))
