import streamlit as st
import psycopg2
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# --------------------------------
# CONFIG
# --------------------------------
st.set_page_config(page_title="Sistema Comercial - NSJ CAPROYECT", layout="wide")

# --------------------------------
# CONEXIÓN BD
# --------------------------------
def conectar():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )


# --------------------------------
# FUNCIONES BD
# --------------------------------
def obtener_ventas():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
        FROM ventas
        WHERE cerrado = FALSE
        ORDER BY fecha DESC
    """)

    rows = cur.fetchall()
    conn.close()

    ventas = []
    for r in rows:
        ventas.append({
            "id": r[0],
            "Fecha": r[1],
            "Cliente": r[2],
            "Producto": r[3],
            "Total": float(r[4]),
            "Pagado": float(r[5]),
            "Saldo": float(r[6]),
            "Estado": r[7],
            "Método de pago": r[8],
            "Entrega": r[9]
        })
    return ventas

def registrar_venta(venta):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ventas 
        (fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        datetime.now(),
        venta["Cliente"],
        venta["Producto"],
        venta["Total"],
        venta["Pagado"],
        venta["Saldo"],
        venta["Estado"],
        venta["Método de pago"],
        venta["Entrega"]
    ))
    conn.commit()
    conn.close()
    st.success("✅ Venta registrada correctamente")
    st.rerun()

def completar_pago(id_venta, total):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ventas
        SET pagado=%s, saldo=0, estado='Pagado'
        WHERE id=%s
    """, (total, id_venta))
    conn.commit()
    conn.close()
    st.rerun()

def eliminar_venta(id_venta):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM ventas WHERE id=%s", (id_venta,))
    conn.commit()
    conn.close()
    st.rerun()

def marcar_entrega(id_venta, estado):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("UPDATE ventas SET entrega=%s WHERE id=%s", (estado, id_venta))
    conn.commit()
    conn.close()
    st.rerun()
    
def cierre_de_caja(usuario_actual):
    conn = conectar()
    cur = conn.cursor()

    # Obtener ventas cerrables
    cur.execute("""
        SELECT id, pagado, metodo_pago
        FROM ventas
        WHERE cerrado = FALSE
        AND entrega = 'Entregado'
        AND saldo = 0
    """)
    ventas = cur.fetchall()

    if not ventas:
        conn.close()
        return False

    total_general = 0
    totales_metodo = {
        "Efectivo": 0,
        "Yape": 0,
        "Plin": 0,
        "Transferencia": 0
    }

    ids = []

    for v in ventas:
        ids.append(v[0])
        monto = float(v[1])
        metodo = v[2]

        total_general += monto
        if metodo in totales_metodo:
            totales_metodo[metodo] += monto

    # Insertar cierre
    cur.execute("""
        INSERT INTO cierres_caja
        (fecha, total_general, total_efectivo, total_yape, total_plin, total_transferencia, usuario)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        datetime.now().date(),
        total_general,
        totales_metodo["Efectivo"],
        totales_metodo["Yape"],
        totales_metodo["Plin"],
        totales_metodo["Transferencia"],
        usuario_actual
    ))

    # Marcar ventas como cerradas
    cur.execute("""
        UPDATE ventas
        SET cerrado = TRUE
        WHERE id = ANY(%s)
    """, (ids,))

    conn.commit()
    conn.close()

    return True

def obtener_cierres():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT fecha, total_general, total_efectivo,
               total_yape, total_plin, total_transferencia,
               usuario, created_at
        FROM cierres_caja
        ORDER BY created_at DESC
    """)
    data = cur.fetchall()
    conn.close()
    return data


# --------------------------------
# INTERFAZ
# --------------------------------

st.title("Sistema Comercial - NSJ CAPROYECT")
st.divider()

METODOS_PAGO = ["Efectivo", "Yape", "Plin", "Transferencia"]

tab_venta, tab_ventas, tab_estadisticas, tab_reporte = st.tabs(
    ["➕ Nueva Venta", "📊 Ventas", "📈 Estadísticas", "📄 Reporte"]
)

# ======================================
# NUEVA VENTA
# ======================================
with tab_venta:
    cliente = st.text_input("Cliente")
    producto = st.text_input("Producto")
    total = st.number_input("Total", min_value=0.0)
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO)
    tipo_pago = st.radio("Tipo de pago", ["Pago completo", "Adelanto"])

    if tipo_pago == "Pago completo":
        pagado = total
        saldo = 0
        estado = "Pagado"
    else:
        adelanto = st.number_input("Monto adelanto", min_value=0.0)
        pagado = adelanto
        saldo = total - adelanto
        estado = "Pendiente" if saldo > 0 else "Pagado"

    entrega = st.selectbox("Estado de entrega", ["Pendiente", "Entregado"])

    if st.button("Registrar venta"):
        registrar_venta({
            "Cliente": cliente,
            "Producto": producto,
            "Total": total,
            "Pagado": pagado,
            "Saldo": saldo,
            "Estado": estado,
            "Método de pago": metodo_pago,
            "Entrega": entrega
        })

