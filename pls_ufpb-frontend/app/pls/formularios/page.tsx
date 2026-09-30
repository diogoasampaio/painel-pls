import Formularios from "@/components/Formularios";

/** Acompanhamento semestral das ações do PLS e valores dos indicadores informados, preenchidos pelos setores. */
export default function FormulariosPls() {
  return (
    <main className="container">
      <h1 className="page-title">Formulários dos setores</h1>
      <p className="caption">
        Cada setor responsável registra aqui o acompanhamento semestral das ações do PLS (as quatro perguntas da seção
        7.2 do plano) e os valores dos indicadores que não vêm de dados públicos. Todo envio fica guardado com data e
        autor; o painel usa o mais recente.
      </p>
      <Formularios />
    </main>
  );
}
