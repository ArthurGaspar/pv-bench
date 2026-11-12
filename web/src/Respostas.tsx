import { useState } from "react";
import {
  baixarCSV,
  carregar,
  gabaritoTexto,
  linkRespostas,
  nomeCurto,
  respostasPorItem,
  segundosTexto,
  type Item,
  type Resposta,
} from "./dados";
import { Selo, Vazio, useDados } from "./ui";

const FILTROS = [
  ["todos", "Todos"],
  ["erros", "Com erro"],
  ["ninguem", "Ninguém acertou"],
  ["divergencias", "Divergências"],
  ["acertos", "Todos acertaram"],
  ["formato", "Fora do formato"],
] as const;

export function Respostas() {
  const { dados, erro } = useDados(carregar);
  const params = new URLSearchParams(location.hash.split("?")[1]);
  const tarefa = params.get("tarefa") ?? "todas";
  const modelo = params.get("modelo") ?? "todos";
  const filtro = params.get("so") ?? "todos";
  const busca = params.get("q") ?? "";
  const itemId = params.get("item");
  function mudar(chave: string, valor: string) {
    const novos = new URLSearchParams(params);
    novos.delete("item");
    if (!valor || valor === "todos" || valor === "todas") novos.delete(chave);
    else novos.set(chave, valor);
    location.hash = `/respostas${novos.size ? `?${novos}` : ""}`;
  }
  if (erro)
    return (
      <Vazio titulo="Não foi possível carregar as respostas">{erro}</Vazio>
    );
  if (!dados) return <Vazio titulo="Lendo as respostas…" />;
  const indice = respostasPorItem(dados);
  const respostas = (id: string) =>
    (indice.get(id) ?? []).filter(
      (r) => modelo === "todos" || r.modelo === modelo,
    );
  const normalizar = (s: string) =>
    s
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase();
  const visiveis = dados.itens.filter((i) => {
    if (itemId && i.id !== itemId) return false;
    if (tarefa !== "todas" && i.task !== tarefa) return false;
    const rs = respostas(i.id);
    if (
      busca &&
      !normalizar(
        [i.id, i.mensagem, i.pega, ...rs.map((r) => r.bruto)].join(" "),
      ).includes(normalizar(busca))
    )
      return false;
    if (filtro === "erros") return rs.some((r) => !r.acertou);
    if (filtro === "ninguem")
      return rs.length > 0 && rs.every((r) => !r.acertou);
    if (filtro === "divergencias")
      return rs.some((r) => r.acertou) && rs.some((r) => !r.acertou);
    if (filtro === "acertos")
      return rs.length > 0 && rs.every((r) => r.acertou);
    if (filtro === "formato") return rs.some((r) => !r.formato_ok);
    return true;
  });

  return (
    <>
      <section className="pagina-intro">
        <p className="sobretitulo">Caderno / Inspecionar</p>
        <h1>Resposta por resposta.</h1>
        <p>
          Compare a mensagem, o gabarito e a saída original. Abra o prompt para
          reproduzir o teste.
        </p>
      </section>
      <section className="barra-filtros" aria-label="Filtrar respostas">
        <div className="campos-filtros">
          <label className="busca">
            Buscar mensagem ou resposta
            <input
              type="search"
              value={busca}
              placeholder="Ex.: fechou, amanhã, valor-07…"
              onChange={(e) => mudar("q", e.target.value)}
            />
          </label>
          <label>
            Tarefa
            <select
              aria-label="Tarefa"
              value={tarefa}
              onChange={(e) => mudar("tarefa", e.target.value)}
            >
              <option value="todas">Todas as tarefas</option>
              {dados.tarefas.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.titulo}
                </option>
              ))}
            </select>
          </label>
          <label>
            Modelo
            <select
              aria-label="Modelo"
              value={modelo}
              onChange={(e) => mudar("modelo", e.target.value)}
            >
              <option value="todos">Comparar todos</option>
              {dados.placar.map((p) => (
                <option key={p.modelo} value={p.modelo}>
                  {nomeCurto(p.modelo)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="filtros" role="group" aria-label="Resultado">
          {FILTROS.map(([f, nome]) => (
            <button
              key={f}
              aria-pressed={filtro === f}
              onClick={() => mudar("so", f)}
            >
              {nome}
            </button>
          ))}
        </div>
      </section>
      <div className="linha entre">
        <p className="peq" role="status">
          {visiveis.length} de {dados.itens.length} mensagens{" "}
          {itemId && <>· item {itemId}</>}
        </p>
        <div className="linha">
          <a href="#/respostas">Limpar filtros</a>
          <button
            className="botao"
            disabled={!visiveis.length}
            onClick={() =>
              baixarCSV(
                visiveis,
                dados.respostas.filter(
                  (r) => modelo === "todos" || r.modelo === modelo,
                ),
              )
            }
          >
            Exportar CSV ↓
          </button>
        </div>
      </div>
      {visiveis.map((item) => (
        <Registro key={item.id} item={item} respostas={respostas(item.id)} />
      ))}
      {!visiveis.length && (
        <div className="vazio">
          <h2>Nenhuma mensagem neste recorte.</h2>
          <p>
            Tente outra busca ou <a href="#/respostas">limpe os filtros</a>.
          </p>
        </div>
      )}
    </>
  );
}

function Registro({ item, respostas }: { item: Item; respostas: Resposta[] }) {
  const [copia, setCopia] = useState<"pronto" | "copiado" | "erro">("pronto");
  async function copiar() {
    try {
      await navigator.clipboard.writeText(
        new URL(linkRespostas({ item: item.id }), location.href).href,
      );
      setCopia("copiado");
    } catch {
      setCopia("erro");
    }
  }
  return (
    <article className="registro" id={item.id}>
      <div className="registro-cabecalho">
        <span className="sobretitulo">
          {item.task} / {item.id}
        </span>
        <button className="texto-botao" onClick={copiar} aria-live="polite">
          {copia === "copiado"
            ? "Link copiado ✓"
            : copia === "erro"
              ? "Falha ao copiar · tentar novamente"
              : "Copiar link ↗"}
        </button>
      </div>
      <div className="registro-corpo">
        <div className="mensagem-coluna">
          {Object.keys(item.contexto).length > 0 && (
            <p className="contexto">
              {Object.entries(item.contexto)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")}
            </p>
          )}
          <blockquote className="mensagem">{item.mensagem}</blockquote>
          {item.alternativas && (
            <ul className="alternativas">
              {Object.entries(item.alternativas).map(([letra, texto]) => (
                <li key={letra}>
                  <b>{letra}</b> {texto}
                </li>
              ))}
            </ul>
          )}
          <div className="gabarito">
            <span className="sobretitulo">Gabarito</span>
            <strong>{gabaritoTexto(item.gabarito)}</strong>
            <p>{item.pega}</p>
          </div>
        </div>
        <div className="saidas">
          {respostas.map((r) => (
            <div className="saida" key={r.modelo}>
              <div className="linha entre">
                <b className="mono peq">{nomeCurto(r.modelo)}</b>
                <Selo ok={r.acertou}>{r.acertou ? "Acertou" : "Errou"}</Selo>
              </div>
              <pre className="resp">{r.bruto || "(resposta vazia)"}</pre>
              <div className="linha entre peq">
                <span>
                  {r.formato_ok ? "✓ Formato limpo" : "× Fora do formato"}
                </span>
                <span className="mono">{segundosTexto(r.segundos, 2)}</span>
              </div>
              {!r.acertou && r.extraido !== null && (
                <p className="peq">
                  Extraído:{" "}
                  <code>
                    {typeof r.extraido === "object"
                      ? JSON.stringify(r.extraido)
                      : String(r.extraido)}
                  </code>
                </p>
              )}
              {r.erro_formato && <p className="peq">{r.erro_formato}</p>}
            </div>
          ))}
        </div>
      </div>
      <details className="prompt">
        <summary>Prompt enviado ao modelo</summary>
        <pre className="resp">{item.prompt}</pre>
      </details>
    </article>
  );
}
