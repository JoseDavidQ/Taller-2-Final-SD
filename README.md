# Taller 2 — Integración, mensajería y transacciones

Sistemas Distribuidos Modernos · Ingeniería en Telemática · Docente: Msc. Ing. Óscar Gabriel Espejo Mojica

**Integrantes:** Gerson Steven Rodríguez Sendoya · José David Quintero Guerrero

Continúa el [Taller 1](../taller1-coordinacion-datos): el coordinador elegido por el algoritmo del matón y el
inventario replicado en Redis siguen siendo la base. Este taller agrega la **API síncrona (gRPC)**, la
**mensajería asíncrona (RabbitMQ)**, el **orden causal (Lamport)**, la **asignación transaccional (Saga)** y el
**empaquetado con Docker Compose**.

## 1. Arquitectura

```
   ┌────────── agente 1 ──────────┐        ┌────────── agente 2 ──────────┐   ┌─ agente 3 ─┐
   │ gRPC AgentControl (:50061)   │        │ ...                          │   │ ...        │
   │ métricas: gRPC + evento      │        │                              │   │            │
   └───────┬──────────────▲───────┘        └──────────────────────────────┘   └────────────┘
   ReportMetrics /        │ Reserve · Release · Commit            (síncrono, con timeout y reintentos)
   RequestAllocation      │
           ▼              │
   ┌────────────── coordinadores 1 · 2 · 3 (elección del Taller 1) ────────────────┐
   │  solo el LÍDER atiende gRPC y consume del broker; los demás esperan (failover)  │
   │  Saga (orquestador) · orden por Lamport · idempotencia · vigilante de nodos      │
   └──────────────┬───────────────────────────────────────────────┬─────────────────┘
        eventos   │  RabbitMQ: metrics · allocations · failover   │  Redis maestro-réplica
        (asíncrono)▼  + agent.<id>.notify                          ▼  (maestro = líder)
              ┌──────────┐                                  ┌───────────────┐
              │  BROKER  │                                  │ BASE DE DATOS │
              └──────────┘                                  └───────────────┘
```

Los **cuatro componentes** son: agente, coordinador, broker (RabbitMQ) y base de datos (Redis). Cada uno
tiene su `Dockerfile` (`agent/`, `coordinator/`, `broker/`, `database/`).

### Secuencia de una asignación

```
Agente1        Coordinador(líder)         Agente origen          Redis (maestro→réplicas)     RabbitMQ
  │ RequestAllocation(id) ─▶│                                                                    │
  │                         │ elige origen (métricas)                                            │
  │                         │ guarda saga EN_CURSO ─────────────────────────▶│                   │
  │                         │ 1) Reserve ───────────────▶│ reserva             │                   │
  │                         │ 2) guarda alloc:<id> ─────────────────────────▶│ replica           │
  │                         │ 3) Commit ───────────────▶│ confirma             │                   │
  │                         │    publica allocation.result.<agente1> ───────────────────────────▶│
  │◀── notificación (ack tras procesar) ─────────────────────────────────────────────────────────│
  │◀── AllocationReply(COMPLETADA) ─│  (si un paso falla: compensa en orden inverso → COMPENSADA)
```

## 2. Decisiones de diseño

