# Componente: COORDINADOR (elección del Taller 1 + API gRPC + consumidores + Saga).
# Construir desde la raíz del repo:  docker build -f coordinator/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proto ./proto
COPY common ./common
COPY coord ./coord
COPY coordinator ./coordinator
COPY tools ./tools
COPY config ./config
RUN python proto/generar.py && mkdir -p /data/logs
EXPOSE 50051 7001
CMD ["python", "-m", "coordinator.main"]
