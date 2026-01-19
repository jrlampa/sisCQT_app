import React from 'react';
import GlassCard from './GlassCard'; // Import GlassCard
import {
  Box,
  Typography,
  Alert,
  List,
  ListItem,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Card, // Using Card for Baricentro Analysis
  CardContent,
  CardHeader,
  IconButton,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

interface Recommendation {
  titulo: string;
  texto: string;
}

interface BaricentroAnalysis {
  status: string;
  msg: string;
}

interface TechnicalSuggestionsProps {
  recomendacoes: Recommendation[];
  baricentroAnalysis: BaricentroAnalysis;
  avisos: string[]; // Still show general warnings
}

const TechnicalSuggestions: React.FC<TechnicalSuggestionsProps> = ({
  recomendacoes,
  baricentroAnalysis,
  avisos,
}) => {
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>Diagnóstico e Sugestões Técnicas</Typography>

      {baricentroAnalysis && (
        <GlassCard sx={{ mb: 3 }}>
          <CardHeader title={<Typography variant="h6">Análise de Baricentro Elétrico</Typography>} />
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Status: {baricentroAnalysis.status}</Typography>
            <Typography variant="body1">{baricentroAnalysis.msg}</Typography>
          </CardContent>
        </GlassCard>
      )}

      {recomendacoes.length > 0 ? (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>Recomendações de Engenharia</Typography>
          {recomendacoes.map((rec, index) => (
            <GlassCard key={index} sx={{ mb: 1 }}> {/* Each accordion item is a GlassCard */}
              <Accordion elevation={0} sx={{ background: 'transparent' }}> {/* Remove default Accordion shadow/background */}
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls={`panel${index}-content`}
                  id={`panel${index}-header`}
                >
                  <Typography variant="subtitle1">{rec.titulo}</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2">{rec.texto}</Typography>
                </AccordionDetails>
              </Accordion>
            </GlassCard>
          ))}
        </Box>
      ) : (
        <Alert severity="success" sx={{ mt: 3 }}>
          Nenhuma recomendação de engenharia adicional necessária.
        </Alert>
      )}

      {avisos.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>Avisos Gerais</Typography>
          <List>
            {avisos.map((aviso, index) => (
              <ListItem key={index} disablePadding>
                <Alert severity="warning" sx={{ width: '100%', mb: 1 }}>
                  {aviso}
                </Alert>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};

export default TechnicalSuggestions;