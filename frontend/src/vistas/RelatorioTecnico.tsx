import React from 'react';
import { NetworkData } from '../tipos/tipos';
import { useCalculoMutation } from '../servicos/servicoEletrico';

interface RelatorioTecnicoProps {
  networkData: NetworkData | null;
  // Assuming 'resultados' and 'abaAtiva' will be passed as props
  resultados: { [key: string]: any[] }; // Replace 'any[]' with a more specific type if known
  abaAtiva: string;
}

const RelatorioTecnico: React.FC<RelatorioTecnicoProps> = ({ networkData, resultados, abaAtiva }) => {
  const { isPending } = useCalculoMutation(); // Using the mock hook for loading state

  const exportMemoryOfCalculation = () => {
    // Logic to format and export data
    const dataToExport = resultados[abaAtiva];
    if (!dataToExport || dataToExport.length === 0) {
      alert('Nenhum dado para exportar na aba ativa.');
      return;
    }

    let csvContent = "data:text/csv;charset=utf-8,";
    // Assuming dataToExport is an array of objects
    const headers = Object.keys(dataToExport[0]);
    csvContent += headers.join(';') + '\n'; // Use semicolon for CSV
    dataToExport.forEach(row => {
      csvContent += headers.map(header => row[header]).join(';') + '\n';
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "memoria_calculo.csv");
    document.body.appendChild(link); // Required for FF
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-8 bg-white shadow-lg rounded-lg text-gray-800">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-700">Relatório Técnico SisCQT</h2>

      {isPending ? (
        <div className="space-y-4">
          <div className="skeleton h-8 w-1/2 mb-4"></div>
          <div className="skeleton h-6 w-full"></div>
          <div className="skeleton h-6 w-full"></div>
          <div className="skeleton h-48 w-full mt-8"></div>
        </div>
      ) : (
        <>
          <div className="mb-8">
            <h3 className="text-xl font-semibold mb-3 text-gray-600">Dados Gerais do Projeto</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <p><strong>Nome do Projeto:</strong> <span className="font-mono-numbers">Projeto Exemplo</span></p>
              <p><strong>Data:</strong> <span className="font-mono-numbers">{new Date().toLocaleDateString()}</span></p>
              <p><strong>Engenheiro Responsável:</strong> <span className="font-mono-numbers">Fulano de Tal</span></p>
              <p><strong>Localização:</strong> <span className="font-mono-numbers">Cidade, Estado</span></p>
            </div>
          </div>

          <div className="mb-8">
            <h3 className="text-xl font-semibold mb-3 text-gray-600">Memória de Cálculo ({abaAtiva})</h3>
            <button
              onClick={exportMemoryOfCalculation}
              className="mb-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Exportar Memória de Cálculo (.csv)
            </button>
            <div className="overflow-x-auto border border-gray-200 rounded-md">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {/* Assuming 'resultados' data has consistent keys for headers */}
                    {resultados[abaAtiva] && resultados[abaAtiva].length > 0 &&
                      Object.keys(resultados[abaAtiva][0]).map((header, index) => (
                        <th
                          key={index}
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          {header}
                        </th>
                      ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {resultados[abaAtiva] && resultados[abaAtiva].map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {Object.values(row).map((value, colIndex) => (
                        <td key={colIndex} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono-numbers">
                          {typeof value === 'number' ? value.toFixed(2) : value}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {(!resultados[abaAtiva] || resultados[abaAtiva].length === 0) && (
                    <tr>
                      <td colSpan={100} className="px-6 py-4 text-center text-sm text-gray-500">
                        Nenhum dado disponível para esta aba.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {networkData && (
            <div className="mb-8">
              <h3 className="text-xl font-semibold mb-3 text-gray-600">Resumo da Rede Elétrica</h3>
              {/* This is a simplified representation. A real report might embed diagrams or more detailed tables. */}
              <p className="text-sm">Total de Nós: <span className="font-mono-numbers">{networkData.nodes.length}</span></p>
              <p className="text-sm">Total de Arestas: <span className="font-mono-numbers">{networkData.edges.length}</span></p>
              {/* Example of displaying some KPI (e.g., highest voltage drop) */}
              <p className="text-sm">Maior Queda de Tensão: <span className="font-mono-numbers">
                {Math.max(...networkData.edges.map(e => e.data?.voltageDrop || 0)).toFixed(2)}%
              </span></p>
            </div>
          )}

          <div className="text-xs text-gray-500 mt-10 border-t pt-4 text-center">
            Este relatório foi gerado automaticamente pelo sistema SisCQT.
          </div>
        </>
      )}
    </div>
  );
};

export default RelatorioTecnico;
