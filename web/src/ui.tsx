import { useEffect, useState, type MouseEvent, type ReactNode } from "react";

export function useDados<T>(carregar: () => Promise<T>): { dados: T | null; erro: string | null } {
  const [estado, setEstado] = useState<{ dados: T | null; erro: string | null }>({ dados: null, erro: null });
  useEffect(() => {
    let vivo = true;
    carregar().then(
      (dados) => vivo && setEstado({ dados, erro: null }),
      (e) => vivo && setEstado({ dados: null, erro: String(e.message ?? e) }),
    );
    return () => {
      vivo = false;
    };
  }, []);
  return estado;
}

export function Vazio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="vazio">
      <h1>{titulo}</h1>
      {children && <p style={{ margin: "0 auto" }}>{children}</p>}
    </div>
  );
}

export function Tile({ valor, rotulo, sub }: { valor: ReactNode; rotulo: string; sub?: ReactNode }) {
  return (
    <div className="tile">
      <div className="v">{valor}</div>
      <div className="l">{rotulo}</div>
      {sub && <div className="s">{sub}</div>}
    </div>
  );
}

export function Selo({ ok, children }: { ok: boolean; children: ReactNode }) {
  return <span className={`selo ${ok ? "ok" : "nao"}`}>{children}</span>;
}

interface Dica {
  x: number;
  y: number;
  texto: string;
}

function CaixaDica({ dica }: { dica: Dica | null }) {
  if (!dica) return null;
  return (
    <div className="dica" style={{ left: Math.min(dica.x + 12, window.innerWidth - 300), top: dica.y + 14 }}>
      {dica.texto}
    </div>
  );
}

interface Serie {
  nome: string;
  cor: string;
  valores: Record<string, { acertos: number; total: number }>;
}

/**
 * Acerto por tarefa, uma barra por modelo. A escala vai sempre até 100% para
 * que as alturas possam ser comparadas entre tarefas, e não só dentro de uma.
 */
export function BarrasPorTarefa({
  tarefas,
  series,
}: {
  tarefas: { id: string; titulo: string }[];
  series: Serie[];
}) {
  const [dica, setDica] = useState<Dica | null>(null);
  const L = 196;
  const W = 680;
  const alturaBarra = 13;
  const espaco = 5;
  const alturaLinha = series.length * (alturaBarra + espaco) + 18;
  const larguraUtil = W - L - 46;

  return (
    <>
      <svg className="grafico" viewBox={`0 0 ${W} ${tarefas.length * alturaLinha + 16}`} width="100%" role="img" aria-label="Acertos por tarefa, por modelo">
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line className="grade" x1={L + larguraUtil * f} x2={L + larguraUtil * f} y1={0} y2={tarefas.length * alturaLinha} />
            <text x={L + larguraUtil * f} y={tarefas.length * alturaLinha + 12} textAnchor="middle">
              {f * 100}%
            </text>
          </g>
        ))}
        {tarefas.map((t, i) => (
          <g key={t.id}>
            <text x={L - 10} y={i * alturaLinha + 14} textAnchor="end">
              {t.titulo.length > 30 ? t.titulo.slice(0, 29) + "…" : t.titulo}
            </text>
            {series.map((s, j) => {
              const v = s.valores[t.id] ?? { acertos: 0, total: 0 };
              const frac = v.total ? v.acertos / v.total : 0;
              const larg = Math.max(2, frac * larguraUtil);
              const y = i * alturaLinha + j * (alturaBarra + espaco) + 2;
              const r = Math.min(4, larg / 2);
              return (
                <g
                  key={s.nome}
                  onMouseMove={(e: MouseEvent) => setDica({ x: e.clientX, y: e.clientY, texto: `${s.nome} · ${t.titulo}: ${v.acertos} de ${v.total}` })}
                  onMouseLeave={() => setDica(null)}
                >
                  <rect x={0} y={y} width={W} height={alturaBarra} fill="transparent" />
                  <path
                    d={`M${L},${y} H${L + larg - r} A${r},${r} 0 0 1 ${L + larg},${y + r} V${y + alturaBarra - r} A${r},${r} 0 0 1 ${L + larg - r},${y + alturaBarra} H${L} Z`}
                    fill={s.cor}
                  />
                  <text x={L + larg + 6} y={y + alturaBarra - 2} style={{ fill: "var(--ink)" }}>
                    {v.acertos}/{v.total}
                  </text>
                </g>
              );
            })}
          </g>
        ))}
      </svg>
      <div className="legenda">
        {series.map((s) => (
          <span key={s.nome} className="linha" style={{ gap: 6 }}>
            <span className="amostra" style={{ background: s.cor }} /> {s.nome}
          </span>
        ))}
      </div>
      <CaixaDica dica={dica} />
    </>
  );
}
