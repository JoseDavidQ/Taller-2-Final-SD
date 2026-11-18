"""Acceso a la base de datos (Redis maestro-réplica del Taller 1): métricas, Sagas, asignaciones,
orden de eventos procesados e idempotencia.

Solo usa get/set/exists/delete/rpush/lrange/sadd/smembers/scan_iter, así que se puede probar con un
Redis en memoria (tests/helpers.py)."""
import json
import time

CLAVES = ("cpu", "mem_mb", "bw_mbps")
TERMINALES = ("COMPLETADA", "COMPENSADA", "RECHAZADA", "FALLIDA")


class Repo:
    def __init__(self, r):
        self.r = r

    # ------------------------------------------------------------ métricas
    def guardar_metricas(self, agente, datos, lamport, node_id, fuente):
        """Guarda la métrica solo si es más reciente en el orden (Lamport, nodo). Idempotente."""
        previa = self.metricas(agente)
        if previa and (previa["lamport"], previa["node_id"]) > (lamport, node_id):
            return False
        rec = dict(datos, lamport=lamport, node_id=node_id, ts=time.time(), source=fuente, down=False)
        self.r.set(f"metrics:{agente}", json.dumps(rec, sort_keys=True))
        return True

    def metricas(self, agente):
        v = self.r.get(f"metrics:{agente}")
        return json.loads(v) if v else None

    def todas_metricas(self):
        res = {}
        for k in self.r.scan_iter("metrics:*"):
            k = k.decode() if isinstance(k, bytes) else k
            v = self.r.get(k)
            if v:
                res[k.split(":", 1)[1]] = json.loads(v)
        return res

    def marcar_nodo(self, agente, down):
        m = self.metricas(agente)
        if m is None:
            return False
        cambio = bool(m.get("down")) != down
        m["down"] = down
        self.r.set(f"metrics:{agente}", json.dumps(m, sort_keys=True))
        return cambio

    def elegir_origen(self, pedido, preferido="", frescura=15.0):
        """Nodo vivo con capacidad suficiente; entre varios, el de más CPU libre."""
        ahora = time.time()
        mejores = []
        for ag, m in self.todas_metricas().items():
            if m.get("down") or ahora - m["ts"] > frescura:
                continue
            if preferido and ag != preferido:
                continue
            libres = m["free"]
            if all(libres[k] >= pedido[k] for k in CLAVES):
                mejores.append((libres["cpu"], libres["mem_mb"], ag))
        if not mejores:
            return None
        return max(mejores)[2]

    # --------------------------------------------------------------- sagas
    def saga(self, sid):
        v = self.r.get(f"saga:{sid}")
        return json.loads(v) if v else None

    def guardar_saga(self, s):
        s["updated"] = time.time()
        self.r.set(f"saga:{s['saga_id']}", json.dumps(s, sort_keys=True))
        self.r.sadd("sagas", s["saga_id"])

    def log_saga(self, sid, linea):
        self.r.rpush(f"saga:{sid}:log", f"{time.strftime('%H:%M:%S', time.gmtime())} {linea}")

    def historial_saga(self, sid):
        return [x.decode() if isinstance(x, bytes) else x for x in self.r.lrange(f"saga:{sid}:log", 0, -1)]

    def ids_sagas(self):
        return sorted(x.decode() if isinstance(x, bytes) else x for x in self.r.smembers("sagas"))

    # -------------------------------------------------------- asignaciones
    def guardar_asignacion(self, sid, rec):
        self.r.set(f"alloc:{sid}", json.dumps(rec, sort_keys=True))

    def asignacion(self, sid):
        v = self.r.get(f"alloc:{sid}")
        return json.loads(v) if v else None

    def borrar_asignacion(self, sid):
        self.r.delete(f"alloc:{sid}")

    def asignaciones_de(self, agente):
        res = []
        for k in self.r.scan_iter("alloc:*"):
            k = k.decode() if isinstance(k, bytes) else k
            v = self.r.get(k)
            if v:
                a = json.loads(v)
                if a.get("origin") == agente and a.get("state") == "CONFIRMADA":
                    res.append(a)
        return res

    # ------------------------------------------------------- orden (Lamport)
    def registrar_orden(self, cola, ev):
        self.r.rpush(f"order:{cola}", f"{ev['lamport']}:{ev['node_id']}:{ev['msg_id']}:{ev['type']}")

    def orden(self, cola):
        return [x.decode() if isinstance(x, bytes) else x for x in self.r.lrange(f"order:{cola}", 0, -1)]
