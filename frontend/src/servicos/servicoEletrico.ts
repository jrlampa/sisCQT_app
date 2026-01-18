import { NetworkData, NodeData, EdgeData } from '../tipos/tipos';
import { useState, useCallback } from 'react';

// Mock function to simulate fetching network data from a backend
export const getNetworkData = (): NetworkData => {
  // In a real application, this would make an API call to your Python backend
  // For now, we return mock data
  const nodes: NodeData[] = [
    { id: '1', type: 'source', position: { x: 0, y: 0 }, data: { label: 'Concessionária', voltage: 13800, current: 0, power: 0, pf: 0, cableType: '', cableSection: '', installationMethod: '', protection: '', status: 'ok' } },
    { id: '2', type: 'default', position: { x: 0, y: 100 }, data: { label: 'QGBT-1', voltage: 380, current: 150, power: 90000, pf: 0.9, cableType: 'XLPE', cableSection: '95mm²', installationMethod: 'B1', protection: 'Disjuntor 200A', status: 'ok' } },
    { id: '3', type: 'load', position: { x: 200, y: 150 }, data: { label: 'Carga 1', voltage: 380, current: 50, power: 30000, pf: 0.85, cableType: 'XLPE', cableSection: '16mm²', installationMethod: 'B1', protection: 'Disjuntor 63A', status: 'attention' } },
    { id: '4', type: 'load', position: { x: 200, y: 250 }, data: { label: 'Carga 2', voltage: 380, current: 100, power: 60000, pf: 0.92, cableType: 'EPR', cableSection: '35mm²', installationMethod: 'C', protection: 'Disjuntor 125A', status: 'critical' } },
  ];

  const edges: EdgeData[] = [
    { id: 'e1-2', source: '1', target: '2', data: { label: 'Alimentador Principal', length: 50, voltageDrop: 1.2, designCurrent: 180, status: 'ok' } },
    { id: 'e2-3', source: '2', target: '3', data: { label: 'Circuito 1', length: 20, voltageDrop: 3.5, designCurrent: 55, status: 'attention' } },
    { id: 'e2-4', source: '2', target: '4', data: { label: 'Circuito 2', length: 30, voltageDrop: 8.1, designCurrent: 110, status: 'critical' } },
  ];

  return { nodes, edges };
};

// Mock function to simulate sending node changes to the backend for recalculation
export const updateNodeAndRecalculate = async (nodeId: string, newData: Partial<NodeData['data']>): Promise<NetworkData> => {
  console.log(`Simulating update for node ${nodeId} with data:`, newData);
  // In a real application, this would be an API call (e.g., POST /api/nodes/:id)
  // For demonstration, we'll just return the current mock data
  return new Promise(resolve => setTimeout(() => resolve(getNetworkData()), 500));
};

// Mock hook to simulate a calculation mutation with loading state
export const useCalculoMutation = () => {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const triggerCalculation = useCallback(async (params: any) => {
    setIsPending(true);
    setError(null);
    try {
      console.log('Simulating backend calculation with params:', params);
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate API call
      // In a real app, you'd make an actual API call here
      // const response = await fetch('/api/calculate', { method: 'POST', body: JSON.stringify(params) });
      // if (!response.ok) throw new Error('Calculation failed');
      // const data = await response.json();
      // return data; // Return calculated data
      return getNetworkData(); // For mock, just return the network data
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setIsPending(false);
    }
  }, []);

  return { isPending, error, triggerCalculation };
};

