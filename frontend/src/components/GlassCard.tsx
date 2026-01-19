import { styled } from '@mui/material/styles';
import { Paper } from '@mui/material';

const GlassCard = styled(Paper)(({ theme }) => ({
  background: 'rgba(255, 255, 255, 0.65)',
  backdropFilter: 'blur(16px)',
  border: '1px solid rgba(255, 255, 255, 0.8)',
  boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
  borderRadius: '16px',
  // Ensure content inside GlassCard has appropriate padding
  padding: theme.spacing(3),
  // Additional styling for elevation if needed, but boxShadow already provides it
  // elevation: 0,
}));

export default GlassCard;
