import streamlit as st
import psycopg2
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import os  # 👈 AGREGA ESTA LÍNEA

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# --------------------------------
# CONFIG
# --------------------------------
st.set_page_config(page_title="Sistema Comercial - NSJ CAPROYECT", layout="wide")

# --------------------------------
# CONEXIÓN BD
# --------------------------------
def conectar():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets["DB_PORT"]
    )


# --------------------------------
# FUNCIONES BD
# --------------------------------
def obtener_ventas():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, fecha, cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega
        FROM ventas
        WHERE cerrado = FALSE
        ORDER BY fecha DESC
    """)

    rows = cur.fetchall()
    conn.close()

    ventas = []
    for r in rows:
        from zoneinfo import ZoneInfo
        fecha_peru = r[1].astimezone(ZoneInfo("America/Lima"))
        ventas.append({
            "id": r[0],
            "Fecha": fecha_peru,
            "Cliente": r[2],
            "Producto": r[3],
            "Total": float(r[4]),
            "Pagado": float(r[5]),
            "Saldo": float(r[6]),
            "Estado": r[7],
            "Método de pago": r[8],
            "Entrega": r[9]
        })
    return ventas

def registrar_venta(venta):
    conn = conectar()
    cur = conn.cursor()

    # Insertar venta y obtener ID
    cur.execute("""
        INSERT INTO ventas
        (cliente, producto, total, pagado, saldo, estado, metodo_pago, entrega)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        venta["Cliente"],
        venta["Producto"],
        venta["Total"],
        venta["Pagado"],
        venta["Saldo"],
        venta["Estado"],
        venta["Método de pago"],
        venta["Entrega"]
    ))

    venta_id = cur.fetchone()[0]

    # 🔥 REGISTRAR PAGO REAL SOLO SI SE PAGÓ ALGO
    if venta["Pagado"] > 0:
        cur.execute("""
            INSERT INTO pagos (venta_id, fecha, monto, metodo)
            VALUES (%s, NOW(), %s, %s)
        """, (
            venta_id,
            venta["Pagado"],
            venta["Método de pago"]
        ))

    conn.commit()
    conn.close()

    st.success("✅ Venta registrada correctamente")
    st.rerun()



def completar_pago(id_venta, total):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ventas
        SET pagado=%s, saldo=0, estado='Pagado'
        WHERE id=%s
    """, (total, id_venta))
    conn.commit()
    conn.close()
    st.rerun()

def eliminar_venta(id_venta):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM ventas WHERE id=%s", (id_venta,))
    conn.commit()
    conn.close()
    st.rerun()

def marcar_entrega(id_venta, estado):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("UPDATE ventas SET entrega=%s WHERE id=%s", (estado, id_venta))
    conn.commit()
    conn.close()
    st.rerun()
def hora_peru():
    return datetime.now(ZoneInfo("America/Lima"))
    
def cierre_de_caja(usuario_actual):
    conn = conectar()
    cur = conn.cursor()

    # Obtener ventas cerrables
    cur.execute("""
        SELECT id, pagado, metodo_pago
        FROM ventas
        WHERE cerrado = FALSE
        AND entrega = 'Entregado'
        AND saldo = 0
    """)
    ventas = cur.fetchall()

    if not ventas:
        conn.close()
        return False

    total_general = 0
    totales_metodo = {
        "Efectivo": 0,
        "Yape": 0,
        "Plin": 0,
        "Transferencia": 0
    }

    ids = []

    for v in ventas:
        ids.append(v[0])
        monto = float(v[1])
        metodo = v[2]

        total_general += monto
        if metodo in totales_metodo:
            totales_metodo[metodo] += monto

    # Insertar cierre
    cur.execute("""
        INSERT INTO cierres_caja
        (fecha, total_general, total_efectivo, total_yape, total_plin, total_transferencia, usuario)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        hora_peru().date(),
        total_general,
        totales_metodo["Efectivo"],
        totales_metodo["Yape"],
        totales_metodo["Plin"],
        totales_metodo["Transferencia"],
        usuario_actual
    ))

    # Marcar ventas como cerradas
    cur.execute("""
        UPDATE ventas
        SET cerrado = TRUE
        WHERE id = ANY(%s)
    """, (ids,))

    conn.commit()
    conn.close()

    return True

