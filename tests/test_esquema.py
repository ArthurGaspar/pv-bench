"""Esquemas versionados, plugins de avaliador, execução em lote e importação."""

import json

import pytest

import bench.importar as importar
import bench.lote as lote
import bench.run as run
from bench.avaliadores import AVALIADORES, Avaliador, Parsed, registrar_avaliador
from bench.dataset import carregar_conjunto, conferir_itens
from bench.esquema import (
    conferir_estrutura_rodada,
    conferir_rodada,
    impressao,
    migrar_conjunto,
    migrar_rodada,
    nome_arquivo,
)
from bench.grade import corrigir
from bench.tasks import TASKS

CONJUNTO = carregar_conjunto()


def gabarito_texto(item):
    task = TASKS[item["task"]]
    return AVALIADORES[task.answer_type].gabarito_como_texto(item, task)


class TestConjunto:
    def test_lista_solta_e_esquema_zero(self):
        dados = migrar_conjunto([{"id": "a"}])
        assert dados["esquema"] == 1 and dados["itens"] == [{"id": "a"}]

    def test_recusa_esquema_do_futuro(self):
        with pytest.raises(ValueError, match="mais novo"):
            migrar_conjunto({"esquema": 99, "nome": "x", "versao": "1", "itens": []})

    def test_cabecalho_invalido(self, tmp_path):
        arquivo = tmp_path / "items.json"
        arquivo.write_text(json.dumps({"esquema": 1, "nome": "", "versao": "1", "itens": [], "extra": 1}))
        with pytest.raises(ValueError, match="nome.*\n.*extra"):
            carregar_conjunto(arquivo)

    def test_impressao_muda_com_o_prompt_e_nao_com_o_gabarito(self):
        itens = [dict(i) for i in CONJUNTO.itens[:3]]
        base = impressao(itens)
        itens[0] = {**itens[0], "gabarito": "outro", "pega": "outra"}
        assert impressao(itens) == base
        itens[0] = {**itens[0], "mensagem": itens[0]["mensagem"] + "!"}
        assert impressao(itens) != base

    def test_conjunto_versionado(self):
        assert CONJUNTO.nome == "recado" and CONJUNTO.versao
        assert CONJUNTO.impressao.startswith("sha256:")


class TestRodada:
    def rodada(self, **extra):
        return {
            "esquema": 1, "modelo": "m", "rodadoEm": "2026-11-01T10:00:00+00:00", "segundos": 1.0,
            "conjunto": CONJUNTO.cabecalho(), "origem": {"tipo": "local"},
            "respostas": [{"id": i["id"], "task": i["task"], "bruto": gabarito_texto(i), "segundos": 0.1} for i in CONJUNTO.itens],
            **extra,
        }

    def test_rodada_antiga_migra_sem_conjunto(self):
        r = migrar_rodada({"modelo": "m", "respostas": []})
        assert r["esquema"] == 1 and r["conjunto"] is None and r["origem"] == {"tipo": "local"}

    def test_estrutura_aponta_todos_os_problemas(self):
        r = self.rodada(rodadoEm="ontem", segundos=-1, origem={"tipo": "outro"})
        r["respostas"][0]["bruto"] = 5
        erros = conferir_estrutura_rodada(r)
        assert len(erros) == 4

    def test_rodada_com_gabarito_acerta_tudo(self):
        respostas, faltando = conferir_rodada(self.rodada(), CONJUNTO.itens, CONJUNTO.cabecalho())
        assert not faltando and all(r["acertou"] for r in respostas)

    def test_recusa_prompts_diferentes(self):
        r = self.rodada(conjunto={**CONJUNTO.cabecalho(), "impressao": "sha256:velha", "versao": "0.9"})
        with pytest.raises(ValueError, match="prompts diferentes"):
            conferir_rodada(r, CONJUNTO.itens, CONJUNTO.cabecalho())

    def test_junta_os_erros(self):
        r = self.rodada()
        r["respostas"][1] = dict(r["respostas"][0])
        r["respostas"][2]["id"] = "nao-existe"
        with pytest.raises(ValueError) as e:
            conferir_rodada(r, CONJUNTO.itens)
        assert "item repetido" in str(e.value) and "item desconhecido" in str(e.value)

    @pytest.mark.parametrize("modelo,arquivo", [
        ("ollama/qwen2.5:7b", "ollama__qwen2.5_7b.json"),
        ("../../etc passwd", "______etc_passwd.json"),
        ("..", "_.json"),
    ])
    def test_nome_de_arquivo_seguro(self, modelo, arquivo):
        assert nome_arquivo(modelo) == arquivo


