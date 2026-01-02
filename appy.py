import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------
# CONFIGURACIÓN
# -------------------------
st.set_page_config(
    page_title="Sistema de Ventas - Gigantografías",
    layout="wide"
)

st.title("🖨️ Sistema de Ventas - Empresa de Gigantografías")
st.caption("Uso interno")

# -------------------------
# DATOS DEL NEGOCIO
# -------------------------
ANCHOS_BANNER = [1.10, 1.60, 2.20, 3.20]

PRECIO_BANNER_M2 = {
    "Sí tiene diseño": 10,
    "No tiene diseño": 13
}

PRECIO_VINIL_M2 = {
    "Sí tiene diseño": 12,
    "No tiene diseño": 15
}

# -------------------------
# INICIALIZAR VENTAS DEL DÍA
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
# 🟦 TAB BANNER
# =====================================================
with tab_banner:
    st.subheader("📋 Venta de Banner")

    col1, col2 = st.columns(2)

    with col1:
        cliente = st.text_input("Cliente", key="banner_cliente")
        ancho = st.selectbox("Ancho (m)", ANCHOS_BANNER, key="banner_ancho")
        alto = st.number_input("Alto (m)", min_value=0.1, step=0.1, key="banner_alto")

    with col2:
        diseno = st.selectbox(
            "¿Cliente trae diseño?",
            PRECIO_BANNER_M2.keys(),
            key="banner_diseno"
        )

    area = ancho * alto
    total = area * PRECIO_BANNER_M2[diseno]

    st.info(f"Área: {area:.2f} m²")
    st.success(f"💰 Total: S/. {total:.2f}")

    if st.button("➕ Agregar venta de Banner"):
        st.session_state.ventas.append({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Banner",
            "Ancho (m)": ancho,
            "Alto (m)": alto,
            "Área (m²)": round(area, 2),
            "Diseño": diseno,
            "Total (S/.)": round(total, 2)
        })
        st.success("Venta de banner registrada")

# =====================================================
# 🟩 TAB VINILES
# =====================================================
with tab_vinil:
    st.subheader("📋 Venta de Vinil")

    col1, col2 = st.columns(2)

    with col1:
        cliente = st.text_input("Cliente", key="vinil_cliente")
        ancho = st.selectbox("Ancho (m)", ANCHOS_BANNER, key="vinil_ancho")
        alto = st.number_input("Alto (m)", min_value=0.1, step=0.1, key="vinil_alto")

    with col2:
        diseno = st.selectbox(
            "¿Cliente trae diseño?",
            PRECIO_VINIL_M2.keys(),
            key="vinil_diseno"
        )

    area = ancho * alto
    total = area * PRECIO_VINIL_M2[diseno]

    st.info(f"Área: {area:.2f} m²")
    st.success(f"💰 Total: S/. {total:.2f}")

    if st.button("➕ Agregar venta de Vinil"):
        st.session_state.ventas.append({
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": "Vinil",
            "Ancho (m)": ancho,
            "Alto (m)": alto,
            "Área (m²)": round(area, 2),
            "Diseño": diseno,
            "Total (S/.)": round(total, 2)
        })
        st.success("Venta de vinil registrada")

# =====================================================
# 📊 TAB VENTAS DEL DÍA
# =====================================================
with tab_ventas:
    st.subheader("📊 Ventas del día")

    if not st.session_state.ventas:
        st.warning("No hay ventas registradas hoy")
    else:
        df = pd.DataFrame(st.session_state.ventas)
        st.dataframe(df, use_container_width=True)

        st.metric("💰 Total del día", f"S/. {df['Total (S/.)'].sum():.2f}")

# =====================================================
# 📁 TAB EXCEL / CIERRE
# =====================================================
with tab_excel:
    st.subheader("📁 Cierre del día")

    if not st.session_state.ventas:
        st.warning("No hay ventas para exportar")
    else:
        df = pd.DataFrame(st.session_state.ventas)

        nombre_archivo = f"ventas_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(nombre_archivo, index=False)

        st.success("Excel generado correctamente")

        with open(nombre_archivo, "rb") as file:
            st.download_button(
                label="⬇️ Descargar Excel del día",
                data=file,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        if st.button("🧹 Cerrar día y limpiar ventas"):
            st.session_state.ventas.clear()
            st.success("Día cerrado. Listo para nuevas ventas.")
