import React, { useState } from 'react';

interface ProjectSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (settings: { temperature: number; resistivity: number }) => void;
  initialSettings: { temperature: number; resistivity: number };
}

const ProjectSettingsModal: React.FC<ProjectSettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialSettings,
}) => {
  const [temperature, setTemperature] = useState(initialSettings.temperature);
  const [resistivity, setResistivity] = useState(initialSettings.resistivity);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ temperature, resistivity });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-xl max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">Configurações do Projeto</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="temperature" className="block text-sm font-medium text-gray-700">
              Temperatura de Operação (°C)
            </label>
            <input
              type="number"
              id="temperature"
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 font-mono-numbers"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              step="0.1"
            />
          </div>
          <div className="mb-6">
            <label htmlFor="resistivity" className="block text-sm font-medium text-gray-700">
              Resistividade dos Condutores (Ω·mm²/m)
            </label>
            <input
              type="number"
              id="resistivity"
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 font-mono-numbers"
              value={resistivity}
              onChange={(e) => setResistivity(parseFloat(e.target.value))}
              step="0.000001" // Example step for resistivity
            />
          </div>
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Salvar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProjectSettingsModal;
