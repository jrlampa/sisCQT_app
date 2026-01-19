import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from '@mui/material/styles'; // Import only ThemeProvider
import theme from './theme'; // Import our custom theme

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider theme={theme}> {/* Use our custom theme */}
      <App />
    </ThemeProvider>
  </StrictMode>,
)