def obtener_cierres():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT fecha, total_general, total_efectivo,
               total_yape, total_plin, total_transferencia,
               usuario, created_at
        FROM cierres_caja
        ORDER BY created_at DESC
    """)
    data = cur.fetchall()
    conn.close()
    return data


# --------------------------------
# INTERFAZ
# --------------------------------

st.title("Sistema Comercial - NSJ CAPROYECT")
st.divider()

METODOS_PAGO = ["Efectivo", "Yape", "Plin", "Transferencia"]

tab_venta, tab_ventas, tab_estadisticas, tab_reporte = st.tabs(
    ["➕ Nueva Venta", "📊 Ventas", "📈 Estadísticas", "📄 Reporte"]
)

# ======================================
# NUEVA VENTA
# ======================================
with tab_venta:
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
            "Cliente": cliente,
            "Producto": producto,
            "Total": total,
            "Pagado": pagado,
            "Saldo": saldo,
            "Estado": estado,
            "Método de pago": metodo_pago,
            "Entrega": entrega
        })

# ======================================
# VENTAS
# ======================================
with tab_ventas:
    ventas = obtener_ventas()

    if ventas:
        from datetime import datetime
        import pytz
        
        peru = pytz.timezone("America/Lima")
        hoy = datetime.now(peru).date()
        
        total_vendido = sum(v["Total"] for v in ventas)
        total_pendiente = sum(v["Saldo"] for v in ventas)
        
        # 🔹 NUEVO: total cobrado real desde tabla pagos
        conn = conectar()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COALESCE(SUM(monto),0)
            FROM pagos
            WHERE DATE(fecha) = %s
        """, (hoy,))
        
        total_cobrado = cur.fetchone()[0]
        
        conn.close()


        col1, col2, col3 = st.columns(3)
        col1.metric("Total Vendido", f"S/. {total_vendido:.2f}")
        col2.metric("Total Cobrado", f"S/. {total_cobrado:.2f}")
        col3.metric("Total Pendiente", f"S/. {total_pendiente:.2f}")

        for v in ventas:
            with st.container(border=True):
        
                st.markdown(f"### 🧾 Pedido #{v['id']}")
        
                st.write(f"📅 Fecha: {v['Fecha'].strftime('%d/%m/%Y %H:%M')}")
                
                col1, col2 = st.columns(2)
        
                with col1:
                    st.write(f"👤 Cliente: {v['Cliente']}")
                    st.write(f"📦 Producto: {v['Producto']}")
                    st.write(f"💳 Método de pago: {v['Método de pago']}")
        
                with col2:
                    st.write(f"💰 Total: S/. {v['Total']:.2f}")
                    st.write(f"💵 Pagado: S/. {v['Pagado']:.2f}")
                    st.write(f"🧾 Saldo: S/. {v['Saldo']:.2f}")
        
                # Estado de pago
                if v["Saldo"] > 0:
                    st.warning(f"⚠️ Adelanto recibido. Falta pagar: S/. {v['Saldo']:.2f}")
                else:
                    st.success("✅ Pagado completamente")
        
                # Estado de entrega
                if v["Entrega"] == "Pendiente":
                    st.info("🚚 Entrega pendiente")
                else:
                    st.success("📦 Pedido entregado")
        
                # -----------------------------
                # BOTONES DE ACCIÓN
                # -----------------------------
                colA, colB, colC = st.columns(3)
        
                # Completar pago
                if v["Saldo"] > 0:
                    if colA.button("💵 Completar pago", key=f"pago_{v['id']}"):
                        completar_pago(v["id"], v["Total"])
        
                # Marcar entrega
                nuevo_estado = "Entregado" if v["Entrega"] == "Pendiente" else "Pendiente"
                if colB.button(f"🚚 Marcar {nuevo_estado}", key=f"ent_{v['id']}"):
                    marcar_entrega(v["id"], nuevo_estado)
        
                # Eliminar
                if colC.button("🗑 Eliminar", key=f"del_{v['id']}"):
                    eliminar_venta(v["id"])
        
                st.divider()


