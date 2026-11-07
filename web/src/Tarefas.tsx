import { carregar, gabaritoTexto, linkRespostas } from "./dados";
import { Vazio, useDados } from "./ui";

const TIPO: Record<string, string> = {
  json: "JSON",
  numero: "Número",
  rotulo: "Rótulo",
  data: "Data ISO",
  alternativa: "Alternativa",
  nome: "Nome",
};

export function Tarefas() {
  const { dados, erro } = useDados(carregar);
  if (erro)
    return <Vazio titulo="Não foi possível carregar o conjunto">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Lendo o conjunto…" />;
  return (
    <>
      <section className="pagina-intro">
        <p className="sobretitulo">Caderno / Conjunto</p>
        <h1>Oito jeitos de perder o fio.</h1>
        <p>
          {dados.itens.length} mensagens sintéticas, escritas em português
          brasileiro informal. Cada tarefa isola um tipo de interpretação e
          exige uma resposta curta.
        </p>
      </section>
      <div className="tarefas-lista">
        {dados.tarefas.map((t, n) => {
          const itens = dados.itens.filter((i) => i.task === t.id);
          const exemplo = itens[0];
          return (
            <section className="tarefa" key={t.id}>
              <p className="sobretitulo">
                {String(n + 1).padStart(2, "0")} / {t.id}
              </p>
              <h2>{t.titulo}</h2>
              <div className="tarefa-meta">
                <span>{itens.length} itens</span>
                <span>Resposta: {TIPO[t.tipo] ?? t.tipo}</span>
              </div>
              <p>{t.descricao}</p>
              {t.rotulos.length > 0 && (
                <p className="peq">Rótulos: {t.rotulos.join(" · ")}</p>
              )}
              {exemplo && (
                <>
                  <p className="contexto">
                    {Object.entries(exemplo.contexto)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(" · ")}
                  </p>
                  <blockquote className="mensagem">
                    “{exemplo.mensagem}”
                  </blockquote>
                  <p className="peq">
                    Gabarito: <b>{gabaritoTexto(exemplo.gabarito)}</b>
                  </p>
                </>
              )}
              <a className="link-seta" href={linkRespostas({ tarefa: t.id })}>
                Inspecionar os {itens.length} itens{" "}
                <span aria-hidden="true">↗</span>
              </a>
            </section>
          );
        })}
      </div>
    </>
  );
}
