import streamlit as st
import pandas as pd
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
ANCHOS_DISPONIBLES = [1.10, 1.60, 2.20, 3.20]

TIPOS_BANNER = {
    "8 onzas (Económico)": 1.0,
    "12 onzas (Premium)": 1.0
}

PRECIO_DISENO = {
    "Sí tiene diseño": 10,
    "No tiene diseño": 13
}

# -------------------------
# FUNCIÓN PARA AJUSTAR ANCHO
# -------------------------
def ajustar_ancho(ancho_solicitado):
    for ancho in ANCHOS_DISPONIBLES:
        if ancho_solicitado <= ancho:
            return ancho
    return ANCHOS_DISPONIBLES[-1]  # máximo disponible

# -------------------------
# FORMULARIO
# -------------------------
st.subheader("📋 Nuevo Pedido de Banner")

col1, col2 = st.columns(2)

with col1:
    cliente = st.text_input("Cliente")
    ancho_cliente = st.number_input(
        "Ancho solicitado por el cliente (m)",
        min_value=0.1,
        step=0.1
    )
    alto = st.number_input(
        "Alto solicitado (m)",
        min_value=0.1,
        step=0.1
    )

with col2:
    tipo_banner = st.selectbox(
        "Tipo de banner",
        list(TIPOS_BANNER.keys())
    )
    diseno = st.selectbox(
        "¿Cliente trae diseño?",
        list(PRECIO_DISENO.keys())
    )

# -------------------------
# CÁLCULOS
# -------------------------
ancho_trabajo = ajustar_ancho(ancho_cliente)
area = ancho_trabajo * alto
precio_m2 = PRECIO_DISENO[diseno]
total = area * precio_m2

# -------------------------
# RESULTADOS
# -------------------------
st.divider()

st.info(f"""
🔹 **Ancho solicitado:** {ancho_cliente:.2f} m  
🔹 **Ancho utilizado para producción:** {ancho_trabajo:.2f} m  
🔹 **Área total:** {area:.2f} m²  
🔹 **Precio por m²:** S/. {precio_m2}
""")

st.success(f"💰 **Precio final: S/. {total:.2f}**")

# -------------------------
# BOTÓN (POR AHORA SOLO VISUAL)
# -------------------------
if st.button("💾 Confirmar Pedido"):
    st.success("Pedido confirmado (listo para guardar en base de datos)")
