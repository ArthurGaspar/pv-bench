import { useEffect, useState } from "react";
import { Metodo } from "./Metodo";
import { Placar } from "./Placar";
import { Respostas } from "./Respostas";
import { Tarefas } from "./Tarefas";

type Tema = "sistema" | "claro" | "escuro";

const PAGINAS = [
  { hash: "#/", rotulo: "Placar" },
  { hash: "#/respostas", rotulo: "Respostas" },
  { hash: "#/tarefas", rotulo: "Tarefas" },
  { hash: "#/metodo", rotulo: "Como funciona" },
];

export function App() {
  const [hash, setHash] = useState(location.hash || "#/");
  const [tema, setTema] = useState<Tema>(() => {
    try {
      return (localStorage.getItem("pv-tema") as Tema) || "sistema";
    } catch {
      return "sistema";
    }
  });

  useEffect(() => {
    const aoMudar = () => {
      setHash(location.hash || "#/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", aoMudar);
    return () => window.removeEventListener("hashchange", aoMudar);
  }, []);

  useEffect(() => {
    if (tema === "sistema") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", tema === "claro" ? "light" : "dark");
    try {
      localStorage.setItem("pv-tema", tema);
    } catch {
      // sem storage o tema vale só para esta visita
    }
  }, [tema]);

  const caminho = (hash.split("?")[0] || "#/") as string;
  const pagina = PAGINAS.some((p) => p.hash === caminho) ? caminho : "#/";

  return (
    <>
      <header className="top">
        <a className="marca" href="#/">
          <b>Deu pra entender?</b>
          <span>benchmark de português brasileiro de verdade</span>
        </a>
        <nav>
          {PAGINAS.map((p) => (
            <a key={p.hash} href={p.hash} aria-current={pagina === p.hash ? "page" : undefined}>
              {p.rotulo}
            </a>
          ))}
        </nav>
        <button className="tema" onClick={() => setTema((t) => (t === "sistema" ? "claro" : t === "claro" ? "escuro" : "sistema"))} aria-label={`Tema: ${tema}`}>
          {tema === "sistema" ? "Auto" : tema === "claro" ? "Claro" : "Escuro"}
        </button>
      </header>
      <main>
        {pagina === "#/" && <Placar />}
        {pagina === "#/respostas" && <Respostas />}
        {pagina === "#/tarefas" && <Tarefas />}
        {pagina === "#/metodo" && <Metodo />}
      </main>
    </>
  );
}
