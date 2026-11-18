"""Cliente gRPC del coordinador: timeout en cada llamada, reintento con espera creciente y
redirección al líder (el Taller 1 elige un único coordinador; los demás responden NOT_LEADER)."""
import time

import grpc

from .retry import delays


def parsear_coordinadores(texto):
    """'1=coord1:50051,2=coord2:50051' -> {'1': 'coord1:50051', ...} (conserva el orden)."""
    res = {}
    for par in texto.split(","):
        par = par.strip()
        if not par:
            continue
        k, _, v = par.partition("=")
        res[k.strip()] = v.strip()
    return res


class ClienteCoordinador:
    def __init__(self, stub_factory, direcciones, log, timeout=3.0, intentos=6, base=0.5, factor=2.0,
                 maximo=8.0):
        self.stub_factory = stub_factory
        self.dirs = direcciones            # {id_coordinador: host:puerto}
        self.ids = list(direcciones)
        self.log, self.timeout, self.intentos = log, timeout, intentos
        self.base, self.factor, self.maximo = base, factor, maximo
        self.actual = self.ids[0]
        self._stubs = {}

    def _stub(self, cid):
        if cid not in self._stubs:
            self._stubs[cid] = self.stub_factory(grpc.insecure_channel(self.dirs[cid]))
        return self._stubs[cid]

    def llamar(self, metodo, request):
        """Invoca `metodo` en el líder. Reintenta con backoff si hay UNAVAILABLE / DEADLINE_EXCEEDED
        y salta al líder indicado cuando recibe NOT_LEADER. Lanza la última excepción si se agota."""
        gen = delays(self.base, self.factor, self.maximo)
        ultimo = None
        for n in range(1, self.intentos + 1):
            cid = self.actual
            try:
                return getattr(self._stub(cid), metodo)(request, timeout=self.timeout)
            except grpc.RpcError as e:
                ultimo = e
                codigo = e.code()
                detalle = e.details() or ""
                if codigo == grpc.StatusCode.FAILED_PRECONDITION and detalle.startswith("NOT_LEADER"):
                    lider = detalle.split("leader=")[-1].strip()
                    if lider in self.dirs and lider != cid:
                        self.log(f"[cliente] coordinador {cid} no es líder; paso al líder {lider}")
                        self.actual = lider
                        continue  # redirección: no cuenta como espera
                    siguiente = self.ids[(self.ids.index(cid) + 1) % len(self.ids)]
                    self.actual = siguiente
                elif codigo in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                    siguiente = self.ids[(self.ids.index(cid) + 1) % len(self.ids)]
                    self.actual = siguiente
                else:
                    raise
                if n == self.intentos:
                    break
                espera = next(gen)
                self.log(f"[cliente] {metodo} falló en {cid} ({codigo.name}); intento {n}/{self.intentos}, "
                         f"reintento en {espera:.1f}s hacia {self.actual}")
                time.sleep(espera)
        raise ultimo
