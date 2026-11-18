"""Dobles de prueba: Redis en memoria, agentes y publicador falsos."""
import fnmatch


class MemRedis:
    """Subconjunto de redis-py suficiente para Repo y DedupeRedis."""

    def __init__(self):
        self.d, self.l, self.s = {}, {}, {}

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v, ex=None):
        self.d[k] = v

    def exists(self, k):
        return 1 if k in self.d else 0

    def delete(self, k):
        self.d.pop(k, None)

    def scan_iter(self, patron):
        return [k for k in list(self.d) if fnmatch.fnmatch(k, patron)]

    def rpush(self, k, v):
        self.l.setdefault(k, []).append(v)

    def lrange(self, k, a, b):
        x = self.l.get(k, [])
        return x if b == -1 else x[a:b + 1]

    def sadd(self, k, v):
        self.s.setdefault(k, set()).add(v)

    def smembers(self, k):
        return set(self.s.get(k, set()))


class AgentesFalsos:
    """Imita ClientesAgente con reservas en memoria y fallos programables."""

    def __init__(self, capacidad=None):
        self.reservas, self.asignadas, self.llamadas = {}, {}, []
        self.falla = set()       # nombres de métodos que lanzan RuntimeError
        self.rechaza_reserva = False

    def reservar(self, agente, sid, rec):
        self.llamadas.append(("reservar", agente, sid))
        if "reservar" in self.falla:
            raise RuntimeError("agente inalcanzable")
        if self.rechaza_reserva:
            return False, "sin capacidad"
        self.reservas[sid] = rec
        return True, "reservada"

    def liberar(self, agente, sid):
        self.llamadas.append(("liberar", agente, sid))
        if "liberar" in self.falla:
            raise RuntimeError("agente inalcanzable")
        self.reservas.pop(sid, None)
        self.asignadas.pop(sid, None)
        return True, "liberada"

    def confirmar(self, agente, sid):
        self.llamadas.append(("confirmar", agente, sid))
        if "confirmar" in self.falla:
            raise RuntimeError("agente inalcanzable")
        r = self.reservas.pop(sid, None)
        if r is None:
            return False, "sin reserva"
        self.asignadas[sid] = r
        return True, "confirmada"


class PublicadorFalso:
    def __init__(self):
        self.enviados, self.ok = [], True

    def publicar(self, clave, ev, max_wait=0):
        if not self.ok:
            return False
        self.enviados.append((clave, ev))
        return True