| Tema | Decisión | Por qué |
|---|---|---|
| API síncrona | **gRPC** (`proto/coordinator.proto`) | Contrato tipado y compilable (E2); plazos (*deadline*) nativos en cada llamada; ya lo usamos en la práctica 3. REST/OpenAPI habría exigido validar los esquemas a mano. |
| Broker | **RabbitMQ** | Confirmaciones de publicación y *ack* manual por mensaje; colas durables; lo conocemos de la práctica 4. Kafka es más pesado para 2 GB. |
| Coordinador | **Elección del Taller 1** (`coord/`) dentro del contenedor | Cumple el requisito previo: un solo líder atiende; si cae, otro es elegido y los agentes se redirigen (`NOT_LEADER leader=<id>`). |
| Base de datos | **Redis maestro-réplica** del Taller 1 | Guarda métricas, Sagas, asignaciones e idempotencia; el maestro es el líder y las réplicas conservan los datos. |
| Transacción | **Saga orquestada** | Cada paso con compensación; el estado se persiste tras cada transición (`saga:<id>` y `saga:<id>:log`). |
| Orden | **(Lamport, id de nodo)** en una ventana | El consumidor acumula el lote hasta 0,5 s de silencio (máx. 3 s) y lo procesa ordenado. Límite: un evento que llegue después de cerrar la ventana se procesa después. |
| Idempotencia | `msg_id` único + marca `dedupe:<cola>:<id>` en Redis | Se marca **después** de procesar y antes del *ack*: si el coordinador cae a mitad, el reenvío se reprocesa sin dañar (los manejadores son idempotentes). |

## 3. Cómo se cumple cada punto del taller

| Requisito | Dónde |
|---|---|
| 3.1 Contrato de la API | `proto/coordinator.proto` (`Coordinator`: `ReportMetrics`, `RequestAllocation`; `AgentControl`: `Reserve`, `Release`, `Commit`) |
| 3.1 Reporte periódico + confirmación | `agent/main.py` (`ciclo_metricas`) → `coordinator/service.py` (`ReportMetrics` devuelve `MetricsAck` con asignaciones vigentes) |
| 3.1 Timeouts y reintento con espera creciente | `common/coord_client.py` (plazo por llamada, backoff exponencial con jitter, redirección al líder), `common/retry.py` |
| 3.2 Colas `metrics`, `allocations`, `failover` | `common/messaging.py` (`COLAS`, `declarar_topologia`); esquema de eventos en `schemas/event.schema.json` |
| 3.2 Confirmación del productor / del consumidor | `Productor.publicar` (*publisher confirms* + `mandatory`); `Consumidor._procesar_lote` (`ack` solo tras procesar) |
| 3.2 Reintentos ante desconexión | `Conexion.conectar` (backoff) y reintentos de `publicar` con el mismo `msg_id` |
| 3.2 Idempotencia | `DedupeRedis` / `DedupeMemoria`; prueba: `tools/duplicado.py` |
| 3.3 Lamport en cada evento y orden `(Lamport, nodo)` | `common/events.py` (`new_event`, `orden_causal`); `Consumidor(ordenar=True)`; experimento: `tools/lamport_experimento.py` |
| 3.4 Saga con 3 pasos y compensaciones | `coordinator/saga.py` (`Orquestador`) |
| 3.4 Estado persistido | `coordinator/repo.py` (`saga:<id>`, `saga:<id>:log`) |
| 3.4 Escenarios (a) sin fallo y (b) falla en el paso 2 | `scripts/e3-flujo-completo.sh`, `scripts/e4-saga-falla.sh` (`--fail-step 2`) |
| 3.5 Dockerfile por componente, compose, README | `*/Dockerfile`, `docker-compose.yml`, `docker-compose.nodo.yml`, este README |

## 4. Despliegue

### Opción A — todo en una máquina (una VM o tu PC)

Requisitos: Docker y Docker Compose v2.

```bash
git clone <URL-del-repo> && cd taller2-integracion-transacciones
cp .env.example .env            # opcional: cambia las contraseñas
docker compose up -d --build    # broker + 3 Redis + 3 coordinadores + 3 agentes
docker compose ps
```

Consola de RabbitMQ: <http://localhost:15672> (usuario/clave del `.env`, por defecto `taller2` / `taller2-pass`).

### Opción B — repartido en 3 VM con Tailscale (una por integrante)

En cada VM (Debian 13): `./scripts/instalar-docker.sh`, `tailscale up`, copiar `config/cluster.vm.example.json` a
`config/cluster.vm.json` con las IP de Tailscale de las tres VM, copiar `.env.example` a `.env` (cambian
`NODE_ID`, `NODE_IP`, `AGENT_ID`) y:

