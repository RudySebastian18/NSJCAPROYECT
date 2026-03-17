import streamlit as st
import psycopg2
import psycopg2.pool
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import os
import time

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# --------------------------------
# CONFIG
# --------------------------------
st.set_page_config(page_title="Sistema Comercial - NSJ CAPROYECT", layout="wide")

# --------------------------------
# CONEXIÓN BD CON POOL
# --------------------------------
@st.cache_resource
def get_connection_pool():
    return psycopg2.pool.SimpleConnectionPool(
        1, 5,
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )

def conectar():
    pool = get_connection_pool()
    return pool.getconn()

def liberar_conexion(conn):
    pool = get_connection_pool()
    pool.putconn(conn)

# --------------------------------
# FUNCIONES BD
# --------------------------------
def hora_peru():
    return datetime.now(ZoneInfo("America/Lima"))

def registrar_venta(venta):
    conn = conectar()
    try:
        cur = conn.cursor()
        fecha_peru = hora_peru()

        cur.execute("""
            INSERT INTO ventas
            (cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega, fecha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            venta["Cliente"], venta["Producto"], venta["Total"],
            venta["Pagado"], venta["Saldo"], venta["Estado"],
            venta["Método de pago"], venta["Entrega"], fecha_peru
        ))

        venta_id = cur.fetchone()[0]

        if venta["Pagado"] > 0:
            cur.execute("""
                INSERT INTO pagos (venta_id, fecha, monto, metodo)
                VALUES (%s, %s, %s, %s)
            """, (venta_id, fecha_peru, venta["Pagado"], venta["Método de pago"]))

        conn.commit()
        st.session_state.mensaje_exito = f"✅ Venta #{venta_id} registrada correctamente"
    finally:
        liberar_conexion(conn)
    st.rerun()

def completar_pago(id_venta, saldo_actual, metodo_pago):
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pagos (venta_id, fecha, monto, metodo)
            VALUES (%s, %s, %s, %s)
        """, (id_venta, hora_peru(), saldo_actual, metodo_pago))

        cur.execute("""
            UPDATE ventas
            SET pagado = pagado + %s, saldo = 0, estado = 'Pagado'
            WHERE id = %s
        """, (saldo_actual, id_venta))

        conn.commit()
        st.session_state.mensaje_exito = f"✅ Pago completado correctamente (S/. {saldo_actual:.2f})"
    finally:
        liberar_conexion(conn)
    st.rerun()

def marcar_entrega(id_venta, estado):
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE ventas SET entrega=%s WHERE id=%s", (estado, id_venta))
        conn.commit()
        st.session_state.mensaje_exito = f"✅ Entrega marcada como: {estado}"
    finally:
        liberar_conexion(conn)
    st.rerun()

def eliminar_venta(id_venta):
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM pagos WHERE venta_id=%s", (id_venta,))
        cur.execute("DELETE FROM ventas WHERE id=%s", (id_venta,))
        conn.commit()
        st.session_state.mensaje_exito = "✅ Venta eliminada correctamente"
    finally:
        liberar_conexion(conn)
    st.rerun()

def cierre_de_caja(usuario_actual):
    conn = conectar()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM ventas
            WHERE cerrado = FALSE AND entrega = 'Entregado' AND saldo = 0
        """)
        ventas_ids = cur.fetchall()

        if not ventas_ids:
            return False

        ids = [v[0] for v in ventas_ids]
        
        cur.execute("""
            SELECT p.metodo, COALESCE(SUM(p.monto), 0) as total
            FROM pagos p
            WHERE p.venta_id = ANY(%s)
            GROUP BY p.metodo
        """, (ids,))
        
        pagos_por_metodo = cur.fetchall()

        totales_metodo = {"Efectivo": 0, "Yape": 0, "Plin": 0, "Transferencia": 0}
        total_general = 0
        
        for metodo, monto in pagos_por_metodo:
            monto_float = float(monto)
            total_general += monto_float
            if metodo in totales_metodo:
                totales_metodo[metodo] += monto_float

        cur.execute("""
            INSERT INTO cierres_caja
            (fecha, total_general, total_efectivo, total_yape, total_plin, total_transferencia, usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            hora_peru().date(), total_general,
            totales_metodo["Efectivo"], totales_metodo["Yape"],
            totales_metodo["Plin"], totales_metodo["Transferencia"],
            usuario_actual
        ))

        cur.execute("UPDATE ventas SET cerrado = TRUE WHERE id = ANY(%s)", (ids,))
        conn.commit()
        st.session_state.mensaje_exito = f"✅ Cierre realizado: S/. {total_general:.2f}"
        return True
    finally:
        liberar_conexion(conn)

