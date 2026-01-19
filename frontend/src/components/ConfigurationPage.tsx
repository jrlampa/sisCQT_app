import React, { useEffect, useState } from 'react';
import axios from 'axios';
import GlassCard from './GlassCard'; // Import GlassCard

import {
  Box,
  Typography,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  IconButton,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid, // Add Grid here
  Paper,
} from '@mui/material';

import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Close'; // Using Close icon for Cancel
import CableIcon from '@mui/icons-material/Cable'; // For Cabos
import LightbulbIcon from '@mui/icons-material/Lightbulb'; // For IPs
import PowerIcon from '@mui/icons-material/Power'; // For Trafos
import PeopleIcon from '@mui/icons-material/People'; // For Perfis (profiles)
import SettingsIcon from '@mui/icons-material/Settings'; // For Simulation Config


const ConfigurationPage: React.FC = () => {
  const [cabos, setCabos] = useState<any[]>([]);
  const [ips, setIps] = useState<any[]>([]);
  const [trafos, setTrafos] = useState<any[]>([]);
  const [perfis, setPerfis] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'cabos' | 'ips' | 'trafos' | 'perfis' | 'simulation'>('cabos'); // New state for active tab
  
  const [newCabo, setNewCabo] = useState({ nome: '', coeficiente: 0, preco: 0 });
  const [newIp, setNewIp] = useState({ nome: '', potencia_watts: 0, preco: 0 });
  const [newTrafo, setNewTrafo] = useState({ kva: 0 });
  const [newPerfil, setNewPerfil] = useState({ nome: '', cqt_max: 0, sobrecarga_max: 0 });

  // State for editing existing CfgCabo
  const [showEditCaboModal, setShowEditCaboModal] = useState(false);
  const [editingCabo, setEditingCabo] = useState<any | null>(null);
  const [editedCaboData, setEditedCaboData] = useState<any>({});
  const [updatingCabo, setUpdatingCabo] = useState(false);

  // State for editing existing CfgIP
  const [showEditIpModal, setShowEditIpModal] = useState(false);
  const [editingIp, setEditingIp] = useState<any | null>(null);
  const [editedIpData, setEditedIpData] = useState<any>({});
  const [updatingIp, setUpdatingIp] = useState(false);

  // State for editing existing CfgTrafo
  const [showEditTrafoModal, setShowEditTrafoModal] = useState(false);
  const [editingTrafo, setEditingTrafo] = useState<any | null>(null);
  const [editedTrafoData, setEditedTrafoData] = useState<any>({});
  const [updatingTrafo, setUpdatingTrafo] = useState(false);

  // State for editing existing CfgPerfil
  const [showEditPerfilModal, setShowEditPerfilModal] = useState(false);
  const [editingPerfil, setEditingPerfil] = useState<any | null>(null);
  const [editedPerfilData, setEditedPerfilData] = useState<any>({});
  const [updatingPerfil, setUpdatingPerfil] = useState(false);

  // State for simulation cables
  const [simulationCables, setSimulationCables] = useState<string[]>([]);

  const fetchAllConfigs = async () => {
    try {
      const [cabosRes, ipsRes, trafosRes, perfisRes] = await Promise.all([
        axios.get(`${import.meta.env.VITE_API_URL}/api/cabos/`),
        axios.get(`${import.meta.env.VITE_API_URL}/api/ips/`),
        axios.get(`${import.meta.env.VITE_API_URL}/api/trafos/`),
        axios.get(`${import.meta.env.VITE_API_URL}/api/perfis/`),
      ]);
      setCabos(cabosRes.data);
      setIps(ipsRes.data);
      setTrafos(trafosRes.data);
      setPerfis(perfisRes.data);
    } catch (error) {
      console.error('Failed to fetch configurations:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllConfigs();
  }, []);

  const handleCreate = async (endpoint: string, data: any, resetter: () => void) => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/${endpoint}/`, data);
      fetchAllConfigs();
      resetter();
    } catch (error: any) {
      console.error(`Failed to create ${endpoint}:`, error.response?.data || error.message);
      alert(`Failed to create ${endpoint}: ${error.response?.data?.error || error.message}`);
    }
  };
  
  const handleDelete = async (endpoint: string, id: string | number) => {
    if (window.confirm(`Are you sure you want to delete this ${endpoint.slice(0, -1)}?`)) {
      try {
        await axios.delete(`${import.meta.env.VITE_API_URL}/api/${endpoint}/${id}/`);
        fetchAllConfigs();
      } catch (error: any) {
        console.error(`Failed to delete ${endpoint}:`, error.response?.data || error.message);
        alert(`Failed to delete ${endpoint}: ${error.response?.data?.detail || error.message}`);
      }
    }
  };

  // Handlers for editing CfgCabo
  const openEditCaboModal = (cabo: any) => {
    setEditingCabo(cabo);
    setEditedCaboData(cabo);
    setShowEditCaboModal(true);
  };

  const handleEditCaboChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditedCaboData(prevData => ({
      ...prevData,
      [name]: name === 'coeficiente' || name === 'preco' ? parseFloat(value) : value,
    }));
  };

  const handleUpdateCabo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCabo) return;
    setUpdatingCabo(true);
    try {
      await axios.put(`${import.meta.env.VITE_API_URL}/api/cabos/${editingCabo.nome}/`, editedCaboData);
      fetchAllConfigs();
      setShowEditCaboModal(false);
      setEditingCabo(null);
      setEditedCaboData({});
    } catch (error: any) {
      console.error('Failed to update cabo:', error.response?.data || error.message);
      alert(`Failed to update cabo: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUpdatingCabo(false);
    }
  };

  // Handlers for editing CfgIP
  const openEditIpModal = (ip: any) => {
    setEditingIp(ip);
    setEditedIpData(ip);
    setShowEditIpModal(true);
  };

  const handleEditIpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditedIpData(prevData => ({
      ...prevData,
      [name]: name === 'potencia_watts' || name === 'preco' ? parseFloat(value) : value,
    }));
  };

  const handleUpdateIp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingIp) return;
    setUpdatingIp(true);
    try {
      await axios.put(`${import.meta.env.VITE_API_URL}/api/ips/${editingIp.nome}/`, editedIpData);
      fetchAllConfigs();
      setShowEditIpModal(false);
      setEditingIp(null);
      setEditedIpData({});
    } catch (error: any) {
      console.error('Failed to update IP:', error.response?.data || error.message);
      alert(`Failed to update IP: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUpdatingIp(false);
    }
  };

  // Handlers for editing CfgTrafo
  const openEditTrafoModal = (trafo: any) => {
    setEditingTrafo(trafo);
    setEditedTrafoData(trafo);
    setShowEditTrafoModal(true);
  };

  const handleEditTrafoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditedTrafoData(prevData => ({
      ...prevData,
      [name]: parseFloat(value), // kva is a float
    }));
  };

  const handleUpdateTrafo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTrafo) return;
    setUpdatingTrafo(true);
    try {
      await axios.put(`${import.meta.env.VITE_API_URL}/api/trafos/${editingTrafo.kva}/`, editedTrafoData);
      fetchAllConfigs();
      setShowEditTrafoModal(false);
      setEditingTrafo(null);
      setEditedTrafoData({});
    } catch (error: any) {
      console.error('Failed to update Trafo:', error.response?.data || error.message);
      alert(`Failed to update Trafo: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUpdatingTrafo(false);
    }
  };

  // Handlers for editing CfgPerfil
  const openEditPerfilModal = (perfil: any) => {
    setEditingPerfil(perfil);
    setEditedPerfilData(perfil);
    setShowEditPerfilModal(true);
  };

  const handleEditPerfilChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditedPerfilData(prevData => ({
      ...prevData,
      [name]: name === 'nome' ? value : parseFloat(value), // nome is string, others are numbers
    }));
  };

  const handleUpdatePerfil = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPerfil) return;
    setUpdatingPerfil(true);
    try {
      await axios.put(`${import.meta.env.VITE_API_URL}/api/perfis/${editingPerfil.nome}/`, editedPerfilData);
      fetchAllConfigs();
      setShowEditPerfilModal(false);
      setEditingPerfil(null);
      setEditedPerfilData({});
    } catch (error: any) {
      console.error('Failed to update Perfil:', error.response?.data || error.message);
      alert(`Failed to update Perfil: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUpdatingPerfil(false);
    }
  };


  if (loading) {
    return (
      <Box sx={{ textAlign: 'center', mt: 5 }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>Loading configurations...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, mt: 2 }}> {/* Main container with padding and top margin for floating app bar */}
      <Typography variant="h4" gutterBottom>Configurações</Typography>

      <Tabs value={activeTab} onChange={(event: React.SyntheticEvent, newValue: typeof activeTab) => setActiveTab(newValue)} aria-label="configuração tabs" sx={{ mb: 3 }}>
        <Tab label="Cabos" value="cabos" icon={<CableIcon />} iconPosition="start" />
        <Tab label="IPs" value="ips" icon={<LightbulbIcon />} iconPosition="start" />
        <Tab label="Trafos" value="trafos" icon={<PowerIcon />} iconPosition="start" />
        <Tab label="Perfis" value="perfis" icon={<PeopleIcon />} iconPosition="start" />
        <Tab label="Simulação" value="simulation" icon={<SettingsIcon />} iconPosition="start" />
      </Tabs>

      {activeTab === 'cabos' && (
        <GlassCard sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>Cabos</Typography>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('cabos', newCabo, () => setNewCabo({ nome: '', coeficiente: 0, preco: 0 })) }}>
              <Grid container spacing={2} alignItems="flex-end" sx={{ mb: 3 }}>
                  <Grid sx={{ width: { xs: '100%', sm: '33.33%' } }}> {/* Equivalent to xs=12 sm=4 */}
                      <TextField fullWidth label="Nome" name="nome" value={newCabo.nome} onChange={(e) => setNewCabo({...newCabo, nome: e.target.value})} required />
                  </Grid>
                  <Grid sx={{ width: { xs: '100%', sm: '33.33%' } }}> {/* Equivalent to xs=12 sm=4 */}
                      <TextField fullWidth label="Coeficiente" name="coeficiente" type="number" step="0.01" value={newCabo.coeficiente} onChange={(e) => setNewCabo({...newCabo, coeficiente: parseFloat(e.target.value)})} required />
                  </Grid>
                  <Grid sx={{ width: { xs: '100%', sm: '33.33%' } }}> {/* Equivalent to xs=12 sm=4 */}
                      <TextField fullWidth label="Preço" name="preco" type="number" step="0.01" value={newCabo.preco} onChange={(e) => setNewCabo({...newCabo, preco: parseFloat(e.target.value)})} required />
                  </Grid>
                  <Grid sx={{ width: '100%' }}> {/* Equivalent to xs=12 */}
                      <Button type="submit" variant="contained" color="primary" startIcon={<AddIcon />} sx={{
                        background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                        boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      }}>
                          Adicionar
                      </Button>
                  </Grid>
              </Grid>
          </form>
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell align="right">Coeficiente</TableCell>
                  <TableCell align="right">Preço</TableCell>
                  <TableCell align="center">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {cabos.map((cabo) => (
                  <TableRow key={cabo.nome} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                    <TableCell component="th" scope="row">{cabo.nome}</TableCell>
                    <TableCell align="right">{cabo.coeficiente}</TableCell>
                    <TableCell align="right">{cabo.preco}</TableCell>
                    <TableCell align="center">
                      <IconButton color="info" onClick={() => openEditCaboModal(cabo)} title="Editar">
                        <EditIcon />
                      </IconButton>
                      <IconButton color="error" onClick={() => handleDelete('cabos', cabo.nome)} title="Deletar">
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </GlassCard>
      )}

      {activeTab === 'ips' && (
        <GlassCard sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>IPs</Typography>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('ips', newIp, () => setNewIp({ nome: '', potencia_watts: 0, preco: 0 })) }}>
              <Grid container spacing={2} alignItems="flex-end" sx={{ mb: 3 }}>
                  <Grid xs={12} sm={4}>
                      <TextField fullWidth label="Nome" name="nome" value={newIp.nome} onChange={(e) => setNewIp({...newIp, nome: e.target.value})} required />
                  </Grid>
                  <Grid xs={12} sm={4}>
                      <TextField fullWidth label="Potência (Watts)" name="potencia_watts" type="number" step="0.01" value={newIp.potencia_watts} onChange={(e) => setNewIp({...newIp, potencia_watts: parseFloat(e.target.value)})} required />
                  </Grid>
                  <Grid xs={12} sm={4}>
                      <TextField fullWidth label="Preço" name="preco" type="number" step="0.01" value={newIp.preco} onChange={(e) => setNewIp({...newIp, preco: parseFloat(e.target.value)})} required />
                  </Grid>
                  <Grid xs={12}>
                      <Button type="submit" variant="contained" color="primary" startIcon={<AddIcon />} sx={{
                        background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                        boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      }}>
                          Adicionar
                      </Button>
                  </Grid>
              </Grid>
          </form>
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell align="right">Potência (Watts)</TableCell>
                  <TableCell align="right">Preço</TableCell>
                  <TableCell align="center">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {ips.map((ip) => (
                  <TableRow key={ip.nome} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                    <TableCell component="th" scope="row">{ip.nome}</TableCell>
                    <TableCell align="right">{ip.potencia_watts}</TableCell>
                    <TableCell align="right">{ip.preco}</TableCell>
                    <TableCell align="center">
                      <IconButton color="info" onClick={() => openEditIpModal(ip)} title="Editar">
                        <EditIcon />
                      </IconButton>
                      <IconButton color="error" onClick={() => handleDelete('ips', ip.nome)} title="Deletar">
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </GlassCard>
      )}

      {activeTab === 'trafos' && (
        <GlassCard sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>Trafos</Typography>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('trafos', newTrafo, () => setNewTrafo({ kva: 0 })) }}>
              <Grid container spacing={2} alignItems="flex-end" sx={{ mb: 3 }}>
                  <Grid xs={12} sm={6}>
                      <TextField fullWidth label="KVA" name="kva" type="number" step="0.01" value={newTrafo.kva} onChange={(e) => setNewTrafo({ kva: parseFloat(e.target.value) })} required />
                  </Grid>
                  <Grid xs={12} sm={6}>
                      <Button type="submit" variant="contained" color="primary" startIcon={<AddIcon />} sx={{
                        background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                        boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      }}>
                          Adicionar
                      </Button>
                  </Grid>
              </Grid>
          </form>
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell>KVA</TableCell>
                  <TableCell align="center">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {trafos.map((trafo) => (
                  <TableRow key={trafo.kva} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                    <TableCell component="th" scope="row">{trafo.kva}</TableCell>
                    <TableCell align="center">
                      <IconButton color="info" onClick={() => openEditTrafoModal(trafo)} title="Editar">
                        <EditIcon />
                      </IconButton>
                      <IconButton color="error" onClick={() => handleDelete('trafos', trafo.kva)} title="Deletar">
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </GlassCard>
      )}

      {activeTab === 'perfis' && (
        <GlassCard sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>Perfis</Typography>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('perfis', newPerfil, () => setNewPerfil({ nome: '', cqt_max: 0, sobrecarga_max: 0 })) }}>
              <Grid container spacing={2} alignItems="flex-end" sx={{ mb: 3 }}>
                  <Grid xs={12} sm={4}>
                      <TextField fullWidth label="Nome" name="nome" value={newPerfil.nome} onChange={(e) => setNewPerfil({...newPerfil, nome: e.target.value})} required />
                  </Grid>
                  <Grid xs={12} sm={4}>
                      <TextField fullWidth label="CQT Máx" name="cqt_max" type="number" step="0.01" value={newPerfil.cqt_max} onChange={(e) => setNewPerfil({...newPerfil, cqt_max: parseFloat(e.target.value)})} required />
                  </Grid>
                  <Grid xs={12} sm={4}>
                      <TextField fullWidth label="Sobrecarga Máx" name="sobrecarga_max" type="number" step="0.01" value={newPerfil.sobrecarga_max} onChange={(e) => setNewPerfil({...newPerfil, sobrecarga_max: parseFloat(e.target.value)})} required />
                  </Grid>
                  <Grid xs={12}>
                      <Button type="submit" variant="contained" color="primary" startIcon={<AddIcon />} sx={{
                        background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                        boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
                      }}>
                          Adicionar
                      </Button>
                  </Grid>
              </Grid>
          </form>
          <TableContainer component={Paper}>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell>Nome</TableCell>
                  <TableCell align="right">CQT Máx</TableCell>
                  <TableCell align="right">Sobrecarga Máx</TableCell>
                  <TableCell align="center">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {perfis.map((perfil) => (
                  <TableRow key={perfil.nome} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                    <TableCell component="th" scope="row">{perfil.nome}</TableCell>
                    <TableCell align="right">{perfil.cqt_max}</TableCell>
                    <TableCell align="right">{perfil.sobrecarga_max}</TableCell>
                    <TableCell align="center">
                      <IconButton color="info" onClick={() => openEditPerfilModal(perfil)} title="Editar">
                        <EditIcon />
                      </IconButton>
                      <IconButton color="error" onClick={() => handleDelete('perfis', perfil.nome)} title="Deletar">
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </GlassCard>
      )}

      {activeTab === 'simulation' && (
        <GlassCard sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>Configuração de Simulação</Typography>
          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel id="simulationCables-label">Cabos Habilitados para Simulação</InputLabel>
            <Select
              labelId="simulationCables-label"
              id="simulationCables"
              multiple
              value={simulationCables}
              onChange={(e) =>
                setSimulationCables(e.target.value as string[])
              }
              renderValue={(selected) => (selected as string[]).join(', ')}
              label="Cabos Habilitados para Simulação"
            >
              {cabos.map(cabo => (
                <MenuItem key={cabo.nome} value={cabo.nome}>
                  {cabo.nome}
                </MenuItem>
              ))}
            </Select>
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>Selecione os cabos que o simulador pode utilizar para readequação.</Typography>
          </FormControl>
          <Button variant="contained" color="primary" sx={{
            background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
            boxShadow: '0 3px 5px 2px rgba(33, 203, 243, .3)',
          }}>
            Salvar Configuração de Simulação
          </Button>
        </GlassCard>
      )}

      {/* Edit CfgCabo Modal - Glassmorphism Style */}
      {showEditCaboModal && editingCabo && (
        <Dialog 
          open={showEditCaboModal} 
          onClose={() => setShowEditCaboModal(false)}
          PaperProps={{
            sx: {
              background: 'rgba(255, 255, 255, 0.8)', // Fundo translúcido
              backdropFilter: 'blur(10px)',            // Efeito de vidro
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              boxShadow: '0 4px 30px rgba(0, 0, 0, 0.1)'
            }
          }}
        >
          <DialogTitle sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            Editar Cabo: {editingCabo?.nome}
          </DialogTitle>
          <DialogContent>
            <Box component="form" sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Nome"
                name="nome"
                value={editedCaboData.nome || ''}
                onChange={handleEditCaboChange}
                fullWidth
                variant="outlined"
                disabled
              />
              <TextField
                label="Coeficiente"
                name="coeficiente"
                type="number"
                inputProps={{ step: "0.01" }}
                value={editedCaboData.coeficiente || 0}
                onChange={handleEditCaboChange}
                fullWidth
                variant="outlined"
              />
              <TextField
                label="Preço (R$)"
                name="preco"
                type="number"
                inputProps={{ step: "0.01" }}
                value={editedCaboData.preco || 0}
                onChange={handleEditCaboChange}
                fullWidth
                variant="outlined"
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setShowEditCaboModal(false)} color="inherit">
              Cancelar
            </Button>
            <Button 
              onClick={handleUpdateCabo} 
              variant="contained" 
              disabled={updatingCabo}
              sx={{ 
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                color: 'white'
              }}
            >
              {updatingCabo ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Edit IP Modal - Glassmorphism Style */}
      {showEditIpModal && editingIp && (
        <Dialog 
          open={showEditIpModal} 
          onClose={() => setShowEditIpModal(false)}
          PaperProps={{
            sx: {
              background: 'rgba(255, 255, 255, 0.8)', // Fundo translúcido
              backdropFilter: 'blur(10px)',            // Efeito de vidro
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              boxShadow: '0 4px 30px rgba(0, 0, 0, 0.1)'
            }
          }}
        >
          <DialogTitle sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            Editar Iluminação Pública
          </DialogTitle>
          <DialogContent>
            <Box component="form" sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Nome / Tipo"
                name="nome"
                value={editedIpData.nome || ''}
                onChange={handleEditIpChange}
                fullWidth
                variant="outlined"
                disabled // Geralmente o nome/chave não se edita, manter lógica anterior
              />
              <TextField
                label="Potência (Watts)"
                name="potencia_watts"
                type="number"
                value={editedIpData.potencia_watts || 0}
                onChange={handleEditIpChange}
                fullWidth
                variant="outlined"
              />
              <TextField
                label="Preço (R$)"
                name="preco"
                type="number"
                value={editedIpData.preco || 0}
                onChange={handleEditIpChange}
                fullWidth
                variant="outlined"
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setShowEditIpModal(false)} color="inherit">
              Cancelar
            </Button>
            <Button 
              onClick={handleUpdateIp} 
              variant="contained" 
              disabled={updatingIp}
              sx={{ 
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                color: 'white'
              }}
            >
              {updatingIp ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Edit Trafo Modal - Glassmorphism Style */}
      {showEditTrafoModal && editingTrafo && (
        <Dialog 
          open={showEditTrafoModal} 
          onClose={() => setShowEditTrafoModal(false)}
          PaperProps={{
            sx: {
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px)',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              boxShadow: '0 4px 30px rgba(0, 0, 0, 0.1)'
            }
          }}
        >
          <DialogTitle sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            Editar Transformador
          </DialogTitle>
          <DialogContent>
            <Box component="form" sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
               {/* O ID ou KVA muitas vezes é a chave, verifique se deve ser disabled */}
              <TextField
                label="Potência (kVA)"
                name="kva"
                type="number"
                value={editedTrafoData.kva || 0}
                onChange={handleEditTrafoChange}
                fullWidth
                variant="outlined"
                disabled
              />
              {/* Se houver campo preço ou outro no Trafo, adicione aqui. 
                  Baseado no código anterior, geralmente só se edita o preço ou disponibilidade */}
               <TextField
                label="Preço (R$)`"
                name="preco" 
                type="number"
                value={editedTrafoData.preco || 0} // Assumindo que existe campo preço
                onChange={handleEditTrafoChange}
                fullWidth
                variant="outlined"
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setShowEditTrafoModal(false)} color="inherit">
              Cancelar
            </Button>
            <Button 
              onClick={handleUpdateTrafo} 
              variant="contained" 
              disabled={updatingTrafo}
              sx={{ 
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                color: 'white'
              }}
            >
              {updatingTrafo ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </DialogActions>
        </Dialog>
      )}

      {/* Edit Perfil Modal - Glassmorphism Style */}
      {showEditPerfilModal && editingPerfil && (
        <Dialog 
          open={showEditPerfilModal} 
          onClose={() => setShowEditPerfilModal(false)}
          PaperProps={{
            sx: {
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px)',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              boxShadow: '0 4px 30px rgba(0, 0, 0, 0.1)'
            }
          }}
        >
          <DialogTitle sx={{ fontWeight: 'bold', color: '#1976d2' }}>
            Editar Perfil de Configuração
          </DialogTitle>
          <DialogContent>
            <Box component="form" sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Nome do Perfil"
                name="nome"
                value={editedPerfilData.nome || ''}
                onChange={handleEditPerfilChange}
                fullWidth
                variant="outlined"
                disabled // Chave primária não editável
              />
              <TextField
                label="Queda de Tensão Máxima (%)"
                name="cqt_max"
                type="number"
                inputProps={{ step: "0.01" }}
                value={editedPerfilData.cqt_max || 0}
                onChange={handleEditPerfilChange}
                fullWidth
                variant="outlined"
              />
              <TextField
                label="Sobrecarga Máxima (%)"
                name="sobrecarga_max"
                type="number"
                inputProps={{ step: "0.01" }}
                value={editedPerfilData.sobrecarga_max || 0}
                onChange={handleEditPerfilChange}
                fullWidth
                variant="outlined"
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 2 }}>
            <Button onClick={() => setShowEditPerfilModal(false)} color="inherit">
              Cancelar
            </Button>
            <Button 
              onClick={handleUpdatePerfil} 
              variant="contained" 
              disabled={updatingPerfil}
              sx={{ 
                background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
                color: 'white'
              }}
            >
              {updatingPerfil ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
};

export default ConfigurationPage;