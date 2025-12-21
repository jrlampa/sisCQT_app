SisCQT - Enterprise V24 ⚡

Sistema de Cálculo de Queda de Tensão e Dimensionamento de Redes BT

O SisCQT é uma ferramenta de engenharia desenvolvida para o dimensionamento, análise e simulação de redes de distribuição de energia em Baixa Tensão. A aplicação utiliza uma interface web interativa (Streamlit) para permitir o cadastro de topologias, cálculo de fluxo de carga, análise de queda de tensão, balanceamento de fases e geração de memoriais descritivos.
📋 Funcionalidades Principais

    Cálculo Elétrico Robusto:

        Cálculo de Queda de Tensão (CQT) por trecho e acumulada.

        Determinação de Demanda (Métodos Probabilísticos e Determinísticos).

        Estimativa de Curto-Circuito (ICC).

        Sugestão de Balanceamento de Fases automático.

    Visualização de Topologia:

        Geração automática de Diagramas Unifilares (Graphviz).

        Coloração dinâmica baseada na criticidade (CQT > Limites).

        Identificação visual do Baricentro de Carga.

    Simulação e Inteligência:

        Diagnóstico de Engenharia: Análise textual sobre conformidade normativa e sugestões de melhoria.

        Simulador de Recondutoração: Algoritmo Top-Down que sugere automaticamente a troca de cabos para resolver problemas de tensão.

    Gestão de Projetos:

        Banco de dados SQLite integrado para salvar múltiplos cenários e projetos.

        Sistema de abas para comparação de cenários ("Atual" vs "Projetado").

    Relatórios:

        Exportação de Memorial de Cálculo em PDF.

        Exportação de dados em CSV e Excel.

🛠️ Arquitetura do Projeto

O sistema é modularizado para separar a lógica de engenharia da interface do usuário.
Arquivo	Descrição
app.py	Entry Point. Gerencia a navegação, carregamento do banco e estado da sessão.
siscqt_engine.py	Core de Cálculo. Contém a classe ElectricalEngine responsável por toda a matemática elétrica (Topologia, Impedância, Demandas).
siscqt_gui.py	Interface. Componentes visuais do Streamlit, formulários de entrada, tabs e geração de PDF.
siscqt_visual.py	Gráficos. Lógica de geração dos diagramas unifilares usando a biblioteca Graphviz.
siscqt_utils.py	Ferramentas Auxiliares. Contém o DiagnosticoEngenharia e o SimuladorReadequacao (lógica de otimização).
siscqt_db.py	Persistência. Gerenciador do SQLite (CRUD de projetos, cenários e configurações).
siscqt_constantes.py*	Constantes globais (Tabelas de demanda, impedância de cabos, etc.).

*Arquivo referenciado nos imports, mas deve estar presente na raiz.
🚀 Instalação e Configuração
Pré-requisitos

    Python 3.8+

    Graphviz (Sistema Operacional): O Graphviz precisa estar instalado no sistema operacional (não apenas a biblioteca Python) para gerar os diagramas.

        Windows: Baixe o instalador em graphviz.org.

        Linux (Ubuntu/Debian): sudo apt-get install graphviz

Passo a Passo

    Clone o repositório ou extraia os arquivos.

    Crie um ambiente virtual (recomendado):
    Bash

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

Instale as dependências:
Bash

pip install -r requirements.txt

Execute a aplicação:
Bash

    streamlit run app.py

📖 Como Usar
1. Gerenciamento de Projetos

Na barra lateral, você pode criar novos projetos ou carregar projetos existentes salvos no banco de dados (siscqt_v24.db).
2. Edição de Topologia (Levantamento)

Na aba de um cenário (ex: "ATUAL"), preencha a tabela com os dados da rede:

    PONTO: Nome do nó (poste/caixa).

    MONTANTE: De onde vem a energia (Nome do nó anterior). Para o início, use "TRAFO" como ponto e deixe o montante vazio (o sistema ajusta automaticamente).

    CABO / METROS: Dados do condutor.

    CARGAS: Quantidade de clientes (Mono, Bi, Tri) ou cargas especiais (IP, etc).

Clique em "PROCESSAR CÁLCULO".
3. Análise de Resultados

Após o cálculo, o sistema exibe:

    KPIs: Ocupação do Trafo, Queda de Tensão Máxima.

    Abas:

        Diagnóstico: Alertas normativos e sugestões de engenharia.

        Tabela Técnica: Dados detalhados nó a nó.

        Diagrama: Visualização gráfica da rede.

        Simulação: Ferramenta para testar recondutoração automática.

4. Configurações

Acesse o menu "Configurações" na sidebar para editar:

    Impedância e custo dos cabos.

    Potência das luminárias (IP).

    Padronização de transformadores.

    Limites normativos (Perfis de Queda de Tensão e Carregamento).

📦 Dependências

As principais bibliotecas utilizadas são:

    streamlit: Interface web.

    pandas & numpy: Manipulação de dados e cálculos vetoriais.

    graphviz: Visualização de grafos/redes.

    fpdf: Geração de relatórios em PDF.

    openpyxl / xlsxwriter: Exportação para Excel.

    sqlite3: Banco de dados (nativo do Python).

👤 Créditos

Desenvolvido por: Jonatas Lampa Empresa: im3 Brasil