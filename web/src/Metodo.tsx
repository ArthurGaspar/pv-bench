import { carregar, nomeCurto, type Benchmark } from "./dados";
import { Vazio, useDados } from "./ui";

export function Metodo() {
  const { dados, erro } = useDados<Benchmark>(carregar);
  if (erro) return <Vazio titulo="Sem dados ainda">{erro}</Vazio>;
  if (!dados) return <Vazio titulo="Carregando…" />;

  return (
    <>
      <section>
        <h1>Como funciona</h1>
        <p>
          O benchmark é o produto aqui: um conjunto de itens, um corretor e um runner que fala com qualquer modelo. Os
          modelos que aparecem no placar são só os primeiros em que ele foi apontado.
        </p>
      </section>

      <section className="painel">
        <h2>A correção</h2>
        <p>
          Todo item tem uma resposta certa e uma só. A correção compara o que o modelo respondeu com o gabarito, sem júri e
          sem modelo avaliando modelo, então a mesma rodada dá sempre o mesmo número.
        </p>
        <p>Duas coisas são medidas separadamente:</p>
        <ul style={{ paddingLeft: 20, color: "var(--ink-2)", maxWidth: "76ch" }}>
          <li>
            <b>Acerto</b>: a resposta, depois de extraída do texto, bate com o gabarito. A extração é tolerante de
            propósito, porque a pergunta é se o modelo entendeu a mensagem.
          </li>
          <li>
            <b>Formato limpo</b>: a resposta já veio exatamente como foi pedido, sem frase em volta e sem markdown. Um
            modelo pode entender tudo e ainda assim escrever "Claro! O valor é R$ 1.500,00 😊".
          </li>
        </ul>
        <p className="peq">
          Nos itens que pedem mais de um campo, como dia <i>e</i> hora, o acerto exige os dois: não há crédito parcial.
        </p>
        <p className="peq">
          Detalhe que importa em português: "1.500" é mil e quinhentos e "1,5" é um e meio. O corretor lê os dois formatos,
          o brasileiro e o inglês, decidindo pelo separador que aparece por último.
        </p>
      </section>

      <section className="painel">
        <h2>Rodar nos seus modelos</h2>
        <p>
          O runner usa LiteLLM, então serve qualquer provedor que ele atenda. O padrão é Ollama na própria máquina, porque
          assim rodar o benchmark não custa nada.
        </p>
        <div className="resp">
          {`pip install -r requirements.txt

# local, de graça
python -m bench.run --modelos ollama/llama3.2:3b

# qualquer provedor que o LiteLLM atenda
export OPENAI_API_KEY=...
python -m bench.run --modelos gpt-4o-mini

python -m bench.build   # junta tudo para o site`}
        </div>
        <p className="peq" style={{ marginTop: 10 }}>
          Os resultados caem em <code>data/resultados/</code>, um arquivo por modelo, com a resposta crua de cada item.
        </p>
      </section>

      <section className="painel">
        <h2>O que este número não é</h2>
        <ul style={{ paddingLeft: 20, color: "var(--ink-2)", maxWidth: "76ch" }}>
          <li>
            <b>São {dados.itens.length} itens.</b> Dá para ver tendência e tropeço, não para cravar que um modelo é melhor
            que outro por três pontos. Cada item vale {(100 / dados.itens.length).toFixed(1)} pontos percentuais.
          </li>
          <li>
            <b>Os itens são escritos à mão.</b> Imitam mensagem real, mas não foram coletados de conversa de ninguém, até
            porque conversa de verdade é dado pessoal.
          </li>
          <li>
            <b>Temperatura zero, uma tentativa por item.</b> Não há média de várias rodadas, então um empate técnico pode
            virar diferença de um ponto por acaso.
          </li>
          <li>
            <b>Nada aqui mede escrita.</b> Só compreensão: todas as respostas são curtas e verificáveis. Um modelo pode
            entender tudo e escrever mal, e isso não aparece.
          </li>
          <li>
            <b>Os itens estão publicados.</b> Isso é bom para auditar e ruim para o futuro: uma vez na internet, podem
            acabar em treino de alguém e deixar de medir o que mediam.
          </li>
        </ul>
      </section>

      <section className="painel">
        <h2>Rodadas publicadas</h2>
        <table>
          <thead>
            <tr>
              <th>Modelo</th>
              <th>Rodado em</th>
              <th className="num">Duração</th>
            </tr>
          </thead>
          <tbody>
            {dados.placar.map((p) => (
              <tr key={p.modelo}>
                <td className="mono">{nomeCurto(p.modelo)}</td>
                <td>{new Date(p.rodadoEm).toLocaleString("pt-BR")}</td>
                <td className="num">{Math.round(p.segundos)}s</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="peq" style={{ marginTop: 10 }}>
          Dados gerados em {new Date(dados.geradoEm).toLocaleString("pt-BR")}. As rodadas acontecem na máquina de quem roda,
          porque o CI não tem GPU nem modelo; o site publica o que foi versionado.
        </p>
      </section>
    </>
  );
}
