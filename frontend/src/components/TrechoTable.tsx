import React, { useState } from 'react';
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
}

const TrechoTable: React.FC<TrechoTableProps> = ({ trechos, onSave }) => {
  const [editRowId, setEditRowId] = useState<number | null>(null);
  const [editedData, setEditedData] = useState<Partial<Trecho>>({});

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
      const response = await axios.put(`http://127.0.0.1:8000/api/trechos/${editRowId}/`, editedData);
      onSave(response.data);
      setEditRowId(null);
      setEditedData({});
    } catch (error) {
      console.error('Failed to save trecho:', error);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, field: keyof Trecho) => {
    setEditedData({ ...editedData, [field]: e.target.value });
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
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {trechos.map((trecho) => (
          <tr key={trecho.id}>
            {editRowId === trecho.id ? (
              <>
                <td><input type="text" value={editedData.ponto || ''} onChange={(e) => handleChange(e, 'ponto')} /></td>
                <td><input type="text" value={editedData.montante || ''} onChange={(e) => handleChange(e, 'montante')} /></td>
                <td><input type="number" value={editedData.metros || 0} onChange={(e) => handleChange(e, 'metros')} /></td>
                <td><input type="text" value={editedData.cabo || ''} onChange={(e) => handleChange(e, 'cabo')} /></td>
                <td><input type="number" value={editedData.mono || 0} onChange={(e) => handleChange(e, 'mono')} /></td>
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
                <td>
                  <button className="btn btn-sm btn-primary" onClick={() => handleEdit(trecho)}>Editar</button>
                </td>
              </>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default TrechoTable;
