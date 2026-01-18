// src/services/api.ts

import axios from 'axios';

// 1. Definição da Interface que o Backend espera
interface BackendPayload {
  config: {
    trafo_kva: number;
    classe_tipo: string;
    classe_manual: string;
    perfil: string;
    fp_ip: number;
  };
  rede: Array<{
    id: string;
    pai_id: string;
    metros: number;
    cabo: string;
    cargas: {
      mono: number;
      bi: number;
      tri: number;
      tri_esp: number;
      carga_esp_kva: number;
      tipo_ip: string;
      qtd_ip: number;
    };
  }>;
}

// 2. Função de Adaptação
export const calcularRede = async (configFrontend: any, trechosFrontend: any[]) => {
  
  // MAPPER: Transforma o formato "Tabela" (Frontend) no formato "Árvore" (Backend)
  const payload: BackendPayload = {
    config: {
      trafo_kva: Number(configFrontend.trafo_kva),
      classe_tipo: configFrontend.classe_tipo,
      classe_manual: configFrontend.classe_manual,
      perfil: configFrontend.perfil,
      fp_ip: Number(configFrontend.fp_ip || 0.92)
    },
    rede: trechosFrontend.map(t => ({
      id: String(t.ponto),          // De 'ponto' para 'id'
      pai_id: String(t.montante),   // De 'montante' para 'pai_id'
      metros: Number(t.metros),
      cabo: String(t.cabo),
      cargas: {                     // Agrupa as cargas
        mono: Number(t.mono),
        bi: Number(t.bi),
        tri: Number(t.tri),
        tri_esp: Number(t.tri_esp),
        carga_esp_kva: Number(t.carga_esp),
        tipo_ip: String(t.tipo_ip),
        qtd_ip: Number(t.qtd_ip)
      }
    }))
  };

  // Envia para o Backend
  return axios.post(`${import.meta.env.VITE_API_URL}/api/v1/calcular`, payload);
};
