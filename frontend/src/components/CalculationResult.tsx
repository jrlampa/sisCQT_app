import TechnicalSuggestions from './TechnicalSuggestions';
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
import GlassCard from './GlassCard'; // Import GlassCard
import { Box, Grid, Typography, List, ListItem, ListItemText, Alert } from '@mui/material'; // Import MUI components

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
    <GlassCard sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>Resultados do Cálculo</Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Typography variant="h6" gutterBottom>KPIs</Typography>
          <List>
            {Object.entries(kpis).map(([key, value]) => (
              <ListItem key={key} disablePadding>
                <ListItemText primary={<Typography component="span" variant="body1" fontWeight="bold">{key}:</Typography>} secondary={typeof value === 'object' ? JSON.stringify(value) : value} />
              </ListItem>
            ))}
          </List>
        </Grid>
        <Grid item xs={12} md={6}>
          <Typography variant="h6" gutterBottom>Avisos</Typography>
          {avisos.length > 0 ? (
            <List>
              {avisos.map((aviso, index) => (
                <ListItem key={index} disablePadding>
                  <Alert severity="warning" sx={{ width: '100%' }}>{aviso}</Alert>
                </ListItem>
              ))}
            </List>
          ) : (
            <Alert severity="success">Nenhum aviso.</Alert>
          )}
        </Grid>
      </Grid>
      
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>Gráfico de Queda de Tensão</Typography>
        <Bar options={chartOptions} data={chartData} />
      </Box>

      {/* Technical Suggestions Component */}
      {kpis.baricentro_analysis && results.recomendacoes && (
        <Box sx={{ mt: 4 }}>
          <TechnicalSuggestions
            recomendacoes={results.recomendacoes}
            baricentroAnalysis={kpis.baricentro_analysis}
            avisos={avisos}
          />
        </Box>
      )}
    </GlassCard>
  );
};

export default CalculationResult;
