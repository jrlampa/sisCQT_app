import React, { useCallback } from 'react';
import ReactFlow, {
  Controls,
  Background,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
  Connection,
  addEdge,
  useReactFlow,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NetworkData, RFNode, RFEdge, NodeData, EdgeData } from '../tipos/tipos';
import { updateNodeAndRecalculate } from '../servicos/servicoEletrico';
import { Zap, Box, Circle } from 'lucide-react'; // Import icons from lucide-react

// Custom Node Component
const CustomNode: React.FC<{ data: NodeData; type: string }> = ({ data, type }) => {
  const Icon = type === 'source' ? Zap : type === 'default' ? Box : Circle;
  const statusClasses = {
    ok: 'border-green-500 bg-green-100',
    attention: 'border-yellow-500 bg-yellow-100',
    critical: 'border-red-500 bg-red-100',
    neutral: 'border-gray-400 bg-gray-50',
  };

  return (
    <div className={`custom-node ${statusClasses[data.status]} p-2 rounded-md shadow-md text-sm relative group`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-gray-500" />
      <div className="flex items-center space-x-2">
        <Icon size={16} />
        <div className="font-semibold">{data.label}</div>
      </div>
      {/* Tooltip for Nodes */}
      <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 p-2 bg-gray-800 text-white text-xs rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-300 z-50">
        <p>I: <span className="font-mono-numbers">{data.current.toFixed(2)}</span> A</p>
        {data.voltageDrop !== undefined && <p>ΔV%: <span className="font-mono-numbers">{data.voltageDrop.toFixed(2)}</span>%</p>}
        {/* Add more details here if needed */}
      </div>
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-gray-500" />
    </div>
  );
};

// Custom Edge Component (for tooltips)
const CustomEdge: React.FC<{ id: string; sourceX: number; sourceY: number; targetX: number; targetY: number; data: EdgeData }> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
}) => {
  const foreignObjectSize = 40; // Adjust based on tooltip content size
  const x = Math.min(sourceX, targetX) + Math.abs(targetX - sourceX) / 2 - foreignObjectSize / 2;
  const y = Math.min(sourceY, targetY) + Math.abs(targetY - sourceY) / 2 - foreignObjectSize / 2;

  const statusClasses = {
    ok: 'stroke-green-500',
    attention: 'stroke-yellow-500',
    critical: 'stroke-red-500',
    neutral: 'stroke-gray-400',
  };

  return (
    <>
      <path
        id={id}
        className={`react-flow__edge-path ${statusClasses[data.status]} stroke-2`}
        d={`M${sourceX},${sourceY}L${targetX},${targetY}`}
      />
      <foreignObject
        x={x}
        y={y}
        width={foreignObjectSize}
        height={foreignObjectSize}
        className="flex items-center justify-center pointer-events-none group" // Pointer-events-none so it doesn't block clicks/selections
      >
        {/* Tooltip for Edges */}
        <div className="absolute p-2 bg-gray-800 text-white text-xs rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity duration-300 z-50 pointer-events-auto">
          <p>I: <span className="font-mono-numbers">{data.designCurrent.toFixed(2)}</span> A</p>
          <p>ΔV%: <span className="font-mono-numbers">{data.voltageDrop.toFixed(2)}</span>%</p>
        </div>
      </foreignObject>
    </>
  );
};

interface DiagramaRedeProps {
  networkData: NetworkData;
  onNodeClick: (node: NodeData) => void;
  onNodeChange: (updatedNode: NodeData) => void;
}

// Define custom node types
const nodeTypes = {
  source: (props: any) => <CustomNode {...props} type="source" />,
  default: (props: any) => <CustomNode {...props} type="default" />,
  load: (props: any) => <CustomNode {...props} type="load" />,
};

// Define custom edge types
const edgeTypes = {
  custom: CustomEdge,
};

const DiagramaRede: React.FC<DiagramaRedeProps> = ({ networkData, onNodeClick, onNodeChange }) => {
  const { setNodes, setEdges } = useReactFlow();

  React.useEffect(() => {
    const rfNodes: RFNode[] = networkData.nodes.map(node => ({
      ...node,
      // Ensure type is correctly set for custom nodes
      type: node.type,
      className: `react-flow__node status-${node.data.status}`,
    }));
    const rfEdges: RFEdge[] = networkData.edges.map(edge => ({
      ...edge,
      type: 'custom', // Use our custom edge type
      className: `react-flow__edge status-${edge.data.status}`,
    }));

    setNodes(rfNodes);
    setEdges(rfEdges);
  }, [networkData, setNodes, setEdges]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [setEdges]
  );

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  const onNodeClickInternal = useCallback(
    (_: React.MouseEvent, node: RFNode) => {
      onNodeClick(node.data); // Pass only the data part
    },
    [onNodeClick]
  );

  const handleNodeDataUpdate = useCallback(async (nodeId: string, updatedData: Partial<NodeData>) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...updatedData } } : node
      )
    );
    const recalculatedNetwork = await updateNodeAndRecalculate(nodeId, updatedData);
    // App.tsx handles the networkData update after an initial get
  }, [setNodes]);

  return (
    <ReactFlow
      nodes={networkData.nodes}
      edges={networkData.edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={onNodeClickInternal}
      fitView
      className="reactflow-wrapper"
      nodeTypes={nodeTypes} // Register custom node types
      edgeTypes={edgeTypes} // Register custom edge types
    >
      <Controls />
      <Background variant="dots" gap={12} size={1} />
    </ReactFlow>
  );
};

export default DiagramaRede;
