import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface SimulationResult {
  df_simulated: any[];
  kpis_simulated: any;
  log_changes: { [ponto: string]: string };
  iterations: number;
  message: string;
  resolved: boolean;
}

interface SimulationModuleProps {
  cenarioId: number;
  currentTrechos: any[]; // Data of the current scenario's trechos
}

const SimulationModule: React.FC<SimulationModuleProps> = ({ cenarioId, currentTrechos }) => {
  const [cabosOptions, setCabosOptions] = useState<string[]>([]);
  const [selectedCables, setSelectedCables] = useState<string[]>([]);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [loadingSimulation, setLoadingSimulation] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCabosOptions = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/cabos/`);
        setCabosOptions(response.data.map((c: any) => c.nome));
        // Optionally pre-select some common cables
        const defaultCables = response.data.filter((c: any) => c.nome.includes('Al')).map((c: any) => c.nome);
        setSelectedCables(defaultCables.length > 0 ? defaultCables : response.data.map((c: any) => c.nome));
      } catch (err: any) {
        console.error('Failed to fetch cable options:', err);
        setError('Failed to load cable options for simulation.');
      }
    };
    fetchCabosOptions();
  }, []);

  const handleSimulate = async () => {
    if (!cenarioId || selectedCables.length === 0) {
      setError('Please select at least one cable for simulation.');
      return;
    }
    setLoadingSimulation(true);
    setError(null);
    setSimulationResult(null);

    try {
      const response = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/cenarios/${cenarioId}/simular_readequacao/`,
        { cabos_habilitados_nomes: selectedCables }
      );
      setSimulationResult(response.data);
    } catch (err: any) {
      console.error('Simulation failed:', err.response?.data || err.message);
      setError(`Simulation failed: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoadingSimulation(false);
    }
  };

  return (
    <div className="mt-4 card p-4">
      <h3>Módulo de Simulação de Readequação</h3>
      <p className="text-muted">
        Execute uma simulação para otimizar o circuito, escolhendo os cabos permitidos para readequação.
      </p>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="mb-3">
        <label htmlFor="selectCables" className="form-label">Cabos Habilitados para Simulação</label>
        <select
          multiple
          className="form-select"
          id="selectCables"
          value={selectedCables}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
            setSelectedCables(Array.from(e.target.selectedOptions, option => option.value))
          }
          style={{ minHeight: '150px' }}
        >
          {cabosOptions.map(option => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <div className="form-text">Selecione um ou mais cabos que o simulador pode usar.</div>
      </div>

      <button className="btn btn-primary" onClick={handleSimulate} disabled={loadingSimulation || selectedCables.length === 0}>
        {loadingSimulation ? 'Simulando...' : 'Executar Simulação'}
      </button>

      {loadingSimulation && (
        <div className="text-center mt-3">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p>Otimizando circuito, por favor aguarde...</p>
        </div>
      )}

      {simulationResult && (
        <div className="mt-4">
          <h4>Resultados da Simulação</h4>
          <div className={`alert ${simulationResult.resolved ? 'alert-success' : 'alert-warning'}`}>
            {simulationResult.message}
          </div>

          <h5>KPIs Simulados</h5>
          <ul className="list-group mb-3">
            {Object.entries(simulationResult.kpis_simulated).map(([key, value]) => (
              <li key={key} className="list-group-item">
                <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : value}
              </li>
            ))}
          </ul>

          {Object.keys(simulationResult.log_changes).length > 0 && (
            <>
              <h5>Alterações Sugeridas</h5>
              <ul className="list-group mb-3">
                {Object.entries(simulationResult.log_changes).map(([ponto, change]) => (
                  <li key={ponto} className="list-group-item">
                    <strong>Ponto {ponto}:</strong> {change}
                  </li>
                ))}
              </ul>
            </>
          )}

          <h5>Trechos Simulados</h5>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            <table className="table table-sm table-bordered">
              <thead>
                <tr>
                  <th>Ponto</th>
                  <th>Montante</th>
                  <th>Cabo (Simulado)</th>
                  <th>Metros</th>
                  <th>CQT Acum. (%)</th>
                  {/* Add more relevant columns from df_simulated */}
                </tr>
              </thead>
              <tbody>
                {simulationResult.df_simulated.map((row, index) => (
                  <tr key={index}>
                    <td>{row.PONTO}</td>
                    <td>{row.MONTANTE}</td>
                    <td>{row.CABO}</td>
                    <td>{row.METROS}</td>
                    <td>{row.CQT_ACUMULADA ? row.CQT_ACUMULADA.toFixed(2) : 'N/A'}</td>
                    {/* Render more data as needed */}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default SimulationModule;