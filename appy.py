import streamlit as st
from datetime import datetime

# -------------------------
# CONFIGURACIÓN
# -------------------------
st.set_page_config(
    page_title="Sistema de Ventas - Banners",
    layout="wide"
)

st.title("🖨️ Sistema de Ventas - Banners")
st.caption("Uso interno - Empresa de gigantografías")

# -------------------------
# DATOS DEL NEGOCIO
# -------------------------
ANCHOS_BANNER = [1.10, 1.60, 2.20, 3.20]

TIPOS_BANNER = [
    "8 onzas (Económico)",
    "12 onzas (Premium)"
]

PRECIO_M2 = {
    "Sí tiene diseño": 10,
    "No tiene diseño": 13
}

# -------------------------
# FORMULARIO DE PEDIDO
# -------------------------
st.subheader("📋 Nuevo Pedido de Banner")

col1, col2 = st.columns(2)

with col1:
    cliente = st.text_input("Cliente")
    ancho = st.selectbox(
        "Ancho del banner (m)",
        ANCHOS_BANNER
    )
    alto = st.number_input(
        "Alto del banner (m)",
        min_value=0.1,
        step=0.1
    )

with col2:
    tipo_banner = st.selectbox(
        "Tipo de banner",
        TIPOS_BANNER
    )
    diseno = st.selectbox(
        "¿Cliente trae diseño?",
        list(PRECIO_M2.keys())
    )

# -------------------------
# CÁLCULO
# -------------------------
area = ancho * alto
precio_m2 = PRECIO_M2[diseno]
total = area * precio_m2

# -------------------------
# RESULTADOS
# -------------------------
st.divider()

st.info(f"""
🔹 **Ancho seleccionado:** {ancho:.2f} m  
🔹 **Alto:** {alto:.2f} m  
🔹 **Área total:** {area:.2f} m²  
🔹 **Precio por m²:** S/. {precio_m2}
""")

st.success(f"💰 **Precio final: S/. {total:.2f}**")

# -------------------------
# CONFIRMAR PEDIDO
# -------------------------
if st.button("💾 Confirmar Pedido"):
    st.success("Pedido confirmado correctamente")
