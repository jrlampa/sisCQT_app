import React from 'react';
import { NetworkData, RFNode, RFEdge } from '../tipos/tipos';

interface TabelaRedeProps {
  networkData: NetworkData;
}

const TabelaRede: React.FC<TabelaRedeProps> = ({ networkData }) => {
  const allElements: (RFNode | RFEdge)[] = [...networkData.nodes, ...networkData.edges];

  return (
    <div className="table-container">
      <table className="min-w-[1400px]">
        <thead>
          <tr>
            <th>ID</th>
            <th>Tipo</th>
            <th>Nome/Label</th>
            <th>Tensão (V)</th>
            <th>Corrente (A)</th>
            <th>Potência (W)</th>
            <th>FP</th>
            <th>Tipo Cabo</th>
            <th>Seção Cabo</th>
            <th>Mét. Inst.</th>
            <th>Proteção</th>
            <th>Comp. (m)</th>
            <th>Queda Tensão (%)</th>
            <th>Corrente Projeto (A)</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {allElements.map((element) => (
            <tr key={element.id}>
              <td>{element.id}</td>
              <td>{'type' in element ? element.type : 'edge'}</td> {/* Differentiate nodes and edges */}
              <td>{element.data?.label || ''}</td>
              {/* Node specific data */}
              {'data' in element && 'voltage' in element.data && (
                <>
                  <td>{element.data.voltage}</td>
                  <td>{element.data.current}</td>
                  <td>{element.data.power}</td>
                  <td>{element.data.pf}</td>
                  <td>{element.data.cableType}</td>
                  <td>{element.data.cableSection}</td>
                  <td>{element.data.installationMethod}</td>
                  <td>{element.data.protection}</td>
                </>
              )}
              {/* Edge specific data */}
              {'data' in element && 'length' in element.data && (
                <>
                  <td></td> {/* Placeholder for voltage */}
                  <td></td> {/* Placeholder for current */}
                  <td></td> {/* Placeholder for power */}
                  <td></td> {/* Placeholder for PF */}
                  <td></td> {/* Placeholder for Type Cable */}
                  <td></td> {/* Placeholder for Section Cable */}
                  <td></td> {/* Placeholder for Installation Method */}
                  <td></td> {/* Placeholder for Protection */}
                  <td>{element.data.length}</td>
                  <td>{element.data.voltageDrop?.toFixed(2)}</td>
                  <td>{element.data.designCurrent}</td>
                </>
              )}
              {/* Common status */}
              <td>{element.data?.status || ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TabelaRede;
