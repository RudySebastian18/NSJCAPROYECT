import streamlit as st
import pandas as pd
from datetime import datetime
import os
from PIL import Image

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

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

    tipo_pago = st.radio("Tipo de pago", ["Pago completo", "Adelanto"])

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

    estado_entrega = st.selectbox("Estado del pedido", ["Pendiente", "Entregado"])

    if st.button("➕ Registrar venta"):
        registrar_venta({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": producto,
            "Total": round(total, 2),
            "Pagado": round(pagado, 2),
            "Saldo": round(saldo, 2),
            "Estado": estado,
            "Método de pago": metodo_pago,
            "Entrega": estado_entrega
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

        # ✅ NUEVO: Estadística métodos de pago
        st.subheader("📊 Métodos de pago más usados")
        df_metodos = pd.DataFrame(st.session_state.ventas)

        if "Método de pago" in df_metodos.columns:
            conteo_metodos = df_metodos["Método de pago"].value_counts()
            st.bar_chart(conteo_metodos)

            for metodo, cantidad in conteo_metodos.items():
                st.write(f"💳 {metodo}: {cantidad} ventas")

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
                st.write(f"🚚 Entrega: {venta['Entrega']}")
                st.write(f"💳 Método: {venta['Método de pago']}")

                colA, colB, colC = st.columns(3)

                if venta["Estado"] == "Pendiente":
                    with colA:
                        if st.button("💳 Completar pago", key=f"pagar_{i}"):
                            venta["Pagado"] = venta["Total"]
                            venta["Saldo"] = 0
                            venta["Estado"] = "Pagado"
                            guardar_ventas()
                            st.rerun()

                if venta["Entrega"] == "Pendiente":
                    with colB:
                        if st.button("🚚 Marcar entregado", key=f"entregar_{i}"):
                            venta["Entrega"] = "Entregado"
                            guardar_ventas()
                            st.rerun()

                with colC:
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
            nombre_pdf = f"Factura_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            doc = SimpleDocTemplate(nombre_pdf)
            elementos = []
            estilos = getSampleStyleSheet()

            elementos.append(Paragraph("<b>NSJ CAPROYECT</b>", estilos["Title"]))
            elementos.append(Paragraph("Sistema de Ventas Interno", estilos["Normal"]))
            elementos.append(Spacer(1, 10))

            fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
            elementos.append(Paragraph(f"<b>Fecha:</b> {fecha_actual}", estilos["Normal"]))
            elementos.append(Paragraph(f"<b>N° Factura:</b> {datetime.now().strftime('%Y%m%d%H%M')}", estilos["Normal"]))
            elementos.append(Spacer(1, 20))

            # ✅ MÉTODO DE PAGO agregado a la tabla
            data = [["Cliente", "Producto", "Total", "Pagado", "Saldo", "Estado", "Entrega", "Método Pago"]]

            for v in st.session_state.ventas:
                data.append([
                    v["Cliente"],
                    v["Producto"],
                    f"S/. {v['Total']:.2f}",
                    f"S/. {v['Pagado']:.2f}",
                    f"S/. {v['Saldo']:.2f}",
                    v["Estado"],
                    v["Entrega"],
                    v["Método de pago"]
                ])

            tabla = Table(data, repeatRows=1)

            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E4053")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))

            elementos.append(tabla)
            elementos.append(Spacer(1, 25))

            total_dia = sum(float(v["Total"]) for v in st.session_state.ventas)
            total_cobrado = sum(float(v["Pagado"]) for v in st.session_state.ventas)
            total_pendiente = sum(float(v["Saldo"]) for v in st.session_state.ventas)

            elementos.append(Paragraph("<b>RESUMEN GENERAL</b>", estilos["Heading2"]))
            elementos.append(Spacer(1, 10))
            elementos.append(Paragraph(f"Total vendido: S/. {total_dia:.2f}", estilos["Normal"]))
            elementos.append(Paragraph(f"Total cobrado: S/. {total_cobrado:.2f}", estilos["Normal"]))
            elementos.append(Paragraph(f"Total pendiente: S/. {total_pendiente:.2f}", estilos["Normal"]))

            # ✅ NUEVO: Resumen métodos de pago en PDF
            elementos.append(Spacer(1, 20))
            elementos.append(Paragraph("<b>Métodos de pago utilizados:</b>", estilos["Heading3"]))

            df_metodos = pd.DataFrame(st.session_state.ventas)
            conteo_metodos = df_metodos["Método de pago"].value_counts()

            for metodo, cantidad in conteo_metodos.items():
                elementos.append(Paragraph(f"{metodo}: {cantidad} ventas", estilos["Normal"]))

            elementos.append(Spacer(1, 30))
            elementos.append(Paragraph("Gracias por su preferencia.", estilos["Normal"]))

            doc.build(elementos)

            with open(nombre_pdf, "rb") as file:
                st.download_button("⬇️ Descargar Factura", file, nombre_pdf)

        st.divider()

        if st.button("🧹 Cerrar día"):
            st.session_state.ventas.clear()
            if os.path.exists(ARCHIVO_VENTAS):
                os.remove(ARCHIVO_VENTAS)
            st.success("✅ Día cerrado correctamente")
            st.rerun()
