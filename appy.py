import streamlit as st
import pandas as pd
from datetime import datetime
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import pagesizes
from reportlab.lib.units import inch

# -------------------------
# ARCHIVO PERSISTENTE
# -------------------------
ARCHIVO_VENTAS = "ventas_hoy.csv"

def cargar_ventas():
    if os.path.exists(ARCHIVO_VENTAS):
        return pd.read_csv(ARCHIVO_VENTAS).to_dict("records")
    return []

def guardar_ventas():
    df = pd.DataFrame(st.session_state.ventas)
    df.to_csv(ARCHIVO_VENTAS, index=False)

# -------------------------
# GENERAR PDF PROFESIONAL
# -------------------------
def generar_pdf(ventas, nombre_archivo):
    doc = SimpleDocTemplate(nombre_archivo, pagesize=pagesizes.A4)
    elementos = []
    estilos = getSampleStyleSheet()

    elementos.append(Paragraph("NSJ CAPROYECT", estilos["Heading1"]))
    elementos.append(Spacer(1, 0.3 * inch))
    elementos.append(Paragraph("REPORTE DE VENTAS DEL DÍA", estilos["Heading2"]))
    elementos.append(Spacer(1, 0.3 * inch))

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    elementos.append(Paragraph(f"Fecha de cierre: {fecha}", estilos["Normal"]))
    elementos.append(Spacer(1, 0.5 * inch))

    data = [["#", "Cliente", "Producto", "Detalle", "Pago", "Total (S/.)"]]
    total_general = 0

    for i, venta in enumerate(ventas, start=1):
        data.append([
            i,
            venta.get("Cliente", ""),
            venta.get("Producto", ""),
            venta.get("Detalle", ""),
            venta.get("Método de pago", ""),
            f"{venta.get('Total', 0):.2f}"
        ])
        total_general += float(venta.get("Total", 0))

    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 0.5 * inch))

    elementos.append(
        Paragraph(f"TOTAL GENERAL: S/. {total_general:.2f}", estilos["Heading2"])
    )

    doc.build(elementos)

# -------------------------
# CONFIGURACIÓN
# -------------------------
st.set_page_config(page_title="Sistema de Ventas - NSJ CAPROYECT", layout="wide")

st.title("🖨️ Sistema de Ventas - NSJ CAPROYECT")
st.caption("Uso interno")

METODOS_PAGO = ["Efectivo", "Yape", "Plin", "Transferencia"]

if "ventas" not in st.session_state:
    st.session_state.ventas = cargar_ventas()

# -------------------------
# REGISTRAR VENTA
# -------------------------
def registrar_venta(venta):
    st.session_state.ventas.append(venta)
    guardar_ventas()
    st.success("✅ Venta registrada correctamente")

# -------------------------
# PESTAÑAS
# -------------------------
tab_registro, tab_ventas, tab_cierre = st.tabs(
    ["➕ Registrar Venta", "📊 Ventas del día", "📁 Cierre"]
)

# =====================================================
# ➕ REGISTRAR VENTA
# =====================================================
with tab_registro:
    st.subheader("Nueva venta")

    cliente = st.text_input("Cliente")
    producto = st.text_input("Producto")
    detalle = st.text_input("Detalle (opcional)")
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO)
    total = st.number_input("Total (S/.)", min_value=0.0, step=1.0)

    if st.button("➕ Agregar venta"):
        registrar_venta({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": producto,
            "Detalle": detalle,
            "Método de pago": metodo_pago,
            "Total": round(total, 2)
        })

# =====================================================
# 📊 VENTAS DEL DÍA
# =====================================================
with tab_ventas:
    st.subheader("Ventas registradas")

    if not st.session_state.ventas:
        st.warning("No hay ventas registradas")
    else:
        total_dia = sum(v["Total"] for v in st.session_state.ventas)
        st.metric("💰 Total del día", f"S/. {total_dia:.2f}")
        st.divider()

        for i, venta in enumerate(st.session_state.ventas):
            with st.container(border=True):
                st.markdown(f"### 🧾 Venta #{i+1}")
                st.write(f"🕒 {venta.get('Fecha')}")
                st.write(f"👤 Cliente: {venta.get('Cliente')}")
                st.write(f"📦 Producto: {venta.get('Producto')}")
                st.write(f"📝 Detalle: {venta.get('Detalle')}")
                st.write(f"💳 Pago: {venta.get('Método de pago')}")
                st.write(f"💰 Total: S/. {venta.get('Total')}")

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✏️ Editar", key=f"edit_{i}"):
                        st.session_state.edit_index = i
                        st.rerun()

                with col2:
                    if st.button("🗑 Eliminar", key=f"del_{i}"):
                        st.session_state.ventas.pop(i)
                        guardar_ventas()
                        st.rerun()

        # PANEL EDICIÓN
        if "edit_index" in st.session_state:
            idx = st.session_state.edit_index
            venta = st.session_state.ventas[idx]

            st.divider()
            st.subheader("Editar venta")

            nuevo_cliente = st.text_input("Cliente", value=venta["Cliente"])
            nuevo_producto = st.text_input("Producto", value=venta["Producto"])
            nuevo_detalle = st.text_input("Detalle", value=venta["Detalle"])
            nuevo_metodo = st.selectbox(
                "Método de pago",
                METODOS_PAGO,
                index=METODOS_PAGO.index(venta["Método de pago"])
            )
            nuevo_total = st.number_input("Total", value=float(venta["Total"]), step=1.0)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Guardar cambios"):
                    venta["Cliente"] = nuevo_cliente
                    venta["Producto"] = nuevo_producto
                    venta["Detalle"] = nuevo_detalle
                    venta["Método de pago"] = nuevo_metodo
                    venta["Total"] = round(nuevo_total, 2)
                    guardar_ventas()
                    del st.session_state.edit_index
                    st.rerun()

            with col2:
                if st.button("❌ Cancelar"):
                    del st.session_state.edit_index
                    st.rerun()

# =====================================================
# 📁 CIERRE
# =====================================================
with tab_cierre:
    st.subheader("Cierre del día")

    if not st.session_state.ventas:
        st.warning("No hay ventas para exportar")
    else:
        df = pd.DataFrame(st.session_state.ventas)

        nombre_excel = f"ventas_{datetime.now().strftime('%Y%m%d')}.xlsx"
        nombre_pdf = f"reporte_ventas_{datetime.now().strftime('%Y%m%d')}.pdf"

        df.to_excel(nombre_excel, index=False)

        col1, col2 = st.columns(2)

        with col1:
            with open(nombre_excel, "rb") as file:
                st.download_button("⬇️ Descargar Excel", file, nombre_excel)

        with col2:
            if st.button("🧾 Generar PDF Profesional"):
                generar_pdf(st.session_state.ventas, nombre_pdf)
                with open(nombre_pdf, "rb") as pdf_file:
                    st.download_button("⬇️ Descargar PDF", pdf_file, nombre_pdf)

        if st.button("🧹 Cerrar día"):
            st.session_state.ventas.clear()
            if os.path.exists(ARCHIVO_VENTAS):
                os.remove(ARCHIVO_VENTAS)
            st.success("✅ Día cerrado correctamente")
            st.rerun()
