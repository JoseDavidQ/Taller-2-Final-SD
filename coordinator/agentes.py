"""Cliente gRPC hacia los agentes (pasos de la Saga) con timeout y reintentos con espera creciente."""
import grpc

from common.gen import coordinator_pb2 as pb
from common.gen import coordinator_pb2_grpc as pbg
from common.retry import retry

REINTENTABLES = (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


class ClientesAgente:
    def __init__(self, repo, clock, log, timeout=3.0, intentos=3):
        self.repo, self.clock, self.log = repo, clock, log
        self.timeout, self.intentos = timeout, intentos
        self._stubs = {}

    def _stub(self, agente):
        m = self.repo.metricas(agente)
        if not m or not m.get("address"):
            raise RuntimeError(f"no se conoce la dirección del agente {agente}")
        dir_ = m["address"]
        if dir_ not in self._stubs:
            self._stubs[dir_] = pbg.AgentControlStub(grpc.insecure_channel(dir_))
        return self._stubs[dir_]

    def _llamar(self, agente, metodo, req):
        def intento():
            try:
                return getattr(self._stub(agente), metodo)(req, timeout=self.timeout)
            except grpc.RpcError as e:
                if e.code() not in REINTENTABLES:
                    raise RuntimeError(f"{metodo} en {agente}: {e.code().name}")
                raise

        def aviso(n, espera, e):
            self.log(f"[saga] {metodo} hacia {agente} falló ({getattr(e, 'code', lambda: e)()}); "
                     f"reintento {n} en {espera:.1f}s")

        try:
            r = retry(intento, intentos=self.intentos, base=0.3, maximo=2.0,
                      retryable=(grpc.RpcError,), on_retry=aviso)
        except grpc.RpcError as e:
            raise RuntimeError(f"{metodo} en {agente}: {e.code().name} tras {self.intentos} intentos")
        self.clock.update(r.lamport)
        return r

    def reservar(self, agente, saga_id, recursos):
        r = self._llamar(agente, "Reserve", pb.ReserveRequest(
            saga_id=saga_id, resources=pb.Resources(**recursos), lamport=self.clock.tick()))
        return r.ok, r.detail

    def liberar(self, agente, saga_id):
        r = self._llamar(agente, "Release", pb.SagaRef(saga_id=saga_id, lamport=self.clock.tick()))
        return r.ok, r.detail

    def confirmar(self, agente, saga_id):
        r = self._llamar(agente, "Commit", pb.SagaRef(saga_id=saga_id, lamport=self.clock.tick()))
        return r.ok, r.detail
