import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import {
  DataGrid,
  GridToolbar,
} from '@mui/x-data-grid';
import type {
  GridColDef,
  GridRowsProp,
  GridRenderEditCellParams,
  GridActionsCellItem,
} from '@mui/x-data-grid';
import {
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Typography,
  Paper,
  Stack,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Close';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';
import AddIcon from '@mui/icons-material/Add';

interface Trecho {
  id: number;
  ponto: string;
  montante: string;
  metros: number;
  cabo: string;
  mono: number;
  bi: number;
  tri: number;
  tri_esp: number;
  carga_esp: number;
  tipo_ip: string;
  qtd_ip: number;
  projeto: number;
  nome_cenario: string;
}

interface TrechoTableProps {
  trechos: Trecho[];
  onSave: (updatedTrecho: Trecho) => void;
  projectId: number;
  nomeCenario: string;
  onAdd: (newTrecho: Trecho) => void;
  onRemove: (trechoId: number) => void;
  cqtResults: { [ponto: string]: number }; // Add cqtResults prop
}

const TrechoTable: React.FC<TrechoTableProps> = ({ trechos, onSave, projectId, nomeCenario, onAdd, onRemove, cqtResults }) => {
  const [rows, setRows] = useState<GridRowsProp>(trechos);
  const [cabosOptions, setCabosOptions] = useState<string[]>([]);
  const [ipsOptions, setIpsOptions] = useState<string[]>([]);
  const [loadingConfig, setLoadingConfig] = useState(true);

  // State for adding new trecho
  const [newTrechoData, setNewTrechoData] = useState<Partial<Trecho>>({
    ponto: '', montante: '', metros: 0, cabo: '', mono: 0, bi: 0, tri: 0, tri_esp: 0, carga_esp: 0, tipo_ip: '', qtd_ip: 0
  });
  const [addingNewTrecho, setAddingNewTrecho] = useState(false);

  useEffect(() => {
    setRows(trechos);
  }, [trechos]);

  useEffect(() => {
    const fetchConfigOptions = async () => {
      try {
        const [cabosRes, ipsRes] = await Promise.all([
          axios.get(`${import.meta.env.VITE_API_URL}/api/cabos/`),
          axios.get(`${import.meta.env.VITE_API_URL}/api/ips/`),
        ]);
        setCabosOptions(cabosRes.data.map((c: any) => c.nome));
        setIpsOptions(ipsRes.data.map((ip: any) => ip.nome));
      } catch (error) {
        console.error('Failed to fetch config options:', error);
      } finally {
        setLoadingConfig(false);
      }
    };
    fetchConfigOptions();
  }, []);

  const processRowUpdate = useCallback(
    async (newRow: Trecho, oldRow: Trecho) => {
      const updatedRow = { ...newRow, isNew: false } as Trecho;
      try {
        const dataToSave = {
          ...updatedRow,
          metros: Number(updatedRow.metros),
          mono: Number(updatedRow.mono),
          bi: Number(updatedRow.bi),
          tri: Number(updatedRow.tri),
          tri_esp: Number(updatedRow.tri_esp),
          carga_esp: Number(updatedRow.carga_esp),
          qtd_ip: Number(updatedRow.qtd_ip),
        };
        const response = await axios.put(`${import.meta.env.VITE_API_URL}/api/trechos/${updatedRow.id}/`, dataToSave);
        onSave(response.data);
        setRows((prevRows) => prevRows.map((row) => (row.id === newRow.id ? response.data : row)));
        return response.data;
      } catch (error: any) {
        console.error('Failed to save trecho:', error.response?.data || error.message);
        alert(`Failed to update trecho: ${error.response?.data?.detail || error.message}`);
        return oldRow; // Revert to old row on error
      }
    },
    [onSave],
  );

  const handleProcessRowUpdateError = useCallback((error: any) => {
    console.error('Error during row update:', error);
  }, []);

  const handleNewTrechoChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | { name?: string; value: unknown }>, field: keyof Trecho) => {
    const { name, value } = e.target;
    setNewTrechoData(prevData => ({ ...prevData, [field]: value }));
  };

  const handleAddNewTrecho = async () => {
    if (!newTrechoData.ponto || !newTrechoData.cabo) {
      alert('Ponto and Cabo are required for new trecho.');
      return;
    }
    setAddingNewTrecho(true);
    try {
      const dataToSave = {
        ...newTrechoData,
        projeto: projectId,
        nome_cenario: nomeCenario,
        metros: Number(newTrechoData.metros || 0),
        mono: Number(newTrechoData.mono || 0),
        bi: Number(newTrechoData.bi || 0),
        tri: Number(newTrechoData.tri || 0),
        tri_esp: Number(newTrechoData.tri_esp || 0),
        carga_esp: Number(newTrechoData.carga_esp || 0),
        qtd_ip: Number(newTrechoData.qtd_ip || 0),
      };

      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/trechos/`, dataToSave);
      onAdd(response.data);
      setRows((prevRows) => [...prevRows, response.data]);
      setNewTrechoData({ ponto: '', montante: '', metros: 0, cabo: '', mono: 0, bi: 0, tri: 0, tri_esp: 0, carga_esp: 0, tipo_ip: '', qtd_ip: 0 });
    } catch (error: any) {
      console.error('Failed to add new trecho:', error.response?.data || error.message);
      alert(`Failed to add new trecho: ${error.response?.data?.error || error.message}`);
    } finally {
      setAddingNewTrecho(false);
    }
  };

  const handleDeleteTrecho = useCallback(
    async (id: number) => {
      if (window.confirm('Are you sure you want to delete this trecho?')) {
        try {
          await axios.delete(`${import.meta.env.VITE_API_URL}/api/trechos/${id}/`);
          onRemove(id);
          setRows((prevRows) => prevRows.filter((row) => row.id !== id));
        } catch (error: any) {
          console.error('Failed to delete trecho:', error.response?.data || error.message);
          alert(`Failed to delete trecho: ${error.response?.data?.detail || error.message}`);
        }
      }
    },
    [onRemove],
  );

  const columns: GridColDef[] = [
    { field: 'ponto', headerName: 'Ponto', width: 100, editable: true },
    { field: 'montante', headerName: 'Montante', width: 120, editable: true },
    { field: 'metros', headerName: 'Metros', type: 'number', width: 90, editable: true },
    {
      field: 'cabo',
      headerName: 'Cabo',
      width: 150,
      editable: true,
      type: 'singleSelect',
      valueOptions: cabosOptions,
    },
    { field: 'mono', headerName: 'Mono', type: 'number', width: 70, editable: true },
    { field: 'bi', headerName: 'Bi', type: 'number', width: 70, editable: true },
    { field: 'tri', headerName: 'Tri', type: 'number', width: 70, editable: true },
    { field: 'tri_esp', headerName: 'Tri Esp', type: 'number', width: 90, editable: true },
    { field: 'carga_esp', headerName: 'Carga Esp', type: 'number', width: 100, editable: true },
    {
      field: 'tipo_ip',
      headerName: 'Tipo IP',
      width: 150,
      editable: true,
      type: 'singleSelect',
      valueOptions: ipsOptions,
    },
    { field: 'qtd_ip', headerName: 'Qtd IP', type: 'number', width: 80, editable: true },
    {
      field: 'cqt_acumulada',
      headerName: 'CQT Acum. (%)',
      type: 'number',
      width: 120,
      valueGetter: (params) => cqtResults[params.row.ponto] || 0,
      renderCell: (params) => (
        <Typography variant="body2" color={params.value > 10 ? 'error' : 'inherit'}>
          {params.value.toFixed(2)}
        </Typography>
      ),
      editable: false,
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Ações',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<DeleteIcon />}
          label="Delete"
          onClick={() => handleDeleteTrecho(params.id as number)}
          color="inherit"
        />,
      ],
    },
  ];

  if (loadingConfig) {
    return <Typography>Loading configuration options...</Typography>;
  }

  return (
    <Box sx={{ height: 600, width: '100%' }}>
      <Typography variant="h6" gutterBottom>Gerenciar Trechos</Typography>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          label="Ponto"
          variant="outlined"
          size="small"
          name="ponto"
          value={newTrechoData.ponto || ''}
          onChange={(e) => handleNewTrechoChange(e, 'ponto')}
          required
        />
        <TextField
          label="Montante"
          variant="outlined"
          size="small"
          name="montante"
          value={newTrechoData.montante || ''}
          onChange={(e) => handleNewTrechoChange(e, 'montante')}
        />
        <TextField
          label="Metros"
          variant="outlined"
          size="small"
          type="number"
          name="metros"
          value={newTrechoData.metros || 0}
          onChange={(e) => handleNewTrechoChange(e, 'metros')}
        />
        <FormControl variant="outlined" size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Cabo</InputLabel>
          <Select
            label="Cabo"
            name="cabo"
            value={newTrechoData.cabo || ''}
            onChange={(e) => handleNewTrechoChange(e, 'cabo')}
            required
          >
            <MenuItem value="">
              <em>Nenhum</em>
            </MenuItem>
            {cabosOptions.map((option) => (
              <MenuItem key={option} value={option}>{option}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAddNewTrecho}
          disabled={addingNewTrecho || !newTrechoData.ponto || !newTrechoData.cabo}
        >
          Adicionar Trecho
        </Button>
      </Stack>

      <DataGrid
        rows={rows}
        columns={columns}
        editMode="cell"
        processRowUpdate={processRowUpdate}
        onProcessRowUpdateError={handleProcessRowUpdateError}
        getRowId={(row) => row.id}
        density="compact"
        sx={{
          '& .MuiDataGrid-row:nth-of-type(odd)': {
            backgroundColor: 'rgba(0, 0, 0, 0.04)',
          },
        }}
        slots={{
          toolbar: GridToolbar,
        }}
        slotProps={{
          toolbar: {
            showQuickFilter: true,
          },
        }}
        initialState={{
          pagination: {
            paginationModel: { pageSize: 10, page: 0 },
          },
        }}
        pageSizeOptions={[5, 10, 25, 50]}
      />

      <Box sx={{ mt: 3, p: 2, border: '1px solid #ccc', borderRadius: '4px' }}>
        <Typography variant="subtitle1" gutterBottom>
          Observações sobre a Tabela de Trechos:
        </Typography>
        <Typography variant="body2">
          - Clique duas vezes em uma célula para editar seu valor.
        </Typography>
        <Typography variant="body2">
          - A coluna "CQT Acum. (%)" exibe a queda de tensão acumulada. Valores acima de 10% são destacados em vermelho.
        </Typography>
        <Typography variant="body2">
          - Use a barra de ferramentas acima da tabela para filtrar, exportar ou gerenciar colunas.
        </Typography>
      </Box>
    </Box>
  );
};

export default TrechoTable;