@st.cache_data(ttl=60)
def obtener_cierres():
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT fecha, total_general, total_efectivo, total_yape, total_plin,
                   total_transferencia, usuario, created_at
            FROM cierres_caja
            ORDER BY created_at DESC
        """)
        data = cur.fetchall()
    finally:
        liberar_conexion(conn)
    return data

def obtener_ventas():
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
            FROM ventas
            WHERE cerrado = FALSE
            ORDER BY fecha DESC
        """)
        rows = cur.fetchall()
    finally:
        liberar_conexion(conn)

    ventas = []
    for r in rows:
        fecha_peru = r[1].astimezone(ZoneInfo("America/Lima"))
        ventas.append({
            "id": r[0], "Fecha": fecha_peru, "Cliente": r[2], "Producto": r[3],
            "Total": float(r[4]), "Pagado": float(r[5]), "Saldo": float(r[6]),
            "Estado": r[7], "Método de pago": r[8], "Entrega": r[9]
        })
    return ventas

# --------------------------------
# FRAGMENTOS OPTIMIZADOS
# --------------------------------
@st.fragment
def mostrar_ventas():
    conn = conectar()
    try:
        cur = conn.cursor()
        
        # Consulta optimizada: todo en una
        cur.execute("""
            SELECT 
                (SELECT COALESCE(SUM(total),0) FROM ventas 
                 WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE) as total_vendido,
                (SELECT COALESCE(SUM(monto),0) FROM pagos 
                 WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE) as total_cobrado,
                (SELECT COALESCE(SUM(saldo),0) FROM ventas 
                 WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE) as total_pendiente
        """)
        
        totales = cur.fetchone()
        total_vendido = float(totales[0])
        total_cobrado = float(totales[1])
        total_pendiente = float(totales[2])
        
        # Ventas no cerradas de hoy
        cur.execute("""
            SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
            FROM ventas
            WHERE cerrado = FALSE
            AND DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE
            ORDER BY fecha DESC
        """)
        rows = cur.fetchall()
    finally:
        liberar_conexion(conn)

    ventas = []
    for r in rows:
        fecha_peru = r[1].astimezone(ZoneInfo("America/Lima"))
        ventas.append({
            "id": r[0], "Fecha": fecha_peru, "Cliente": r[2], "Producto": r[3],
            "Total": float(r[4]), "Pagado": float(r[5]), "Saldo": float(r[6]),
            "Estado": r[7], "Método de pago": r[8], "Entrega": r[9]
        })
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vendido (Hoy)", f"S/. {total_vendido:.2f}")
    col2.metric("Total Cobrado (Hoy)", f"S/. {total_cobrado:.2f}")
    col3.metric("Total Pendiente (Hoy)", f"S/. {total_pendiente:.2f}")
    st.divider()
    
    if not ventas:
        st.info("✅ No hay ventas pendientes hoy")
        return

    st.subheader("📋 Ventas Pendientes")

    for v in ventas:
        with st.container(border=True):
            st.markdown(f"### 🧾 Pedido #{v['id']}")
            st.write(f"📅 Fecha: {v['Fecha'].strftime('%d/%m/%Y %H:%M')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"👤 Cliente: {v['Cliente']}")
                st.write(f"📦 Producto: {v['Producto']}")
                st.write(f"💳 Método de pago inicial: {v['Método de pago']}")
            with col2:
                st.write(f"💰 Total: S/. {v['Total']:.2f}")
                st.write(f"💵 Pagado: S/. {v['Pagado']:.2f}")
                st.write(f"🧾 Saldo: S/. {v['Saldo']:.2f}")
    
            if v["Saldo"] > 0:
                st.warning(f"⚠️ Adelanto recibido. Falta pagar: S/. {v['Saldo']:.2f}")
            else:
                st.success("✅ Pagado completamente")
    
            if v["Entrega"] == "Pendiente":
                st.info("🚚 Entrega pendiente")
            else:
                st.success("📦 Pedido entregado")
    
            colA, colB, colC = st.columns(3)
    
            if v["Saldo"] > 0:
                with colA:
                    popover = st.popover("💵 Completar pago")
                    with popover:
                        st.write(f"**Saldo pendiente:** S/. {v['Saldo']:.2f}")
                        metodo_completar = st.selectbox("Método de pago", METODOS_PAGO, key=f"metodo_pago_{v['id']}")
                        if st.button("✅ Confirmar pago", key=f"confirmar_{v['id']}", type="primary"):
                            completar_pago(v["id"], v["Saldo"], metodo_completar)
    
            with colB:
                nuevo_estado = "Entregado" if v["Entrega"] == "Pendiente" else "Pendiente"
                if st.button(f"🚚 Marcar {nuevo_estado}", key=f"ent_{v['id']}"):
                    marcar_entrega(v["id"], nuevo_estado)
    
            with colC:
                if st.button("🗑 Eliminar", key=f"del_{v['id']}"):
                    eliminar_venta(v["id"])
    
            st.divider()

@st.fragment
def mostrar_ventas_anteriores():
    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
            FROM ventas
            WHERE cerrado = FALSE
            AND DATE(fecha AT TIME ZONE 'America/Lima') < CURRENT_DATE
            ORDER BY fecha DESC
        """)
        rows = cur.fetchall()
    finally:
        liberar_conexion(conn)

    ventas = []
    for r in rows:
        fecha_peru = r[1].astimezone(ZoneInfo("America/Lima"))
        ventas.append({
            "id": r[0], "Fecha": fecha_peru, "Cliente": r[2], "Producto": r[3],
            "Total": float(r[4]), "Pagado": float(r[5]), "Saldo": float(r[6]),
            "Estado": r[7], "Método de pago": r[8], "Entrega": r[9]
        })
    
    if not ventas:
        st.info("✅ No hay ventas pendientes de días anteriores")
        return

    st.subheader(f"📋 Ventas Pendientes de Días Anteriores ({len(ventas)})")
    st.warning("⚠️ Estas ventas son de días anteriores y no se incluyen en los totales de hoy")
    st.divider()

    for v in ventas:
        with st.container(border=True):
            st.markdown(f"### 🧾 Pedido #{v['id']}")
            st.write(f"📅 Fecha: {v['Fecha'].strftime('%d/%m/%Y %H:%M')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"👤 Cliente: {v['Cliente']}")
                st.write(f"📦 Producto: {v['Producto']}")
                st.write(f"💳 Método de pago inicial: {v['Método de pago']}")
            with col2:
                st.write(f"💰 Total: S/. {v['Total']:.2f}")
                st.write(f"💵 Pagado: S/. {v['Pagado']:.2f}")
                st.write(f"🧾 Saldo: S/. {v['Saldo']:.2f}")
    
            if v["Saldo"] > 0:
                st.warning(f"⚠️ Adelanto recibido. Falta pagar: S/. {v['Saldo']:.2f}")
            else:
                st.success("✅ Pagado completamente")
    
            if v["Entrega"] == "Pendiente":
                st.info("🚚 Entrega pendiente")
            else:
                st.success("📦 Pedido entregado")
    
            colA, colB, colC = st.columns(3)
    
            if v["Saldo"] > 0:
                with colA:
                    popover = st.popover("💵 Completar pago")
                    with popover:
                        st.write(f"**Saldo pendiente:** S/. {v['Saldo']:.2f}")
                        metodo_completar = st.selectbox("Método de pago", METODOS_PAGO, key=f"metodo_ant_{v['id']}")
                        if st.button("✅ Confirmar pago", key=f"confirmar_ant_{v['id']}", type="primary"):
                            completar_pago(v["id"], v["Saldo"], metodo_completar)
    
            with colB:
                nuevo_estado = "Entregado" if v["Entrega"] == "Pendiente" else "Pendiente"
                if st.button(f"🚚 Marcar {nuevo_estado}", key=f"ent_ant_{v['id']}"):
                    marcar_entrega(v["id"], nuevo_estado)
    
            with colC:
                if st.button("🗑 Eliminar", key=f"del_ant_{v['id']}"):
                    eliminar_venta(v["id"])
    
            st.divider()

@st.fragment
def mostrar_estadisticas():
    conn = conectar()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT metodo, COUNT(*), COALESCE(SUM(monto),0)
            FROM pagos
            WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE
            GROUP BY metodo
            ORDER BY SUM(monto) DESC
        """)
        resultados = cur.fetchall()
        
        cur.execute("""
            SELECT COALESCE(SUM(monto),0)
            FROM pagos
            WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE
        """)
        total_general = cur.fetchone()[0]
    finally:
        liberar_conexion(conn)
    
    st.subheader("📊 Métodos de pago del día")
    st.metric("💰 Total cobrado hoy", f"S/. {float(total_general):.2f}")
    st.divider()
    
    if resultados:
        st.markdown("### Desglose por método de pago:")
        for metodo, cantidad, total in resultados:
            col1, col2 = st.columns([2, 1])
            with col1:
                porcentaje = (float(total) / float(total_general) * 100) if total_general > 0 else 0
                st.write(f"**💳 {metodo}**")
                st.progress(porcentaje / 100)
            with col2:
                st.metric(label=f"{cantidad} pago{'s' if cantidad > 1 else ''}", value=f"S/. {float(total):.2f}")
            st.divider()
    else:
        st.info("No hay pagos registrados hoy.")

