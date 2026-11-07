import { useEffect, useState, type ReactNode } from "react";

export function useDados<T>(carregar: () => Promise<T>) {
  const [estado, setEstado] = useState<{
    dados: T | null;
    erro: string | null;
  }>({ dados: null, erro: null });
  useEffect(() => {
    let vivo = true;
    carregar().then(
      (dados) => vivo && setEstado({ dados, erro: null }),
      (e) => vivo && setEstado({ dados: null, erro: String(e.message ?? e) }),
    );
    return () => {
      vivo = false;
    };
  }, [carregar]);
  return estado;
}

export function Vazio({
  titulo,
  children,
}: {
  titulo: string;
  children?: ReactNode;
}) {
  return (
    <div className="vazio" role="status">
      <h1>{titulo}</h1>
      {children && <p>{children}</p>}
    </div>
  );
}

export function Selo({ ok, children }: { ok: boolean; children: ReactNode }) {
  return (
    <span className={`selo ${ok ? "ok" : "nao"}`}>
      {ok ? "✓" : "×"} {children}
    </span>
  );
}
