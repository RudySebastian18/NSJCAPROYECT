import streamlit as st
import pandas as pd
from datetime import datetime

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
# INICIALIZAR VENTAS
# -------------------------
if "ventas" not in st.session_state:
    st.session_state.ventas = []

# -------------------------
# PESTAÑAS
# -------------------------
tab_banner, tab_vinil, tab_ventas, tab_excel = st.tabs(
    ["🟦 Banner", "🟩 Viniles", "📊 Ventas del día", "📁 Cierre / Excel"]
)

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
        "💰 Precio final a cobrar (editable)",
        min_value=0.0,
        value=float(round(precio_calculado, 2)),
        step=1.0,
        key="b_precio_final"
    )

    st.info(f"Área: {area:.2f} m² | Precio sugerido: S/. {precio_calculado:.2f}")

    if st.button("➕ Agregar venta de Banner"):
        st.session_state.ventas.append({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Banner",
            "Tipo": tipo_banner,
            "Ancho (m)": ancho,
            "Alto (m)": alto,
            "Área (m²)": round(area, 2),
            "Diseño": diseno,
            "Método de pago": metodo_pago,
            "Total (S/.)": round(precio_final, 2)
        })
        st.success("Venta de banner registrada correctamente")

# =====================================================
# 🟩 VINILES
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
        "💰 Precio final a cobrar (editable)",
        min_value=0.0,
        value=float(round(precio_calculado, 2)),
        step=1.0,
        key="v_precio_final"
    )

    st.info(f"Área: {area:.2f} m² | Precio sugerido: S/. {precio_calculado:.2f}")

    if st.button("➕ Agregar venta de Vinil"):
        st.session_state.ventas.append({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Vinil",
            "Tipo": "-",
            "Ancho (m)": ancho,
            "Alto (m)": alto,
            "Área (m²)": round(area, 2),
            "Diseño": diseno,
            "Método de pago": metodo_pago,
            "Total (S/.)": round(precio_final, 2)
        })
        st.success("Venta de vinil registrada correctamente")

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
        st.metric("💰 Total del día", f"S/. {df['Total (S/.)'].sum():.2f}")

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
            st.download_button(
                "⬇️ Descargar Excel del día",
                file,
                nombre_archivo
            )

        if st.button("🧹 Cerrar día"):
            st.session_state.ventas.clear()
            st.success("Día cerrado correctamente")
