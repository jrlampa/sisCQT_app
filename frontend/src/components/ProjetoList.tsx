import React, { useEffect, useState } from 'react';
import axios from 'axios';
import TrechoTable from './TrechoTable';
import CalculationResult from './CalculationResult';

interface Trecho {
  id: number;
  ponto: string;
  montante: string;
  metros: number;
  cabo: string;
  mono: number;
  bi: number;
  tri: number;
  tri_esp: number;
  carga_esp: number;
  tipo_ip: string;
  qtd_ip: number;
  projeto: number;
  nome_cenario: string;
}

interface Projeto {
  id: number;
  nome: string;
  data_criacao: string;
  cenarios: Cenario[];
}

interface Cenario {
  id: number;
  nome_cenario: string;
}

interface CalculationResultData {
  resultados_calculo: any[];
  kpis: any;
  avisos: string[];
}

const ProjetoList: React.FC = () => {
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<Cenario | null>(null);
  const [trechos, setTrechos] = useState<Trecho[]>([]);
  const [loadingTrechos, setLoadingTrechos] = useState<boolean>(false);
  const [calculationResult, setCalculationResult] = useState<CalculationResultData | null>(null);
  const [loadingCalculation, setLoadingCalculation] = useState<boolean>(false);

  useEffect(() => {
    const fetchProjetos = async () => {
      try {
        const response = await axios.get<Projeto[]>('http://127.0.0.1:8000/api/projetos/');
        setProjetos(response.data);
      } catch (err) {
        setError('Failed to fetch projects.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchProjetos();
  }, []);

  const handleScenarioClick = async (cenario: Cenario, projetoId: number) => {
    setSelectedScenario(cenario);
    setCalculationResult(null); // Clear previous results
    setLoadingTrechos(true);
    try {
      const response = await axios.get<Trecho[]>(`http://127.0.0.1:8000/api/trechos/?projeto=${projetoId}&nome_cenario=${cenario.nome_cenario}`);
      setTrechos(response.data);
    } catch (err) {
      console.error('Failed to fetch trechos:', err);
    } finally {
      setLoadingTrechos(false);
    }
  };
  
  const handleSaveTrecho = (updatedTrecho: Trecho) => {
    setTrechos(trechos.map(t => t.id === updatedTrecho.id ? updatedTrecho : t));
  };

  const handleCalcularClick = async (cenarioId: number) => {
    setLoadingCalculation(true);
    try {
      const response = await axios.post<CalculationResultData>(`http://127.0.0.1:8000/api/cenarios/${cenarioId}/calcular/`);
      setCalculationResult(response.data);
    } catch (err) {
      console.error('Failed to calculate:', err);
    } finally {
      setLoadingCalculation(false);
    }
  };

  if (loading) {
    return <div className="text-center mt-5">Loading projects...</div>;
  }

  if (error) {
    return <div className="alert alert-danger mt-5">{error}</div>;
  }

  return (
    <div className="container mt-5">
      <h1 className="mb-4">Lista de Projetos</h1>
      {projetos.length === 0 ? (
        <div className="alert alert-info">Nenhum projeto encontrado.</div>
      ) : (
        <div className="row">
          {projetos.map((projeto) => (
            <div key={projeto.id} className="col-md-6 col-lg-4 mb-4">
              <div className="card h-100">
                <div className="card-body">
                  <h5 className="card-title">{projeto.nome}</h5>
                  <p className="card-text">Criado em: {new Date(projeto.data_criacao).toLocaleDateString()}</p>
                  <h6 className="card-subtitle mb-2 text-muted">Cenários:</h6>
                  {projeto.cenarios && projeto.cenarios.length > 0 ? (
                    <ul className="list-group list-group-flush">
                      {projeto.cenarios.map((cenario) => (
                        <li key={cenario.id} className="list-group-item d-flex justify-content-between align-items-center" onClick={() => handleScenarioClick(cenario, projeto.id)} style={{cursor: 'pointer'}}>
                          {cenario.nome_cenario}
                          <button className="btn btn-sm btn-primary" onClick={(e) => { e.stopPropagation(); handleCalcularClick(cenario.id); }}>Calcular</button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>Nenhum cenário associado.</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedScenario && (
        <div className="mt-5">
          <h2>Trechos para o cenário: {selectedScenario.nome_cenario}</h2>
          {loadingTrechos ? (
            <div>Loading trechos...</div>
          ) : (
            <TrechoTable trechos={trechos} onSave={handleSaveTrecho} />
          )}
        </div>
      )}

      {loadingCalculation && <div className="text-center mt-5">Calculando...</div>}
      {calculationResult && (
        <div className="mt-5">
          <CalculationResult results={calculationResult} />
        </div>
      )}
    </div>
  );
};

export default ProjetoList;
