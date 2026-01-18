import React from 'react';
import { NodeData } from '../tipos/tipos';

interface PainelDetalhesProps {
  selectedNode: NodeData | null;
}

const statusClasses = {
  ok: 'text-green-600 font-bold',
  attention: 'text-yellow-600 font-bold',
  critical: 'text-red-600 font-bold',
  neutral: 'text-gray-600',
};

const PainelDetalhes: React.FC<PainelDetalhesProps> = ({ selectedNode }) => {
  if (!selectedNode) {
    return (
      <div className="text-gray-600">
        Clique em um elemento no diagrama para ver os detalhes.
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <h3 className="text-lg font-bold mb-2">{selectedNode.label}</h3>
      <div className="text-sm">
        <p><strong>Tensão:</strong> {selectedNode.voltage} V</p>
        <p><strong>Corrente:</strong> {selectedNode.current} A</p>
        <p><strong>Potência:</strong> {selectedNode.power} W</p>
        <p><strong>Fator de Potência:</strong> {selectedNode.pf}</p>
        <p><strong>Tipo de Cabo:</strong> {selectedNode.cableType}</p>
        <p><strong>Seção do Cabo:</strong> {selectedNode.cableSection}</p>
        <p><strong>Método de Instalação:</strong> {selectedNode.installationMethod}</p>
        <p><strong>Dispositivo de Proteção:</strong> {selectedNode.protection}</p>
        <p>
          <strong>Status:</strong>{' '}
          <span className={statusClasses[selectedNode.status]}>
            {selectedNode.status.toUpperCase()}
          </span>
        </p>
        {/* Add more details as needed based on NodeData */}
      </div>
    </div>
  );
};

export default PainelDetalhes;