# --------------------------------
# AUTO-REFRESH
# --------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    auto_refresh = st.checkbox("🔄 Auto-actualizar cada 5s", value=False)
    if st.button("🔄 Actualizar ahora", use_container_width=True):
        st.rerun()
    if auto_refresh:
        time.sleep(5)
        st.rerun()
    st.divider()
    st.caption(f"Última actualización: {hora_peru().strftime('%H:%M:%S')}")

# --------------------------------
# INTERFAZ
# --------------------------------
st.title("Sistema Comercial - NSJ CAPROYECT")
st.divider()

METODOS_PAGO = ["Efectivo", "Yape", "Plin", "Transferencia"]

tab_venta, tab_ventas, tab_anteriores, tab_estadisticas, tab_reporte = st.tabs(
    ["➕ Nueva Venta", "📊 Ventas Hoy", "📋 Ventas Anteriores", "📈 Estadísticas", "📄 Reporte"]
)

# ======================================
# NUEVA VENTA
# ======================================
with tab_venta:
    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito
    
    cliente = st.text_input("Cliente")
    producto = st.text_input("Producto")
    total = st.number_input("Total", min_value=0.0)
    metodo_pago = st.selectbox("Método de pago", METODOS_PAGO)
    tipo_pago = st.radio("Tipo de pago", ["Pago completo", "Adelanto"])

    if tipo_pago == "Pago completo":
        pagado = total
        saldo = 0
        estado = "Pagado"
    else:
        adelanto = st.number_input("Monto adelanto", min_value=0.0)
        pagado = adelanto
        saldo = total - adelanto
        estado = "Pendiente" if saldo > 0 else "Pagado"

    entrega = st.selectbox("Estado de entrega", ["Pendiente", "Entregado"])

    if st.button("Registrar venta"):
        registrar_venta({
            "Cliente": cliente, "Producto": producto, "Total": total,
            "Pagado": pagado, "Saldo": saldo, "Estado": estado,
            "Método de pago": metodo_pago, "Entrega": entrega
        })

