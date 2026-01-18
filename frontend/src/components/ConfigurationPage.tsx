import React, { useEffect, useState } from 'react';
import axios from 'axios';

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
        axios.get('http://127.0.0.1:8000/api/cabos/'),
        axios.get('http://127.0.0.1:8000/api/ips/'),
        axios.get('http://127.0.0.1:8000/api/trafos/'),
        axios.get('http://127.0.0.1:8000/api/perfis/'),
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
      await axios.post(`http://127.0.0.1:8000/api/${endpoint}/`, data);
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
        await axios.delete(`http://127.0.0.1:8000/api/${endpoint}/${id}/`);
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
      await axios.put(`http://127.0.0.1:8000/api/cabos/${editingCabo.nome}/`, editedCaboData);
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
      await axios.put(`http://127.0.0.1:8000/api/ips/${editingIp.nome}/`, editedIpData);
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
      await axios.put(`http://127.0.0.1:8000/api/trafos/${editingTrafo.kva}/`, editedTrafoData);
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
      await axios.put(`http://127.0.0.1:8000/api/perfis/${editingPerfil.nome}/`, editedPerfilData);
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
    return <div className="text-center mt-5">Loading configurations...</div>;
  }

  return (
    <div className="container mt-5">
      <h1>Configurações</h1>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'cabos' ? 'active' : ''}`}
            onClick={() => setActiveTab('cabos')}
          >
            Cabos
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'ips' ? 'active' : ''}`}
            onClick={() => setActiveTab('ips')}
          >
            IPs
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'trafos' ? 'active' : ''}`}
            onClick={() => setActiveTab('trafos')}
          >
            Trafos
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'perfis' ? 'active' : ''}`}
            onClick={() => setActiveTab('perfis')}
          >
            Perfis
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'simulation' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulation')}
          >
            Simulação
          </button>
        </li>
      </ul>

      {activeTab === 'cabos' && (
        <div className="mt-4">
          <h2>Cabos</h2>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('cabos', newCabo, () => setNewCabo({ nome: '', coeficiente: 0, preco: 0 })) }} className="mb-3">
              <div className="row g-3">
                  <div className="col"><input type="text" name="nome" value={newCabo.nome} onChange={(e) => setNewCabo({...newCabo, nome: e.target.value})} className="form-control" placeholder="Nome" required /></div>
                  <div className="col"><input type="number" step="0.01" name="coeficiente" value={newCabo.coeficiente} onChange={(e) => setNewCabo({...newCabo, coeficiente: parseFloat(e.target.value)})} className="form-control" placeholder="Coeficiente" required /></div>
                  <div className="col"><input type="number" step="0.01" name="preco" value={newCabo.preco} onChange={(e) => setNewCabo({...newCabo, preco: parseFloat(e.target.value)})} className="form-control" placeholder="Preço" required /></div>
                  <div className="col-auto"><button type="submit" className="btn btn-primary">Adicionar</button></div>
              </div>
          </form>
          <table className="table">
            <thead><tr><th>Nome</th><th>Coeficiente</th><th>Preço</th><th>Ações</th></tr></thead>
            <tbody>{cabos.map((cabo) => (<tr key={cabo.nome}><td>{cabo.nome}</td><td>{cabo.coeficiente}</td><td>{cabo.preco}</td><td>
              <button className="btn btn-sm btn-info me-2" onClick={() => openEditCaboModal(cabo)}>Editar</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete('cabos', cabo.nome)}>Deletar</button>
            </td></tr>))}</tbody>
          </table>
        </div>
      )}

      {activeTab === 'ips' && (
        <div className="mt-4">
          <h2>IPs</h2>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('ips', newIp, () => setNewIp({ nome: '', potencia_watts: 0, preco: 0 })) }} className="mb-3">
              <div className="row g-3">
                  <div className="col"><input type="text" name="nome" value={newIp.nome} onChange={(e) => setNewIp({...newIp, nome: e.target.value})} className="form-control" placeholder="Nome" required /></div>
                  <div className="col"><input type="number" step="0.01" name="potencia_watts" value={newIp.potencia_watts} onChange={(e) => setNewIp({...newIp, potencia_watts: parseFloat(e.target.value)})} className="form-control" placeholder="Potência (W)" required /></div>
                  <div className="col"><input type="number" step="0.01" name="preco" value={newIp.preco} onChange={(e) => setNewIp({...newIp, preco: parseFloat(e.target.value)})} className="form-control" placeholder="Preço" required /></div>
                  <div className="col-auto"><button type="submit" className="btn btn-primary">Adicionar</button></div>
              </div>
          </form>
          <table className="table">
            <thead><tr><th>Nome</th><th>Potência (Watts)</th><th>Preço</th><th>Ações</th></tr></thead>
            <tbody>{ips.map((ip) => (<tr key={ip.nome}><td>{ip.nome}</td><td>{ip.potencia_watts}</td><td>{ip.preco}</td><td>
              <button className="btn btn-sm btn-info me-2" onClick={() => openEditIpModal(ip)}>Editar</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete('ips', ip.nome)}>Deletar</button>
            </td></tr>))}</tbody>
          </table>
        </div>
      )}

      {activeTab === 'trafos' && (
        <div className="mt-4">
          <h2>Trafos</h2>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('trafos', newTrafo, () => setNewTrafo({ kva: 0 })) }} className="mb-3">
              <div className="row g-3">
                  <div className="col"><input type="number" step="0.01" name="kva" value={newTrafo.kva} onChange={(e) => setNewTrafo({ kva: parseFloat(e.target.value) })} className="form-control" placeholder="KVA" required /></div>
                  <div className="col-auto"><button type="submit" className="btn btn-primary">Adicionar</button></div>
              </div>
          </form>
          <table className="table">
            <thead><tr><th>KVA</th><th>Ações</th></tr></thead>
            <tbody>{trafos.map((trafo) => (<tr key={trafo.kva}><td>{trafo.kva}</td><td>
              <button className="btn btn-sm btn-info me-2" onClick={() => openEditTrafoModal(trafo)}>Editar</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete('trafos', trafo.kva)}>Deletar</button>
            </td></tr>))}</tbody>
          </table>
        </div>
      )}

      {activeTab === 'perfis' && (
        <div className="mt-4">
          <h2>Perfis</h2>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate('perfis', newPerfil, () => setNewPerfil({ nome: '', cqt_max: 0, sobrecarga_max: 0 })) }} className="mb-3">
              <div className="row g-3">
                  <div className="col"><input type="text" name="nome" value={newPerfil.nome} onChange={(e) => setNewPerfil({...newPerfil, nome: e.target.value})} className="form-control" placeholder="Nome" required /></div>
                  <div className="col"><input type="number" step="0.01" name="cqt_max" value={newPerfil.cqt_max} onChange={(e) => setNewPerfil({...newPerfil, cqt_max: parseFloat(e.target.value)})} className="form-control" placeholder="CQT Máx" required /></div>
                  <div className="col"><input type="number" step="0.01" name="sobrecarga_max" value={newPerfil.sobrecarga_max} onChange={(e) => setNewPerfil({...newPerfil, sobrecarga_max: parseFloat(e.target.value)})} className="form-control" placeholder="Sobrecarga Máx" required /></div>
                  <div className="col-auto"><button type="submit" className="btn btn-primary">Adicionar</button></div>
              </div>
          </form>
          <table className="table">
            <thead><tr><th>Nome</th><th>CQT Máx</th><th>Sobrecarga Máx</th><th>Ações</th></tr></thead>
            <tbody>{perfis.map((perfil) => (<tr key={perfil.nome}><td>{perfil.nome}</td><td>{perfil.cqt_max}</td><td>{perfil.sobrecarga_max}</td><td>
              <button className="btn btn-sm btn-info me-2" onClick={() => openEditPerfilModal(perfil)}>Editar</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete('perfis', perfil.nome)}>Deletar</button>
            </td></tr>))}</tbody>
          </table>
        </div>
      )}

      {activeTab === 'simulation' && (
        <div className="mt-4">
          <h2>Configuração de Simulação</h2>
          <div className="mb-3">
            <label htmlFor="simulationCables" className="form-label">Cabos Habilitados para Simulação</label>
            <select
              multiple
              className="form-select"
              id="simulationCables"
              value={simulationCables}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setSimulationCables(Array.from(e.target.selectedOptions, option => option.value))
              }
              style={{ minHeight: '150px' }}
            >
              {cabos.map(cabo => (
                <option key={cabo.nome} value={cabo.nome}>
                  {cabo.nome}
                </option>
              ))}
            </select>
            <div className="form-text">Selecione os cabos que o simulador pode utilizar para readequação.</div>
          </div>
          <button className="btn btn-primary">Salvar Configuração de Simulação</button>
        </div>
      )}

      {/***** Edit CfgCabo Modal *****/}
      {showEditCaboModal && editingCabo && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Editar Cabo: {editingCabo.nome}</h5>
                <button type="button" className="btn-close" onClick={() => setShowEditCaboModal(false)}></button>
              </div>
              <form onSubmit={handleUpdateCabo}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="editCaboNome" className="form-label">Nome</label>
                    <input type="text" className="form-control" id="editCaboNome" name="nome" value={editedCaboData.nome || ''} onChange={handleEditCaboChange} required disabled />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editCaboCoeficiente" className="form-label">Coeficiente</label>
                    <input type="number" step="0.01" className="form-control" id="editCaboCoeficiente" name="coeficiente" value={editedCaboData.coeficiente || 0} onChange={handleEditCaboChange} required />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editCaboPreco" className="form-label">Preço</label>
                    <input type="number" step="0.01" className="form-control" id="editCaboPreco" name="preco" value={editedCaboData.preco || 0} onChange={handleEditCaboChange} required />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowEditCaboModal(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary" disabled={updatingCabo}>
                    {updatingCabo ? 'Salvando...' : 'Salvar Alterações'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/***** Edit CfgIP Modal *****/}
      {showEditIpModal && editingIp && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Editar IP: {editingIp.nome}</h5>
                <button type="button" className="btn-close" onClick={() => setShowEditIpModal(false)}></button>
              </div>
              <form onSubmit={handleUpdateIp}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="editIpNome" className="form-label">Nome</label>
                    <input type="text" className="form-control" id="editIpNome" name="nome" value={editedIpData.nome || ''} onChange={handleEditIpChange} required disabled />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editIpPotenciaWatts" className="form-label">Potência (Watts)</label>
                    <input type="number" step="0.01" className="form-control" id="editIpPotenciaWatts" name="potencia_watts" value={editedIpData.potencia_watts || 0} onChange={handleEditIpChange} required />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editIpPreco" className="form-label">Preço</label>
                    <input type="number" step="0.01" className="form-control" id="editIpPreco" name="preco" value={editedIpData.preco || 0} onChange={handleEditIpChange} required />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowEditIpModal(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary" disabled={updatingIp}>
                    {updatingIp ? 'Salvando...' : 'Salvar Alterações'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/***** Edit CfgTrafo Modal *****/}
      {showEditTrafoModal && editingTrafo && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Editar Trafo: {editingTrafo.kva} kVA</h5>
                <button type="button" className="btn-close" onClick={() => setShowEditTrafoModal(false)}></button>
              </div>
              <form onSubmit={handleUpdateTrafo}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="editTrafoKva" className="form-label">KVA</label>
                    <input type="number" step="0.01" className="form-control" id="editTrafoKva" name="kva" value={editedTrafoData.kva || 0} onChange={handleEditTrafoChange} required />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowEditTrafoModal(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary" disabled={updatingTrafo}>
                    {updatingTrafo ? 'Salvando...' : 'Salvar Alterações'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/***** Edit CfgPerfil Modal *****/}
      {showEditPerfilModal && editingPerfil && (
        <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Editar Perfil: {editingPerfil.nome}</h5>
                <button type="button" className="btn-close" onClick={() => setShowEditPerfilModal(false)}></button>
              </div>
              <form onSubmit={handleUpdatePerfil}>
                <div className="modal-body">
                  <div className="mb-3">
                    <label htmlFor="editPerfilNome" className="form-label">Nome</label>
                    <input type="text" className="form-control" id="editPerfilNome" name="nome" value={editedPerfilData.nome || ''} onChange={handleEditPerfilChange} required disabled />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editPerfilCqtMax" className="form-label">CQT Máx</label>
                    <input type="number" step="0.01" className="form-control" id="editPerfilCqtMax" name="cqt_max" value={editedPerfilData.cqt_max || 0} onChange={handleEditPerfilChange} required />
                  </div>
                  <div className="mb-3">
                    <label htmlFor="editPerfilSobrecargaMax" className="form-label">Sobrecarga Máx</label>
                    <input type="number" step="0.01" className="form-control" id="editPerfilSobrecargaMax" name="sobrecarga_max" value={editedPerfilData.sobrecarga_max || 0} onChange={handleEditPerfilChange} required />
                  </div>
                </div>
                <div className="modal-footer">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowEditPerfilModal(false)}>Cancelar</button>
                  <button type="submit" className="btn btn-primary" disabled={updatingPerfil}>
                    {updatingPerfil ? 'Salvando...' : 'Salvar Alterações'}
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

export default ConfigurationPage;