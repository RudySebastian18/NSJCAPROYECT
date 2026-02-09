import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
import os

# ===================================
# CONFIGURACIÓN
# ===================================
st.set_page_config(page_title="Sistema NSJ CAPROYECT", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===================================
# LOGIN
# ===================================
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def login():
    st.title("🔐 Inicio de Sesión")

    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):

        if user == st.secrets["GERENTE_USER"] and password == st.secrets["GERENTE_PASS"]:
            st.session_state.user_role = "gerente"
            st.rerun()

        elif user == st.secrets["VENDEDOR_USER"] and password == st.secrets["VENDEDOR_PASS"]:
            st.session_state.user_role = "vendedor"
            st.rerun()

        else:
            st.error("Credenciales incorrectas")

if st.session_state.user_role is None:
    login()
    st.stop()

# ===================================
# HEADER
# ===================================
col1, col2 = st.columns([6,1])
with col1:
    st.title("🖨️ Sistema de Ventas - NSJ CAPROYECT")
with col2:
    if st.button("Cerrar sesión"):
        st.session_state.user_role = None
        st.rerun()

# ===================================
# FUNCIONES
# ===================================
def registrar_venta(data):
    supabase.table("ventas").insert(data).execute()
    st.success("✅ Venta registrada")
    st.rerun()

def obtener_ventas():
    return supabase.table("ventas").select("*").order("fecha", desc=True).execute().data

# ===================================
# TABS
# ===================================
tabs = ["💰 Venta Completa", "🟡 Adelanto", "🧾 Completar Pago", "📁 PDF"]

if st.session_state.user_role == "gerente":
    tabs.append("📊 Panel Gerente")

tab_objects = st.tabs(tabs)

# ===================================
# 💰 VENTA COMPLETA
# ===================================
with tab_objects[0]:

    cliente = st.text_input("Cliente")
    producto = st.text_input("Producto")
    detalle = st.text_input("Detalle")
    metodo_pago = st.selectbox("Método de pago", ["Efectivo","Yape","Plin","Transferencia"])
    total = st.number_input("Total", min_value=1.0, step=1.0)

    if st.button("Registrar Venta"):
        registrar_venta({
            "cliente": cliente,
            "producto": producto,
            "detalle": detalle,
            "metodo_pago": metodo_pago,
            "total": total,
            "tipo_pago": "Completo",
            "monto_pagado": total,
            "restante": 0
        })

# ===================================
# 🟡 ADELANTO
# ===================================
with tab_objects[1]:

    cliente = st.text_input("Cliente (adelanto)")
    producto = st.text_input("Producto (adelanto)")
    detalle = st.text_input("Detalle (adelanto)")
    metodo_pago = st.selectbox("Método de pago (adelanto)", ["Efectivo","Yape","Plin","Transferencia"])
    total = st.number_input("Total del producto", min_value=1.0, step=1.0)
    adelanto = st.number_input("Monto adelantado", min_value=1.0, step=1.0)

    if st.button("Registrar Adelanto"):
        registrar_venta({
            "cliente": cliente,
            "producto": producto,
            "detalle": detalle,
            "metodo_pago": metodo_pago,
            "total": total,
            "tipo_pago": "Adelanto",
            "monto_pagado": adelanto,
            "restante": total - adelanto
        })

# ===================================
# 🧾 COMPLETAR PAGO
# ===================================
with tab_objects[2]:

    pendientes = supabase.table("ventas").select("*").gt("restante",0).execute().data

    if not pendientes:
        st.success("No hay pagos pendientes")
    else:
        for venta in pendientes:
            with st.container(border=True):
                st.write(f"Cliente: {venta['cliente']}")
                st.write(f"Producto: {venta['producto']}")
                st.write(f"Restante: S/ {venta['restante']}")

                if st.button("Completar Pago", key=venta["id"]):
                    supabase.table("ventas").update({
                        "monto_pagado": venta["total"],
                        "restante": 0,
                        "tipo_pago": "Completo"
                    }).eq("id", venta["id"]).execute()

                    st.success("Pago completado")
                    st.rerun()

# ===================================
# 📁 PDF DEL DÍA
# ===================================
with tab_objects[3]:

    ventas = obtener_ventas()

    if ventas:
        if st.button("Generar PDF del día"):

            df = pd.DataFrame(ventas)
            total_dia = df["monto_pagado"].sum()

            file_path = "reporte_ventas.pdf"
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []

            style = ParagraphStyle(name='Normal', fontSize=10)

            elements.append(Paragraph("<b>NSJ CAPROYECT</b>", style))
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", style))
            elements.append(Spacer(1, 0.3 * inch))

            data = [["Cliente","Producto","Pagado","Restante"]]

            for v in ventas:
                data.append([
                    v["cliente"],
                    v["producto"],
                    f"S/ {v['monto_pagado']}",
                    f"S/ {v['restante']}"
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.grey),
                ('GRID',(0,0),(-1,-1),1,colors.black)
            ]))

            elements.append(table)
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(f"<b>Total Ingresado Hoy: S/ {total_dia:.2f}</b>", style))

            doc.build(elements)

            with open(file_path, "rb") as f:
                st.download_button("Descargar PDF", f, file_path)

# ===================================
# 📊 PANEL GERENTE
# ===================================
if st.session_state.user_role == "gerente":
    with tab_objects[-1]:

        ventas = obtener_ventas()

        if ventas:
            df = pd.DataFrame(ventas)

            total_ingresado = df["monto_pagado"].sum()
            total_pendiente = df["restante"].sum()

            st.metric("💰 Total Ingresado", f"S/ {total_ingresado:.2f}")
            st.metric("🟡 Pendiente por Cobrar", f"S/ {total_pendiente:.2f}")

            st.dataframe(df)
