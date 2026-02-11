import streamlit as st
import psycopg2
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os

# --------------------------------
# CONFIG
# --------------------------------
st.set_page_config(page_title="Sistema de Ventas - NSJ CAPROYECT", layout="wide")

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
        (cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
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
        SET pagado = %s, saldo = 0, estado = 'Pagado'
        WHERE id = %s
    """, (total, id_venta))
    conn.commit()
    conn.close()
    st.rerun()


def eliminar_venta(id_venta):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM ventas WHERE id = %s", (id_venta,))
    conn.commit()
    conn.close()
    st.rerun()


def marcar_entrega(id_venta, estado):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ventas
        SET entrega = %s
        WHERE id = %s
    """, (estado, id_venta))
    conn.commit()
    conn.close()
    st.rerun()


# --------------------------------
# INTERFAZ
# --------------------------------
st.title("Sistema de Ventas - NSJ CAPROYECT")
st.divider()

METODOS_PAGO = ["Efectivo", "Yape", "Plin", "Transferencia"]

tab_venta, tab_ventas, tab_reporte = st.tabs(
    ["➕ Nueva Venta", "📊 Ventas", "📄 Reporte"]
)

# ======================================
# NUEVA VENTA
# ======================================
with tab_venta:

    cliente = st.text_input("Cliente")
    producto = st.text_input("Producto")
    total = st.number_input("Total", min_value=0.0, step=1.0)
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO)

    tipo_pago = st.radio("Tipo de pago", ["Pago completo", "Adelanto"])

    if tipo_pago == "Pago completo":
        pagado = total
        saldo = 0
        estado = "Pagado"
    else:
        adelanto = st.number_input("Monto adelanto", min_value=0.0, step=1.0)
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

    if not ventas:
        st.warning("No hay ventas registradas")
    else:
        total_dia = sum(v["Total"] for v in ventas)
        total_cobrado = sum(v["Pagado"] for v in ventas)
        total_pendiente = sum(v["Saldo"] for v in ventas)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total vendido", f"S/. {total_dia:.2f}")
        col2.metric("Total cobrado", f"S/. {total_cobrado:.2f}")
        col3.metric("Total pendiente", f"S/. {total_pendiente:.2f}")

        st.divider()

        for v in ventas:
            with st.container(border=True):
                st.write(f"👤 Cliente: {v['Cliente']}")
                st.write(f"📦 Producto: {v['Producto']}")
                st.write(f"💰 Total: S/. {v['Total']}")
                st.write(f"💵 Pagado: S/. {v['Pagado']}")
                st.write(f"🧾 Saldo: S/. {v['Saldo']}")
                st.write(f"📌 Estado: {v['Estado']}")
                st.write(f"💳 Método: {v['Método de pago']}")
                st.write(f"🚚 Entrega: {v['Entrega']}")

                colA, colB, colC = st.columns(3)

                if v["Estado"] == "Pendiente":
                    if colA.button("Completar pago", key=f"pago_{v['id']}"):
                        completar_pago(v["id"], v["Total"])

                if colB.button("Eliminar", key=f"del_{v['id']}"):
                    eliminar_venta(v["id"])

                nuevo_estado = "Entregado" if v["Entrega"] == "Pendiente" else "Pendiente"
                if colC.button(f"Marcar {nuevo_estado}", key=f"ent_{v['id']}"):
                    marcar_entrega(v["id"], nuevo_estado)

# ======================================
# REPORTE PDF
# ======================================
with tab_reporte:

    ventas = obtener_ventas()

    if st.button("Generar PDF"):
        nombre_pdf = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        doc = SimpleDocTemplate(nombre_pdf)
        elementos = []
        estilos = getSampleStyleSheet()

        elementos.append(Paragraph("<b>REPORTE DE VENTAS</b>", estilos["Title"]))
        elementos.append(Spacer(1, 20))

        data = [["Cliente", "Producto", "Total", "Pagado", "Saldo", "Estado", "Método", "Entrega"]]

        for v in ventas:
            data.append([
                v["Cliente"],
                v["Producto"],
                f"S/. {v['Total']}",
                f"S/. {v['Pagado']}",
                f"S/. {v['Saldo']}",
                v["Estado"],
                v["Método de pago"],
                v["Entrega"]
            ])

        tabla = Table(data, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        elementos.append(tabla)
        doc.build(elementos)

        with open(nombre_pdf, "rb") as f:
            st.download_button("Descargar PDF", f, nombre_pdf)