class TestPlugins:
    @pytest.fixture
    def avaliador_sim(self):
        class Sim(Avaliador):
            nome = "sim_nao"

            def extrair(self, bruto, item, task):
                t = bruto.strip().casefold()
                return Parsed(t if t in ("sim", "não") else None, t in ("sim", "não"), None if t in ("sim", "não") else "nem sim nem não")

            def conferir(self, valor, item, task):
                return valor == item["gabarito"]

            def validar_item(self, item, task):
                return [] if item["gabarito"] in ("sim", "não") else ["gabarito deveria ser sim ou não"]

        registrar_avaliador(Sim())
        from bench.tasks import Task, registrar_tarefa
        registrar_tarefa(Task("teste_sim", "t", "d", "sim_nao", "{mensagem}"))
        yield
        AVALIADORES.pop("sim_nao")
        TASKS.pop("teste_sim")

    def test_plugin_corrige_e_valida(self, avaliador_sim):
        item = {"id": "s1", "task": "teste_sim", "mensagem": "m", "gabarito": "sim", "pega": "p"}
        assert corrigir(item, "Sim")["acertou"]
        assert corrigir(item, "talvez")["erro_formato"] == "nem sim nem não"
        with pytest.raises(ValueError, match="sim ou não"):
            conferir_itens([{**item, "gabarito": "x"}])

    def test_tipo_sem_avaliador(self):
        from bench.tasks import Task
        TASKS["orfa"] = Task("orfa", "t", "d", "inexistente", "{mensagem}")
        try:
            with pytest.raises(ValueError, match="falta carregar um plugin"):
                conferir_itens([{"id": "o", "task": "orfa", "mensagem": "m", "gabarito": 1, "pega": "p"}])
        finally:
            TASKS.pop("orfa")

    def test_avaliador_incompleto_e_recusado(self):
        class Meio(Avaliador):
            nome = "meio"

            def extrair(self, bruto, item, task):
                return Parsed(None, False)

        with pytest.raises(TypeError, match="conferir"):
            registrar_avaliador(Meio())

    def test_nome_repetido_e_recusado(self):
        with pytest.raises(ValueError, match="já registrado"):
            registrar_avaliador(type(AVALIADORES["numero"])())

    def test_plugin_de_exemplo(self):
        import importlib

        modulo = importlib.import_module("exemplos.plugin_hora")
        try:
            item = {"id": "h", "task": "horario", "mensagem": "umas 3 da tarde", "gabarito": "15:00", "pega": "p"}
            assert corrigir(item, "15h")["acertou"] and not corrigir(item, "15h")["formato_ok"]
            assert corrigir(item, "15:00")["formato_ok"]
        finally:
            AVALIADORES.pop("hora")
            TASKS.pop("horario")
            del modulo


@pytest.fixture
def saida(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "SAIDA", tmp_path)
    monkeypatch.setattr(run, "PARCIAL", tmp_path / ".parcial")
    monkeypatch.setattr(lote, "SAIDA", tmp_path)
    monkeypatch.setattr(importar, "SAIDA", tmp_path)
    return tmp_path


