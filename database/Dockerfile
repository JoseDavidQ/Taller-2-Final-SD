# Componente: BASE DE DATOS (Redis, replicación maestro-réplica gestionada por la elección del Taller 1).
# Imagen oficial multi-arquitectura (amd64/arm64).
FROM redis:7-alpine
COPY redis.conf /usr/local/etc/redis/redis.conf
EXPOSE 6379
# La contraseña llega por variable de entorno (nunca se guarda en la imagen)
CMD ["sh", "-c", "exec redis-server /usr/local/etc/redis/redis.conf --requirepass \"$REDIS_PASSWORD\" --masterauth \"$REDIS_PASSWORD\""]
