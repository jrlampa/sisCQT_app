import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { calcularRede } from '../services/api';
import TrechoTable from './TrechoTable';
import CalculationResult from './CalculationResult';
import SimulationModule from './SimulationModule'; // Import the SimulationModule

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
  trafo_kva: number;
  classe_tipo: string;
  classe_manual: string;
  fp_ip: number;
  perfil: string;
}

interface CalculationResultData {
  resultados_calculo: any[];
  kpis: any;
  avisos: string[];
  recomendacoes: any[]; // Added for TechnicalSuggestions
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

  // State for new project creation
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectFile, setNewProjectFile] = useState<File | null>(null);
  const [creatingProject, setCreatingProject] = useState(false);

  // State for new scenario creation
  const [showCreateScenarioModal, setShowCreateScenarioModal] = useState(false);
  const [currentProjectIdForScenario, setCurrentProjectIdForScenario] = useState<number | null>(null);
  const [newScenarioName, setNewScenarioName] = useState('');
  const [scenarioToCopyId, setScenarioToCopyId] = useState<number | null>(null);
  const [creatingScenario, setCreatingScenario] = useState(false);

  // State for editing existing scenario
  const [showEditScenarioModal, setShowEditScenarioModal] = useState(false);
  const [editingScenario, setEditingScenario] = useState<Cenario | null>(null);
  const [editedScenarioData, setEditedScenarioData] = useState<any>({}); // To hold form data for editing
  const [updatingScenario, setUpdatingScenario] = useState(false);

  // Current active tab for displaying results (Trecho Table, Calculation Results, Simulation)
  const [activeResultTab, setActiveResultTab] = useState<'trechos' | 'calculation' | 'simulation'>('trechos');


  // Handler for deleting a project
  const handleDeleteProject = async (projectId: number) => {
    if (window.confirm('Are you sure you want to delete this project and all its scenarios?')) {
        try {
            await axios.delete(`${import.meta.env.VITE_API_URL}/api/projetos/${projectId}/`);
            setProjetos(projetos.filter(p => p.id !== projectId));
            // Clear selected scenario and trechos if the deleted project contained them
            if (selectedScenario && projetos.find(p => p.id === projectId)?.cenarios.some(c => c.id === selectedScenario.id)) {
                setSelectedScenario(null);
                setTrechos([]);
                setCalculationResult(null);
            }
        } catch (err: any) {
            console.error('Failed to delete project:', err);
            setError('Failed to delete project.');
        }
    }
  };

  // Handler for deleting a scenario
  const handleDeleteScenario = async (scenarioId: number, projectId: number) => {
    if (window.confirm('Are you sure you want to delete this scenario?')) {
        try {
            await axios.delete(`${import.meta.env.VITE_API_URL}/api/cenarios/${scenarioId}/`);
            setProjetos(prevProjetos => prevProjetos.map(p =>
                p.id === projectId
                    ? { ...p, cenarios: p.cenarios.filter(c => c.id !== scenarioId) }
                    : p
            ));
            // Clear selected scenario and trechos if the deleted scenario was active
            if (selectedScenario && selectedScenario.id === scenarioId) {
                setSelectedScenario(null);
                setTrechos([]);
                setCalculationResult(null);
            }
            setError(null); // Clear any previous error
        } catch (err: any) {
            console.error('Failed to delete scenario:', err.response?.data || err.message);
            setError(`Failed to delete scenario: ${err.response?.data?.detail || err.message}`);
        }
    }
  };

  // Handler for creating a project
  const handleCreateProject = async (e: React.FormEvent) => {
      e.preventDefault();
      setCreatingProject(true);
      try {
          if (newProjectFile) {
              const formData = new FormData();
              formData.append('file', newProjectFile);
              // The backend expects project_name as a query parameter for upload_excel
              const response = await axios.post(
                  `${import.meta.env.VITE_API_URL}/api/projetos/upload_excel/?project_name=${newProjectName}`,
                  formData,
                  {
                      headers: {
                          'Content-Type': 'multipart/form-data',
                      },
                  }
              );
              setProjetos([...projetos, response.data]);
          } else if (newProjectName) {
              // If no file is provided, it means we are creating a blank project.
              // Currently, the backend's ProjetoViewSet doesn't have a direct 'create_blank_project' endpoint.
              // The default POST to /api/projetos/ expects a JSON body matching the serializer.
              // Let's assume for now that if only a name is provided, we still try to create a project
              // and the backend serializer handles the defaults.
              // If the backend required more data, this would need to be adjusted.
              const response = await axios.post(
                  `${import.meta.env.VITE_API_URL}/api/projetos/`,
                  { nome: newProjectName } // Only send the name for a blank project
              );
              setProjetos([...projetos, response.data]);
          } else {
              setError('Please provide a project name or upload an Excel file.');
              return;
          }
          setNewProjectName('');
          setNewProjectFile(null);
          setError(null); // Clear any previous error
      } catch (err: any) {
          console.error('Failed to create project:', err.response?.data || err.message);
          setError(`Failed to create project: ${err.response?.data?.error || err.message}`);
      } finally {
          setCreatingProject(false);
      }
  };

  // Handler for creating a new scenario
  const handleCreateScenario = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!currentProjectIdForScenario || !newScenarioName.trim()) {
          setError('Project ID and scenario name are required.');
          return;
      }
      setCreatingScenario(true);
      try {
          const payload: any = {
              projeto: currentProjectIdForScenario,
              nome_cenario: newScenarioName,
          };
          if (scenarioToCopyId) {
              payload.copy_from_cenario_id = scenarioToCopyId; // Custom field for copying logic in backend
          }

          const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/cenarios/`, payload);
          // Instead of re-fetching all projects, we can optimize by updating the specific project
          setProjetos(prevProjetos => prevProjetos.map(p =>
              p.id === currentProjectIdForScenario
                  ? { ...p, cenarios: [...p.cenarios, response.data] } // Assuming response.data is the new scenario
                  : p
          ));

          setNewScenarioName('');
          setScenarioToCopyId(null);
          setShowCreateScenarioModal(false);
          setError(null);
      } catch (err: any) {
          console.error('Failed to create scenario:', err.response?.data || err.message);
          setError(`Failed to create scenario: ${err.response?.data?.detail || err.response?.data?.nome_cenario || err.message}`);
      } finally {
          setCreatingScenario(false);
      }
  };

  // Function to open the modal for scenario creation
  const openCreateScenarioModal = (projectId: number) => {
      setCurrentProjectIdForScenario(projectId);
      setNewScenarioName('');
      setScenarioToCopyId(null);
      setShowCreateScenarioModal(true);
      setError(null); // Clear any previous error
  };

  // Handler for updating an existing scenario
  const handleUpdateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingScenario) return;
    setUpdatingScenario(true);
    try {
        const response = await axios.put(
            `${import.meta.env.VITE_API_URL}/api/cenarios/${editingScenario.id}/`,
            editedScenarioData
        );
        // Update the projects state with the modified scenario
        setProjetos(prevProjetos => prevProjetos.map(p =>
            p.id === response.data.projeto // Assuming the response includes the project ID
                ? { ...p, cenarios: p.cenarios.map(c => c.id === response.data.id ? response.data : c) }
                : p
        ));
        setShowEditScenarioModal(false);
        setEditingScenario(null);
        setEditedScenarioData({});
        setError(null);
    } catch (err: any) {
        console.error('Failed to update scenario:', err.response?.data || err.message);
        setError(`Failed to update scenario: ${err.response?.data?.detail || err.message}`);
    } finally {
        setUpdatingScenario(false);
    }
  };

  // Function to open the edit modal
  const openEditScenarioModal = (scenario: Cenario) => {
      setEditingScenario(scenario);
      setEditedScenarioData(scenario); // Pre-populate form with current scenario data
      setShowEditScenarioModal(true);
      setError(null);
  };

  // Handle changes in the edit form
  const handleEditScenarioChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const { name, value } = e.target;
      setEditedScenarioData(prevData => ({
          ...prevData,
          [name]: name === 'trafo_kva' || name === 'fp_ip' ? parseFloat(value) : value,
      }));
  };


  useEffect(() => {
    const fetchProjetos = async () => {
      try {
        const response = await axios.get<Projeto[]>(`${import.meta.env.VITE_API_URL}/api/projetos/`);
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
      const response = await axios.get<Trecho[]>(`${import.meta.env.VITE_API_URL}/api/trechos/?projeto=${projetoId}&nome_cenario=${cenario.nome_cenario}`);
      setTrechos(response.data);
      setActiveResultTab('trechos'); // Set active tab to trechos when a scenario is selected
    } catch (err) {
      console.error('Failed to fetch trechos:', err);
    } finally {
      setLoadingTrechos(false);
    }
  };
  
  const handleSaveTrecho = (updatedTrecho: Trecho) => {
    setTrechos(trechos.map(t => t.id === updatedTrecho.id ? updatedTrecho : t));
  };

  const handleAddTrechoToList = (newTrecho: Trecho) => {
    setTrechos(prevTrechos => [...prevTrechos, newTrecho]);
  };

  const handleRemoveTrechoFromList = (trechoId: number) => {
    setTrechos(prevTrechos => prevTrechos.filter(t => t.id !== trechoId));
  };

  const handleCalcularClick = async (cenario: Cenario) => {
    setLoadingCalculation(true);
    try {
      if (!cenario || !trechos) {
        setError('Cenário ou trechos não selecionados.');
        setLoadingCalculation(false);
        return;
      }
      const response = await calcularRede(cenario, trechos);
      setCalculationResult(response.data);
      setActiveResultTab('calculation'); // Set active tab to calculation results
    } catch (err: any) {
      console.error('Failed to calculate:', err);
      setError(`Failed to calculate: ${err.response?.data?.error || err.message}`);
    } finally {
      setLoadingCalculation(false);
    }
  };

  // Handlers for exporting data
  const handleExportCsv = async (cenarioId: number, nomeProjeto: string, nomeCenario: string) => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/cenarios/${cenarioId}/export_csv/`, {
        responseType: 'blob', // Important for file downloads
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${nomeProjeto}_${nomeCenario}_resultados.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err: any) {
      console.error('Failed to export CSV:', err.response?.data || err.message);
      alert(`Failed to export CSV: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleExportPdf = async (cenarioId: number, nomeProjeto: string, nomeCenario: string) => {
    try {
      const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/cenarios/${cenarioId}/export_pdf/`, {
        responseType: 'blob', // Important for file downloads
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${nomeProjeto}_${nomeCenario}_relatorio.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err: any) {
      console.error('Failed to export PDF:', err.response?.data || err.message);
      alert(`Failed to export PDF: ${err.response?.data?.detail || err.message}`);
    }
  };


  if (loading) {
    return <div className="text-center mt-5">Loading projects...</div>;
  }

  if (error) {
    return <div className="alert alert-danger mt-5">{error}</div>;
  }

  // It should only be created if calculationResult is available.
  const cqtResultsMap: { [ponto: string]: number } = {};
  if (calculationResult && calculationResult.resultados_calculo) {
      calculationResult.resultados_calculo.forEach(res => {
          cqtResultsMap[res.PONTO] = res.CQT_ACUMULADA;
      });
  }

  return (
    <div className="container mt-5">
      <h1 className="mb-4">Lista de Projetos</h1>
      <div className="mb-4 p-4 border rounded shadow-sm">
          <h2>Criar Novo Projeto</h2>
          <form onSubmit={handleCreateProject}>
              <div className="mb-3">
                  <label htmlFor="newProjectName" className="form-label">Nome do Projeto</label>
                  <input
                      type="text"
                      className="form-control"
                      id="newProjectName"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      placeholder="Ex: Projeto Nova Rede"
                      required
                  />
              </div>
              <div className="mb-3">
                  <label htmlFor="newProjectFile" className="form-label">Upload de Arquivo Excel (Opcional)</label>
                  <input
                      type="file"
                      className="form-control"
                      id="newProjectFile"
                      accept=".xlsx, .xls"
                      onChange={(e) => setNewProjectFile(e.target.files ? e.target.files[0] : null)}
                  />
                  <div className="form-text">Planilha da concessionária para importação automática.</div>
              </div>
              <button type="submit" className="btn btn-success" disabled={creatingProject}>
                  {creatingProject ? 'Criando...' : 'Criar Projeto'}
              </button>
              {creatingProject && <div className="spinner-border spinner-border-sm ms-2" role="status"></div>}
              {error && <div className="alert alert-danger mt-3">{error}</div>}
          </form>
      </div>
      {projetos.length === 0 ? (
        <div className="alert alert-info">Nenhum projeto encontrado.</div>
      ) : (
        <div className="row">
          {projetos.map((projeto) => (
            <div key={projeto.id} className="col-md-6 col-lg-4 mb-4">
              <div className="card h-100">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <h5 className="card-title mb-0">{projeto.nome}</h5>
                    <button
                        className="btn btn-sm btn-danger"
                        onClick={(e) => { e.stopPropagation(); handleDeleteProject(projeto.id); }}
                        title="Delete Project"
                    >
                        Delete
                    </button>
                  </div>
                  <p className="card-text">Criado em: {new Date(projeto.data_criacao).toLocaleDateString()}</p>
                  <h6 className="card-subtitle mb-2 text-muted">Cenários:</h6>
                  {projeto.cenarios && projeto.cenarios.length > 0 ? (
                    <ul className="list-group list-group-flush">
                      {projeto.cenarios.map((cenario) => (
                        <li key={cenario.id} className="list-group-item d-flex justify-content-between align-items-center" onClick={() => handleScenarioClick(cenario, projeto.id)} style={{cursor: 'pointer'}}>
                          {cenario.nome_cenario}
                          <div>
                            <button className="btn btn-sm btn-info me-2" onClick={(e) => { e.stopPropagation(); openEditScenarioModal(cenario); }} title="Edit Scenario">Edit</button>
                            <button className="btn btn-sm btn-primary me-2" onClick={(e) => { e.stopPropagation(); handleCalcularClick(cenario); }}>Calcular</button>
                            {/* Export Buttons */}
                            <button className="btn btn-sm btn-secondary me-2" onClick={(e) => { e.stopPropagation(); handleExportCsv(cenario.id, projeto.nome, cenario.nome_cenario); }} title="Export CSV">CSV</button>
                            <button className="btn btn-sm btn-secondary me-2" onClick={(e) => { e.stopPropagation(); handleExportPdf(cenario.id, projeto.nome, cenario.nome_cenario); }} title="Export PDF">PDF</button>
                            <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); handleDeleteScenario(cenario.id, projeto.id); }} title="Delete Scenario">Delete</button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>Nenhum cenário associado.</p>
                  )}
                  <div className="d-grid mt-3">
                    <button className="btn btn-sm btn-outline-secondary" onClick={() => openCreateScenarioModal(projeto.id)}>
                      + Adicionar Cenário
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedScenario && (
        <div className="mt-5">
          <h2>Trechos para o cenário: {selectedScenario.nome_cenario}</h2>

          {/* Navigation Tabs for Trecho Table, Calculation Results, Simulation */}
          <ul className="nav nav-tabs mb-3">
            <li className="nav-item">
              <button
                className={`nav-link ${activeResultTab === 'trechos' ? 'active' : ''}`}
                onClick={() => setActiveResultTab('trechos')}
              >
                Tabela de Trechos
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link ${activeResultTab === 'calculation' ? 'active' : ''}`}
                onClick={() => setActiveResultTab('calculation')}
                disabled={!calculationResult} // Disable if no calculation has been run
              >
                Resultados do Cálculo
              </button>
            </li>
            <li className="nav-item">
              <button
                className={`nav-link ${activeResultTab === 'simulation' ? 'active' : ''}`}
                onClick={() => setActiveResultTab('simulation')}
                disabled={!calculationResult} // Disable if no calculation has been run
              >
                Simulação
              </button>
            </li>
          </ul>

          {activeResultTab === 'trechos' && (
            loadingTrechos ? (
              <div>Loading trechos...</div>
            ) : (
              <TrechoTable
                trechos={trechos}
                onSave={handleSaveTrecho}
                projectId={selectedScenario.projeto}
                nomeCenario={selectedScenario.nome_cenario}
                onAdd={handleAddTrechoToList}
                onRemove={handleRemoveTrechoFromList}
                cqtResults={cqtResultsMap}
              />
            )
          )}

          {activeResultTab === 'calculation' && loadingCalculation && (
            <div className="text-center mt-5">Calculando...</div>
          )}
          {activeResultTab === 'calculation' && calculationResult && (
            <div className="mt-5">
              <CalculationResult results={calculationResult} />
            </div>
          )}

          {activeResultTab === 'simulation' && selectedScenario && calculationResult && (
            <div className="mt-5">
              <SimulationModule cenarioId={selectedScenario.id} currentTrechos={trechos} />
            </div>
          )}
        </div>
      )}

      {/***** Create Scenario Modal *****/}
      {showCreateScenarioModal && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Criar Novo Cenário para Projeto {currentProjectIdForScenario}</h5>
                <button type="button" className="btn-close" onClick={() => setShowCreateScenarioModal(false)}></button>
              </div>
              <form onSubmit={handleCreateScenario}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="newScenarioName" className="form-label">Nome do Cenário</label>
                    <input
                      type="text"
                      className="form-control"
                      id="newScenarioName"
                      name="nome_cenario"
                      value={newScenarioName}
                      onChange={(e) => setNewScenarioName(e.target.value)}
                      placeholder="Ex: Cenário Otimizado"
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="scenarioToCopy" className="form-label">Copiar de Cenário Existente (Opcional)</label>
                    <select
                      className="form-select"
                      id="scenarioToCopy"
                      value={scenarioToCopyId || ''}
                      onChange={(e) => setScenarioToCopyId(e.target.value ? parseInt(e.target.value) : null)}
                    >
                      <option value="">-- Selecione um cenário --</option>
                      {currentProjectIdForScenario &&
                        projetos.find(p => p.id === currentProjectIdForScenario)?.cenarios.map(cenario => (
                          <option key={cenario.id} value={cenario.id}>
                            {cenario.nome_cenario}
                          </option>
                        ))}
                    </select>
                  </div>
                  {error && <div className="alert alert-danger mt-3">{error}</div>}
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowCreateScenarioModal(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary" disabled={creatingScenario}>
                    {creatingScenario ? 'Criando...' : 'Criar Cenário'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/***** Edit Scenario Modal *****/}
      {showEditScenarioModal && editingScenario && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Editar Cenário: {editingScenario.nome_cenario}</h5>
                <button type="button" className="btn-close" onClick={() => setShowEditScenarioModal(false)}></button>
              </div>
              <form onSubmit={handleUpdateScenario}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="editNomeCenario" className="form-label">Nome do Cenário</label>
                    <input
                      type="text"
                      className="form-control"
                      id="editNomeCenario"
                      name="nome_cenario"
                      value={editedScenarioData.nome_cenario || ''}
                      onChange={handleEditScenarioChange}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editTrafoKva" className="form-label">Trafo kVA</label>
                    <input
                      type="number"
                      step="0.01"
                      className="form-control"
                      id="editTrafoKva"
                      name="trafo_kva"
                      value={editedScenarioData.trafo_kva || 0}
                      onChange={handleEditScenarioChange}
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editClasseTipo" className="form-label">Classe Tipo</label>
                    <select
                      className="form-select"
                      id="editClasseTipo"
                      name="classe_tipo"
                      value={editedScenarioData.classe_tipo || ''}
                      onChange={handleEditScenarioChange}
                    >
                      <option value="Automático">Automático</option>
                      <option value="Manual">Manual</option>
                    </select>
                  </div>
                  {editedScenarioData.classe_tipo === 'Manual' && (
                    <div className="mb-3">
                      <label htmlFor="editClasseManual" className="form-label">Classe Manual</label>
                      <select
                        className="form-select"
                        id="editClasseManual"
                        name="classe_manual"
                        value={editedScenarioData.classe_manual || ''}
                        onChange={handleEditScenarioChange}
                      >
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                        <option value="D">D</option>
                      </select>
                    </div>
                  )}
                  <div className="mb-3">
                    <label htmlFor="editFpIp" className="form-label">FP IP</label>
                    <input
                      type="number"
                      step="0.01"
                      className="form-control"
                      id="editFpIp"
                      name="fp_ip"
                      value={editedScenarioData.fp_ip || 0}
                      onChange={handleEditScenarioChange}
                    />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editPerfil" className="form-label">Perfil</label>
                    <input
                      type="text"
                      className="form-control"
                      id="editPerfil"
                      name="perfil"
                      value={editedScenarioData.perfil || ''}
                      onChange={handleEditScenarioChange}
                    />
                  </div>
                  {error && <div className="alert alert-danger mt-3">{error}</div>}
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowEditScenarioModal(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary" disabled={updatingScenario}>
                    {updatingScenario ? 'Salvando...' : 'Salvar Alterações'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjetoList;
