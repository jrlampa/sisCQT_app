import React, { useEffect, useState } from 'react'; // Import useEffect
import axios from 'axios';

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

interface TrechoTableProps {
  trechos: Trecho[];
  onSave: (updatedTrecho: Trecho) => void;
  projectId: number;
  nomeCenario: string;
  onAdd: (newTrecho: Trecho) => void;
  onRemove: (trechoId: number) => void;
  cqtResults: { [ponto: string]: number }; // Add cqtResults prop
}

const TrechoTable: React.FC<TrechoTableProps> = ({ trechos, onSave, projectId, nomeCenario, onAdd }) => {
  const [editRowId, setEditRowId] = useState<number | null>(null);
  const [editedData, setEditedData] = useState<Partial<Trecho>>({});
  const [cabosOptions, setCabosOptions] = useState<string[]>([]);
  const [ipsOptions, setIpsOptions] = useState<string[]>([]);

  // State for adding new trecho
  const [newTrechoData, setNewTrechoData] = useState<Partial<Trecho>>({
      ponto: '', montante: '', metros: 0, cabo: '', mono: 0, bi: 0, tri: 0, tri_esp: 0, carga_esp: 0, tipo_ip: '', qtd_ip: 0
  });
  const [addingNewTrecho, setAddingNewTrecho] = useState(false);

  useEffect(() => {
    const fetchConfigOptions = async () => {
      try {
        const [cabosRes, ipsRes] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_URL}/api/cabos/`),
          axios.get(`${import.meta.env.VITE_API_URL}/api/ips/`),
        ]);
        setCabosOptions(cabosRes.data.map((c: any) => c.nome));
        setIpsOptions(ipsRes.data.map((ip: any) => ip.nome));
      } catch (error) {
        console.error('Failed to fetch config options:', error);
      }
    };
    fetchConfigOptions();
  }, []);

  const handleEdit = (trecho: Trecho) => {
    setEditRowId(trecho.id);
    setEditedData(trecho);
  };

  const handleCancel = () => {
    setEditRowId(null);
    setEditedData({});
  };

  const handleSave = async () => {
    if (editRowId === null) return;
    try {
      // Ensure numeric fields are correctly parsed before sending
      const dataToSave = {
        ...editedData,
        metros: parseFloat(editedData.metros?.toString() || '0'),
        mono: parseInt(editedData.mono?.toString() || '0'),
        bi: parseInt(editedData.bi?.toString() || '0'),
        tri: parseInt(editedData.tri?.toString() || '0'),
        tri_esp: parseInt(editedData.tri_esp?.toString() || '0'),
        carga_esp: parseFloat(editedData.carga_esp?.toString() || '0'),
        qtd_ip: parseInt(editedData.qtd_ip?.toString() || '0'),
      };

      const response = await axios.put(`${import.meta.env.VITE_API_URL}/api/trechos/${editRowId}/`, dataToSave);
      onSave(response.data);
      setEditRowId(null);
      setEditedData({});
    } catch (error) {
      console.error('Failed to save trecho:', error);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>, field: keyof Trecho) => {
    const value = e.target.value;
    // Special handling for numeric fields
    if (['metros', 'mono', 'bi', 'tri', 'tri_esp', 'carga_esp', 'qtd_ip'].includes(field as string)) {
        setEditedData({ ...editedData, [field]: parseFloat(value) || 0 });
    } else {
        setEditedData({ ...editedData, [field]: value });
    }
  };

  const handleNewTrechoChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>, field: keyof Trecho) => {
    const value = e.target.value;
    if (['metros', 'mono', 'bi', 'tri', 'tri_esp', 'carga_esp', 'qtd_ip'].includes(field as string)) {
        setNewTrechoData(prevData => ({ ...prevData, [field]: parseFloat(value) || 0 }));
    } else {
        setNewTrechoData(prevData => ({ ...prevData, [field]: value }));
    }
  };

  const handleAddNewTrecho = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTrechoData.ponto || !newTrechoData.cabo) { // Basic validation
        alert('Ponto and Cabo are required for new trecho.');
        return;
    }
    setAddingNewTrecho(true);
    try {
        const dataToSave = {
            ...newTrechoData,
            projeto: projectId, // Passed as prop
            nome_cenario: nomeCenario, // Passed as prop
            metros: parseFloat(newTrechoData.metros?.toString() || '0'),
            mono: parseInt(newTrechoData.mono?.toString() || '0'),
            bi: parseInt(newTrechoData.bi?.toString() || '0'),
            tri: parseInt(newTrechoData.tri?.toString() || '0'),
            tri_esp: parseInt(newTrechoData.tri_esp?.toString() || '0'),
            carga_esp: parseFloat(newTrechoData.carga_esp?.toString() || '0'),
            qtd_ip: parseInt(newTrechoData.qtd_ip?.toString() || '0'),
        };

        const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/trechos/`, dataToSave);
        onAdd(response.data); // Notify parent component to update its trechos state
        // Reset form fields
        setNewTrechoData({ ponto: '', montante: '', metros: 0, cabo: '', mono: 0, bi: 0, tri: 0, tri_esp: 0, carga_esp: 0, tipo_ip: '', qtd_ip: 0 });
    } catch (error: any) {
        console.error('Failed to add new trecho:', error.response?.data || error.message);
        alert(`Failed to add new trecho: ${error.response?.data?.error || error.message}`);
    } finally {
        setAddingNewTrecho(false);
    }
  };

  const handleDeleteTrecho = async (trechoId: number) => {
      if (window.confirm('Are you sure you want to delete this trecho?')) {
          try {
              await axios.delete(`${import.meta.env.VITE_API_URL}/api/trechos/${trechoId}/`);
              onRemove(trechoId); // Notify parent component to update its trechos state
          } catch (error: any) {
              console.error('Failed to delete trecho:', error.response?.data || error.message);
              alert(`Failed to delete trecho: ${error.response?.data?.detail || error.message}`);
          }
      }
  };

  return (
    <table className="table table-bordered">
      <thead>
        <tr>
          <th>Ponto</th>
          <th>Montante</th>
          <th>Metros</th>
          <th>Cabo</th>
          <th>Mono</th>
          <th>Bi</th>
          <th>Tri</th>
          <th>Tri Esp</th>
          <th>Carga Esp</th>
          <th>Tipo IP</th>
          <th>Qtd IP</th>
          <th>CQT Acum. (%)</th> {/* New column */}
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {trechos.map((trecho) => (
          <tr key={trecho.id}>
            {editRowId === trecho.id ? (
              <>
                <td><input type="text" value={editedData.ponto || ''} onChange={(e) => handleChange(e, 'ponto')} className="form-control" /></td>
                <td><input type="text" value={editedData.montante || ''} onChange={(e) => handleChange(e, 'montante')} className="form-control" /></td>
                <td><input type="number" step="0.01" value={editedData.metros || 0} onChange={(e) => handleChange(e, 'metros')} className="form-control" /></td>
                <td>
                  <select value={editedData.cabo || ''} onChange={(e) => handleChange(e, 'cabo')} className="form-select">
                    <option value="">-- Selecione --</option>
                    {cabosOptions.map(option => <option key={option} value={option}>{option}</option>)}
                  </select>
                </td>
                <td><input type="number" step="1" value={editedData.mono || 0} onChange={(e) => handleChange(e, 'mono')} className="form-control" /></td>
                <td><input type="number" step="1" value={editedData.bi || 0} onChange={(e) => handleChange(e, 'bi')} className="form-control" /></td>
                <td><input type="number" step="1" value={editedData.tri || 0} onChange={(e) => handleChange(e, 'tri')} className="form-control" /></td>
                <td><input type="number" step="1" value={editedData.tri_esp || 0} onChange={(e) => handleChange(e, 'tri_esp')} className="form-control" /></td>
                <td><input type="number" step="0.01" value={editedData.carga_esp || 0} onChange={(e) => handleChange(e, 'carga_esp')} className="form-control" /></td>
                <td>
                  <select value={editedData.tipo_ip || ''} onChange={(e) => handleChange(e, 'tipo_ip')} className="form-select">
                    <option value="">-- Selecione --</option>
                    {ipsOptions.map(option => <option key={option} value={option}>{option}</option>)}
                  </select>
                </td>
                <td><input type="number" step="1" value={editedData.qtd_ip || 0} onChange={(e) => handleChange(e, 'qtd_ip')} className="form-control" /></td>
                <td>{(cqtResults[editedData.ponto || ''] || 0).toFixed(2)}</td> {/* Display CQT Acumulada */}
                <td>
                  <button className="btn btn-sm btn-success me-2" onClick={handleSave}>Salvar</button>
                  <button className="btn btn-sm btn-secondary" onClick={handleCancel}>Cancelar</button>
                </td>
              </>
            ) : (
              <>
                <td>{trecho.ponto}</td>
                <td>{trecho.montante}</td>
                <td>{trecho.metros}</td>
                <td>{trecho.cabo}</td>
                <td>{trecho.mono}</td>
                <td>{trecho.bi}</td>
                <td>{trecho.tri}</td>
                <td>{trecho.tri_esp}</td>
                <td>{trecho.carga_esp}</td>
                <td>{trecho.tipo_ip}</td>
                <td>{trecho.qtd_ip}</td>
                <td>{(cqtResults[trecho.ponto] || 0).toFixed(2)}</td> {/* Display CQT Acumulada */}
                <td>
                  <button className="btn btn-sm btn-primary me-2" onClick={() => handleEdit(trecho)}>Editar</button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDeleteTrecho(trecho.id)}>Deletar</button>
                </td>
              </>
            )}
          </tr>
        ))}
      </tbody>
    </table>
      <div className="mt-4 p-3 border rounded shadow-sm">
        <h5>Adicionar Novo Trecho</h5>
        <form onSubmit={handleAddNewTrecho}>
          <div className="row g-2">
            <div className="col-md-2">
              <input type="text" className="form-control" placeholder="Ponto" name="ponto" value={newTrechoData.ponto || ''} onChange={(e) => handleNewTrechoChange(e, 'ponto')} required />
            </div>
            <div className="col-md-2">
              <input type="text" className="form-control" placeholder="Montante" name="montante" value={newTrechoData.montante || ''} onChange={(e) => handleNewTrechoChange(e, 'montante')} />
            </div>
            <div className="col-md-1">
              <input type="number" step="0.01" className="form-control" placeholder="Metros" name="metros" value={newTrechoData.metros || 0} onChange={(e) => handleNewTrechoChange(e, 'metros')} />
            </div>
            <div className="col-md-2">
              <select className="form-select" name="cabo" value={newTrechoData.cabo || ''} onChange={(e) => handleNewTrechoChange(e, 'cabo')} required>
                <option value="">-- Cabo --</option>
                {cabosOptions.map(option => <option key={option} value={option}>{option}</option>)}
              </select>
            </div>
            <div className="col-md-1">
              <input type="number" step="1" className="form-control" placeholder="Mono" name="mono" value={newTrechoData.mono || 0} onChange={(e) => handleNewTrechoChange(e, 'mono')} />
            </div>
            <div className="col-md-1">
              <input type="number" step="1" className="form-control" placeholder="Bi" name="bi" value={newTrechoData.bi || 0} onChange={(e) => handleNewTrechoChange(e, 'bi')} />
            </div>
            <div className="col-md-1">
              <input type="number" step="1" className="form-control" placeholder="Tri" name="tri" value={newTrechoData.tri || 0} onChange={(e) => handleNewTrechoChange(e, 'tri')} />
            </div>
            <div className="col-md-1">
              <input type="number" step="1" className="form-control" placeholder="Tri Esp" name="tri_esp" value={newTrechoData.tri_esp || 0} onChange={(e) => handleNewTrechoChange(e, 'tri_esp')} />
            </div>
            <div className="col-md-1">
              <input type="number" step="0.01" className="form-control" placeholder="Carga Esp" name="carga_esp" value={newTrechoData.carga_esp || 0} onChange={(e) => handleNewTrechoChange(e, 'carga_esp')} />
            </div>
            <div className="col-md-2">
              <select className="form-select" name="tipo_ip" value={newTrechoData.tipo_ip || ''} onChange={(e) => handleNewTrechoChange(e, 'tipo_ip')}>
                <option value="">-- Tipo IP --</option>
                {ipsOptions.map(option => <option key={option} value={option}>{option}</option>)}
              </select>
            </div>
            <div className="col-md-1">
              <input type="number" step="1" className="form-control" placeholder="Qtd IP" name="qtd_ip" value={newTrechoData.qtd_ip || 0} onChange={(e) => handleNewTrechoChange(e, 'qtd_ip')} />
            </div>
            <div className="col-md-auto">
              <button type="submit" className="btn btn-success" disabled={addingNewTrecho}>
                {addingNewTrecho ? 'Adicionando...' : 'Adicionar'}
              </button>
            </div>
          </div>
        </form>
      </div>
  );
};

export default TrechoTable;
