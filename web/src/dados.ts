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
}

let promessa: Promise<Benchmark> | null = null;

export function carregar(): Promise<Benchmark> {
  if (!promessa) {
    const url = `${import.meta.env.BASE_URL}data/benchmark.json`;
    promessa = fetch(url)
      .then((r) => {
        if (!r.ok)
          throw new Error(
            "Os resultados estão indisponíveis. Tente recarregar a página.",
          );
        return r.json();
      })
      .catch(() => {
        promessa = null;
        throw new Error(
          "Os resultados estão indisponíveis. Tente recarregar a página.",
        );
      });
  }
  return promessa;
}

export const nomeCurto = (modelo: string) => modelo.replace(/^[^/]+\//, "");

export const gabaritoTexto = (g: Item["gabarito"]) =>
  typeof g === "object" && g !== null
    ? Object.entries(g)
        .map(([k, v]) => `${k}: ${v}`)
        .join(" · ")
    : String(g);

export const pct = (parte: number, total: number) =>
  total ? `${Math.round((parte / total) * 100)}%` : "-";

export const CORES = [
  "var(--c-1)",
  "var(--c-2)",
  "#8566aa",
  "#9b741e",
  "#327fa2",
];

export function respostasPorItem(dados: Benchmark) {
  const indice = new Map<string, Resposta[]>();
  for (const r of dados.respostas)
    indice.set(r.id, [...(indice.get(r.id) ?? []), r]);
  return indice;
}

export function linkRespostas(params: Record<string, string>) {
  return `#/respostas?${new URLSearchParams(params)}`;
}

export function baixarCSV(itens: Item[], respostas: Resposta[]) {
  const campo = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const porId = new Map(itens.map((i) => [i.id, i]));
  const linhas: unknown[][] = [
    [
      "item",
      "tarefa",
      "mensagem",
      "gabarito",
      "modelo",
      "resposta",
      "extraido",
      "acertou",
      "formato_ok",
      "segundos",
    ],
  ];
  for (const r of respostas) {
    const i = porId.get(r.id);
    if (i)
      linhas.push([
        i.id,
        i.task,
        i.mensagem,
        gabaritoTexto(i.gabarito),
        r.modelo,
        r.bruto,
        JSON.stringify(r.extraido),
        r.acertou,
        r.formato_ok,
        r.segundos,
      ]);
  }
  const url = URL.createObjectURL(
    new Blob(
      ["\ufeff", linhas.map((l) => l.map(campo).join(",")).join("\r\n")],
      { type: "text/csv;charset=utf-8" },
    ),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = "recado-bench-respostas.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
