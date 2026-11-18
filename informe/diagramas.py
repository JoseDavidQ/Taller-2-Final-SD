"""Genera los diagramas del informe (componentes y secuencia) con matplotlib."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

AQUI = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(AQUI, "recursos")
os.makedirs(REC, exist_ok=True)
plt.rcParams["font.family"] = ["Calibri", "DejaVu Sans"]

AZUL, VERDE, NARANJA, GRIS, ROJO = "#DCE9F7", "#DDEFD9", "#F8D8B8", "#EEEEEE", "#F4C7C3"


def caja(ax, x, y, w, h, texto, color, size=8.5, bold=False, borde="#444444", estilo="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=color, ec=borde,
                                lw=1.1, ls=estilo))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal")


def flecha(ax, p, q, texto="", color="#333333", ls="-", dos=False, off=(0, 0.12), size=7.5):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="<->" if dos else "->", color=color, lw=1.2, ls=ls))
    if texto:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], texto, ha="center", va="center",
                fontsize=size, color=color, bbox=dict(fc="white", ec="none", pad=0.6))


def componentes():
    fig, ax = plt.subplots(figsize=(7.4, 3.9), dpi=200)
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 6.5)
    ax.axis("off")
    for i, y in enumerate((4.7, 2.95, 1.2)):
        caja(ax, 0.2, y, 2.2, 1.15, f"AGENTE {i + 1}\nVM {i + 1}\ngRPC :50061", AZUL, bold=False)
        lider = i == 1
        caja(ax, 4.6, y, 2.6, 1.15, f"COORDINADOR {i + 1}" + ("\n(LÍDER, Taller 1)" if lider else "\n(en espera)"),
             VERDE if lider else GRIS, bold=lider)
        caja(ax, 9.3, y, 2.5, 1.15, f"BASE DE DATOS {i + 1}\nRedis " + ("MAESTRO" if lider else "réplica"),
             NARANJA if lider else GRIS, bold=lider)
        flecha(ax, (2.4, y + 0.58), (4.6, y + 0.58), "gRPC" if i == 1 else "", dos=True,
               color="#1f4e9c" if lider else "#999999", ls="-" if lider else ":")
        flecha(ax, (7.2, y + 0.58), (9.3, y + 0.58), "datos" if lider else "", dos=True,
               color="#b4571b" if lider else "#999999", ls="-" if lider else ":")
    flecha(ax, (10.55, 4.7), (10.55, 4.1), "", color="#b4571b")
    ax.text(10.9, 4.4, "replica", fontsize=7, color="#b4571b", ha="left")
    flecha(ax, (10.55, 2.95), (10.55, 2.35), "", color="#b4571b")
    caja(ax, 4.2, 0.1, 3.4, 0.6, "BROKER  RabbitMQ  (VM 3)", ROJO, bold=True)
    ax.text(0.2, 0.4, "metrics · allocations · failover\nagent.<id>.notify", fontsize=7.5, va="center")
    for x in (1.3,):
        flecha(ax, (1.3, 1.2), (4.2, 0.45), "AMQP", color="#a33", off=(-0.3, 0.2))
    flecha(ax, (5.9, 1.2), (5.9, 0.7), "AMQP", color="#a33", off=(0.55, 0))
    ax.text(6.1, 6.25, "Los 3 coordinadores forman la elección del Taller 1; solo el líder atiende gRPC y consume del broker",
            ha="center", fontsize=7.5, style="italic")
    fig.savefig(os.path.join(REC, "diagrama-componentes.png"), bbox_inches="tight")
    plt.close(fig)


def secuencia():
    fig, ax = plt.subplots(figsize=(7.4, 3.6), dpi=200)
    nombres = ["Agente 1\n(solicitante)", "Coordinador\nlíder", "Agente origen", "Redis\n(maestro→réplicas)", "RabbitMQ"]
    xs = [0.8, 3.1, 5.4, 7.7, 10.0]
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.2, 9.2)
    ax.axis("off")
    for x, n in zip(xs, nombres):
        caja(ax, x - 0.85, 8.35, 1.7, 0.7, n, AZUL, size=7.6)
        ax.plot([x, x], [0.1, 8.35], color="#999999", lw=0.9, ls="--")
    pasos = [
        (0, 1, 7.8, "1. RequestAllocation(id)", "-"),
        (1, 3, 7.1, "2. guarda Saga EN_CURSO", "-"),
        (1, 2, 6.4, "3. Paso 1: Reserve", "-"),
        (2, 1, 5.8, "reserva OK", ":"),
        (1, 3, 5.1, "4. Paso 2: guarda alloc:<id> (replica)", "-"),
        (1, 2, 4.4, "5. Paso 3: Commit", "-"),
        (2, 1, 3.8, "confirmada", ":"),
        (1, 4, 3.1, "6. publica allocation.result.<agente>", "-"),
        (4, 0, 2.4, "7. notificación (ack tras procesar)", "-"),
        (1, 0, 1.7, "8. AllocationReply: COMPLETADA", ":"),
    ]
    for a, b, y, t, ls in pasos:
        ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y), arrowprops=dict(arrowstyle="->", lw=1.1, ls=ls, color="#222"))
        ax.text((xs[a] + xs[b]) / 2, y + 0.18, t, ha="center", fontsize=7.2,
                bbox=dict(fc="white", ec="none", pad=0.4))
    ax.text(5.5, 0.55, "Si el paso 2 o el 3 falla: compensación en orden inverso (liberar reserva, borrar registro) → COMPENSADA",
            ha="center", fontsize=7.4, color="#a33", style="italic")
    fig.savefig(os.path.join(REC, "diagrama-secuencia.png"), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    componentes()
    secuencia()
    print("diagramas generados en", REC)
