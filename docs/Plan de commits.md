# Plan de commits (Taller 2)

El taller pide un repositorio con commits de todos los integrantes. El proyecto está dividido en 17 bloques que
`aplicar-commits.sh` confirma de a uno. **Cada persona ejecuta solo sus bloques con su propia identidad de Git**
(`git config user.name` / `user.email` solo en este repo) y cada quien debería poder explicar lo que sube. Se
respeta el orden numérico porque los bloques posteriores dependen de los anteriores.

| Bloque | Contenido | Sugerido |
|---|---|---|
| 1 | Estructura inicial, `.gitignore`, dependencias | José David |
| 2 | Contratos: `.proto` y esquema de eventos JSON (E2) | Gerson |
| 3 | Elección de coordinador del Taller 1 integrada (`coord/`) | José David |
| 4 | Utilidades comunes: eventos con Lamport, reintentos, log | Gerson |
| 5 | Mensajería RabbitMQ (confirmaciones, idempotencia, orden) | Gerson |
| 6 | Cliente gRPC con timeout, backoff y redirección al líder | José David |
| 7 | Agente | Gerson |
| 8 | Coordinador: repositorio, API gRPC, clientes de agentes | José David |
| 9 | Saga con compensaciones y arranque del coordinador | Gerson |
| 10 | Pruebas unitarias | José David |
| 11 | Dockerfiles de los cuatro componentes y configuración | José David |
| 12 | `docker-compose` (una máquina y repartido) y `.env.example` | José David |
| 13 | Herramientas y scripts de experimentos | Gerson |
| 14 | Documentación (README, guía, plan) | José David |
| 15 | Evidencias E3 y E4 | José David |
| 16 | Evidencia E5 y experimento de Lamport | Gerson |
| 17 | Informe (PDF) y su generador | José David |

Ajusten el reparto como prefieran; lo importante es que ambos tengan commits propios y que se refleje trabajo
de cada uno.

## Procedimiento

1. Crear el repositorio vacío en GitHub (cuenta personal) y agregar al otro integrante como colaborador
   (Settings → Collaborators).
2. En la carpeta del proyecto, una sola vez:
   ```bash
   git init -b main
   git remote add origin https://github.com/<usuario>/<repo>.git
   git config user.name "Nombre Apellido"
   git config user.email "correo-o-noreply"
   ```
3. Confirmar y subir los bloques propios, en orden: `./aplicar-commits.sh 1 3` y `git push -u origin main`.
4. La otra persona hace `git pull origin main`, confirma sus bloques y sube. Se alternan hasta el 17.
   `./aplicar-commits.sh lista` muestra todos los bloques.

Los bloques 15 a 17 (evidencias e informe) se hacen **después** de correr los experimentos en las VM.

## Qué NO se sube (ya está en `.gitignore`)

Claves privadas (`*.pem`, `*.key`, `.ssh/`), `.env`, `config/cluster.vm.json` (IP y contraseñas), los stubs
generados (`common/gen/`) y el `.docx` del informe.