# ======================================
# VENTAS
# ======================================
with tab_ventas:
    ventas = obtener_ventas()

    if ventas:
        total_vendido = sum(v["Total"] for v in ventas)
        total_cobrado = sum(v["Pagado"] for v in ventas)
        total_pendiente = sum(v["Saldo"] for v in ventas)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Vendido", f"S/. {total_vendido:.2f}")
        col2.metric("Total Cobrado", f"S/. {total_cobrado:.2f}")
        col3.metric("Total Pendiente", f"S/. {total_pendiente:.2f}")

        for v in ventas:
            with st.container(border=True):
                st.write(f"Cliente: {v['Cliente']}")
                st.write(f"Producto: {v['Producto']}")
                st.write(f"Método: {v['Método de pago']}")
                st.write(f"Entrega: {v['Entrega']}")

                colA, colB, colC = st.columns(3)

                if v["Estado"] == "Pendiente":
                    if colA.button("Completar pago", key=f"p_{v['id']}"):
                        completar_pago(v["id"], v["Total"])

                if colB.button("Eliminar", key=f"d_{v['id']}"):
                    eliminar_venta(v["id"])

                nuevo = "Entregado" if v["Entrega"] == "Pendiente" else "Pendiente"
                if colC.button(f"Marcar {nuevo}", key=f"e_{v['id']}"):
                    marcar_entrega(v["id"], nuevo)

# ======================================
# ESTADÍSTICAS
# ======================================
with tab_estadisticas:
    ventas = obtener_ventas()

    if ventas:
        metodos = {}
        for v in ventas:
            metodos[v["Método de pago"]] = metodos.get(v["Método de pago"], 0) + v["Pagado"]

        st.subheader("Métodos de pago más usados")

        for metodo, monto in metodos.items():
            st.write(f"{metodo}: S/. {monto:.2f}")

# ======================================
# REPORTE PROFESIONAL
# ======================================
# ======================================
# REPORTE PROFESIONAL
# ======================================
with tab_reporte:

    st.divider()
    st.subheader("🔒 Cierre de Caja")

    if st.button("Realizar Cierre de Caja"):
        resultado = cierre_de_caja("Admin")

        if resultado:
            st.success("✅ Cierre realizado correctamente")
            st.rerun()
        else:
            st.warning("No hay ventas entregadas y pagadas para cerrar")

    st.divider()
    st.subheader("📜 Historial de Cierres")

    cierres = obtener_cierres()

    if cierres:
        for c in cierres:
            with st.container(border=True):
                st.write(f"📅 Fecha: {c[0]}")
                st.write(f"💰 Total General: S/. {c[1]}")
                st.write(f"Efectivo: S/. {c[2]}")
                st.write(f"Yape: S/. {c[3]}")
                st.write(f"Plin: S/. {c[4]}")
                st.write(f"Transferencia: S/. {c[5]}")
                st.write(f"👤 Usuario: {c[6]}")
                st.write(f"🕒 Registrado: {c[7]}")
    else:
        st.info("No hay cierres registrados aún.")

    st.divider()

    ventas = obtener_ventas()

    if not ventas:
        st.warning("No hay ventas para generar reporte")
    else:
        if st.button("Generar PDF"):

            nombre_pdf = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            doc = SimpleDocTemplate(nombre_pdf)
            elementos = []
            estilos = getSampleStyleSheet()

            elementos.append(Paragraph("<b>SISTEMA COMERCIAL - NSJ CAPROYECT</b>", estilos["Title"]))
            elementos.append(Spacer(1, 10))
            elementos.append(Paragraph(f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos["Normal"]))
            elementos.append(Spacer(1, 20))

            total_vendido = sum(v["Total"] for v in ventas)
            total_cobrado = sum(v["Pagado"] for v in ventas)
            total_pendiente = sum(v["Saldo"] for v in ventas)

            elementos.append(Paragraph(f"<b>Total Vendido:</b> S/. {total_vendido:.2f}", estilos["Normal"]))
            elementos.append(Paragraph(f"<b>Total Cobrado (Ganancia Real):</b> S/. {total_cobrado:.2f}", estilos["Normal"]))
            elementos.append(Paragraph(f"<b>Total Pendiente:</b> S/. {total_pendiente:.2f}", estilos["Normal"]))
            elementos.append(Spacer(1, 15))

            metodos = {}
            for v in ventas:
                metodos[v["Método de pago"]] = metodos.get(v["Método de pago"], 0) + v["Pagado"]

            elementos.append(Paragraph("<b>Resumen por Método de Pago:</b>", estilos["Heading2"]))
            elementos.append(Spacer(1, 10))

            for metodo, monto in metodos.items():
                elementos.append(Paragraph(f"{metodo}: S/. {monto:.2f}", estilos["Normal"]))

            elementos.append(Spacer(1, 20))

            elementos.append(Paragraph("<b>Detalle Completo de Ventas</b>", estilos["Heading2"]))
            elementos.append(Spacer(1, 10))

            data = [[
                "Fecha",
                "Cliente",
                "Producto",
                "Total",
                "Pagado",
                "Saldo",
                "Estado",
                "Método",
                "Entrega"
            ]]

            for v in ventas:
                data.append([
                    str(v["Fecha"]),
                    v["Cliente"],
                    v["Producto"],
                    f"S/. {v['Total']:.2f}",
                    f"S/. {v['Pagado']:.2f}",
                    f"S/. {v['Saldo']:.2f}",
                    v["Estado"],
                    v["Método de pago"],
                    v["Entrega"]
                ])

            tabla = Table(data, repeatRows=1)

            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8)
            ]))

            elementos.append(tabla)

            doc.build(elementos)

            with open(nombre_pdf, "rb") as f:
                st.download_button("Descargar PDF", f, nombre_pdf)

