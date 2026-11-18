"""Genera el informe del Taller 2 en Word (estilo de los laboratorios anteriores).

    python informe/diagramas.py && python informe/generar_informe.py
Luego se exporta a PDF con Word o con .\informe\exportar_pdf.ps1.
"""
import os
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

AQUI = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(AQUI, "recursos")
LOGO = os.path.join(AQUI, "recursos", "logo-universidad-distrital.png")
SALIDA = os.path.join(AQUI, "Informe Taller 2 Integración y Transacciones.docx")
REPO = "(enlace del repositorio del Taller 2)"
FUENTE = "Calibri"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(1)
sec.top_margin = sec.bottom_margin = Inches(0.9)

st = doc.styles["Normal"]
st.font.name = FUENTE
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
st.paragraph_format.space_after = Pt(5)
st.paragraph_format.line_spacing = 1.07

for nombre, tam in (("Heading 1", 15), ("Heading 2", 12.5)):
    h = doc.styles[nombre]
    h.font.name = FUENTE
    h.font.size = Pt(tam)
    h.font.bold = False
    h.font.color.rgb = RGBColor(0, 0, 0)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
    h.element.rPr.rFonts.set(qn("w:ascii"), FUENTE)
    h.element.rPr.rFonts.set(qn("w:hAnsi"), FUENTE)
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(4)
    h.paragraph_format.keep_with_next = True


def runs(p, texto, size=None, italic=False):
    """Texto con **negrita**, *cursiva* y `código`."""
    import re
    for t in re.split(r"(\*\*.+?\*\*|`.+?`|\*[^*\s][^*]*?\*)", texto):
        if not t:
            continue
        if t.startswith("**"):
            r = p.add_run(t[2:-2]); r.bold = True
        elif t.startswith("`"):
            r = p.add_run(t[1:-1]); r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            if size is None:
                r.font.size = Pt(9.5)
        elif t.startswith("*") and len(t) > 2:
            r = p.add_run(t[1:-1]); r.italic = True
        else:
            r = p.add_run(t)
        if italic:
            r.italic = True
        if size and not t.startswith("`"):
            r.font.size = Pt(size)
        elif size:
            r.font.size = Pt(size - 0.5)
    return p


def par(texto, align=None, size=None, after=None, italic=False, keep=False):
    p = doc.add_paragraph()
    runs(p, texto, size, italic)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


def h1(t):
    return doc.add_heading(t, level=1)


def h2(t):
    return doc.add_heading(t, level=2)


