# Guía de despliegue y experimentos (3 VM con Tailscale)

Usa las mismas 3 VM del Taller 1 (Debian 13; nodo 3 = 3 GB). Orden:

## 0. Encender las VM y conectarse (desde tu PC)

```powershell
gcloud compute instances start taller1-nodo1 taller1-nodo2 taller1-nodo3 --zone=us-central1-a --project=goia-back-prod --account=Aowner@tryvarx.com
gcloud compute instances list --filter="labels.proyecto=taller1" --project=goia-back-prod --account=Aowner@tryvarx.com
ssh -i $HOME\.ssh\taller1 taller@IP_EXTERNA_NUEVA
```

Las IP externas cambian al encender. Tailscale conserva las IP `100.x.y.z` (nodo 1 `100.108.57.51`,
nodo 2 `100.67.78.91`, nodo 3 `100.98.213.46`); comprueba con `tailscale status`.

> **Antes de empezar** apaga los servicios del Taller 1 para liberar memoria y puertos:
> `sudo systemctl disable --now coord-nodo@N` y `sudo systemctl stop redis-server` (el Taller 2 trae su propio Redis).

## 1. Copiar el repo a cada VM

Desde tu PC (o `git clone` si ya lo subieron a GitHub):

```powershell
cd "D:\Descargas\Documentos de identidad"
foreach ($ip in "IP1","IP2","IP3") { scp -i $HOME\.ssh\taller1 -r taller2-integracion-transacciones taller@${ip}:~/ }
```

## 2. En CADA VM: Docker y configuración

```bash
cd ~/taller2-integracion-transacciones
bash scripts/instalar-docker.sh && exit        # vuelve a entrar por SSH después (grupo docker)
```

```bash
cd ~/taller2-integracion-transacciones
cp config/cluster.vm.example.json config/cluster.vm.json
nano config/cluster.vm.json     # reemplaza 100.x.x.1/2/3 por las IP de Tailscale de los nodos 1, 2, 3
cp .env.example .env
nano .env                       # NODE_ID, NODE_IP, AGENT_ID (ver tabla), BROKER_HOST = IP del nodo 3, claves
```

| VM | NODE_ID | NODE_IP | AGENT_ID |
|---|---|---|---|
| nodo 1 | 1 | 100.108.57.51 | agent1 |
| nodo 2 | 2 | 100.67.78.91 | agent2 |
| nodo 3 | 3 | 100.98.213.46 | agent3 |

`BROKER_HOST=100.98.213.46` y `COORDINATORS=1=100.108.57.51:50051,2=100.67.78.91:50051,3=100.98.213.46:50051`
en las tres. `REDIS_PASSWORD` igual en las tres.

## 3. Levantar

```bash
# nodo 3 primero (broker):
docker compose -f docker-compose.nodo.yml --profile broker up -d --build
# nodos 1 y 2:
docker compose -f docker-compose.nodo.yml up -d --build
docker compose -f docker-compose.nodo.yml ps
docker compose -f docker-compose.nodo.yml logs -f coordinator       # ver "ELEGIDO LÍDER" / "SOY EL COORDINADOR"
```

La primera construcción tarda unos minutos (2 GB de RAM alcanzan).

> **Dos formas de correr los experimentos**
> * **Una VM** (la de 3 GB): `docker compose up -d --build` (Opción A, todo en una máquina). Los scripts
>   `scripts/e*.sh` y `scripts/lamport-experimento.sh` funcionan tal cual y dejan los logs en `evidencias/`.
> * **Tres VM** (Opción B): se demuestra con los comandos de la sección 4, que usan los servicios `agent`,
>   `coordinator` y `redis` de cada VM. Es la que prueba la comunicación entre máquinas por Tailscale.
> Para el informe conviene mostrar ambas: el despliegue repartido funcionando y los experimentos completos.

## 4. Comandos manuales en el despliegue repartido

```bash
export C="docker compose -f docker-compose.nodo.yml"
$C exec agent python -m agent.request --cpu 1 --mem 256 --bw 10               # E3: flujo completo
$C exec agent python -m agent.request --cpu 2 --mem 512 --bw 20 --fail-step 2  # E4: falla en el paso 2
$C exec coordinator python -m tools.inspeccionar sagas                        # tabla de estados
$C exec coordinator python -m tools.lamport_experimento 10                    # experimento de Lamport
$C exec coordinator python -m tools.duplicado                                  # idempotencia
# E5: en la VM del broker
$C stop rabbitmq; sleep 25; $C logs --tail 40 agent; $C start rabbitmq
# caída del coordinador líder (failover):
$C stop coordinator        # en la VM del líder; los agentes se redirigen al nuevo líder
```

## 5. Capturas que conviene tomar

1. `docker compose ps` con los componentes y el líder elegido.
2. E3: salida de `scripts/e3-flujo-completo.sh` (secuencia y tabla de la Saga).
3. E4: la tabla de estados y el historial de la Saga compensada.
4. E5: reintentos durante la caída y `RECONECTADO` al volver.
5. Experimento de Lamport: orden de publicación frente a orden de procesamiento.
6. `scripts/verificar-lista-avance.sh` con todo marcado.

## 6. Al terminar

```powershell
gcloud compute instances stop taller1-nodo1 taller1-nodo2 taller1-nodo3 --zone=us-central1-a --project=goia-back-prod --account=Aowner@tryvarx.com
```
