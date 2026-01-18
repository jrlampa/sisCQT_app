import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface CalculationResultProps {
  results: {
    resultados_calculo: any[];
    kpis: any;
    avisos: string[];
  };
}

const CalculationResult: React.FC<CalculationResultProps> = ({ results }) => {
  const { resultados_calculo, kpis, avisos } = results;

  const chartData = {
    labels: resultados_calculo.map(r => r.PONTO),
    datasets: [
      {
        label: 'Queda de Tensão Acumulada (%)',
        data: resultados_calculo.map(r => r.CQT_ACUMULADA),
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Perfil de Queda de Tensão',
      },
    },
  };

  return (
    <div className="mt-4">
      <h3>Resultados do Cálculo</h3>
      
      <div className="row">
        <div className="col-md-6">
          <h4>KPIs</h4>
          <ul className="list-group">
            {Object.entries(kpis).map(([key, value]) => (
              <li key={key} className="list-group-item">
                <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : value}
              </li>
            ))}
          </ul>
        </div>
        <div className="col-md-6">
          <h4>Avisos</h4>
          {avisos.length > 0 ? (
            <ul className="list-group">
              {avisos.map((aviso, index) => (
                <li key={index} className="list-group-item list-group-item-warning">
                  {aviso}
                </li>
              ))}
            </ul>
          ) : (
            <div className="alert alert-success">Nenhum aviso.</div>
          )}
        </div>
      </div>
      
      <div className="mt-4">
        <h4>Gráfico de Queda de Tensão</h4>
        <Bar options={chartOptions} data={chartData} />
      </div>
    </div>
  );
};

export default CalculationResult;
