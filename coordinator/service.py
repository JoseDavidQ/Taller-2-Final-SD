"""Servidor gRPC del coordinador. Solo el líder elegido (Taller 1) atiende; los demás responden
FAILED_PRECONDITION con 'NOT_LEADER leader=<id>' para que el agente se redirija."""
import grpc

from common.gen import coordinator_pb2 as pb
from common.gen import coordinator_pb2_grpc as pbg


class Coordinador(pbg.CoordinatorServicer):
    def __init__(self, ctx):
        self.ctx = ctx  # ctx: repo, saga, eleccion, clock, log, publicar_evento

    def _exigir_lider(self, context):
        if not self.ctx.eleccion.es_lider():
            context.abort(grpc.StatusCode.FAILED_PRECONDITION,
                          f"NOT_LEADER leader={self.ctx.eleccion.lider_id() or ''}")

    def ReportMetrics(self, request, context):
        self._exigir_lider(context)
        c = self.ctx
        c.clock.update(request.lamport)
        datos = {"agent_id": request.agent_id, "address": request.agent_address,
                 "free": {"cpu": request.free.cpu, "mem_mb": request.free.mem_mb, "bw_mbps": request.free.bw_mbps},
                 "capacity": {"cpu": request.capacity.cpu, "mem_mb": request.capacity.mem_mb,
                              "bw_mbps": request.capacity.bw_mbps},
                 "cpu_load": request.cpu_load}
        previa = c.repo.metricas(request.agent_id)
        c.repo.guardar_metricas(request.agent_id, datos, request.lamport, request.node_id, "grpc")
        if previa and previa.get("down"):
            c.log(f"el agente {request.agent_id} volvió a reportar: nodo ARRIBA")
            c.publicar_evento("failover.node_up", {"agent_id": request.agent_id})
        activas = [pb.Assignment(saga_id=a["saga_id"], origin_node=a["origin"], state=a["state"],
                                 resources=pb.Resources(**a["resources"]))
                   for a in c.repo.asignaciones_de(request.agent_id)]
        c.log(f"métrica recibida por gRPC de {request.agent_id} (lamport={request.lamport}, "
              f"libres={datos['free']})")
        return pb.MetricsAck(accepted=True, lamport=c.clock.tick(), leader_id=str(c.eleccion.node_id),
                             term=c.eleccion.termino(), active_assignments=activas)

    def RequestAllocation(self, request, context):
        self._exigir_lider(context)
        c = self.ctx
        c.clock.update(request.lamport)
        c.log(f"solicitud de asignación {request.request_id[:8]} de {request.requester_id}: "
              f"{request.resources.cpu} cpu, {request.resources.mem_mb} MB, {request.resources.bw_mbps} Mbps")
        saga = c.saga.ejecutar({
            "request_id": request.request_id, "solicitante": request.requester_id,
            "recursos": {"cpu": request.resources.cpu, "mem_mb": request.resources.mem_mb,
                         "bw_mbps": request.resources.bw_mbps},
            "origen_preferido": request.preferred_origin, "falla_en_paso": request.fail_at_step})
        return pb.AllocationReply(saga_id=saga["saga_id"], state=saga["estado"], origin_node=saga.get("origen") or "",
                                  detail=saga.get("detalle", ""), lamport=c.clock.tick(),
                                  steps=c.saga.resumen(saga))
