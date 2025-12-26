# SisCQT Enterprise ⚡

**SisCQT** (Sistema de Cálculo de Queda de Tensão) é uma solução Fullstack profissional para engenharia elétrica, projetada para o dimensionamento de redes de distribuição de baixa tensão em conformidade com a norma **Enel CNS-OMBR-MAT-19-0285**.



## 🚀 Funcionalidades Principais

- **Motor de Cálculo de Alta Performance**: Processamento iterativo de grafos capaz de calcular redes com 1000+ nós em milissegundos.
- **Importação Inteligente (Excel/CSV)**: Algoritmo de busca dinâmica de cabeçalhos que suporta planilhas com formatações variadas e dados "sujos".
- **Análise Normativa Automática**: Verificação em tempo real de limites de Queda de Tensão (QT) e Sobrecarga de Transformadores.
- **Balanceamento de Fases**: Algoritmo preditivo para sugestão de distribuição de cargas monofásicas e bifásicas (A, B, C).
- **Memorial de Cálculo em PDF**: Geração automática de relatórios técnicos profissionais.
- **Visualização de Topologia**: Diagramas de rede gerados dinamicamente via Graphviz.

## 🏗️ Arquitetura do Sistema

O projeto utiliza uma arquitetura desacoplada para garantir escalabilidade:

- **Backend**: FastAPI (Python 3.11+) - API assíncrona com validação de dados via Pydantic.
- **Frontend**: Streamlit - Interface reativa focada na experiência do engenheiro.
- **Database**: SQLite com modo WAL para suporte a múltiplas requisições.
- **Core Engine**: Lógica puramente matemática e de grafos para cálculos elétricos (momento elétrico e queda de tensão).



## 🧪 Qualidade e Confiabilidade

O projeto conta com uma suite de **37 testes automatizados** (Pytest) que cobrem:
- Integridade da Física Elétrica (Lei de Ohm).
- Deteção de ciclos e topologias impossíveis.
- Stress tests de carga massiva.
- Testes de contrato de API.

Para rodar os testes:
```bash
pytest -v