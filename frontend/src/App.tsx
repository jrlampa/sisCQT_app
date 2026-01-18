import React, { useState, useCallback } from 'react';
import DiagramaRede from './componentes/DiagramaRede';
import PainelDetalhes from './componentes/PainelDetalhes';
import TabelaRede from './componentes/TabelaRede';
import RelatorioTecnico from './vistas/RelatorioTecnico';
import VistaComparacao from './vistas/VistaComparacao';
import ProjectSettingsModal from './componentes/ProjectSettingsModal';
import { NetworkData, NodeData } from './tipos/tipos';
import { getNetworkData, useCalculoMutation } from './servicos/servicoEletrico';

// Define a type for the active view
type ActiveView = 'diagrama' | 'relatorio' | 'comparacao';

function App() {
  const [networkData, setNetworkData] = useState<NetworkData | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>('diagrama');
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [projectSettings, setProjectSettings] = useState({
    temperature: 30, // Default operating temperature
    resistivity: 0.0172 // Default copper resistivity (Ω·mm²/m)
  });

  const { isPending: calculoIsPending, triggerCalculation } = useCalculoMutation();

  // Mock results and active tab for RelatorioTecnico
  const mockResultados = {
    'Cálculo Cabos': [
      { circuito: 'C1', secao: '16mm²', queda_tensao: 3.5, corrente: 55 },
      { circuito: 'C2', secao: '35mm²', queda_tensao: 8.1, corrente: 110 },
    ],
    'Dados de Carga': [
      { carga: 'Motor 1', potencia: 15000, fp: 0.8 },
      { carga: 'Iluminação', potencia: 5000, fp: 0.95 },
    ]
  };
  const mockAbaAtiva = 'Cálculo Cabos';


  // Load initial network data on component mount
  React.useEffect(() => {
    const data = getNetworkData(); // This will initially be mock data
    setNetworkData(data);
  }, []);

  const handleNodeClick = useCallback((node: NodeData) => {
    setSelectedNode(node);
  }, []);

  const handleNodeChange = useCallback(async (updatedNode: NodeData) => {
    console.log('Node changed:', updatedNode);
    // Trigger recalculation on the backend
    try {
      const newNetworkData = await triggerCalculation({
        ...updatedNode,
        projectSettings // Pass current project settings to backend
      });
      setNetworkData(newNetworkData);
    } catch (error) {
      console.error("Error during recalculation:", error);
      // Handle error, e.g., show a toast notification
    }
  }, [triggerCalculation, projectSettings]);

  const handleSaveProjectSettings = useCallback(async (settings: { temperature: number; resistivity: number }) => {
    console.log('Saving project settings:', settings);
    setProjectSettings(settings);
    // Optionally trigger a full network recalculation with new settings
    try {
      const newNetworkData = await triggerCalculation({ projectSettings: settings });
      setNetworkData(newNetworkData);
    } catch (error) {
      console.error("Error applying new project settings:", error);
    }
  }, [triggerCalculation]);

  if (!networkData && !calculoIsPending) { // Show loading only initially or during a calculation
    return <div className="loading">Carregando dados da rede...</div>;
  }

  return (
    <div className="App flex flex-col h-screen">
      <header className="App-header bg-gray-800 text-white p-4 text-center flex items-center justify-between">
        <h1 className="text-xl font-bold">SisCQT - Diagrama Unifilar Elétrico</h1>
        <nav className="flex space-x-4">
          <button
            className={`px-3 py-1 rounded ${activeView === 'diagrama' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
            onClick={() => setActiveView('diagrama')}
          >
            Diagrama
          </button>
          <button
            className={`px-3 py-1 rounded ${activeView === 'relatorio' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
            onClick={() => setActiveView('relatorio')}
          >
            Relatório
          </button>
          <button
            className={`px-3 py-1 rounded ${activeView === 'comparacao' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
            onClick={() => setActiveView('comparacao')}
          >
            Comparação
          </button>
          <button
            className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600"
            onClick={() => setIsSettingsModalOpen(true)}
          >
            Configurações
          </button>
        </nav>
      </header>
      <main className="flex-grow flex">
        {activeView === 'diagrama' && (
          <>
            <div className="flex-grow relative border-r border-gray-700">
              {calculoIsPending && <div className="absolute inset-0 bg-white bg-opacity-70 flex items-center justify-center z-10">
                <span className="text-blue-500 text-lg">Recalculando Rede...</span>
              </div>}
              {networkData && (
                <DiagramaRede
                  networkData={networkData}
                  onNodeClick={handleNodeClick}
                  onNodeChange={handleNodeChange}
                />
              )}
            </div>
            <aside className="w-1/4 bg-gray-100 p-4 overflow-y-auto">
              <h2 className="text-lg font-bold mb-4">Detalhes do Elemento</h2>
              <PainelDetalhes selectedNode={selectedNode} />
            </aside>
          </>
        )}

        {activeView === 'relatorio' && (
          <div className="flex-grow p-4">
            <RelatorioTecnico
              networkData={networkData}
              resultados={mockResultados}
              abaAtiva={mockAbaAtiva}
            />
          </div>
        )}

        {activeView === 'comparacao' && (
          <div className="flex-grow p-4">
            <VistaComparacao />
          </div>
        )}
      </main>
      <footer className="bg-gray-800 text-white p-2 text-center text-sm">
        {calculoIsPending ? (
          <div className="skeleton h-4 w-1/4 mx-auto"></div>
        ) : (
          <TabelaRede networkData={networkData || { nodes: [], edges: [] }} />
        )}
      </footer>

      <ProjectSettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        onSave={handleSaveProjectSettings}
        initialSettings={projectSettings}
      />
    </div>
  );
}

export default App;