class TestLote:
    def test_spec_invalida_lista_tudo(self):
        erros = lote.conferir_spec({
            "modelos": ["a/b", {"modelo": "a/b"}, {"paralelo": 2}, {"modelo": "c", "paralelo": 0, "x": 1}],
            "padrao": {"max_tokens": "200"},
            "tarefas": "valor",
        })
        texto = "\n".join(erros)
        for trecho in ("repetido", "deveria ser um nome", "pelo menos 1", "opção desconhecida", "max_tokens deveria ser int", "'tarefas'"):
            assert trecho in texto

    def test_planejar_aplica_padrao(self):
        plano = lote.planejar({"padrao": {"paralelo": 3}, "modelos": ["a", {"modelo": "b", "paralelo": 1}]})
        assert [p["paralelo"] for p in plano] == [3, 1]

    def test_lote_roda_retoma_e_continua_apos_falha(self, saida, monkeypatch, tmp_path):
        por_prompt = {TASKS[i["task"]].render(i): gabarito_texto(i) for i in CONJUNTO.itens}
        chamadas = []

        def falso(modelo, prompt, max_tokens=200, api_base=None):
            chamadas.append(modelo)
            if modelo == "fake/quebrado":
                raise RuntimeError("explodiu")
            return por_prompt[prompt], 0.01, None

        monkeypatch.setattr(run, "chamar", falso)
        spec = tmp_path / "lote.json"
        spec.write_text(json.dumps({"tarefas": ["valor"], "padrao": {"paralelo": 4},
                                    "modelos": ["fake/quebrado", "fake/bom"]}))
        assert lote.main([str(spec)]) == 1  # um modelo falhou
        resultado = json.loads((saida / "fake__bom.json").read_text(encoding="utf-8"))
        assert resultado["conjunto"] == CONJUNTO.cabecalho()
        assert all(r["acertou"] for r in resultado["respostas"])
        assert not (saida / ".parcial" / "fake__bom.jsonl").exists()

        chamadas.clear()
        spec.write_text(json.dumps({"tarefas": ["valor"], "modelos": ["fake/bom"]}))
        assert lote.main([str(spec), "--pular-prontos"]) == 0
        assert chamadas == []

    def test_retoma_parcial_e_refaz_falhas_do_provedor(self, saida, monkeypatch):
        itens = [i for i in CONJUNTO.itens if i["task"] == "valor"]
        parcial = saida / ".parcial" / "fake__m.jsonl"
        parcial.parent.mkdir()
        linhas = [{"modelo": "fake/m", "impressao": CONJUNTO.impressao, "rodadoEm": "2026-11-01T00:00:00+00:00"}]
        linhas.append({"id": itens[0]["id"], "task": "valor", "bruto": "1", "segundos": 1.0, "acertou": False,
                       "extraido": 1.0, "formato_ok": True, "erro_formato": None})
        linhas.append({"id": itens[1]["id"], "task": "valor", "bruto": "", "segundos": 1.0, "acertou": False,
                       "extraido": None, "formato_ok": False, "erro_formato": "Timeout"})
        parcial.write_text("\n".join(json.dumps(l) for l in linhas), encoding="utf-8")

        pedidos = []
        monkeypatch.setattr(run, "chamar", lambda m, p, *a: (pedidos.append(p), ("0", 0.5, None))[1])
        r = run.executar("fake/m", CONJUNTO, itens, log=lambda *_: None)
        assert len(pedidos) == len(itens) - 1  # o item já respondido não é refeito; o que falhou é
        assert r["rodadoEm"] == "2026-11-01T00:00:00+00:00"
        assert [x["id"] for x in r["respostas"]] == [i["id"] for i in itens]