```bash
docker compose -f docker-compose.nodo.yml up -d --build                   # VM 1 y VM 2
docker compose -f docker-compose.nodo.yml --profile broker up -d --build   # VM 3 (3 GB): además levanta RabbitMQ
```

Guía completa con comandos: [docs/Guía de despliegue y experimentos.md](docs/Gu%C3%ADa%20de%20despliegue%20y%20experimentos.md).
Imágenes con variante `amd64` y `arm64` (`python:3.12-slim`, `redis:7-alpine`, `rabbitmq:3.13-management-alpine`).

## 5. Uso y experimentos (E3, E4, E5)

```bash
docker compose exec agent1 python -m agent.request --cpu 1 --mem 256 --bw 10            # una asignación
docker compose exec agent1 python -m agent.request --cpu 2 --mem 512 --bw 20 --fail-step 2   # con falla en el paso 2
docker compose exec coord1 python -m tools.inspeccionar sagas                           # tabla de estados

./scripts/e3-flujo-completo.sh          # E3: flujo completo sin fallos
./scripts/e4-saga-falla.sh              # E4: falla en el paso 2 + compensación + tabla de estados
./scripts/e5-desconexion-broker.sh      # E5: broker caído, reintentos, reconexión, duplicados
./scripts/lamport-experimento.sh        # 3.3: dos agentes concurrentes y orden (Lamport, nodo)
./scripts/verificar-lista-avance.sh     # sección 6: lista de avance mínimo
```

`--fail-step N` es un **gancho de pruebas** de la solicitud: provoca un fallo en el paso N para demostrar la
compensación. Sin él, el sistema se comporta normalmente.

## 6. Pruebas

```bash
pip install -r requirements.txt && python proto/generar.py
PYTHONPATH=. python -m unittest discover -s tests -t .      # 25 pruebas sin Docker (Saga, orden, idempotencia, reintentos)
```

## 7. Estructura

```
proto/ schemas/        contrato gRPC (.proto) y esquema de eventos JSON (E2)
common/                eventos, Lamport, mensajería RabbitMQ, reintentos, cliente gRPC
coord/                 elección del Taller 1 (matón con términos y quórum) y su Redis maestro-réplica
agent/                 agente (+ Dockerfile)           coordinator/   coordinador y Saga (+ Dockerfile)
broker/  database/     Dockerfile de RabbitMQ y de Redis
config/                clúster de la elección (compose y VM)
tools/ scripts/        experimentos y verificación       tests/   pruebas unitarias
evidencias/            logs E3, E4, E5, Lamport          docs/    guías y plan de commits
```

## 8. Limitaciones

* La ordenación por Lamport es por lote (ventana de silencio): no garantiza orden global si un evento llega tarde.
* La Saga es orquestada por un único líder; tras un cambio de líder, las Sagas a medias se compensan (`recuperar`).
* La Saga no se reanuda hacia adelante, solo se compensa. Los mensajes no van cifrados (se confía en Tailscale).

## 9. Bibliotecas de terceros (norma 8)

[grpcio / grpcio-tools](https://grpc.io) (Apache-2.0), [pika](https://github.com/pika/pika) (BSD-3),
[redis-py](https://github.com/redis/redis-py) (MIT), RabbitMQ, Redis, Docker, Tailscale. El resto
(elección, Saga, mensajería fiable, ordenación, reintentos) está escrito en este repositorio y no proviene de bibliotecas de terceros.

## 10. Referencias

* Garcia-Molina, H., & Salem, K. (1987). Sagas. *ACM SIGMOD*.
* Lamport, L. (1978). Time, Clocks, and the Ordering of Events in a Distributed System. *CACM*, 21(7).
* Documentación oficial de RabbitMQ, Docker y Docker Compose, gRPC y Redis.
