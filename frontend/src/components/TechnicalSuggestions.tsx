import React from 'react';

interface Recommendation {
  titulo: string;
  texto: string;
}

interface BaricentroAnalysis {
  status: string;
  msg: string;
}

interface TechnicalSuggestionsProps {
  recomendacoes: Recommendation[];
  baricentroAnalysis: BaricentroAnalysis;
  avisos: string[]; // Still show general warnings
}

const TechnicalSuggestions: React.FC<TechnicalSuggestionsProps> = ({
  recomendacoes,
  baricentroAnalysis,
  avisos,
}) => {
  return (
    <div className="mt-4">
      <h3>Diagnóstico e Sugestões Técnicas</h3>

      {baricentroAnalysis && (
        <div className="card mb-3">
          <div className="card-header">Análise de Baricentro Elétrico</div>
          <div className="card-body">
            <h5 className="card-title">Status: {baricentroAnalysis.status}</h5>
            <p className="card-text">{baricentroAnalysis.msg}</p>
          </div>
        </div>
      )}

      {recomendacoes.length > 0 ? (
        <div className="mb-3">
          <h4>Recomendações de Engenharia</h4>
          <div className="accordion" id="recommendationsAccordion">
            {recomendacoes.map((rec, index) => (
              <div className="accordion-item" key={index}>
                <h2 className="accordion-header" id={`heading${index}`}>
                  <button
                    className="accordion-button collapsed"
                    type="button"
                    data-bs-toggle="collapse"
                    data-bs-target={`#collapse${index}`}
                    aria-expanded="false"
                    aria-controls={`collapse${index}`}
                  >
                    {rec.titulo}
                  </button>
                </h2>
                <div
                  id={`collapse${index}`}
                  className="accordion-collapse collapse"
                  aria-labelledby={`heading${index}`}
                  data-bs-parent="#recommendationsAccordion"
                >
                  <div className="accordion-body">{rec.texto}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="alert alert-success">
          Nenhuma recomendação de engenharia adicional necessária.
        </div>
      )}

      {avisos.length > 0 && (
        <div className="mt-3">
          <h4>Avisos Gerais</h4>
          <ul className="list-group">
            {avisos.map((aviso, index) => (
              <li key={index} className="list-group-item list-group-item-warning">
                {aviso}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default TechnicalSuggestions;