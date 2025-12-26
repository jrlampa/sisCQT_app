# Dockerfile
FROM python:3.11-slim

# Impede a criação de ficheiros .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala o Graphviz no Sistema Operativo
RUN apt-get update && apt-get install -y \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Expõe as portas (API e UI)
EXPOSE 8000
EXPOSE 8501

# Script de inicialização dupla
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port 8000 & streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0"]