import React, { useState } from 'react';
import { NetworkData, RFNode, RFEdge } from '../tipos/tipos';
import { useCalculoMutation } from '../servicos/servicoEletrico';
// Assuming useDadosProjetoStore is a custom hook to access project data/scenarios
// import { useDadosProjetoStore } from '../store/useDadosProjetoStore';

interface VistaComparacaoProps {
  // Placeholder for project data store, needs to be implemented
  // projectScenarios: { id: string; name: string; data: NetworkData }[];
}

const renderNetworkSummary = (scenario: NetworkData | null, title: string, isPending: boolean) => {
  if (isPending) {
    return (
      <div className="flex-1 p-4 border rounded-lg shadow-sm">
        <div className="skeleton h-6 w-3/4 mb-4"></div>
        <div className="space-y-2">
          <div className="skeleton h-4 w-full"></div>
          <div className="skeleton h-4 w-5/6"></div>
          <div className="skeleton h-4 w-full"></div>
        </div>
      </div>
    );
  }

  if (!scenario) {
    return (
      <div className="flex-1 p-4 border rounded-lg shadow-sm text-gray-500">
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p>Nenhum cenário selecionado.</p>
      </div>
    );
  }

  const totalVoltageDrop = scenario.edges.reduce((sum, edge) => sum + (edge.data?.voltageDrop || 0), 0);
  const maxVoltageDrop = Math.max(...scenario.edges.map(e => e.data?.voltageDrop || 0));

  return (
    <div className="flex-1 p-4 border rounded-lg shadow-sm bg-white">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p>Total de Nós: <span className="font-mono-numbers">{scenario.nodes.length}</span></p>
      <p>Total de Arestas: <span className="font-mono-numbers">{scenario.edges.length}</span></p>
      <p>Queda de Tensão Total: <span className="font-mono-numbers">{totalVoltageDrop.toFixed(2)}%</span></p>
      <p>Maior Queda de Tensão: <span className="font-mono-numbers">{maxVoltageDrop.toFixed(2)}%</span></p>
      {/* Add more relevant KPIs here */}
    </div>
  );
};

const VistaComparacao: React.FC<VistaComparacaoProps> = () => {
  const [scenarioA, setScenarioA] = useState<NetworkData | null>(null);
  const [scenarioB, setScenarioB] = useState<NetworkData | null>(null);
  const { isPending: isCalculating } = useCalculoMutation(); // Mock loading state

  // Mock project scenarios for demonstration
  const mockScenarios = [
    {
      id: 'sc1', name: 'Cenário Base',
      data: {
        nodes: [{ id: '1', type: 'source', position: { x: 0, y: 0 }, data: { label: 'Concessionária', voltage: 13800, current: 0, power: 0, pf: 0, cableType: '', cableSection: '', installationMethod: '', protection: '', status: 'ok' } }, { id: '2', type: 'default', position: { x: 0, y: 100 }, data: { label: 'QGBT-1', voltage: 380, current: 150, power: 90000, pf: 0.9, cableType: 'XLPE', cableSection: '95mm²', installationMethod: 'B1', protection: 'Disjuntor 200A', status: 'ok' } }],
        edges: [{ id: 'e1-2', source: '1', target: '2', data: { label: 'Alimentador Principal', length: 50, voltageDrop: 1.2, designCurrent: 180, status: 'ok' } }]
      }
    },
    {
      id: 'sc2', name: 'Cenário com Cabo Otimizado',
      data: {
        nodes: [{ id: '1', type: 'source', position: { x: 0, y: 0 }, data: { label: 'Concessionária', voltage: 13800, current: 0, power: 0, pf: 0, cableType: '', cableSection: '', installationMethod: '', protection: '', status: 'ok' } }, { id: '2', type: 'default', position: { x: 0, y: 100 }, data: { label: 'QGBT-1', voltage: 380, current: 150, power: 90000, pf: 0.9, cableType: 'XLPE', cableSection: '120mm²', installationMethod: 'B1', protection: 'Disjuntor 200A', status: 'ok' } }],
        edges: [{ id: 'e1-2', source: '1', target: '2', data: { label: 'Alimentador Principal', length: 50, voltageDrop: 0.8, designCurrent: 180, status: 'ok' } }]
      }
    },
    // More scenarios from useDadosProjetoStore
  ];


  // Function to compare and highlight differences
  const compareValue = (valueA: number, valueB: number, isLowerBetter: boolean = true) => {
    if (valueA === valueB) {
      return <span className="font-mono-numbers">{valueA.toFixed(2)}</span>;
    } else if (isLowerBetter) {
      return valueB < valueA ? <span className="text-green-600 font-bold font-mono-numbers">{valueB.toFixed(2)} ↓</span> : <span className="text-red-600 font-bold font-mono-numbers">{valueB.toFixed(2)} ↑</span>;
    } else { // Higher is better
      return valueB > valueA ? <span className="text-green-600 font-bold font-mono-numbers">{valueB.toFixed(2)} ↑</span> : <span className="text-red-600 font-bold font-mono-numbers">{valueB.toFixed(2)} ↓</span>;
    }
  };

  const currentVoltageDropA = scenarioA?.edges.reduce((sum, edge) => sum + (edge.data?.voltageDrop || 0), 0) || 0;
  const currentVoltageDropB = scenarioB?.edges.reduce((sum, edge) => sum + (edge.data?.voltageDrop || 0), 0) || 0;

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Comparação de Cenários</h2>

      <div className="flex space-x-4 mb-6">
        <div className="flex-1">
          <label htmlFor="scenarioA" className="block text-sm font-medium text-gray-700">Cenário A</label>
          <select
            id="scenarioA"
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            onChange={(e) => setScenarioA(mockScenarios.find(s => s.id === e.target.value)?.data || null)}
          >
            <option value="">Selecione um cenário</option>
            {mockScenarios.map(sc => (
              <option key={sc.id} value={sc.id}>{sc.name}</option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label htmlFor="scenarioB" className="block text-sm font-medium text-gray-700">Cenário B</label>
          <select
            id="scenarioB"
            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            onChange={(e) => setScenarioB(mockScenarios.find(s => s.id === e.target.value)?.data || null)}
          >
            <option value="">Selecione um cenário</option>
            {mockScenarios.map(sc => (
              <option key={sc.id} value={sc.id}>{sc.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex space-x-4">
        {renderNetworkSummary(scenarioA, 'Resumo Cenário A', isCalculating)}
        {renderNetworkSummary(scenarioB, 'Resumo Cenário B', isCalculating)}
      </div>

      {(scenarioA && scenarioB && !isCalculating) && (
        <div className="mt-8 border-t pt-6">
          <h3 className="text-xl font-semibold mb-4">Diferenças Chave</h3>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Métrica</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cenário A</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cenário B</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Queda de Tensão Total</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono-numbers">{currentVoltageDropA.toFixed(2)}%</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{compareValue(currentVoltageDropA, currentVoltageDropB, true)}%</td>
              </tr>
              {/* Add more comparable metrics */}
              <tr>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Total de Nós</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono-numbers">{scenarioA.nodes.length}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">{compareValue(scenarioA.nodes.length, scenarioB.nodes.length, false)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default VistaComparacao;
