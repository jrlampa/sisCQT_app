import React, { useState } from 'react';
import ProjetoList from './components/ProjetoList';
import ConfigurationPage from './components/ConfigurationPage';
import SimulationModule from './components/SimulationModule'; // Assuming this is another page
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  CssBaseline,
  IconButton,
  Divider,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SettingsIcon from '@mui/icons-material/Settings';
import EngineeringIcon from '@mui/icons-material/Engineering';
import DashboardIcon from '@mui/icons-material/Dashboard';
import { styled, useTheme } from '@mui/material/styles';
import type { Theme } from '@mui/material/styles';

const drawerWidth = 240;

const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })<{
  open?: boolean;
}>(({ theme, open }) => ({
  flexGrow: 1,
  padding: theme.spacing(3),
  paddingTop: `calc(${theme.mixins.toolbar.minHeight}px + 16px + ${theme.spacing(3)})`, // Account for AppBar height + top margin + existing padding
  transition: theme.transitions.create('margin', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  marginLeft: `-${drawerWidth}px`,
  ...(open && {
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
    marginLeft: 0,
  }),
}));

const AppBarStyled = styled(AppBar, {
  shouldForwardProp: (prop) => prop !== 'open',
})<{
  open?: boolean;
}>(({ theme, open }) => ({
  // Glassmorphism styles
  background: 'rgba(255, 255, 255, 0.65)',
  backdropFilter: 'blur(16px)',
  border: '1px solid rgba(255, 255, 255, 0.8)',
  boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.15)',
  borderRadius: '16px',
  color: theme.palette.text.primary, // Ensure text color is readable against glassmorphism

  // Floating effect
  top: '16px', // Margin from top
  left: '16px', // Margin from left
  right: '16px', // Margin from right
  width: `calc(100% - 32px)`, // Adjust width for side margins
  position: 'fixed', // Keep it fixed at the top

  // Transitions for drawer open/close
  transition: theme.transitions.create(['width', 'margin', 'border-radius', 'left', 'right'], { // Add border-radius, left, right to transition
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  ...(open && {
    marginLeft: `${drawerWidth + 16}px`, // Adjust marginLeft for drawer and left margin of AppBar
    width: `calc(100% - ${drawerWidth + 32}px)`, // Adjust width for drawer and side margins
    left: `${drawerWidth + 16}px`, // Adjust left for drawer to prevent overlap
    right: '16px',
    transition: theme.transitions.create(['width', 'margin', 'border-radius', 'left', 'right'], {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
}));

const DrawerHeader = styled('div')(({ theme }) => ({
  // necessary for content to be below app bar
  ...theme.mixins.toolbar,
  paddingTop: '16px', // Account for AppBar's top margin
  paddingLeft: theme.spacing(1), // Keep existing left padding
  paddingRight: theme.spacing(1), // Keep existing right padding
  justifyContent: 'flex-end',
}));

function App() {
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState<'projetos' | 'configuracoes' | 'simulacao'>('projetos');

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBarStyled position="fixed" open={open}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={handleDrawerOpen}
            edge="start"
            sx={{ mr: 2, ...(open && { display: 'none' }) }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            SisCQT Enterprise
          </Typography>
        </Toolbar>
      </AppBarStyled>
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="persistent"
        anchor="left"
        open={open}
      >
        <DrawerHeader>
          <IconButton onClick={handleDrawerClose}>
            {theme.direction === 'ltr' ? <MenuIcon /> : <MenuIcon />}
          </IconButton>
        </DrawerHeader>
        <Divider />
        <List>
          <ListItem disablePadding>
            <ListItemButton onClick={() => { setPage('projetos'); handleDrawerClose(); }}>
              <ListItemIcon>
                <DashboardIcon /> {/* Projects Icon */}
              </ListItemIcon>
              <ListItemText primary="Projetos" />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton onClick={() => { setPage('configuracoes'); handleDrawerClose(); }}>
              <ListItemIcon>
                <SettingsIcon /> {/* Configuration Icon */}
              </ListItemIcon>
              <ListItemText primary="Configurações" />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton onClick={() => { setPage('simulacao'); handleDrawerClose(); }}>
              <ListItemIcon>
                <EngineeringIcon /> {/* Simulation Icon, can change later */}
              </ListItemIcon>
              <ListItemText primary="Simulação" />
            </ListItemButton>
          </ListItem>
        </List>
      </Drawer>
      <Main open={open}>
        <DrawerHeader />
        <Box sx={{ p: 3 }}>
          {page === 'projetos' && <ProjetoList />}
          {page === 'configuracoes' && <ConfigurationPage />}
          {page === 'simulacao' && <SimulationModule cenarioId={0} currentTrechos={[]} />} {/* cenarioId and currentTrechos will need to be properly managed */}
        </Box>
      </Main>
    </Box>
  );
}

export default App;
