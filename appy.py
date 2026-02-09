import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import tempfile

# =====================================================
# 🔐 CONFIGURA AQUI TU SUPABASE
# =====================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# LOGIN SIMPLE
# =====================================================

USUARIOS = {
    "caja": {"password": "1234", "rol": "caja"},
    "gerente": {"password": "admin123", "rol": "gerente"}
}

if "user" not in st.session_state:
    st.session_state.user = None

def login():
    st.title("🔐 Iniciar Sesión")

    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user in USUARIOS and USUARIOS[user]["password"] == password:
            st.session_state.user = USUARIOS[user]
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

if not st.session_state.user:
    login()
    st.stop()

# =====================================================
# CONFIG APP
# =====================================================

st.set_page_config(page_title="Sistema de Ventas", layout="wide")
st.title("🖨️ Sistema de Ventas - NSJ CAPROYECT")

rol = st.session_state.user["rol"]
st.sidebar.write(f"👤 Rol: {rol}")

if st.sidebar.button("Cerrar sesión"):
    st.session_state.user = None
    st.rerun()

# =====================================================
# FUNCIONES BD
# =====================================================

def obtener_ventas():
    response = supabase.table("ventas").select("*").execute()
    return pd.DataFrame(response.data)

def registrar_venta(data):
    supabase.table("ventas").insert(data).execute()

def eliminar_venta(id):
    supabase.table("ventas").delete().eq("id", id).execute()

# =====================================================
# PESTAÑAS
# =====================================================

tab_registrar, tab_ventas, tab_cierre = st.tabs(
    ["➕ Registrar Venta", "📊 Ventas", "📁 Cierre del Día"]
)

# =====================================================
# REGISTRAR VENTA
# =====================================================

with tab_registrar:

    if rol != "caja" and rol != "gerente":
        st.warning("No autorizado")
    else:
        cliente = st.text_input("Cliente")
        producto = st.selectbox("Producto", ["Banner", "Vinil", "Extra"])
        detalle = st.text_input("Detalle")
        total = st.number_input("Total (S/.)", min_value=1.0, step=1.0)
        pagado = st.number_input("Monto pagado", min_value=0.0, step=1.0)

        metodo_pago = st.selectbox(
            "Método de pago",
            ["Efectivo", "Yape", "Plin", "Transferencia"]
        )

        pendiente = total - pagado
        estado = "Pagado" if pendiente <= 0 else "Pendiente"

        if st.button("Guardar venta"):
            registrar_venta({
                "cliente": cliente,
                "producto": producto,
                "detalle": detalle,
                "metodo_pago": metodo_pago,
                "total": total,
                "pagado": pagado,
                "pendiente": pendiente,
                "estado": estado
            })
            st.success("Venta registrada")
            st.rerun()

# =====================================================
# VER VENTAS
# =====================================================

with tab_ventas:

    df = obtener_ventas()

    if df.empty:
        st.warning("No hay ventas")
    else:
        st.dataframe(df, use_container_width=True)

        total_general = df["total"].sum()
        st.metric("💰 Total General", f"S/. {total_general:.2f}")

        if rol == "gerente":
            ganancias = df["pagado"].sum()
            st.metric("💵 Ingreso Real Recibido", f"S/. {ganancias:.2f}")

        st.divider()

        for _, row in df.iterrows():
            col1, col2 = st.columns([4,1])
            with col1:
                st.write(f"**{row['cliente']}** - {row['producto']} - {row['estado']}")
            with col2:
                if st.button("Eliminar", key=row["id"]):
                    eliminar_venta(row["id"])
                    st.rerun()

# =====================================================
# CIERRE DEL DIA + PDF
# =====================================================

with tab_cierre:

    df = obtener_ventas()

    if df.empty:
        st.warning("No hay ventas")
    else:

        total_dia = df["total"].sum()

        if st.button("Generar PDF del día"):

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

            doc = SimpleDocTemplate(temp_file.name, pagesize=A4)
            elements = []

            styles = getSampleStyleSheet()

            elements.append(Paragraph("<b>NSJ CAPROYECT</b>", styles["Title"]))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))
            elements.append(Spacer(1, 12))

            data = [["Cliente", "Producto", "Total", "Estado"]]

            for _, row in df.iterrows():
                data.append([
                    row["cliente"],
                    row["producto"],
                    f"S/. {row['total']}",
                    row["estado"]
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.grey),
                ("GRID", (0,0), (-1,-1), 1, colors.black)
            ]))

            elements.append(table)
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"<b>Total del día: S/. {total_dia:.2f}</b>", styles["Heading2"]))

            doc.build(elements)

            with open(temp_file.name, "rb") as f:
                st.download_button(
                    "Descargar PDF",
                    f,
                    file_name="reporte_ventas.pdf"
                )

        if rol == "gerente":
            if st.button("Cerrar día (Eliminar todas las ventas)"):
                supabase.table("ventas").delete().neq("id", "").execute()
                st.success("Día cerrado")
                st.rerun()