def sombrear(celda, hexcolor):
    tcPr = celda._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def codigo(lineas):
    """Bloque de comandos (Consolas, fondo gris)."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    sombrear(c, "F2F2F2")
    c.paragraphs[0].text = ""
    for i, l in enumerate(lineas):
        p = c.paragraphs[0] if i == 0 else c.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(l)
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def tabla(cabecera, filas, anchos, size=8.5, negrita_primera=False):
    t = doc.add_table(rows=1, cols=len(cabecera))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, txt in enumerate(cabecera):
        c = t.rows[0].cells[i]
        sombrear(c, "F4B183")
        c.paragraphs[0].text = ""
        r = c.paragraphs[0].add_run(txt)
        r.bold = True
        r.font.size = Pt(size)
        c.paragraphs[0].paragraph_format.space_after = Pt(0)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for fila in filas:
        cells = t.add_row().cells
        for i, txt in enumerate(fila):
            cells[i].paragraphs[0].text = ""
            runs(cells[i].paragraphs[0], str(txt), size)
            cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
    for fila in t.rows:
        for i, w in enumerate(anchos):
            fila.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def imagen(nombre, ancho, centrar=True, after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if centrar:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(CAP, nombre), width=Inches(ancho))
    return p


def imagenes_lado_a_lado(izq, der, wi, wd):
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for celda, grupo, w in ((t.rows[0].cells[0], izq, wi), (t.rows[0].cells[1], der, wd)):
        celda.paragraphs[0].text = ""
        primero = True
        for nombre in grupo:
            p = celda.paragraphs[0] if primero else celda.add_paragraph()
            primero = False
            p.paragraph_format.space_after = Pt(3)
            p.add_run().add_picture(os.path.join(CAP, nombre), width=Inches(w))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def salto():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ====================================================================== PORTADA
par("Taller 2 de Sistemas Distribuidos Modernos", "c", size=12).runs[0].bold = True
for _ in range(5):
    par("", after=6)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(LOGO, width=Inches(2.1))
for _ in range(4):
    par("", after=6)
par("Integración, mensajería y transacciones: gRPC, RabbitMQ, relojes de Lamport y patrón Saga", "c",
    size=11).runs[0].bold = True
for _ in range(3):
    par("", after=6)
par("Gerson Steven Rodríguez Sendoya", "c", after=8)
par("José David Quintero Guerrero", "c", after=8)
for _ in range(3):
    par("", after=6)
for l in ("Universidad Distrital Francisco José de Caldas", "Facultad Tecnológica",
          "Ingeniería Telemática", "Bogotá D.C", "2026"):
    par(l, "c", after=8)
salto()

# ============================================================ 1. ARQUITECTURA
h1("1. Arquitectura integrada")
par("El Taller 2 se apoya en el Taller 1: los tres coordinadores corren la elección de líder (matón con términos "
    "y quórum) y su Redis maestro-réplica es la base de datos. Encima agregamos los cuatro componentes pedidos: "
    "**agente**, **coordinador**, **broker** (RabbitMQ) y **base de datos** (Redis), cada uno en un contenedor "
    "con su `Dockerfile`. Lo desplegamos en las mismas tres VM Debian 13 unidas por Tailscale: en cada VM corren un "
    "agente, un coordinador y un Redis, y la VM 3 (3 GB) aloja además el broker. Solo el coordinador líder atiende "
    "las llamadas gRPC y consume del broker; los otros dos quedan en espera y toman el relevo si el líder cae.")
imagen("diagrama-componentes.png", 4.9, after=4)
par("Una asignación recorre los componentes así. El agente la pide por gRPC al líder; el coordinador elige el nodo "
    "origen con las métricas, ejecuta la Saga (reservar en el agente origen, replicar en la base de datos, confirmar) "
    "y publica el resultado por el broker, que el agente confirma después de procesarlo.")
imagen("diagrama-secuencia.png", 4.9, after=2)
par("En las VM, el coordinador 2 ganó la elección (término 1, votos de los nodos 1 y 2) y los otros dos lo "
    "reconocieron como líder.", after=3)

# ================================================================ 2. CONTRATOS
h1("2. Contratos de comunicación y tipo de API")
par("Elegimos **gRPC** (archivo `proto/coordinator.proto`) en lugar de REST: el contrato es tipado y se compila a "
    "código para el agente y el coordinador, cada llamada admite un plazo (*deadline*) de forma nativa y ya lo "
    "habíamos usado en la práctica 3. Hay dos servicios:")
tabla(["Servicio", "Método", "Quién llama", "Qué hace"], [
    ["Coordinator", "`ReportMetrics`", "agente → líder", "Reporta recursos libres cada 3 s; responde `MetricsAck` con "
                                                          "las asignaciones vigentes del agente"],
    ["Coordinator", "`RequestAllocation`", "agente → líder", "Pide una asignación (id único = id de la Saga) y "
                                                             "devuelve su estado y la traza de pasos"],
    ["AgentControl", "`Reserve` / `Release` / `Commit`", "coordinador → agente", "Paso 1 de la Saga, su compensación "
                                                                                 "y el paso 3"],
], [1.1, 1.6, 1.2, 2.6])
par("**Timeouts y reintentos.** Toda llamada lleva plazo (3 s en métricas y en los pasos de la Saga, 5 s en la "
    "solicitud de asignación). Si el coordinador no responde, el agente reintenta con espera creciente (0,5 s, "
    "1 s, 2 s… hasta 8 s, con variación aleatoria, 6 intentos) y rota entre los coordinadores; si recibe "
    "`NOT_LEADER leader=<id>` salta directamente al líder. **Eventos asíncronos.** Todos los mensajes del broker "
    "comparten un sobre JSON (`schemas/event.schema.json`) con `msg_id`, tipo, nodo, marca de Lamport y carga útil. "
    "Hay tres colas durables, `metrics`, `allocations` y `failover`, más una cola de notificación por agente. El "
    "productor espera la confirmación del broker y el consumidor confirma solo después de procesar.")

# ============================================================= 3. LAMPORT
h1("3. Orden de eventos y experimento de Lamport")
par("Cada evento sale con la marca de Lamport de su emisor (el reloj avanza al publicar y al recibir cualquier "
    "mensaje). El coordinador acumula los eventos de la cola `metrics` en un lote (hasta 0,5 s de silencio o 3 s "
    "como máximo) y los procesa ordenados por el par **(marca de Lamport, identificador de nodo)**; el empate "
    "se rompe con el menor nodo. Para probarlo, dos agentes (nodos 101 y 102) publicaron 10 eventos cada uno "
    "**a la vez**, con eventos locales intercalados que adelantan sus relojes. Los 20 eventos se procesaron en el "
    "orden esperado, distinto del orden de publicación:")
imagen("capturas/lamport.png", 5.8, after=3)
par("En la captura se ve el desempate (3:102 se publicó antes que 3:101, pero se procesa después) y que 11:102, "
    "publicado después de 15:101, se procesa antes que 12:101. Resultado del experimento: **CORRECTO**, 20 de 20 "
    "eventos en orden. El límite del diseño es que el orden es por lote: un evento que llegue después de "
    "cerrada la ventana se procesa después.")

# ================================================================= 4. SAGA
h1("4. Diseño de la Saga")
tabla(["Paso", "Acción", "Compensación"], [
    ["1 Reservar", "El agente origen reserva CPU, memoria y ancho de banda (`Reserve`)", "Liberar la reserva (`Release`)"],
    ["2 Replicar", "Guardar `alloc:<id>` en Redis (el maestro replica a las demás bases)", "Borrar el registro"],
    ["3 Confirmar y notificar", "`Commit` en el agente y evento `allocation.result` al solicitante",
     "Liberar en el agente y borrar el registro"],
], [1.3, 3.4, 1.8])
par("El coordinador orquesta los pasos y, si uno falla, ejecuta las compensaciones de los ya hechos en orden "
    "inverso. **Estados:** `EN_CURSO` → `COMPLETADA`; `EN_CURSO` → `COMPENSANDO` → `COMPENSADA` (o `FALLIDA` si una "
    "compensación también falla); `RECHAZADA` si ningún nodo tiene capacidad. Cada transición se guarda en Redis "
    "(`saga:<id>` y un historial `saga:<id>:log`), así que sobrevive a un cambio de líder; las Sagas que queden a "
    "medias se compensan al asumir el nuevo líder. El identificador de la solicitud es el de la Saga: repetirla "
    "devuelve el resultado guardado sin repetir pasos (idempotencia).")

# ============================================================ 5. RESULTADOS
h1("5. Resultados de las pruebas")
h2("E3. Flujo completo sin fallos")
par("El agente 1 (VM 1) pidió 1 CPU, 256 MB y 10 Mbps. Como el coordinador 1 no era líder, el cliente se redirigió "
    "al coordinador 2 (VM 2), que ejecutó la Saga: reservó en el agente origen, replicó en la base de datos y "
    "confirmó. Terminó **COMPLETADA** en unos 100 ms, el agente recibió la notificación por el broker y la "
    "asignación se leyó desde la base de datos de otro nodo (réplica).", after=3)
imagen("capturas/e3.png", 5.8, after=3)
h2("E4. Falla en el paso 2 y compensación")
par("Con `--fail-step 2` el paso 2 falla a propósito. El coordinador compensó el paso 1 (el agente liberó la "
    "reserva) y la Saga quedó **COMPENSADA**; en la base de datos no quedó ningún registro de esa asignación. "
    "La captura muestra ambos escenarios y la tabla de estados guardada en Redis (incluye también la Saga que se "
    "compensó por el broker caído en E5):", after=3)
imagen("capturas/e4.png", 5.0, after=3)
h2("E5. Desconexión del broker y reintentos")
par("Detuvimos RabbitMQ 25 segundos con el sistema en marcha. Al instante, los productores y consumidores "
    "(agentes y coordinador) detectaron la pérdida y **reintentaron con espera creciente** (0,5 s, 1 s, 1,6 s… "
    "hasta 8 s):", after=3)
imagen("capturas/e5a.png", 5.0, after=3)
par("Al volver el broker, todos se **reconectaron** entre las 16:54:15 y las 16:54:21 (8 a 9 intentos) y el "
    "flujo de métricas continuó; los mensajes sin confirmar se reenviaron con el mismo `msg_id`. Con el broker "
    "caído también pedimos una asignación: la notificación del paso 3 no se pudo confirmar y la Saga se compensó "
    "completa (**COMPENSADA**). El cliente venció su plazo de 5 s, reintentó contra el líder y recibió el "
    "resultado guardado, sin repetir pasos. Por último, publicamos el **mismo mensaje tres veces**: el "
    "coordinador lo procesó una sola vez y descartó dos duplicados.", after=3)
imagen("capturas/e5b.png", 5.2, after=3)

# ================================================================ 6. AVANCE
h1("6. Estado de avance frente a la lista mínima")
tabla(["Punto de la sección 6", "Estado", "Evidencia"], [
    ["Los cuatro componentes implementados y en contenedores", "Cumple", "`docker compose ps` en las 3 VM"],
    ["Un agente reporta métricas al coordinador por la API definida", "Cumple", "logs de gRPC (`ReportMetrics`)"],
    ["Los eventos pasan por el broker y se procesan con confirmación", "Cumple", "`PROCESADO cola=metrics`"],
    ["Una asignación completa de extremo a extremo", "Cumple", "E3"],
    ["La base de datos replicada registra las asignaciones", "Cumple", "E3 (lectura en otro nodo)"],
    ["La Saga tiene sus compensaciones (y la prueba de falla)", "Cumple", "E4 y E5"],
    ["El repositorio se despliega con docker compose", "Cumple", "`docker-compose.yml` y `docker-compose.nodo.yml`"],
], [3.5, 0.8, 2.2])
par("Queda para el tercer corte: pruebas de falla más amplias (partición con el sistema integrado y matriz de "
    "caos), métricas finales y la documentación completa. Limitaciones conocidas: la ordenación por Lamport es por "
    "lote, la Saga solo compensa (no se reanuda hacia adelante) y los mensajes no van cifrados (se confía en "
    "Tailscale). Repositorio y evidencias: " + REPO + ".")

# ================================================================ BITACORA
salto()
h1("Bitácora de autoevaluación")
par("**José David Quintero Guerrero**", after=3)
par("En este taller seguí con la parte de infraestructura. Volví a levantar las tres máquinas virtuales, instalé "
    "Docker en cada una y desplegué los componentes con docker compose, revisando que los nodos se siguieran "
    "comunicando entre ellos por Tailscale. Lo que más me gustó fue ver crecer la arquitectura del Taller 1: sobre "
    "la misma base de coordinación y datos ahora hay agentes, un broker y una Saga, y todo funciona de forma "
    "integrada, con un coordinador que atiende y otros dos listos para reemplazarlo.")
par("También me pareció muy interesante la parte de los contratos de comunicación y el tipo de API, porque se ve "
    "cómo el archivo del contrato define exactamente lo que se dicen el agente y el coordinador, y el experimento "
    "de Lamport, porque con datos reales se comprueba que eventos publicados al mismo tiempo se procesan en el orden "
    "definido. Ver todo el sistema funcionando junto, incluso cuando apagamos el broker y los componentes se "
    "reconectaron solos, fue lo más gratificante. Siento que cumplí con mi parte y que sigo aprendiendo mucho "
    "sobre cómo se comporta un sistema distribuido cuando algo falla.")
par("", after=4)
par("**Gerson Steven Rodríguez Sendoya**", after=3)
par("Me pareció muy chévere el tema de los contratos de comunicación y del tipo de API; trabajar con gRPC me "
    "gustó mucho porque el contrato deja claro qué se envía y qué se responde entre las partes. Lo de los relojes "
    "de Lamport ya lo habíamos visto en clase, pero se me hizo bastante más interesante al aplicarlo, porque se "
    "entiende para qué sirve cuando hay eventos reales llegando al mismo tiempo desde distintos nodos.")
par("También me gustó trabajar con los flujos completos sobre las máquinas virtuales. Con los datos que "
    "generó el sistema es interesante analizarlos y hacer un resumen de lo que pasó, porque ayuda a entender cómo "
    "se comporta cada componente y cómo se recupera cuando algo falla.")

doc.save(SALIDA)
print("Guardado:", SALIDA)
