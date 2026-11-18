# Componente: AGENTE. Construir desde la raíz del repo:  docker build -f agent/Dockerfile .
# python:3.12-slim tiene variantes amd64 y arm64.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto ./proto
COPY common ./common
COPY coord ./coord
COPY agent ./agent
COPY tools ./tools
RUN python proto/generar.py
EXPOSE 50061
CMD ["python", "-m", "agent.main"]
