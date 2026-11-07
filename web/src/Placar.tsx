import { useState } from "react";
import { Vazio, useDados } from "./ui";
import {
  carregar,
  CORES,
  gabaritoTexto,
  linkRespostas,
  nomeCurto,
  pct,
  respostasPorItem,
} from "./dados";

export function Placar() {
  const { dados, erro } = useDados(carregar);
  const [metrica, setMetrica] = useState<"acerto" | "formato">("acerto");
  if (erro)
    return <Vazio titulo="Não foi possível carregar as rodadas">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Lendo as rodadas…" />;
  const { placar, itens, tarefas } = dados;
  const indice = respostasPorItem(dados);
  const ninguem = itens.filter((i) => {
    const rs = indice.get(i.id) ?? [];
    return (
      rs.length === placar.length &&
      rs.length > 0 &&
      rs.every((r) => !r.acertou)
    );
  });
  const divergencias = itens.filter((i) => {
    const rs = indice.get(i.id) ?? [];
    return rs.some((r) => r.acertou) && rs.some((r) => !r.acertou);
  });
  const exemplo = ninguem.find((i) => i.task === "resposta") ?? ninguem[0];

  return (
    <>
      <section className="abertura">
        <div>
          <p className="sobretitulo">Caderno de avaliação / PT-BR</p>
          <h1>
            O recado chegou.
            <br />O modelo <em>entendeu?</em>
          </h1>
          <p>
            Abreviação, indireta, data e conta no meio da conversa.{" "}
            {itens.length} mensagens escritas à mão, com gabarito verificável.
          </p>
          <a className="link-seta" href="#/respostas">
            Abrir as respostas <span aria-hidden="true">↗</span>
          </a>
        </div>
        {exemplo && (
          <aside className="recado">
            <span className="sobretitulo">Do conjunto / {exemplo.id}</span>
            <blockquote>“{exemplo.mensagem}”</blockquote>
            <div className="recado-nota">
              <span className="carimbo">
                {placar.length} modelos · 0 acertos
              </span>
              <p>
                Gabarito: <b>{gabaritoTexto(exemplo.gabarito)}</b>
              </p>
            </div>
            <a href={linkRespostas({ item: exemplo.id })}>
              O que responderam ↗
            </a>
          </aside>
        )}
      </section>

      <div className="numeros" aria-label="Resumo do conjunto">
        <div>
          <strong>
            {itens.length}
            <small> / {tarefas.length} tarefas</small>
          </strong>
          <span>mensagens no conjunto</span>
        </div>
        <div>
          <strong>{placar.length}</strong>
          <span>modelos avaliados</span>
        </div>
        <a href={linkRespostas({ so: "ninguem" })}>
          <strong>{ninguem.length}</strong>
          <span>itens sem nenhum acerto ↗</span>
        </a>
        <a href={linkRespostas({ so: "divergencias" })}>
          <strong>{divergencias.length}</strong>
          <span>itens com resultados diferentes ↗</span>
        </a>
      </div>

      <section>
        <div className="cabecalho-secao">
          <div>
            <p className="sobretitulo">01 / Rodadas publicadas</p>
            <h2>Resultados gerais</h2>
          </div>
          <span className="nota-margem">
            1 item = {(100 / itens.length).toFixed(2).replace(".", ",")} p.p.
            <br />
            Amostra pequena; leia os erros.
          </span>
        </div>
        <div className="tabela-scroll">
          <table className="placar">
            <caption className="sr-only">
              Resultados das rodadas completas
            </caption>
            <thead>
              <tr>
                <th>Modelo</th>
                <th>Acertos</th>
                <th className="num">Formato limpo</th>
                <th className="num">Tempo / item</th>
                <th>
                  <span className="sr-only">Respostas</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {placar.map((p, n) => (
                <tr key={p.modelo}>
                  <td>
                    <span className="indice">
                      {String(n + 1).padStart(2, "0")}
                    </span>
                    <span
                      className="ponto"
                      style={{ background: CORES[n % CORES.length] }}
                    />
                    <b className="mono">{nomeCurto(p.modelo)}</b>
                  </td>
                  <td>
                    <div className="resultado">
                      <strong>{pct(p.acertos, p.total)}</strong>
                      <span className="peq">
                        {p.acertos}/{p.total}
                      </span>
                    </div>
                    <div className="trilho">
                      <span
                        style={{
                          width: pct(p.acertos, p.total),
                          background: CORES[n % CORES.length],
                        }}
                      />
                    </div>
                  </td>
                  <td className="num mono">{pct(p.formatoOk, p.total)}</td>
                  <td className="num mono">
                    {p.segundosPorItem.toFixed(1).replace(".", ",")} s
                  </td>
                  <td>
                    <a
                      aria-label={`Inspecionar ${nomeCurto(p.modelo)}`}
                      href={linkRespostas({ modelo: p.modelo })}
                    >
                      ↗
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="peq rodape-tabela">
          Acerto após extração da resposta. Formato limpo mede a obediência ao
          formato pedido. Tempo observado na máquina da rodada, sem controle de
          hardware.
        </p>
      </section>

      <section>
        <div className="cabecalho-secao">
          <div>
            <p className="sobretitulo">02 / Raio-X por tarefa</p>
            <h2>Onde a conversa se perde</h2>
          </div>
          <div className="filtros" role="group" aria-label="Métrica da matriz">
            <button
              aria-pressed={metrica === "acerto"}
              onClick={() => setMetrica("acerto")}
            >
              Acerto
            </button>
            <button
              aria-pressed={metrica === "formato"}
              onClick={() => setMetrica("formato")}
            >
              Formato
            </button>
          </div>
        </div>
        <div className="matriz-legenda">
          <span>Um traço por mensagem. Clique para inspecionar.</span>
          <span>
            <i className="estado-dot ok" />{" "}
            {metrica === "acerto" ? "acertou" : "formato limpo"}{" "}
            <i className="estado-dot nao" />{" "}
            {metrica === "acerto" ? "errou" : "fora do formato"}
          </span>
        </div>
        <div className="matriz">
          {tarefas.map((t, n) => (
            <div className="matriz-linha" key={t.id}>
              <a className="tarefa-nome" href={linkRespostas({ tarefa: t.id })}>
                <span className="indice">{String(n + 1).padStart(2, "0")}</span>
                {t.titulo}
                <span aria-hidden="true">↗</span>
              </a>
              <div className="matriz-modelos">
                {placar.map((p) => {
                  const rs = dados.respostas.filter(
                    (r) => r.modelo === p.modelo && r.task === t.id,
                  );
                  const ok = rs.filter((r) =>
                    metrica === "acerto" ? r.acertou : r.formato_ok,
                  ).length;
                  return (
                    <div className="matriz-serie" key={p.modelo}>
                      <span className="mono peq">{nomeCurto(p.modelo)}</span>
                      <div className="tracos">
                        {itens
                          .filter((i) => i.task === t.id)
                          .map((i) => {
                            const r = rs.find((r) => r.id === i.id);
                            const passou =
                              r &&
                              (metrica === "acerto" ? r.acertou : r.formato_ok);
                            return (
                              <a
                                key={i.id}
                                className={`traco ${r ? (passou ? "ok" : "nao") : "ausente"}`}
                                href={linkRespostas({ item: i.id })}
                                aria-label={`${i.id}, ${nomeCurto(p.modelo)}: ${r ? (passou ? "passou" : "falhou") : "sem resposta"}`}
                                title={`${i.id}: ${i.mensagem}`}
                              />
                            );
                          })}
                      </div>
                      <b className="mono peq">
                        {ok}/{rs.length}
                      </b>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
      <aside className="aviso">
        <b>O que este recorte permite dizer</b>
        <p>
          São mensagens sintéticas e uma tentativa por item. Os resultados
          descrevem estas rodadas; não representam todo o português brasileiro.{" "}
          <a href="#/metodo">Ler o método ↗</a>
        </p>
      </aside>
    </>
  );
}
