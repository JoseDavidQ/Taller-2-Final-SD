"""Adaptador con la elección de coordinador del Taller 1 (algoritmo del matón con términos y quórum).

Cada contenedor coordinador arranca un `coord.node.Node` del Taller 1 sobre su Redis local. Solo el
nodo que gana la elección es 'líder' (su Redis es el maestro) y por tanto el único que atiende
las llamadas gRPC y consume del broker. Los demás son réplicas en espera (failover)."""
import os

from coord import config as cfgmod
from coord.node import LIDER, Node, build_store


class Eleccion:
    def __init__(self, node_id, ruta_cluster, log_dir="/data/logs"):
        self.node_id = int(node_id)
        self.cfg = cfgmod.load(ruta_cluster)
        self.store = build_store("redis", self.node_id, self.cfg)
        self.node = Node(self.node_id, self.cfg, self.store, log_dir=log_dir)

    def iniciar(self):
        self.node.start()

    def es_lider(self):
        # líder lógico Y Redis local ya promovido a maestro (evita escribir en una réplica)
        if self.node.state != LIDER:
            return False
        try:
            return self.store.role() == "master"
        except Exception:
            return False

    def lider_id(self):
        return self.node.leader_id

    def termino(self):
        return int(self.node.term)

    def detener(self):
        self.node.stop()
