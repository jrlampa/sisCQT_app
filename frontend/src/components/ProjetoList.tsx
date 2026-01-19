import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { calcularRede } from '../services/api';
import TrechoTable from './TrechoTable';
import CalculationResult from './CalculationResult';
import SimulationModule from './SimulationModule'; // Import the SimulationModule
import GlassCard from './GlassCard'; // Import GlassCard

import {
  Box,
  Grid,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Tab,
  Tabs,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  ListItemButton,
} from '@mui/material';

import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import DescriptionIcon from '@mui/icons-material/Description'; // For CSV
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'; // For PDF

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
    return (
      <Box sx={{ textAlign: 'center', mt: 5 }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>Loading projects...</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error" sx={{ mt: 5 }}>{error}</Alert>;
  }

  // It should only be created if calculationResult is available.
  const cqtResultsMap: { [ponto: string]: number } = {};
  if (calculationResult && calculationResult.resultados_calculo) {
      calculationResult.resultados_calculo.forEach(res => {
          cqtResultsMap[res.PONTO] = res.CQT_ACUMULADA;
      });
  }

  return (
    <Box sx={{ p: 3, mt: 2 }}> {/* Main container with padding and top margin for floating app bar */}
      <Typography variant="h4" gutterBottom>Lista de Projetos</Typography> {/* h1 converted to Typography */}
      <GlassCard sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom>Criar Novo Projeto</Typography>
          <form onSubmit={handleCreateProject}>
              <TextField
                  fullWidth
                  label="Nome do Projeto"
                  id="newProjectName"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="Ex: Projeto Nova Rede"
                  required
                  sx={{ mb: 2 }}
              />
              <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel shrink htmlFor="newProjectFile">Upload de Arquivo Excel (Opcional)</InputLabel>
                  <TextField
                      fullWidth
                      type="file"
                      id="newProjectFile"
                      inputProps={{ accept: ".xlsx, .xls" }}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewProjectFile(e.target.files ? e.target.files[0] : null)}
                      sx={{ mt: 3 }} // Adjust mt to align with InputLabel
                  />
                  <Typography variant="caption" display="block" sx={{ mt: 1 }}>Planilha da concessionária para importação automática.</Typography>
              </FormControl>
              <Button type="submit" variant="contained" color="primary" disabled={creatingProject} sx={{
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
              }}>
                  {creatingProject ? 'Criando...' : 'Criar Projeto'}
              </Button>
              {creatingProject && <CircularProgress size={20} sx={{ ml: 2 }} />}
              {error && <Alert severity="error" sx={{ mt: 3 }}>{error}</Alert>}
          </form>
      </GlassCard>
      {projetos.length === 0 ? (
        <Alert severity="info" sx={{ mt: 3 }}>Nenhum projeto encontrado.</Alert>
      ) : (
        <Grid container spacing={3}>
          {projetos.map((projeto) => (
            <Grid key={projeto.id} sx={{ width: { xs: '100%', sm: '50%', md: '33.33%' } }}>
              <GlassCard sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">{projeto.nome}</Typography>
                  <IconButton
                      color="error"
                      onClick={(e) => { e.stopPropagation(); handleDeleteProject(projeto.id); }}
                      title="Delete Project"
                  >
                      <DeleteIcon />
                  </IconButton>
                </Box>
                <Typography variant="body2" color="text.secondary">Criado em: {new Date(projeto.data_criacao).toLocaleDateString()}</Typography>
                <Typography variant="subtitle1" color="text.secondary" mt={2} mb={1}>Cenários:</Typography>
                {projeto.cenarios && projeto.cenarios.length > 0 ? (
                  <List disablePadding sx={{ flexGrow: 1 }}>
                    {projeto.cenarios.map((cenario) => (
                      <ListItem
                        key={cenario.id}
                        disablePadding
                        secondaryAction={
                          <Box>
                            <IconButton edge="end" aria-label="edit" onClick={(e) => { e.stopPropagation(); openEditScenarioModal(cenario); }} title="Edit Scenario">
                              <EditIcon />
                            </IconButton>
                            <Button
                                variant="contained"
                                size="small"
                                onClick={(e) => { e.stopPropagation(); handleCalcularClick(cenario); }}
                                sx={{
                                  ml: 1, // Margin left for spacing
                                  background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                                  boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                                }}
                            >
                              Calcular
                            </Button>
                            <IconButton edge="end" aria-label="export csv" onClick={(e) => { e.stopPropagation(); handleExportCsv(cenario.id, projeto.nome, cenario.nome_cenario); }} title="Export CSV" sx={{ ml: 1 }}>
                              <DescriptionIcon />
                            </IconButton>
                            <IconButton edge="end" aria-label="export pdf" onClick={(e) => { e.stopPropagation(); handleExportPdf(cenario.id, projeto.nome, cenario.nome_cenario); }} title="Export PDF" sx={{ ml: 1 }}>
                              <PictureAsPdfIcon />
                            </IconButton>
                            <IconButton edge="end" aria-label="delete scenario" color="error" onClick={(e) => { e.stopPropagation(); handleDeleteScenario(cenario.id, projeto.id); }} title="Delete Scenario" sx={{ ml: 1 }}>
                              <DeleteIcon />
                            </IconButton>
                          </Box>
                        }
                      >
                        <ListItemButton onClick={() => handleScenarioClick(cenario, projeto.id)}>
                          <ListItemText primary={cenario.nome_cenario} />
                        </ListItemButton>
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2">Nenhum cenário associado.</Typography>
                )}
                <Box mt={3}>
                  <Button
                    fullWidth
                    variant="contained"
                    color="primary"
                    onClick={() => openCreateScenarioModal(projeto.id)}
                    startIcon={<AddIcon />}
                    sx={{
                      background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                      boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                    }}
                  >
                    Adicionar Cenário
                  </Button>
                </Box>
              </GlassCard>
            </Grid>
          ))}
        </Grid>
      )}

      {selectedScenario && (
        <Box sx={{ mt: 5 }}>
          <Typography variant="h5" gutterBottom>Trechos para o cenário: {selectedScenario.nome_cenario}</Typography>

          {/* Navigation Tabs for Trecho Table, Calculation Results, Simulation */}
          <Tabs value={activeResultTab} onChange={(event: React.SyntheticEvent, newValue: 'trechos' | 'calculation' | 'simulation') => setActiveResultTab(newValue)} aria-label="resultado tabs" sx={{ mb: 3 }}>
            <Tab label="Tabela de Trechos" value="trechos" />
            <Tab label="Resultados do Cálculo" value="calculation" disabled={!calculationResult} />
            <Tab label="Simulação" value="simulation" disabled={!calculationResult} />
          </Tabs>
          {activeResultTab === 'trechos' && (
            loadingTrechos ? (
              <Box sx={{ textAlign: 'center', mt: 5 }}><CircularProgress /><Typography sx={{ mt: 2 }}>Loading trechos...</Typography></Box>
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
            <Box sx={{ textAlign: 'center', mt: 5 }}><CircularProgress /><Typography sx={{ mt: 2 }}>Calculando...</Typography></Box>
          )}
          {activeResultTab === 'calculation' && calculationResult && (
            <GlassCard sx={{ mt: 5 }}>
              <CalculationResult results={calculationResult} />
            </GlassCard>
          )}

          {activeResultTab === 'simulation' && selectedScenario && calculationResult && (
            <Box sx={{ mt: 5 }}>
              <SimulationModule cenarioId={selectedScenario.id} currentTrechos={trechos} />
            </Box>
          )}
        </Box>
      )}

      {/***** Create Scenario Modal (MUI Dialog) *****/}
      <Dialog open={showCreateScenarioModal} onClose={() => setShowCreateScenarioModal(false)}>
        <DialogTitle>Criar Novo Cenário para Projeto {currentProjectIdForScenario}</DialogTitle>
        <form onSubmit={handleCreateScenario}>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              id="newScenarioName"
              label="Nome do Cenário"
              type="text"
              fullWidth
              variant="outlined"
              name="nome_cenario"
              value={newScenarioName}
              onChange={(e) => setNewScenarioName(e.target.value)}
              placeholder="Ex: Cenário Otimizado"
              required
              sx={{ mb: 2 }}
            />
            <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
              <InputLabel id="scenarioToCopy-label">Copiar de Cenário Existente (Opcional)</InputLabel>
              <Select
                labelId="scenarioToCopy-label"
                id="scenarioToCopy"
                value={scenarioToCopyId || ''}
                label="Copiar de Cenário Existente (Opcional)"
                onChange={(e) => setScenarioToCopyId(e.target.value ? parseInt(e.target.value as string) : null)}
              >
                <MenuItem value="">-- Selecione um cenário --</MenuItem>
                {currentProjectIdForScenario &&
                  projetos.find(p => p.id === currentProjectIdForScenario)?.cenarios.map(cenario => (
                    <MenuItem key={cenario.id} value={cenario.id}>
                      {cenario.nome_cenario}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowCreateScenarioModal(false)}>Cancelar</Button>
            <Button type="submit" disabled={creatingScenario} sx={{
              background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
              boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
            }}>
              {creatingScenario ? <CircularProgress size={24} /> : 'Criar Cenário'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/***** Edit Scenario Modal (MUI Dialog) *****/}
      {showEditScenarioModal && editingScenario && (
        <Dialog open={showEditScenarioModal} onClose={() => setShowEditScenarioModal(false)}>
          <DialogTitle>Editar Cenário: {editingScenario.nome_cenario}</DialogTitle>
          <form onSubmit={handleUpdateScenario}>
            <DialogContent>
              <TextField
                autoFocus
                margin="dense"
                id="editNomeCenario"
                label="Nome do Cenário"
                type="text"
                fullWidth
                variant="outlined"
                name="nome_cenario"
                value={editedScenarioData.nome_cenario || ''}
                onChange={handleEditScenarioChange}
                required
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                id="editTrafoKva"
                label="Trafo kVA"
                type="number"
                step="0.01"
                fullWidth
                variant="outlined"
                name="trafo_kva"
                value={editedScenarioData.trafo_kva || 0}
                onChange={handleEditScenarioChange}
                sx={{ mb: 2 }}
              />
              <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                <InputLabel id="editClasseTipo-label">Classe Tipo</InputLabel>
                <Select
                  labelId="editClasseTipo-label"
                  id="editClasseTipo"
                  name="classe_tipo"
                  value={editedScenarioData.classe_tipo || ''}
                  label="Classe Tipo"
                  onChange={handleEditScenarioChange}
                >
                  <MenuItem value="Automático">Automático</MenuItem>
                  <MenuItem value="Manual">Manual</MenuItem>
                </Select>
              </FormControl>
              {editedScenarioData.classe_tipo === 'Manual' && (
                <FormControl fullWidth margin="dense" sx={{ mb: 2 }}>
                  <InputLabel id="editClasseManual-label">Classe Manual</InputLabel>
                  <Select
                    labelId="editClasseManual-label"
                    id="editClasseManual"
                    name="classe_manual"
                    value={editedScenarioData.classe_manual || ''}
                    label="Classe Manual"
                    onChange={handleEditScenarioChange}
                  >
                    <MenuItem value="A">A</MenuItem>
                    <MenuItem value="B">B</MenuItem>
                    <MenuItem value="C">C</MenuItem>
                    <MenuItem value="D">D</MenuItem>
                  </Select>
                </FormControl>
              )}
              <TextField
                margin="dense"
                id="editFpIp"
                label="FP IP"
                type="number"
                step="0.01"
                fullWidth
                variant="outlined"
                name="fp_ip"
                value={editedScenarioData.fp_ip || 0}
                onChange={handleEditScenarioChange}
                sx={{ mb: 2 }}
              />
              <TextField
                margin="dense"
                id="editPerfil"
                label="Perfil"
                type="text"
                fullWidth
                variant="outlined"
                name="perfil"
                value={editedScenarioData.perfil || ''}
                onChange={handleEditScenarioChange}
                sx={{ mb: 2 }}
              />
              {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setShowEditScenarioModal(false)}>Cancelar</Button>
              <Button type="submit" disabled={updatingScenario} sx={{
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
              }}>
                {updatingScenario ? <CircularProgress size={24} /> : 'Salvar Alterações'}
              </Button>
            </DialogActions>
          </form>
        </Dialog>
      )}
          </Box>  );
};

export default ProjetoList;
