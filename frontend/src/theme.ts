import { createTheme, responsiveFontSizes } from '@mui/material/styles';

let theme = createTheme({
  palette: {
    primary: {
      main: '#2196F3', // A shade of blue for primary actions, complementing glassmorphism
    },
    secondary: {
      main: '#21CBF3', // Another shade of blue/cyan
    },
    background: {
      default: 'transparent', // Let the body's gradient background show through
      paper: 'transparent', // Make Paper components transparent by default
    },
    text: {
      primary: '#2c3e50', // Dark gray for primary text
      secondary: 'rgba(44, 62, 80, 0.7)', // Slightly lighter for secondary text
    },
  },
  typography: {
    fontFamily: ['Inter', 'Roboto', 'sans-serif'].join(','),
    h1: {
      fontWeight: 700,
    },
    h2: {
      fontWeight: 600,
    },
    h3: {
      fontWeight: 500,
    },
    h4: {
      fontWeight: 500,
    },
    h5: {
      fontWeight: 500,
    },
    h6: {
      fontWeight: 500,
    },
    subtitle1: {
      fontWeight: 400,
    },
    subtitle2: {
      fontWeight: 400,
    },
    body1: {
      fontWeight: 400,
    },
    body2: {
      fontWeight: 400,
    },
    button: {
      fontWeight: 500,
      textTransform: 'none', // Prevent uppercase transformation for buttons
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px', // Slightly rounded buttons
        },
      },
    },
    MuiPaper: { // Apply glassmorphism defaults to Paper components
      styleOverrides: {
        root: {
          background: 'rgba(255, 255, 255, 0.65)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.8)',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
          borderRadius: '16px',
        },
      },
    },
    MuiAppBar: { // Custom styling for AppBar to better fit the glassmorphism aesthetic
      styleOverrides: {
        root: {
          background: 'rgba(255, 255, 255, 0.65)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.8)',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
          borderRadius: '16px',
          color: '#2c3e50', // Ensure text on AppBar is dark for contrast
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: 'rgba(255, 255, 255, 0.8)', // Slightly more opaque for readability
          backdropFilter: 'blur(12px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.8)',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none', // Prevent uppercase transformation for tabs
        },
      },
    },
  },
});

theme = responsiveFontSizes(theme);

export default theme;
