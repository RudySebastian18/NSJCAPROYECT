import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PIL import Image

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# -------------------------
# CONFIGURACIÓN
# -------------------------
st.set_page_config(page_title="Sistema de Ventas - NSJ CAPROYECT", layout="wide")

ARCHIVO_VENTAS = "ventas_hoy.csv"

# -------------------------
# FUNCIONES CSV
# -------------------------
def cargar_ventas():
    if os.path.exists(ARCHIVO_VENTAS):
        return pd.read_csv(ARCHIVO_VENTAS).to_dict("records")
    return []

def guardar_ventas():
    df = pd.DataFrame(st.session_state.ventas)
    df.to_csv(ARCHIVO_VENTAS, index=False)

# -------------------------
# INICIALIZAR
# -------------------------
if "ventas" not in st.session_state:
    st.session_state.ventas = cargar_ventas()

# -------------------------
# HEADER CON LOGO
# -------------------------
col_logo, col_title = st.columns([1, 4])

with col_logo:
    if os.path.exists("logo.png"):
        logo = Image.open("logo.png")
        st.image(logo, width=120)

with col_title:
    st.title("Sistema de Ventas - NSJ CAPROYECT")
    st.caption("Uso interno")

st.divider()

# -------------------------
# MÉTODOS DE PAGO
# -------------------------
METODOS_PAGO = ["Efectivo", "Yape", "Plin", "Transferencia"]

# -------------------------
# FUNCIÓN REGISTRAR
# -------------------------
def registrar_venta(venta):
    st.session_state.ventas.append(venta)
    guardar_ventas()
    st.success("✅ Venta registrada correctamente")

# -------------------------
# PESTAÑAS
# -------------------------
tab_venta, tab_ventas, tab_cierre = st.tabs(
    ["➕ Nueva Venta", "📊 Ventas del día", "📁 Cierre / Reporte"]
)

# =====================================================
# ➕ NUEVA VENTA
# =====================================================
with tab_venta:
    st.subheader("Registrar nueva venta")

    cliente = st.text_input("Cliente")
    producto = st.text_input("Producto / Descripción")
    total = st.number_input("Total del producto (S/.)", min_value=0.0, step=1.0)
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO)

    tipo_pago = st.radio(
        "Tipo de pago",
        ["Pago completo", "Adelanto"]
    )

    if tipo_pago == "Pago completo":
        pagado = total
        saldo = 0
        estado = "Pagado"

        st.success("✔ Venta pagada completamente")

    else:
        adelanto = st.number_input("Monto del adelanto", min_value=0.0, step=1.0)
        pagado = adelanto
        saldo = total - adelanto
        estado = "Pendiente" if saldo > 0 else "Pagado"

        st.info(f"Saldo pendiente: S/. {saldo:.2f}")

    if st.button("➕ Registrar venta"):
        registrar_venta({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": producto,
            "Total": round(total, 2),
            "Pagado": round(pagado, 2),
            "Saldo": round(saldo, 2),
            "Estado": estado,
            "Método de pago": metodo_pago
        })


# =====================================================
# 📊 VENTAS DEL DÍA
# =====================================================
with tab_ventas:
    st.subheader("Ventas registradas")

    if not st.session_state.ventas:
        st.warning("No hay ventas registradas")
    else:
        total_dia = sum(float(v["Total"]) for v in st.session_state.ventas)
        total_cobrado = sum(float(v["Pagado"]) for v in st.session_state.ventas)
        total_pendiente = sum(float(v["Saldo"]) for v in st.session_state.ventas)

        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Total vendido", f"S/. {total_dia:.2f}")
        col2.metric("💵 Total cobrado", f"S/. {total_cobrado:.2f}")
        col3.metric("🧾 Total pendiente", f"S/. {total_pendiente:.2f}")

        st.divider()

        for i, venta in enumerate(st.session_state.ventas):
            with st.container(border=True):
                st.markdown(f"### 🧾 Venta #{i+1}")
                st.write(f"👤 Cliente: {venta['Cliente']}")
                st.write(f"📦 Producto: {venta['Producto']}")
                st.write(f"💰 Total: S/. {venta['Total']}")
                st.write(f"💵 Pagado: S/. {venta['Pagado']}")
                st.write(f"🧾 Saldo: S/. {venta['Saldo']}")
                st.write(f"📌 Estado: {venta['Estado']}")
                st.write(f"💳 Método: {venta['Método de pago']}")

                colA, colB = st.columns(2)

                if venta["Estado"] == "Pendiente":
                    with colA:
                        if st.button("💳 Completar pago", key=f"pagar_{i}"):
                            venta["Pagado"] = venta["Total"]
                            venta["Saldo"] = 0
                            venta["Estado"] = "Pagado"
                            guardar_ventas()
                            st.rerun()

                with colB:
                    if st.button("🗑 Eliminar", key=f"del_{i}"):
                        st.session_state.ventas.pop(i)
                        guardar_ventas()
                        st.rerun()

# =====================================================
# 📁 CIERRE Y PDF
# =====================================================
with tab_cierre:
    st.subheader("Generar reporte del día")

    if not st.session_state.ventas:
        st.warning("No hay ventas para exportar")
    else:
        if st.button("📄 Generar PDF"):
            nombre_pdf = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            doc = SimpleDocTemplate(nombre_pdf)
            elementos = []

            estilos = getSampleStyleSheet()

            # Logo
            if os.path.exists("logo.png"):
                logo = RLImage("logo.png", width=120, height=60)
                elementos.append(logo)
                elementos.append(Spacer(1, 20))

            elementos.append(Paragraph("<b>REPORTE DE VENTAS DEL DÍA</b>", estilos["Title"]))
            elementos.append(Spacer(1, 20))

            data = [["Cliente", "Producto", "Total", "Pagado", "Saldo", "Estado"]]

            for v in st.session_state.ventas:
                data.append([
                    v["Cliente"],
                    v["Producto"],
                    f"S/. {v['Total']}",
                    f"S/. {v['Pagado']}",
                    f"S/. {v['Saldo']}",
                    v["Estado"]
                ])

            tabla = Table(data, repeatRows=1)
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (2, 1), (-2, -1), 'RIGHT'),
            ]))

            elementos.append(tabla)
            elementos.append(Spacer(1, 30))

            total_dia = sum(float(v["Total"]) for v in st.session_state.ventas)
            total_cobrado = sum(float(v["Pagado"]) for v in st.session_state.ventas)
            total_pendiente = sum(float(v["Saldo"]) for v in st.session_state.ventas)

            elementos.append(Paragraph(f"<b>Total vendido:</b> S/. {total_dia:.2f}", estilos["Normal"]))
            elementos.append(Paragraph(f"<b>Total cobrado:</b> S/. {total_cobrado:.2f}", estilos["Normal"]))
            elementos.append(Paragraph(f"<b>Total pendiente:</b> S/. {total_pendiente:.2f}", estilos["Normal"]))

            doc.build(elementos)

            with open(nombre_pdf, "rb") as file:
                st.download_button("⬇️ Descargar PDF", file, nombre_pdf)

        st.divider()

        if st.button("🧹 Cerrar día"):
            st.session_state.ventas.clear()
            if os.path.exists(ARCHIVO_VENTAS):
                os.remove(ARCHIVO_VENTAS)
            st.success("✅ Día cerrado correctamente")
            st.rerun()
