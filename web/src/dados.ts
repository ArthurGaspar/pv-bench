/** Tipos e carregamento do JSON que `python -m bench.build` publica. */

export interface Tarefa {
  id: string;
  titulo: string;
  descricao: string;
  tipo: string;
  rotulos: string[];
}

export interface Item {
  id: string;
  task: string;
  mensagem: string;
  contexto: Record<string, string>;
  alternativas: Record<string, string> | null;
  gabarito: string | number | Record<string, string>;
  pega: string;
  prompt: string;
}

interface LinhaPlacar {
  modelo: string;
  rodadoEm: string;
  segundos: number;
  acertos: number;
  total: number;
  formatoOk: number;
  segundosPorItem: number;
  porTarefa: Record<string, { acertos: number; total: number }>;
}

export interface Resposta {
  modelo: string;
  id: string;
  task: string;
  bruto: string;
  segundos: number;
  extraido: unknown;
  acertou: boolean;
  formato_ok: boolean;
  erro_formato: string | null;
}

export interface Benchmark {
  geradoEm: string;
  tarefas: Tarefa[];
  itens: Item[];
  placar: LinhaPlacar[];
  respostas: Resposta[];
  itensPorTarefa: Record<string, number>;
}

let promessa: Promise<Benchmark> | null = null;

export function carregar(): Promise<Benchmark> {
  if (!promessa) {
    const url = `${import.meta.env.BASE_URL}data/benchmark.json`;
    promessa = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${url} respondeu ${r.status}. Rode \`python -m bench.build\` antes.`);
      return r.json();
    });
  }
  return promessa;
}

/** "ollama/qwen2.5:7b" vira "qwen2.5:7b", que é o que interessa na tabela. */
export const nomeCurto = (modelo: string) => modelo.replace(/^[^/]+\//, "");

export const gabaritoTexto = (g: Item["gabarito"]) =>
  typeof g === "object" && g !== null ? Object.entries(g).map(([k, v]) => `${k}: ${v}`).join(" · ") : String(g);

export const pct = (parte: number, total: number) => (total ? `${Math.round((parte / total) * 100)}%` : "-");
