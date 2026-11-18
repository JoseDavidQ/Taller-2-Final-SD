#!/usr/bin/env bash
# Crea los commits del Taller 2 en bloques lógicos (el taller exige varios commits de TODOS los integrantes).
# Cada integrante ejecuta SOLO sus bloques con su propia identidad de Git y hace push; el otro hace pull y sigue.
#
#   git config user.name "Tu Nombre"; git config user.email "tu@correo"     (una vez, solo en este repo)
#   ./aplicar-commits.sh lista        # muestra los bloques
#   ./aplicar-commits.sh 1 3          # bloques 1 a 3 en orden
# Reparto sugerido: docs/Plan de commits.md
set -euo pipefail
cd "$(dirname "$0")"
[ -d .git ] || git init -b main

bloque() {
  case "$1" in
    1) MSG="Estructura inicial: .gitignore, .dockerignore y dependencias"
       FILES=(.gitignore .gitattributes .dockerignore requirements.txt evidencias/.gitkeep resultados/.gitkeep) ;;
    2) MSG="Contratos de la API (.proto) y esquema de eventos JSON (E2)"
       FILES=(proto/coordinator.proto proto/generar.py schemas/event.schema.json) ;;
    3) MSG="Elección de coordinador del Taller 1 integrada (matón con términos y quórum)"
       FILES=(coord) ;;
    4) MSG="Utilidades comunes: eventos con reloj de Lamport, reintentos con espera creciente y log"
       FILES=(common/__init__.py common/events.py common/retry.py common/log.py) ;;
    5) MSG="Mensajería RabbitMQ: confirmaciones, reintentos, idempotencia y orden por Lamport"
       FILES=(common/messaging.py) ;;
    6) MSG="Cliente gRPC del coordinador con timeout, backoff y redirección al líder"
       FILES=(common/coord_client.py) ;;
    7) MSG="Agente: métricas por gRPC y por el broker, pasos de la Saga y notificaciones"
       FILES=(agent/__init__.py agent/resources.py agent/service.py agent/main.py agent/request.py) ;;
    8) MSG="Coordinador: repositorio en Redis, API gRPC, clientes de agentes y adaptador de la elección"
       FILES=(coordinator/__init__.py coordinator/repo.py coordinator/agentes.py coordinator/service.py coordinator/eleccion.py) ;;
    9) MSG="Saga con compensaciones, estados persistidos y arranque del coordinador"
       FILES=(coordinator/saga.py coordinator/main.py) ;;
    10) MSG="Pruebas unitarias: Saga, orden de Lamport, idempotencia, recursos y reintentos"
       FILES=(tests) ;;
    11) MSG="Dockerfiles de los cuatro componentes y configuración del clúster"
       FILES=(agent/Dockerfile coordinator/Dockerfile broker database config) ;;
    12) MSG="docker-compose (una máquina y despliegue repartido en VM) y variables de ejemplo"
       FILES=(docker-compose.yml docker-compose.nodo.yml .env.example) ;;
    13) MSG="Herramientas y scripts de los experimentos E3, E4, E5 y Lamport"
       FILES=(tools scripts) ;;
    14) MSG="Documentación: README, guía de despliegue y plan de commits"
       FILES=(README.md docs aplicar-commits.sh) ;;
    15) MSG="Evidencias E3 y E4: flujo completo y Saga con compensación"
       FILES=(evidencias/E3* evidencias/E4*) ;;
    16) MSG="Evidencia E5 y experimento de Lamport: desconexión del broker, duplicados y orden"
       FILES=(evidencias/E5* "evidencias/Experimento*" "evidencias/Lista*" evidencias/logs-vm1 evidencias/logs-vm2 evidencias/logs-vm3) ;;
    17) MSG="Informe técnico del taller (PDF) y su generador"
       FILES=(informe) ;;
    *) echo "bloque desconocido: $1"; exit 1 ;;
  esac
}

if [ "${1:-}" = "lista" ] || [ $# -eq 0 ]; then
  for i in $(seq 1 17); do bloque "$i"; printf '%2s  %s\n' "$i" "$MSG"; done
  exit 0
fi
DESDE="$1"; HASTA="${2:-$1}"
for i in $(seq "$DESDE" "$HASTA"); do
  bloque "$i"
  git add -- "${FILES[@]}" 2>/dev/null || { echo "bloque $i: faltan archivos (¿ya generaste las evidencias?)"; continue; }
  if git diff --cached --quiet; then
    echo "bloque $i: nada nuevo que confirmar"
  else
    git commit -q -m "$MSG"
    echo "bloque $i confirmado: $MSG"
  fi
done
