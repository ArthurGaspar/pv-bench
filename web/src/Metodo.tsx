import { carregar, nomeCurto } from "./dados";
import { Vazio, useDados } from "./ui";

export function Metodo() {
  const { dados, erro } = useDados(carregar);
  if (erro)
    return <Vazio titulo="Não foi possível carregar o método">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Lendo as rodadas…" />;
  return (
    <>
      <section className="pagina-intro">
        <p className="sobretitulo">Caderno / Método</p>
        <h1>Como o ponto é contado.</h1>
        <p>
          Um conjunto público, prompts fixos e correção por regra. Nenhum modelo
          participa da avaliação das respostas.
        </p>
      </section>
      <section className="metodo-grid">
        <h2>01. Correção</h2>
        <div>
          <p>
            <b>Acerto:</b> o valor extraído precisa coincidir com o gabarito. Em
            respostas com mais de um campo, todos devem bater; não há crédito
            parcial.
          </p>
          <p>
            <b>Formato limpo:</b> o texto respeita o formato aceito pelo parser.
            Essa medida é independente do acerto. Cercas de Markdown são
            removidas antes da verificação.
          </p>
          <p>
            O corretor aceita números brasileiros e ingleses. A extração tolera
            texto adicional quando consegue identificar uma única resposta.
          </p>
          <p className="peq">
            Ao montar o site, as respostas brutas são corrigidas novamente. IDs
            duplicados, itens desconhecidos e tarefas inconsistentes interrompem
            a publicação. Rodadas parciais ficam fora do placar.
          </p>
        </div>
      </section>
      <section className="metodo-grid">
        <h2>02. Reproduzir</h2>
        <div>
          <pre className="resp">{`python -m venv .venv
# Ative a venv e instale as dependências:
pip install -r requirements.txt

# Com o Ollama instalado e o modelo baixado:
python -m bench.run --modelos ollama/qwen2.5:7b
python -m pytest -q
python -m bench.build

cd web
npm ci
npm run dev`}</pre>
          <p className="peq">
            Outros provedores podem ser usados via LiteLLM, com a chave no
            ambiente. O comando de execução pode gerar cobrança nesses
            provedores. O site apenas lê os resultados versionados.
          </p>
          <a
            className="link-seta"
            href="https://github.com/arthurgaspar/pv-bench"
          >
            Ver código e conjunto <span aria-hidden="true">↗</span>
          </a>
        </div>
      </section>
      <section className="metodo-grid">
        <h2>03. Limites</h2>
        <ul>
          <li>
            <b>{dados.itens.length} itens manuais.</b> Cada item vale{" "}
            {(100 / dados.itens.length).toFixed(2).replace(".", ",")} pontos
            percentuais. Diferenças pequenas não sustentam um ranking geral.
          </li>
          <li>
            <b>Uma tentativa, temperatura zero.</b> Não há repetição para
            estimar a variação entre execuções.
          </li>
          <li>
            <b>Mensagens sintéticas.</b> O conjunto não amostra conversas reais,
            regiões, faixas etárias ou variedades do português de forma
            representativa.
          </li>
          <li>
            <b>Gabarito e parser têm limites.</b> Erros podem vir da
            compreensão, do cálculo ou da extração. A resposta bruta e o prompt
            ficam disponíveis para auditoria.
          </li>
          <li>
            <b>Conjunto público.</b> Há risco de contaminação por dados de
            treino. O teste mede respostas curtas, não qualidade de escrita.
          </li>
          <li>
            <b>Tempo sem controle de hardware.</b> As durações incluem a
            execução local e não servem para comparar a velocidade intrínseca de
            modelos.
          </li>
        </ul>
      </section>
      <section className="metodo-grid">
        <h2>04. Registro</h2>
        <div className="tabela-scroll">
          <table>
            <caption className="sr-only">Proveniência das rodadas</caption>
            <thead>
              <tr>
                <th>Modelo</th>
                <th>Data da rodada</th>
                <th>Origem</th>
                <th className="num">Duração</th>
              </tr>
            </thead>
            <tbody>
              {dados.placar.map((p) => (
                <tr key={p.modelo}>
                  <td className="mono">{nomeCurto(p.modelo)}</td>
                  <td>
                    {new Date(p.rodadoEm).toLocaleString("pt-BR", {
                      timeZone: "America/Sao_Paulo",
                    })}
                  </td>
                  <td>{p.origem === "importado" ? "Importada" : "Local"}</td>
                  <td className="num mono">
                    {p.segundos === null ? "-" : `${Math.round(p.segundos)} s`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="peq rodape-tabela">
            Horário de Brasília. Conjunto {dados.conjunto.nome}{" "}
            {dados.conjunto.versao}. Dados montados em{" "}
            {new Date(dados.geradoEm).toLocaleString("pt-BR", {
              timeZone: "America/Sao_Paulo",
            })}
            .
          </p>
        </div>
      </section>
    </>
  );
}
