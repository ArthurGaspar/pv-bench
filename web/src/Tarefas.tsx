import { carregar, gabaritoTexto, type Benchmark } from "./dados";
import { Vazio, useDados } from "./ui";

const TIPO: Record<string, string> = {
  json: "um objeto JSON com campos fixos",
  numero: "um número",
  rotulo: "um rótulo de uma lista fechada",
  data: "uma data AAAA-MM-DD",
  alternativa: "a letra de uma alternativa",
  nome: "um primeiro nome",
};

export function Tarefas() {
  const { dados, erro } = useDados<Benchmark>(carregar);
  if (erro) return <Vazio titulo="Sem dados ainda">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Carregando…" />;

  return (
    <>
      <section>
        <h1>As tarefas</h1>
        <p>
          Oito tipos de mensagem que todo brasileiro recebe e responde sem pensar, e que exigem do modelo mais do que
          traduzir palavra por palavra. Cada tarefa pede uma resposta de um formato só, para que a correção seja mecânica.
        </p>
      </section>

      {dados.tarefas.map((t) => {
        const exemplos = dados.itens.filter((i) => i.task === t.id);
        const exemplo = exemplos[0];
        return (
          <section className="painel" key={t.id}>
            <div className="linha" style={{ justifyContent: "space-between" }}>
              <h3 style={{ margin: 0 }}>{t.titulo}</h3>
              <span className="peq">
                {exemplos.length} itens · resposta é {TIPO[t.tipo] ?? t.tipo}
              </span>
            </div>
            <p style={{ margin: "6px 0 12px" }}>{t.descricao}</p>
            {t.rotulos.length > 0 && (
              <p className="peq" style={{ marginTop: -6 }}>
                Rótulos possíveis: {t.rotulos.join(", ")}.
              </p>
            )}
            {exemplo && (
              <>
                <div className="bolha">{exemplo.mensagem}</div>
                <p className="peq" style={{ margin: "8px 0 0" }}>
                  <b>Certo:</b> {gabaritoTexto(exemplo.gabarito)} · <b>Por que pega:</b> {exemplo.pega}
                </p>
              </>
            )}
          </section>
        );
      })}
    </>
  );
}
