import streamlit as st
import pandas as pd
from datetime import datetime
import os

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
# CONFIGURACIÓN
# -------------------------
st.set_page_config(
    page_title="Sistema de Ventas - NSJ CAPROYECT",
    layout="wide"
)

st.title("🖨️ Sistema de Ventas - NSJ CAPROYECT")
st.caption("Uso interno")

# -------------------------
# DATOS DEL NEGOCIO
# -------------------------
ANCHOS = [1.10, 1.60, 2.20, 3.20]

TIPOS_BANNER = [
    "8 onzas (Económico)",
    "12 onzas (Premium)"
]

PRECIO_BANNER_M2 = {
    "Sí tiene diseño": 10,
    "No tiene diseño": 13
}

PRECIO_VINIL_M2 = {
    "Sí tiene diseño": 12,
    "No tiene diseño": 15
}

METODOS_PAGO = [
    "Efectivo",
    "Yape",
    "Plin",
    "Transferencia"
]

# -------------------------
# INICIALIZAR VENTAS CON RECUPERACIÓN
# -------------------------
if "ventas" not in st.session_state:
    st.session_state.ventas = cargar_ventas()

# -------------------------
# PESTAÑAS
# -------------------------
tab_banner, tab_vinil, tab_extra, tab_ventas, tab_excel = st.tabs(
    ["🟦 Banner", "🟩 Viniles", "➕ Venta Extra", "📊 Ventas del día", "📁 Cierre / Excel"]
)

# =====================================================
# FUNCIÓN PARA REGISTRAR VENTA
# =====================================================
def registrar_venta(venta):
    st.session_state.ventas.append(venta)
    guardar_ventas()
    st.success("Venta registrada correctamente")

# =====================================================
# 🟦 BANNER
# =====================================================
with tab_banner:
    st.subheader("📋 Venta de Banner")

    col1, col2 = st.columns(2)

    with col1:
        cliente = st.text_input("Cliente", key="b_cliente")
        ancho = st.selectbox("Ancho (m)", ANCHOS, key="b_ancho")
        alto = st.number_input("Alto (m)", min_value=0.1, step=0.1, key="b_alto")
        tipo_banner = st.selectbox("Tipo de banner", TIPOS_BANNER, key="b_tipo")

    with col2:
        diseno = st.selectbox("¿Cliente trae diseño?", PRECIO_BANNER_M2.keys(), key="b_diseno")
        metodo_pago = st.selectbox("Método de pago", METODOS_PAGO, key="b_pago")

    area = ancho * alto
    precio_calculado = area * PRECIO_BANNER_M2[diseno]

    precio_final = st.number_input(
        "💰 Precio final a cobrar",
        min_value=0.0,
        value=float(round(precio_calculado, 2)),
        step=1.0,
        key="b_precio_final"
    )

    if st.button("➕ Agregar Banner"):
        registrar_venta({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Banner",
            "Tipo": tipo_banner,
            "Detalle": diseno,
            "Método de pago": metodo_pago,
            "Total": round(precio_final, 2)
        })

# =====================================================
# 🟩 VINIL
# =====================================================
with tab_vinil:
    st.subheader("📋 Venta de Vinil")

    col1, col2 = st.columns(2)

    with col1:
        cliente = st.text_input("Cliente", key="v_cliente")
        ancho = st.selectbox("Ancho (m)", ANCHOS, key="v_ancho")
        alto = st.number_input("Alto (m)", min_value=0.1, step=0.1, key="v_alto")

    with col2:
        diseno = st.selectbox("¿Cliente trae diseño?", PRECIO_VINIL_M2.keys(), key="v_diseno")
        metodo_pago = st.selectbox("Método de pago", METODOS_PAGO, key="v_pago")

    area = ancho * alto
    precio_calculado = area * PRECIO_VINIL_M2[diseno]

    precio_final = st.number_input(
        "💰 Precio final a cobrar",
        min_value=0.0,
        value=float(round(precio_calculado, 2)),
        step=1.0,
        key="v_precio_final"
    )

    if st.button("➕ Agregar Vinil"):
        registrar_venta({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Vinil",
            "Tipo": "-",
            "Detalle": diseno,
            "Método de pago": metodo_pago,
            "Total": round(precio_final, 2)
        })

# =====================================================
# ➕ VENTA EXTRA
# =====================================================
with tab_extra:
    st.subheader("➕ Venta Extra")

    cliente = st.text_input("Cliente", key="e_cliente")
    concepto = st.text_input("Concepto (ej: Instalación, Diseño, Mantenimiento)")
    monto = st.number_input("Monto (S/.)", min_value=1.0, step=1.0)
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO, key="e_pago")

    if st.button("➕ Agregar Venta Extra"):
        registrar_venta({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Extra",
            "Tipo": concepto,
            "Detalle": "-",
            "Método de pago": metodo_pago,
            "Total": round(monto, 2)
        })

# =====================================================
# 📊 VENTAS DEL DÍA
# =====================================================
with tab_ventas:
    st.subheader("📊 Ventas del día")

    if not st.session_state.ventas:
        st.warning("No hay ventas registradas")
    else:
        df = pd.DataFrame(st.session_state.ventas)
        st.dataframe(df, use_container_width=True)
        st.metric("💰 Total del día", f"S/. {df['Total'].sum():.2f}")

# =====================================================
# 📁 CIERRE / EXCEL
# =====================================================
with tab_excel:
    st.subheader("📁 Cierre del día")

    if not st.session_state.ventas:
        st.warning("No hay ventas para exportar")
    else:
        df = pd.DataFrame(st.session_state.ventas)
        nombre_archivo = f"ventas_{datetime.now().strftime('%Y%m%d')}.xlsx"

        df.to_excel(nombre_archivo, index=False)

        with open(nombre_archivo, "rb") as file:
            st.download_button("⬇️ Descargar Excel", file, nombre_archivo)

        if st.button("🧹 Cerrar día"):
            st.session_state.ventas.clear()
            if os.path.exists(ARCHIVO_VENTAS):
                os.remove(ARCHIVO_VENTAS)
            st.success("Día cerrado correctamente")
