import { BarrasPorTarefa, Tile, Vazio, useDados } from "./ui";
import { carregar, nomeCurto, pct, type Benchmark } from "./dados";

const CORES = ["var(--c-1)", "var(--c-2)"];

export function Placar() {
  const { dados, erro } = useDados<Benchmark>(carregar);
  if (erro) return <Vazio titulo="Sem resultados ainda">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Carregando…" />;
  const { placar, itens, tarefas } = dados;
  const melhor = placar[0];
  const total = melhor?.total ?? itens.length;

  // Itens que nenhum modelo acertou: é onde o benchmark realmente morde.
  const porItem = new Map<string, number>();
  for (const r of dados.respostas) porItem.set(r.id, (porItem.get(r.id) ?? 0) + (r.acertou ? 1 : 0));
  const ninguem = itens.filter((i) => (porItem.get(i.id) ?? 0) === 0);
  const todos = itens.filter((i) => (porItem.get(i.id) ?? 0) === placar.length);

  return (
    <>
      <section>
        <h1>Deu pra entender?</h1>
        <p>
          Um benchmark de português brasileiro como ele aparece no celular: abreviação, erro de digitação, emoji, ironia e
          pedido que ninguém faz com todas as letras. São {itens.length} itens em {tarefas.length} tarefas, e cada um tem
          uma resposta só, conferida por regra. Não tem modelo dando nota para modelo.
        </p>
      </section>

      <div className="tiles">
        <Tile valor={itens.length} rotulo="Itens" sub={`${tarefas.length} tarefas, resposta objetiva`} />
        <Tile valor={placar.length} rotulo="Modelos rodados" sub="qualquer modelo do LiteLLM serve" />
        <Tile valor={melhor ? pct(melhor.acertos, melhor.total) : "-"} rotulo="Melhor resultado" sub={melhor ? nomeCurto(melhor.modelo) : ""} />
        <Tile valor={ninguem.length} rotulo="Itens que ninguém acertou" sub={`${todos.length} todos acertaram`} />
      </div>

      <section className="painel">
        <h2>Placar</h2>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Modelo</th>
                <th className="num">Acertos</th>
                <th className="num">%</th>
                <th className="num esconde-peq">Formato limpo</th>
                <th className="num esconde-peq">Seg. por item</th>
              </tr>
            </thead>
            <tbody>
              {placar.map((p) => (
                <tr key={p.modelo}>
                  <td className="mono">{nomeCurto(p.modelo)}</td>
                  <td className="num">
                    {p.acertos}/{p.total}
                  </td>
                  <td className="num" style={{ fontWeight: 700 }}>
                    {pct(p.acertos, p.total)}
                  </td>
                  <td className="num esconde-peq">{pct(p.formatoOk, p.total)}</td>
                  <td className="num esconde-peq">{p.segundosPorItem.toFixed(1)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="peq" style={{ marginTop: 10 }}>
          <b>Formato limpo</b> é quando a resposta já veio exatamente no formato pedido, sem frase em volta. Entender a
          mensagem e obedecer o formato são duas habilidades diferentes, então aparecem em colunas diferentes: a extração é
          tolerante e o acerto não depende do enfeite.
        </p>
      </section>

      {placar.length > 0 && (
        <section className="painel">
          <h2>Acertos por tarefa</h2>
          <BarrasPorTarefa
            tarefas={tarefas}
            series={placar.map((p, i) => ({ nome: nomeCurto(p.modelo), cor: CORES[i % CORES.length], valores: p.porTarefa }))}
          />
          <p className="peq" style={{ marginTop: 10 }}>
            São {total / tarefas.length} itens por tarefa, então cada item vale bastante: a diferença de um acerto já mexe no
            desenho. Serve para ver onde o modelo tropeça, não para cravar ranking.
          </p>
        </section>
      )}

      {ninguem.length > 0 && (
        <section className="painel">
          <h2>Onde todo mundo errou</h2>
          <p>Os itens que nenhum dos modelos acertou. É a parte do português que ainda não passou.</p>
          {ninguem.slice(0, 6).map((i) => (
            <div key={i.id} style={{ marginBottom: 14 }}>
              <div className="bolha">{i.mensagem}</div>
              <p className="peq" style={{ margin: "6px 0 0" }}>
                {i.pega}. Resposta certa: <b>{typeof i.gabarito === "object" ? JSON.stringify(i.gabarito) : String(i.gabarito)}</b>{" "}
                · <a href={`#/respostas?item=${i.id}`}>ver o que responderam</a>
              </p>
            </div>
          ))}
          {ninguem.length > 6 && (
            <p className="peq">
              e mais {ninguem.length - 6}. <a href="#/respostas?so=erros">ver todos os erros</a>
            </p>
          )}
        </section>
      )}
    </>
  );
}
