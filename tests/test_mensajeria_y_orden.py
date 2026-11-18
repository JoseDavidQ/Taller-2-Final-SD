import unittest

import grpc

from agent.resources import Recursos
from common.coord_client import ClienteCoordinador, parsear_coordinadores
from common.events import new_event, orden_causal, validate_event
from common.messaging import DedupeMemoria, DedupeRedis
from common.retry import delays, retry
from coord.clock import LamportClock
from coordinator.repo import Repo

from .helpers import MemRedis


class EventosTest(unittest.TestCase):
    def test_evento_valido_y_lamport_crece(self):
        c = LamportClock()
        a = new_event("metrics.sample", 1, c, {"x": 1})
        b = new_event("metrics.sample", 1, c, {"x": 2})
        self.assertEqual(validate_event(a), [])
        self.assertLess(a["lamport"], b["lamport"])
        self.assertNotEqual(a["msg_id"], b["msg_id"])

    def test_evento_invalido(self):
        self.assertTrue(validate_event({"type": "x"}))

    def test_orden_por_lamport_y_nodo(self):
        evs = [{"lamport": 5, "node_id": 2, "msg_id": "c"}, {"lamport": 3, "node_id": 9, "msg_id": "a"},
               {"lamport": 5, "node_id": 1, "msg_id": "b"}]
        evs.sort(key=orden_causal)
        self.assertEqual([e["msg_id"] for e in evs], ["a", "b", "c"])  # empate de Lamport: menor nodo primero


class IdempotenciaTest(unittest.TestCase):
    def test_dedupe_memoria(self):
        d = DedupeMemoria()
        self.assertFalse(d.procesado("q", "m1"))
        d.marcar("q", "m1")
        self.assertTrue(d.procesado("q", "m1"))
        self.assertFalse(d.procesado("otra", "m1"))

    def test_dedupe_redis(self):
        d = DedupeRedis(MemRedis())
        self.assertFalse(d.procesado("metrics", "x"))
        d.marcar("metrics", "x")
        self.assertTrue(d.procesado("metrics", "x"))

    def test_metrica_vieja_no_pisa_a_la_nueva(self):
        repo = Repo(MemRedis())
        dato = {"address": "a:1", "free": {"cpu": 1, "mem_mb": 1, "bw_mbps": 1}, "capacity": {}, "cpu_load": 0}
        self.assertTrue(repo.guardar_metricas("ag", dato, lamport=10, node_id=1, fuente="broker"))
        self.assertFalse(repo.guardar_metricas("ag", dato, lamport=7, node_id=1, fuente="broker"))
        self.assertEqual(repo.metricas("ag")["lamport"], 10)


class RecursosTest(unittest.TestCase):
    def setUp(self):
        self.r = Recursos({"cpu": 4, "mem_mb": 1000, "bw_mbps": 100})
        self.p = {"cpu": 2, "mem_mb": 500, "bw_mbps": 50}

    def test_reservar_confirmar_liberar_idempotentes(self):
        self.assertTrue(self.r.reservar("s", self.p)[0])
        self.assertTrue(self.r.reservar("s", self.p)[0])            # repetida: no duplica
        self.assertEqual(self.r.libres()["cpu"], 2)
        self.assertTrue(self.r.confirmar("s")[0])
        self.assertTrue(self.r.confirmar("s")[0])
        self.assertEqual(self.r.libres()["cpu"], 2)
        self.r.liberar("s")
        self.r.liberar("s")
        self.assertEqual(self.r.libres()["cpu"], 4)

    def test_sin_capacidad(self):
        self.assertTrue(self.r.reservar("a", self.p)[0])
        self.assertTrue(self.r.reservar("b", self.p)[0])
        self.assertFalse(self.r.reservar("c", {"cpu": 1, "mem_mb": 1, "bw_mbps": 1})[0])


class ReintentosTest(unittest.TestCase):
    def test_backoff_crece_y_se_acota(self):
        g = delays(0.5, 2.0, 4.0, jitter=0)
        self.assertEqual([next(g) for _ in range(5)], [0.5, 1.0, 2.0, 4.0, 4.0])

    def test_retry_reintenta_y_luego_funciona(self):
        n = {"i": 0}
        esperas = []

        def f():
            n["i"] += 1
            if n["i"] < 3:
                raise OSError("x")
            return "ok"
        self.assertEqual(retry(f, intentos=5, base=0.1, jitter=0, retryable=(OSError,), sleep=esperas.append), "ok")
        self.assertEqual(esperas, [0.1, 0.2])

    def test_retry_agota(self):
        with self.assertRaises(OSError):
            retry(lambda: (_ for _ in ()).throw(OSError("x")), intentos=2, base=0.01, retryable=(OSError,),
                  sleep=lambda s: None)


class FakeErr(grpc.RpcError):
    def __init__(self, codigo, detalle=""):
        self._c, self._d = codigo, detalle

    def code(self):
        return self._c

    def details(self):
        return self._d


class StubFalso:
    def __init__(self, respuestas):
        self.resp, self.n = respuestas, 0

    def ReportMetrics(self, req, timeout=None):
        self.n += 1
        r = self.resp.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class ClienteCoordinadorTest(unittest.TestCase):
    def armar(self, por_id):
        cli = ClienteCoordinador(lambda canal: None, {"1": "a:1", "2": "b:2", "3": "c:3"}, lambda m: None,
                                 timeout=0.1, intentos=5, base=0.001, maximo=0.002)
        cli._stub = lambda cid: por_id[cid]
        return cli

    def test_parsear(self):
        self.assertEqual(parsear_coordinadores("1=a:1, 2=b:2"), {"1": "a:1", "2": "b:2"})

    def test_redirige_al_lider(self):
        s1 = StubFalso([FakeErr(grpc.StatusCode.FAILED_PRECONDITION, "NOT_LEADER leader=2")])
        s2 = StubFalso(["OK"])
        cli = self.armar({"1": s1, "2": s2, "3": StubFalso([])})
        self.assertEqual(cli.llamar("ReportMetrics", object()), "OK")
        self.assertEqual(cli.actual, "2")

    def test_reintenta_si_no_responde(self):
        s1 = StubFalso([FakeErr(grpc.StatusCode.UNAVAILABLE), FakeErr(grpc.StatusCode.DEADLINE_EXCEEDED)])
        s2 = StubFalso([FakeErr(grpc.StatusCode.UNAVAILABLE)])
        s3 = StubFalso(["OK"])
        cli = self.armar({"1": s1, "2": s2, "3": s3})
        self.assertEqual(cli.llamar("ReportMetrics", object()), "OK")

    def test_se_rinde_tras_los_intentos(self):
        e = FakeErr(grpc.StatusCode.UNAVAILABLE)
        cli = self.armar({k: StubFalso([e] * 9) for k in "123"})
        with self.assertRaises(grpc.RpcError):
            cli.llamar("ReportMetrics", object())


if __name__ == "__main__":
    unittest.main()
