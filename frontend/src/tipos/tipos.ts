import { Node, Edge } from 'reactflow';

export type NodeStatus = 'ok' | 'attention' | 'critical' | 'neutral';
export type NodeType = 'source' | 'load' | 'default'; // 'default' for QGBT, QD, etc.

export interface NodeData {
  label: string;
  voltage: number; // Tensão (V)
  current: number; // Corrente (A)
  power: number; // Potência (W)
  pf: number; // Fator de Potência
  cableType: string; // Tipo de Cabo
  cableSection: string; // Seção do Cabo (mm²)
  installationMethod: string; // Método de Instalação
  protection: string; // Dispositivo de Proteção
  status: NodeStatus; // Estado visual do nó
}

export interface EdgeData {
  label: string;
  length: number; // Comprimento do cabo (m)
  voltageDrop: number; // Queda de tensão (%)
  designCurrent: number; // Corrente de projeto (A)
  status: NodeStatus; // Estado visual da aresta
}

// Extend ReactFlow's Node and Edge types with our custom data
export type RFNode = Node<NodeData>;
export type RFEdge = Edge<EdgeData>;

export interface NetworkData {
  nodes: RFNode[];
  edges: RFEdge[];
}

export interface DetailedNodeInfo extends NodeData {
  id: string;
  type: NodeType;
  // Add any other detailed info that comes from the backend
}

export interface CircuitData {
  name: string;
  voltage: number;
  current: number;
  power: number;
  pf: number;
  cableType: string;
  cableSection: string;
  installationMethod: string;
  protection: string;
  cableLength: number;
  voltageDrop: number;
  designCurrent: number;
  thermalVerification: NodeStatus; // ok, attention, critical
  status: NodeStatus;
}
