import { useMemo, useState } from "react";
import { carregar, gabaritoTexto, nomeCurto, type Benchmark, type Item } from "./dados";
import { Selo, Vazio, useDados } from "./ui";

type Filtro = "todos" | "erros" | "acertos" | "formato";

/** Lê #/respostas?item=valor-07&so=erros, que o placar usa para apontar para um item. */
function parametros(): { item?: string; so?: Filtro } {
  const q = (location.hash.split("?")[1] ?? "").replace(/^\?/, "");
  const p = new URLSearchParams(q);
  const so = p.get("so");
  return { item: p.get("item") ?? undefined, so: so === "erros" || so === "acertos" || so === "formato" ? so : undefined };
}

export function Respostas() {
  const { dados, erro } = useDados<Benchmark>(carregar);
  const inicial = useMemo(parametros, []);
  const [tarefa, setTarefa] = useState<string>("todas");
  const [filtro, setFiltro] = useState<Filtro>(inicial.so ?? "todos");
  const [aberto, setAberto] = useState<string | null>(inicial.item ?? null);

  if (erro) return <Vazio titulo="Sem resultados ainda">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Carregando…" />;

  const porItem = new Map(dados.itens.map((i) => [i.id, i]));
  const respostasDe = (id: string) => dados.respostas.filter((r) => r.id === id);

  const visiveis = dados.itens.filter((i) => {
    if (tarefa !== "todas" && i.task !== tarefa) return false;
    const rs = respostasDe(i.id);
    if (filtro === "erros") return rs.some((r) => !r.acertou);
    if (filtro === "acertos") return rs.length > 0 && rs.every((r) => r.acertou);
    if (filtro === "formato") return rs.some((r) => !r.formato_ok);
    return true;
  });

  return (
    <>
      <section>
        <h1>Todas as respostas</h1>
        <p>
          Cada item, o que cada modelo respondeu e por que valeu ponto ou não. Um benchmark que não deixa olhar a resposta é
          só um número; aqui está tudo, inclusive o prompt exato que foi enviado.
        </p>
      </section>

      <div className="linha">
        <div className="filtros" role="group" aria-label="Tarefa">
          <button aria-pressed={tarefa === "todas"} onClick={() => setTarefa("todas")}>
            Todas
          </button>
          {dados.tarefas.map((t) => (
            <button key={t.id} aria-pressed={tarefa === t.id} onClick={() => setTarefa(t.id)}>
              {t.titulo}
            </button>
          ))}
        </div>
        <div className="filtros" role="group" aria-label="Resultado">
          {(
            [
              ["todos", "Todos"],
              ["erros", "Com erro"],
              ["acertos", "Todos acertaram"],
              ["formato", "Formato sujo"],
            ] as [Filtro, string][]
          ).map(([f, nome]) => (
            <button key={f} aria-pressed={filtro === f} onClick={() => setFiltro(f)}>
              {nome}
            </button>
          ))}
        </div>
      </div>

      <p className="peq" style={{ margin: 0 }}>
        {visiveis.length} de {dados.itens.length} itens
      </p>

      {visiveis.map((item) => (
        <Cartao key={item.id} item={item} respostas={respostasDe(item.id)} aberto={aberto === item.id} alternar={() => setAberto(aberto === item.id ? null : item.id)} />
      ))}
      {visiveis.length === 0 && <p className="peq">Nenhum item com esse filtro.</p>}
      {porItem.size === 0 && <p className="peq">Nenhum item carregado.</p>}
    </>
  );
}

function Cartao({
  item,
  respostas,
  aberto,
  alternar,
}: {
  item: Item;
  respostas: Benchmark["respostas"];
  aberto: boolean;
  alternar: () => void;
}) {
  const contexto = Object.entries(item.contexto);
  return (
    <section className="painel" id={item.id}>
      <div className="linha" style={{ justifyContent: "space-between", marginBottom: 10 }}>
        <span className="peq mono">{item.id}</span>
        <span className="linha" style={{ gap: 6 }}>
          {respostas.map((r) => (
            <Selo key={r.modelo} ok={r.acertou}>
              {nomeCurto(r.modelo)} {r.acertou ? "acertou" : "errou"}
            </Selo>
          ))}
        </span>
      </div>

      {contexto.length > 0 && (
        <div className="bolha ctx" style={{ marginBottom: 8 }}>
          {contexto.map(([k, v]) => `${k}: ${v}`).join("  ·  ")}
        </div>
      )}
      <div className="bolha">{item.mensagem}</div>

      {item.alternativas && (
        <ul className="peq" style={{ margin: "10px 0 0", paddingLeft: 18 }}>
          {Object.entries(item.alternativas).map(([letra, texto]) => (
            <li key={letra} style={{ fontWeight: letra === item.gabarito ? 700 : 400, color: letra === item.gabarito ? "var(--acerto)" : undefined }}>
              {letra}) {texto}
            </li>
          ))}
        </ul>
      )}

      <p className="peq" style={{ margin: "10px 0 0" }}>
        <b>Resposta certa:</b> {gabaritoTexto(item.gabarito)} · <b>A pegadinha:</b> {item.pega}
      </p>

      <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
        {respostas.map((r) => (
          <div key={r.modelo}>
            <div className="linha" style={{ gap: 8, marginBottom: 4 }}>
              <span className="mono peq">{nomeCurto(r.modelo)}</span>
              {!r.formato_ok && <span className="selo neutro">{r.erro_formato ?? "formato fora do pedido"}</span>}
            </div>
            <div className="resp" style={{ borderColor: r.acertou ? "var(--acerto)" : "var(--erro)" }}>
              {r.bruto || "(resposta vazia)"}
            </div>
            {!r.acertou && r.extraido !== null && (
              <p className="peq" style={{ margin: "4px 0 0" }}>
                entendido como <b>{typeof r.extraido === "object" ? JSON.stringify(r.extraido) : String(r.extraido)}</b>
              </p>
            )}
          </div>
        ))}
      </div>

      <button className="tema" style={{ marginTop: 12 }} onClick={alternar} aria-expanded={aberto}>
        {aberto ? "Esconder o prompt" : "Ver o prompt enviado"}
      </button>
      {aberto && (
        <div className="resp" style={{ marginTop: 8 }}>
          {item.prompt}
        </div>
      )}
    </section>
  );
}
