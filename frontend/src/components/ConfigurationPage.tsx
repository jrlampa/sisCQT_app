import React, { useEffect, useState } from 'react';
import axios from 'axios';

const ConfigurationPage: React.FC = () => {
  const [cabos, setCabos] = useState<any[]>([]);
  const [ips, setIps] = useState<any[]>([]);
  const [trafos, setTrafos] = useState<any[]>([]);
  const [perfis, setPerfis] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  
  const [newCabo, setNewCabo] = useState({ nome: '', coeficiente: 0, preco: 0 });
  const [newIp, setNewIp] = useState({ nome: '', potencia_watts: 0, preco: 0 });
  const [newTrafo, setNewTrafo] = useState({ kva: 0 });
  const [newPerfil, setNewPerfil] = useState({ nome: '', cqt_max: 0, sobrecarga_max: 0 });

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
    } catch (error) {
      console.error(`Failed to create ${endpoint}:`, error);
    }
  };
  
  const handleDelete = async (endpoint: string, id: string | number) => {
    try {
      await axios.delete(`http://127.0.0.1:8000/api/${endpoint}/${id}/`);
      fetchAllConfigs();
    } catch (error) {
      console.error(`Failed to delete ${endpoint}:`, error);
    }
  };

  if (loading) {
    return <div className="text-center mt-5">Loading configurations...</div>;
  }

  return (
    <div className="container mt-5">
      <h1>Configurações</h1>

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
          <tbody>{cabos.map((cabo) => (<tr key={cabo.nome}><td>{cabo.nome}</td><td>{cabo.coeficiente}</td><td>{cabo.preco}</td><td><button className="btn btn-sm btn-danger" onClick={() => handleDelete('cabos', cabo.nome)}>Deletar</button></td></tr>))}</tbody>
        </table>
      </div>

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
          <tbody>{ips.map((ip) => (<tr key={ip.nome}><td>{ip.nome}</td><td>{ip.potencia_watts}</td><td>{ip.preco}</td><td><button className="btn btn-sm btn-danger" onClick={() => handleDelete('ips', ip.nome)}>Deletar</button></td></tr>))}</tbody>
        </table>
      </div>

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
          <tbody>{trafos.map((trafo) => (<tr key={trafo.kva}><td>{trafo.kva}</td><td><button className="btn btn-sm btn-danger" onClick={() => handleDelete('trafos', trafo.kva)}>Deletar</button></td></tr>))}</tbody>
        </table>
      </div>

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
          <tbody>{perfis.map((perfil) => (<tr key={perfil.nome}><td>{perfil.nome}</td><td>{perfil.cqt_max}</td><td>{perfil.sobrecarga_max}</td><td><button className="btn btn-sm btn-danger" onClick={() => handleDelete('perfis', perfil.nome)}>Deletar</button></td></tr>))}</tbody>
        </table>
      </div>
    </div>
  );
};

export default ConfigurationPage;
