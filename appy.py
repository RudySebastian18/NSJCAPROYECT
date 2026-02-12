import streamlit as st
import psycopg2
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Sistema NSJ CAPROYECT", layout="wide")

# ---------------------------
# CONEXIÓN
# ---------------------------
def conectar():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )

# ---------------------------
# LOGIN
# ---------------------------
def verificar_usuario(usuario, password):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, rol FROM usuarios WHERE usuario=%s AND password=%s",
        (usuario, password)
    )
    user = cur.fetchone()
    conn.close()
    return user

if "usuario_id" not in st.session_state:
    st.session_state.usuario_id = None
    st.session_state.rol = None

if st.session_state.usuario_id is None:
    st.title("🔐 Iniciar Sesión")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        user = verificar_usuario(usuario, password)
        if user:
            st.session_state.usuario_id = user[0]
            st.session_state.rol = user[1]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

# ---------------------------
# FUNCIONES BD
# ---------------------------
def obtener_ventas():
    conn = conectar()
    cur = conn.cursor()

    if st.session_state.rol == "admin":
        cur.execute("""
            SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
            FROM ventas
            ORDER BY fecha DESC
        """)
    else:
        cur.execute("""
            SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
            FROM ventas
            WHERE usuario_id=%s
            ORDER BY fecha DESC
        """, (st.session_state.usuario_id,))

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
            "Método": r[8],
            "Entrega": r[9]
        })
    return ventas

# ---------------------------
# INTERFAZ
# ---------------------------
st.sidebar.write(f"Usuario: {st.session_state.rol}")
if st.sidebar.button("Cerrar sesión"):
    st.session_state.usuario_id = None
    st.rerun()

st.title("Sistema Comercial - NSJ CAPROYECT")

tab1, tab2, tab3 = st.tabs(["📊 Ventas", "📈 Estadísticas", "📄 Reporte Profesional"])

ventas = obtener_ventas()

# =====================================================
# 📊 VENTAS
# =====================================================
with tab1:

    if not ventas:
        st.warning("No hay ventas registradas")
    else:
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
                st.write(f"Método: {v['Método']}")
                st.write(f"Entrega: {v['Entrega']}")

# =====================================================
# 📈 ESTADÍSTICAS
# =====================================================
with tab2:

    if ventas:
        metodos = {}
        for v in ventas:
            metodos[v["Método"]] = metodos.get(v["Método"], 0) + v["Pagado"]

        st.subheader("Ingresos por Método de Pago")

        for metodo, total in metodos.items():
            st.metric(metodo, f"S/. {total:.2f}")

        st.subheader("Resumen General")

        ganancia_total = sum(v["Pagado"] for v in ventas)
        st.success(f"💰 Ganancia Total: S/. {ganancia_total:.2f}")

# =====================================================
# 📄 REPORTE PROFESIONAL
# =====================================================
with tab3:

    if st.button("Generar Reporte Profesional PDF"):

        nombre_pdf = "reporte_profesional.pdf"
        doc = SimpleDocTemplate(nombre_pdf)
        elementos = []
        estilos = getSampleStyleSheet()

        elementos.append(Paragraph("<b>NSJ CAPROYECT</b>", estilos["Title"]))
        elementos.append(Spacer(1, 12))
        elementos.append(Paragraph("Reporte General de Ventas", estilos["Heading2"]))
        elementos.append(Spacer(1, 20))

        data = [["Cliente", "Producto", "Total", "Pagado", "Método"]]

        for v in ventas:
            data.append([
                v["Cliente"],
                v["Producto"],
                f"S/. {v['Total']}",
                f"S/. {v['Pagado']}",
                v["Método"]
            ])

        tabla = Table(data, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.black),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))

        elementos.append(tabla)
        elementos.append(Spacer(1, 30))

        total_vendido = sum(v["Total"] for v in ventas)
        total_cobrado = sum(v["Pagado"] for v in ventas)

        elementos.append(Paragraph(f"<b>Total Vendido:</b> S/. {total_vendido:.2f}", estilos["Normal"]))
        elementos.append(Paragraph(f"<b>Total Cobrado (Ganancia):</b> S/. {total_cobrado:.2f}", estilos["Normal"]))
        elementos.append(Spacer(1, 15))

        elementos.append(Paragraph("<b>Ingresos por Método de Pago:</b>", estilos["Heading3"]))

        metodos = {}
        for v in ventas:
            metodos[v["Método"]] = metodos.get(v["Método"], 0) + v["Pagado"]

        for metodo, total in metodos.items():
            elementos.append(Paragraph(f"{metodo}: S/. {total:.2f}", estilos["Normal"]))

        doc.build(elementos)

        with open(nombre_pdf, "rb") as f:
            st.download_button("Descargar PDF", f, nombre_pdf)
