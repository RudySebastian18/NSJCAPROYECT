import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------------
# Configuración
# -------------------------
st.set_page_config(
    page_title="Sistema de Ventas - Gigantografías",
    layout="wide"
)

st.title("🖨️ Sistema de Ventas - Empresa de Gigantografías")
st.caption("Uso interno - Registro de pedidos")

# -------------------------
# Catálogo de productos
# -------------------------
PRODUCTOS = {
    "Gigantografía": 35.0,
    "Banner Publicitario": 30.0,
    "Vinil Adhesivo": 40.0
}

MATERIALES = {
    "Estándar": 1.0,
    "Premium": 1.25
}

ACABADOS = {
    "Sin acabado": 1.0,
    "Ojales": 1.10,
    "Laminado": 1.20
}

# -------------------------
# Inicializar ventas
# -------------------------
if "ventas" not in st.session_state:
    st.session_state.ventas = []

# -------------------------
# Menú
# -------------------------
menu = st.sidebar.selectbox(
    "Menú",
    ["Nuevo Pedido", "Ventas Registradas", "Reporte"]
)

# -------------------------
# Nuevo Pedido
# -------------------------
if menu == "Nuevo Pedido":
    st.subheader("📋 Nuevo Pedido")

    col1, col2 = st.columns(2)

    with col1:
        cliente = st.text_input("Cliente")
        producto = st.selectbox("Producto", list(PRODUCTOS.keys()))
        material = st.selectbox("Material", list(MATERIALES.keys()))

    with col2:
        ancho = st.number_input("Ancho (m)", min_value=0.1, step=0.1)
        alto = st.number_input("Alto (m)", min_value=0.1, step=0.1)
        acabado = st.selectbox("Acabado", list(ACABADOS.keys()))

    # -------------------------
    # Cálculo
    # -------------------------
    area = ancho * alto
    precio_base = PRODUCTOS[producto]
    precio_final = area * precio_base * MATERIALES[material] * ACABADOS[acabado]

    st.divider()
    st.info(f"Área total: **{area:.2f} m²**")
    st.success(f"💰 Precio final: **S/. {precio_final:.2f}**")

    # -------------------------
    # Guardar pedido
    # -------------------------
    if st.button("💾 Registrar Pedido"):
        pedido = {
            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Cliente": cliente,
            "Producto": producto,
            "Material": material,
            "Acabado": acabado,
            "Ancho (m)": ancho,
            "Alto (m)": alto,
            "Área (m²)": round(area, 2),
            "Total (S/.)": round(precio_final, 2)
        }
        st.session_state.ventas.append(pedido)
        st.success("Pedido registrado correctamente")

# -------------------------
# Ventas Registradas
# -------------------------
elif menu == "Ventas Registradas":
    st.subheader("📊 Pedidos registrados")

    if not st.session_state.ventas:
        st.warning("No hay pedidos registrados")
    else:
        df = pd.DataFrame(st.session_state.ventas)
        st.dataframe(df, use_container_width=True)

# -------------------------
# Reporte
# -------------------------
elif menu == "Reporte":
    st.subheader("📈 Reporte de Ventas")

    if not st.session_state.ventas:
        st.warning("No hay datos disponibles")
    else:
        df = pd.DataFrame(st.session_state.ventas)

        col1, col2 = st.columns(2)
        col1.metric("Total vendido", f"S/. {df['Total (S/.)'].sum():.2f}")
        col2.metric("Pedidos", len(df))

        st.bar_chart(df.groupby("Producto")["Total (S/.)"].sum())
