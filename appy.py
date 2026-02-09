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
st.caption("Registro interno de ventas")

# -------------------------
# DATOS DEL NEGOCIO
# -------------------------
PRODUCTOS = ["Banner", "Vinil", "Extra"]

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
    st.session_state.ventas = cargar_ventas()

# =====================================================
# FUNCIÓN PARA REGISTRAR VENTA
# =====================================================
def registrar_venta(venta):
    st.session_state.ventas.append(venta)
    guardar_ventas()
    st.success("✅ Venta registrada correctamente")

# =====================================================
# 📌 NUEVA VENTA
# =====================================================
st.subheader("➕ Registrar nueva venta")

col1, col2 = st.columns(2)

with col1:
    cliente = st.text_input("Cliente")
    producto = st.selectbox("Producto", PRODUCTOS)
    detalle = st.text_input("Detalle / Concepto")

with col2:
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO)
    total = st.number_input("Total (S/.)", min_value=0.0, step=1.0)

if st.button("➕ Agregar Venta"):
    registrar_venta({
        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Cliente": cliente,
        "Producto": producto,
        "Detalle": detalle,
        "Método de pago": metodo_pago,
        "Total": round(total, 2)
    })

st.divider()

# =====================================================
# 📊 VENTAS DEL DÍA
# =====================================================
st.subheader("📊 Ventas del día")

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

    # ===============================
    # PANEL DE EDICIÓN
    # ===============================
    if "edit_index" in st.session_state:
        idx = st.session_state.edit_index
        venta = st.session_state.ventas[idx]

        st.divider()
        st.subheader(f"✏️ Editando venta #{idx+1}")

        nuevo_cliente = st.text_input("Cliente", value=venta["Cliente"])
        nuevo_producto = st.selectbox(
            "Producto",
            PRODUCTOS,
            index=PRODUCTOS.index(venta["Producto"])
        )
        nuevo_detalle = st.text_input("Detalle", value=venta["Detalle"])
        nuevo_metodo = st.selectbox(
            "Método de pago",
            METODOS_PAGO,
            index=METODOS_PAGO.index(venta["Método de pago"])
        )
        nuevo_total = st.number_input(
            "Total",
            value=float(venta["Total"]),
            step=1.0
        )

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

st.divider()

# =====================================================
# 📁 CIERRE / EXPORTAR EXCEL
# =====================================================
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
        st.success("✅ Día cerrado correctamente")
        st.rerun()
