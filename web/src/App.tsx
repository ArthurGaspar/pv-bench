import { useEffect, useState } from "react";
import { Metodo } from "./Metodo";
import { Placar } from "./Placar";
import { Respostas } from "./Respostas";
import { Tarefas } from "./Tarefas";

type Tema = "claro" | "escuro";
const PAGINAS = [
  { hash: "#/", rotulo: "Visão geral" },
  { hash: "#/respostas", rotulo: "Inspecionar" },
  { hash: "#/tarefas", rotulo: "Conjunto" },
  { hash: "#/metodo", rotulo: "Método" },
];

export function App() {
  const [hash, setHash] = useState(location.hash || "#/");
  const [tema, setTema] = useState<Tema>(() => {
    try {
      return localStorage.getItem("recado-tema") === "escuro"
        ? "escuro"
        : "claro";
    } catch {
      return "claro";
    }
  });
  useEffect(() => {
    const mudar = (e: HashChangeEvent) => {
      setHash(location.hash || "#/");
      if (
        new URL(e.oldURL).hash.split("?")[0] !==
        new URL(e.newURL).hash.split("?")[0]
      )
        window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", mudar);
    return () => window.removeEventListener("hashchange", mudar);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = tema;
    try {
      localStorage.setItem("recado-tema", tema);
    } catch {
      /* Tema da visita. */
    }
  }, [tema]);
  const caminho = hash.split("?")[0];
  const pagina = PAGINAS.some((p) => p.hash === caminho) ? caminho : "#/";

  return (
    <>
      <a
        className="pular"
        href="#conteudo"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("conteudo")?.focus();
        }}
      >
        Pular para o conteúdo
      </a>
      <header className="top">
        <a className="marca" href="#/" aria-label="Recado bench, início">
          <span className="marca-sinal" aria-hidden="true">
            r<span>↗</span>
          </span>
          <span>
            recado<span className="marca-bench">/ bench</span>
          </span>
        </a>
        <nav aria-label="Navegação principal">
          {PAGINAS.map((p, n) => (
            <a
              key={p.hash}
              href={p.hash}
              aria-current={pagina === p.hash ? "page" : undefined}
            >
              <span className="nav-num">0{n + 1}</span>
              {p.rotulo}
            </a>
          ))}
        </nav>
        <button
          className="tema"
          onClick={() => setTema((t) => (t === "claro" ? "escuro" : "claro"))}
          aria-label={`Ativar tema ${tema === "claro" ? "escuro" : "claro"}`}
        >
          {tema === "claro" ? "◐" : "◑"}
        </button>
      </header>
      <main id="conteudo" tabIndex={-1}>
        {pagina === "#/" && <Placar />}
        {pagina === "#/respostas" && <Respostas />}
        {pagina === "#/tarefas" && <Tarefas />}
        {pagina === "#/metodo" && <Metodo />}
      </main>
      <footer>
        <a className="marca" href="#/">
          recado / bench
        </a>
        <span>
          Feito por Arthur Gaspar · mensagens sintéticas, respostas reais.
        </span>
        <a href="https://github.com/arthurgaspar/pv-bench">Código & dados ↗</a>
      </footer>
    </>
  );
}
