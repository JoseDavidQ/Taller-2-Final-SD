import time
import unittest

from coord.clock import LamportClock
from coordinator.repo import Repo
from coordinator.saga import Orquestador

from .helpers import AgentesFalsos, MemRedis, PublicadorFalso

PEDIDO = {"cpu": 1, "mem_mb": 256, "bw_mbps": 10}


def armar():
    r = MemRedis()
    repo = Repo(r)
    for i in (1, 2):
        repo.guardar_metricas(f"agent{i}", {"address": f"agent{i}:50061", "free": {"cpu": 4, "mem_mb": 4096, "bw_mbps": 100},
                                            "capacity": {"cpu": 4, "mem_mb": 4096, "bw_mbps": 100}, "cpu_load": 0.1},
                              lamport=i, node_id=i, fuente="test")
    ag, pub = AgentesFalsos(), PublicadorFalso()
    saga = Orquestador(repo, ag, pub, LamportClock(), 1, lambda m: None)
    return repo, ag, pub, saga


def req(sid="s-1", falla=0, **kw):
    d = {"request_id": sid, "solicitante": "agent1", "recursos": dict(PEDIDO), "falla_en_paso": falla}
    d.update(kw)
    return d


class SagaTest(unittest.TestCase):
    def test_flujo_completo(self):
        repo, ag, pub, saga = armar()
        s = saga.ejecutar(req())
        self.assertEqual(s["estado"], "COMPLETADA")
        self.assertEqual([p["estado"] for p in s["pasos"]], ["OK", "OK", "OK"])
        self.assertEqual(repo.asignacion("s-1")["state"], "CONFIRMADA")
        self.assertIn("s-1", ag.asignadas)
        self.assertEqual(pub.enviados[-1][1]["payload"]["state"], "COMPLETADA")
        self.assertEqual(pub.enviados[-1][0], "allocation.result.agent1")

    def test_falla_paso2_compensa_paso1(self):
        repo, ag, pub, saga = armar()
        s = saga.ejecutar(req(falla=2))
        self.assertEqual(s["estado"], "COMPENSADA")
        self.assertEqual([p["estado"] for p in s["pasos"]], ["COMPENSADO", "FALLO", "PENDIENTE"])
        self.assertNotIn("s-1", ag.reservas)         # la reserva se liberó
        self.assertIsNone(repo.asignacion("s-1"))    # nada quedó replicado
        self.assertEqual(pub.enviados[-1][1]["payload"]["state"], "COMPENSADA")

    def test_falla_paso3_compensa_todo(self):
        repo, ag, pub, saga = armar()
        s = saga.ejecutar(req(falla=3))
        self.assertEqual(s["estado"], "COMPENSADA")
        self.assertIsNone(repo.asignacion("s-1"))
        self.assertNotIn("s-1", ag.reservas)
        self.assertNotIn("s-1", ag.asignadas)

    def test_notificacion_sin_broker_compensa(self):
        repo, ag, pub, saga = armar()
        pub.ok = False  # el broker no confirma
        s = saga.ejecutar(req())
        self.assertEqual(s["estado"], "COMPENSADA")
        self.assertNotIn("s-1", ag.asignadas)

    def test_rechazada_sin_capacidad(self):
        repo, ag, pub, saga = armar()
        s = saga.ejecutar(req(recursos={"cpu": 99, "mem_mb": 1, "bw_mbps": 1}))
        self.assertEqual(s["estado"], "RECHAZADA")
        self.assertEqual(ag.llamadas, [])

    def test_agente_rechaza_reserva(self):
        repo, ag, pub, saga = armar()
        ag.rechaza_reserva = True
        s = saga.ejecutar(req())
        self.assertEqual(s["estado"], "COMPENSADA")
        self.assertEqual(s["pasos"][0]["estado"], "FALLO")

    def test_compensacion_fallida(self):
        repo, ag, pub, saga = armar()
        ag.falla = {"liberar"}
        s = saga.ejecutar(req(falla=2))
        self.assertEqual(s["estado"], "FALLIDA")

    def test_idempotente(self):
        repo, ag, pub, saga = armar()
        a = saga.ejecutar(req())
        n = len(ag.llamadas)
        b = saga.ejecutar(req())
        self.assertEqual(a["estado"], b["estado"])
        self.assertEqual(len(ag.llamadas), n)  # no repitió pasos

    def test_estados_persistidos_en_orden(self):
        repo, ag, pub, saga = armar()
        saga.ejecutar(req(falla=2))
        h = " | ".join(repo.historial_saga("s-1"))
        self.assertIn("EN_CURSO", h)
        self.assertIn("COMPENSANDO", h)
        self.assertLess(h.index("EN_CURSO"), h.index("COMPENSANDO"))
        self.assertTrue(h.endswith("COMPENSANDO -> COMPENSADA"))

    def test_recuperacion_de_saga_a_medias(self):
        repo, ag, pub, saga = armar()
        ag.reservas["s-9"] = PEDIDO
        repo.guardar_saga({"saga_id": "s-9", "estado": "EN_CURSO", "origen": "agent1", "solicitante": "agent1",
                           "recursos": PEDIDO, "falla_en_paso": 0, "detalle": "",
                           "pasos": [{"n": 1, "nombre": "reservar", "estado": "OK"},
                                     {"n": 2, "nombre": "replicar", "estado": "PENDIENTE"},
                                     {"n": 3, "nombre": "confirmar y notificar", "estado": "PENDIENTE"}]})
        time.sleep(0.05)
        self.assertEqual(saga.recuperar(antiguedad=0), 1)
        self.assertEqual(repo.saga("s-9")["estado"], "COMPENSADA")
        self.assertNotIn("s-9", ag.reservas)


if __name__ == "__main__":
    unittest.main()