class TestImportar:
    def escrever(self, tmp_path, nome, texto):
        (tmp_path / "entrada").mkdir(exist_ok=True)
        arquivo = tmp_path / "entrada" / nome
        arquivo.write_text(texto, encoding="utf-8")
        return arquivo

    def test_jsonl_completo_recorrige_e_grava(self, saida, tmp_path):
        linhas = [json.dumps({"id": i["id"], "bruto": gabarito_texto(i), "acertou": False}) for i in CONJUNTO.itens]
        arquivo = self.escrever(tmp_path, "ext.jsonl", "\n".join(linhas))
        assert importar.main([str(arquivo), "--modelo", "ext/modelo"]) == 0
        gravado = json.loads((saida / "ext__modelo.json").read_text(encoding="utf-8"))
        assert gravado["origem"]["tipo"] == "importado" and gravado["origem"]["formato"] == "jsonl"
        assert all(r["acertou"] for r in gravado["respostas"])

        # O que foi gravado passa pela montagem do site.
        from bench.build import ler_rodadas, preparar_rodadas
        assert len(preparar_rodadas(ler_rodadas([saida / "ext__modelo.json"]), CONJUNTO.itens, CONJUNTO.cabecalho())) == 1

    def test_avisa_divergencia_e_rodada_parcial(self, tmp_path, saida):
        item = CONJUNTO.itens[0]
        arquivo = self.escrever(tmp_path, "ext.jsonl", json.dumps({"id": item["id"], "bruto": gabarito_texto(item), "acertou": False}))
        [rel] = importar.importar(arquivo, CONJUNTO, modelo="x")
        assert not rel.erros
        texto = "\n".join(rel.avisos)
        assert "diferem da recorreção" in texto and "parcial" in texto and "impressão" in texto

    def test_csv_do_site_com_varios_modelos(self, saida, tmp_path):
        linhas = ["﻿item,tarefa,modelo,resposta,segundos"]
        for modelo in ("a/um", "b/dois"):
            linhas += [f'{i["id"]},{i["task"]},{modelo},"{gabarito_texto(i).replace(chr(34), chr(34) * 2)}",1.5' for i in CONJUNTO.itens[:2]]
        arquivo = self.escrever(tmp_path, "export.csv", "\n".join(linhas))
        rels = importar.importar(arquivo, CONJUNTO)
        assert sorted(r.modelo for r in rels) == ["a/um", "b/dois"]

    def test_erros_impedem_gravacao(self, saida, tmp_path):
        linhas = [
            {"id": "nao-existe", "bruto": "1"},
            {"id": CONJUNTO.itens[0]["id"], "bruto": "1", "task": "valor" if CONJUNTO.itens[0]["task"] != "valor" else "quem"},
            {"id": CONJUNTO.itens[1]["id"], "bruto": 42},
        ]
        arquivo = self.escrever(tmp_path, "ruim.json", json.dumps(linhas))
        assert importar.main([str(arquivo), "--modelo", "x/y"]) == 1
        assert not list(saida.glob("*.json"))

    def test_rodada_nativa_de_outro_conjunto(self, saida, tmp_path):
        rodada = {"esquema": 1, "modelo": "m", "rodadoEm": "2026-11-01T00:00:00+00:00", "segundos": 1,
                  "conjunto": {"nome": "recado", "versao": "0.1", "impressao": "sha256:outra"}, "origem": {"tipo": "local"},
                  "respostas": [{"id": CONJUNTO.itens[0]["id"], "task": CONJUNTO.itens[0]["task"], "bruto": "x", "segundos": 1}]}
        arquivo = self.escrever(tmp_path, "r.json", json.dumps(rodada))
        [rel] = importar.importar(arquivo, CONJUNTO)
        assert any("prompts diferentes" in e for e in rel.erros)

    def test_nao_sobrescreve_sem_pedir(self, saida, tmp_path):
        (saida / "x__y.json").write_text("{}")
        item = CONJUNTO.itens[0]
        arquivo = self.escrever(tmp_path, "e.jsonl", json.dumps({"id": item["id"], "bruto": "1"}))
        [rel] = importar.importar(arquivo, CONJUNTO, modelo="x/y")
        assert any("--substituir" in e for e in rel.erros)
        [rel] = importar.importar(arquivo, CONJUNTO, modelo="x/y", substituir=True)
        assert not rel.erros

    def test_sem_modelo(self, tmp_path):
        arquivo = self.escrever(tmp_path, "e.jsonl", json.dumps({"id": "a", "bruto": "1"}))
        [rel] = importar.importar(arquivo, CONJUNTO)
        assert "passe --modelo" in rel.erros[0]