# ======================================
# ESTADÍSTICAS
# ======================================
with tab_estadisticas:

    from datetime import datetime
    import pytz

    peru = pytz.timezone("America/Lima")
    hoy = datetime.now(peru).date()

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT metodo, COUNT(*), COALESCE(SUM(monto),0)
        FROM pagos
        WHERE DATE(fecha) = %s
        GROUP BY metodo
        ORDER BY SUM(monto) DESC
    """, (hoy,))

    resultados = cur.fetchall()
    conn.close()

    st.subheader("📊 Métodos de pago más usados (Hoy)")

    if resultados:
        for metodo, cantidad, total in resultados:
            st.write(f"💳 {metodo}")
            st.write(f"   • Cantidad de pagos: {cantidad}")
            st.write(f"   • Total recibido: S/. {total:.2f}")
            st.divider()
    else:
        st.info("No hay pagos registrados hoy.")

# ======================================
# REPORTE PROFESIONAL
# ======================================
    from io import BytesIO
    from reportlab.platypus import Image
    from reportlab.lib.units import inch
    
    if st.button("Generar PDF"):
    
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        elementos = []
        estilos = getSampleStyleSheet()
    
        # ==========================
        # LOGO
        # ==========================
        if os.path.exists("logo.png"):
            logo = Image("logo.png", width=2*inch, height=1*inch)
            elementos.append(logo)
    
        elementos.append(Spacer(1, 10))
    
        # ==========================
        # ENCABEZADO
        # ==========================
        elementos.append(Paragraph("<b>SISTEMA COMERCIAL</b>", estilos["Title"]))
        elementos.append(Paragraph("<b>NSJ CAPROYECT</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 5))
        elementos.append(Paragraph(
            f"Fecha de emisión: {hora_peru().strftime('%d/%m/%Y %H:%M')}",
            estilos["Normal"]
        ))
        elementos.append(Spacer(1, 20))
    
        # ==========================
        # TOTALES GENERALES
        # ==========================
        total_vendido = sum(v["Total"] for v in ventas)
        total_cobrado = sum(v["Pagado"] for v in ventas)
        total_pendiente = sum(v["Saldo"] for v in ventas)
    
        elementos.append(Paragraph("<b>RESUMEN GENERAL</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))
    
        resumen_data = [
            ["Total Vendido", f"S/. {total_vendido:.2f}"],
            ["Total Cobrado (Ganancia Real)", f"S/. {total_cobrado:.2f}"],
            ["Total Pendiente", f"S/. {total_pendiente:.2f}"],
        ]
    
        tabla_resumen = Table(resumen_data, colWidths=[250, 150])
        tabla_resumen.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
    
        elementos.append(tabla_resumen)
        elementos.append(Spacer(1, 20))
    
        # ==========================
        # RESUMEN MÉTODOS DE PAGO
        # ==========================
        elementos.append(Paragraph("<b>RESUMEN POR MÉTODO DE PAGO</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))
    
        metodos = {}
        for v in ventas:
            metodos[v["Método de pago"]] = metodos.get(v["Método de pago"], 0) + v["Pagado"]
    
        data_metodos = [["Método", "Monto Recibido"]]
    
        for metodo, monto in metodos.items():
            data_metodos.append([metodo, f"S/. {monto:.2f}"])
    
        tabla_metodos = Table(data_metodos, repeatRows=1, colWidths=[200, 150])
        tabla_metodos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
    
        elementos.append(tabla_metodos)
        elementos.append(Spacer(1, 25))
    
        # ==========================
        # DETALLE COMPLETO DE VENTAS
        # ==========================
        elementos.append(Paragraph("<b>DETALLE COMPLETO DE VENTAS</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))
    
        data = [[
            "Fecha",
            "Cliente",
            "Producto",
            "Total",
            "Pagado",
            "Saldo",
            "Estado",
            "Método",
            "Entrega"
        ]]
    
        for v in ventas:
            data.append([
                str(v["Fecha"]),
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
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
        ]))
    
        elementos.append(tabla)
    
        # ==========================
        # PIE DE PÁGINA
        # ==========================
        elementos.append(Spacer(1, 30))
    
        # Construir PDF
        doc.build(elementos)
    
        buffer.seek(0)
    
        st.download_button(
            "Descargar Reporte ",
            buffer,
            "reporte_ventas_profesional.pdf",
            "application/pdf"
        )

# ======================================
# CIERRE DE CAJA
# ======================================
with tab_reporte:
    from io import BytesIO
    from reportlab.platypus import Image
    from reportlab.lib.units import inch
    
    if st.button("Generar PDF"):
    
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer)
        elementos = []
        estilos = getSampleStyleSheet()
    
        # ==========================
        # LOGO
        # ==========================
        if os.path.exists("logo.png"):
            logo = Image("logo.png", width=2*inch, height=1*inch)
            elementos.append(logo)
    
        elementos.append(Spacer(1, 10))
    
        # ==========================
        # ENCABEZADO
        # ==========================
        elementos.append(Paragraph("<b>SISTEMA COMERCIAL</b>", estilos["Title"]))
        elementos.append(Paragraph("<b>NSJ CAPROYECT</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 5))
        elementos.append(Paragraph(
            f"Fecha de emisión: {hora_peru().strftime('%d/%m/%Y %H:%M')}",
            estilos["Normal"]
        ))
        elementos.append(Spacer(1, 20))
    
        # ==========================
        # TOTALES GENERALES
        # ==========================
        total_vendido = sum(v["Total"] for v in ventas)
        total_cobrado = sum(v["Pagado"] for v in ventas)
        total_pendiente = sum(v["Saldo"] for v in ventas)
    
        elementos.append(Paragraph("<b>RESUMEN GENERAL</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))
    
        resumen_data = [
            ["Total Vendido", f"S/. {total_vendido:.2f}"],
            ["Total Cobrado (Ganancia Real)", f"S/. {total_cobrado:.2f}"],
            ["Total Pendiente", f"S/. {total_pendiente:.2f}"],
        ]
    
        tabla_resumen = Table(resumen_data, colWidths=[250, 150])
        tabla_resumen.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
    
        elementos.append(tabla_resumen)
        elementos.append(Spacer(1, 20))
    
        # ==========================
        # RESUMEN MÉTODOS DE PAGO
        # ==========================
        elementos.append(Paragraph("<b>RESUMEN POR MÉTODO DE PAGO</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))
    
        metodos = {}
        for v in ventas:
            metodos[v["Método de pago"]] = metodos.get(v["Método de pago"], 0) + v["Pagado"]
    
        data_metodos = [["Método", "Monto Recibido"]]
    
        for metodo, monto in metodos.items():
            data_metodos.append([metodo, f"S/. {monto:.2f}"])
    
        tabla_metodos = Table(data_metodos, repeatRows=1, colWidths=[200, 150])
        tabla_metodos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
    
        elementos.append(tabla_metodos)
        elementos.append(Spacer(1, 25))
    
        # ==========================
        # DETALLE COMPLETO DE VENTAS
        # ==========================
        elementos.append(Paragraph("<b>DETALLE COMPLETO DE VENTAS</b>", estilos["Heading2"]))
        elementos.append(Spacer(1, 10))
    
        data = [[
            "Fecha",
            "Cliente",
            "Producto",
            "Total",
            "Pagado",
            "Saldo",
            "Estado",
            "Método",
            "Entrega"
        ]]
    
        for v in ventas:
            data.append([
                str(v["Fecha"]),
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
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
        ]))
    
        elementos.append(tabla)
    
        # ==========================
        # PIE DE PÁGINA
        # ==========================
        elementos.append(Spacer(1, 30))
    
        # Construir PDF
        doc.build(elementos)
    
        buffer.seek(0)
    
        st.download_button(
            "Descargar Reporte ",
            buffer,
            "reporte_ventas_profesional.pdf",
            "application/pdf"
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
                st.write(f"Efectivo: S/. {c[2]}")
                st.write(f"Yape: S/. {c[3]}")
                st.write(f"Plin: S/. {c[4]}")
                st.write(f"Transferencia: S/. {c[5]}")
                st.write(f"👤 Usuario: {c[6]}")
                st.write(f"🕒 Registrado: {c[7]}")
    else:
        st.info("No hay cierres registrados aún.")

    st.divider()