# ======================================
# VENTAS HOY
# ======================================
with tab_ventas:
    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito
    mostrar_ventas()

# ======================================
# VENTAS ANTERIORES
# ======================================
with tab_anteriores:
    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito
    mostrar_ventas_anteriores()

# ======================================
# ESTADÍSTICAS
# ======================================
with tab_estadisticas:
    mostrar_estadisticas()

# ======================================
# REPORTE
# ======================================
with tab_reporte:
    ventas = obtener_ventas()

    st.subheader("📄 Reporte Profesional")

    if not ventas:
        st.warning("No hay ventas para generar reporte")
    else:
        if st.button("Generar PDF"):
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer)
            elementos = []
            estilos = getSampleStyleSheet()

            # LOGO
            if os.path.exists("logo.png"):
                logo = Image("logo.png", width=2*inch, height=1*inch)
                elementos.append(logo)

            elementos.append(Spacer(1, 10))
            
            # ENCABEZADO
            elementos.append(Paragraph("<b>SISTEMA COMERCIAL</b>", estilos["Title"]))
            elementos.append(Paragraph("<b>NSJ CAPROYECT</b>", estilos["Heading2"]))
            elementos.append(Spacer(1, 5))
            elementos.append(Paragraph(f"Fecha de emisión: {hora_peru().strftime('%d/%m/%Y %H:%M')}", estilos["Normal"]))
            elementos.append(Spacer(1, 20))

            # TOTALES GENERALES
            total_vendido = sum(v["Total"] for v in ventas)
            total_pagado = sum(v["Pagado"] for v in ventas)
            total_pendiente = sum(v["Saldo"] for v in ventas)

            resumen_data = [
                ["Total Vendido", f"S/. {total_vendido:.2f}"],
                ["Total Cobrado", f"S/. {total_pagado:.2f}"],
                ["Total Pendiente", f"S/. {total_pendiente:.2f}"],
            ]

            tabla_resumen = Table(resumen_data, colWidths=[250, 150])
            tabla_resumen.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))

            elementos.append(tabla_resumen)
            elementos.append(Spacer(1, 25))

            # ✅ ESTADÍSTICAS POR MÉTODO DE PAGO
            conn = conectar()
            try:
                cur = conn.cursor()
                
                # Obtener estadísticas de pagos
                cur.execute("""
                    SELECT metodo, COUNT(*), COALESCE(SUM(monto),0)
                    FROM pagos
                    WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE
                    GROUP BY metodo
                    ORDER BY SUM(monto) DESC
                """)
                estadisticas = cur.fetchall()
                
                # Total cobrado hoy
                cur.execute("""
                    SELECT COALESCE(SUM(monto),0)
                    FROM pagos
                    WHERE DATE(fecha AT TIME ZONE 'America/Lima') = CURRENT_DATE
                """)
                total_cobrado_hoy = float(cur.fetchone()[0])
            finally:
                liberar_conexion(conn)

            if estadisticas:
                elementos.append(Paragraph("<b>ESTADÍSTICAS DE PAGOS DEL DÍA</b>", estilos["Heading3"]))
                elementos.append(Spacer(1, 10))
                
                # Tabla de estadísticas
                estadisticas_data = [["Método de Pago", "Cantidad", "Total Recibido", "Porcentaje"]]
                
                for metodo, cantidad, total in estadisticas:
                    porcentaje = (float(total) / total_cobrado_hoy * 100) if total_cobrado_hoy > 0 else 0
                    estadisticas_data.append([
                        metodo,
                        str(cantidad),
                        f"S/. {float(total):.2f}",
                        f"{porcentaje:.1f}%"
                    ])
                
                # Fila de totales
                total_pagos = sum(e[1] for e in estadisticas)
                estadisticas_data.append([
                    "TOTAL",
                    str(total_pagos),
                    f"S/. {total_cobrado_hoy:.2f}",
                    "100.0%"
                ])
                
                tabla_estadisticas = Table(estadisticas_data, colWidths=[150, 80, 120, 80])
                tabla_estadisticas.setStyle(TableStyle([
                    # Encabezado
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    
                    # Contenido
                    ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -2), 9),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
                    
                    # Fila de totales
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, -1), (-1, -1), 10),
                    
                    # Bordes
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ]))
                
                elementos.append(tabla_estadisticas)
                elementos.append(Spacer(1, 25))

            # DETALLE DE VENTAS
            elementos.append(Paragraph("<b>DETALLE DE VENTAS PENDIENTES</b>", estilos["Heading3"]))
            elementos.append(Spacer(1, 10))

            data = [["Fecha", "Cliente", "Producto", "Total", "Pagado", "Saldo", "Estado", "Método", "Entrega"]]
            for v in ventas:
                data.append([
                    v["Fecha"].strftime('%d/%m/%Y %H:%M'), 
                    v["Cliente"], 
                    v["Producto"],
                    f"S/. {v['Total']:.2f}", 
                    f"S/. {v['Pagado']:.2f}", 
                    f"S/. {v['Saldo']:.2f}",
                    v["Estado"], 
                    v["Método de pago"], 
                    v["Entrega"]
                ])

            tabla = Table(data, repeatRows=1)
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
            ]))

            elementos.append(tabla)
            
            # PIE DE PÁGINA
            elementos.append(Spacer(1, 20))
            elementos.append(Paragraph(
                f"<i>Reporte generado automáticamente por Sistema Comercial NSJ CAPROYECT</i>",
                estilos["Normal"]
            ))

            doc.build(elementos)
            buffer.seek(0)

            st.download_button(
                "📥 Descargar Reporte Completo", 
                buffer, 
                f"reporte_ventas_{hora_peru().strftime('%Y%m%d_%H%M%S')}.pdf", 
                "application/pdf",
                use_container_width=True
            )

    st.divider()
    st.subheader("🔒 Cierre de Caja")

    if st.button("Realizar Cierre de Caja"):
        resultado = cierre_de_caja("Admin")
        if resultado:
            st.success("✅ Cierre realizado correctamente")
            st.rerun()
        else:
            st.warning("No hay ventas entregadas y pagadas para cerrar")

    st.divider()
    st.subheader("📜 Historial de Cierres")

    cierres = obtener_cierres()
    if cierres:
        for c in cierres:
            with st.container(border=True):
                st.write(f"📅 Fecha: {c[0]}")
                st.write(f"💰 Total General: S/. {c[1]}")
                st.write(f"Efectivo: S/. {c[2]} | Yape: S/. {c[3]} | Plin: S/. {c[4]} | Transferencia: S/. {c[5]}")
                st.write(f"👤 Usuario: {c[6]} | 🕒 Registrado: {c[7]}")
    else:
        st.info("No hay cierres registrados aún.")
