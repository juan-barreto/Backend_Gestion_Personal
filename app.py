from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta # Agregamos timedelta para filtros de fecha
import json
# --- Importaciones de Database (Migradas a Supabase) ---
# Importamos directamente las funciones necesarias, no las de creacion_tabla que ya no son activas.
from database import (
    creacion_tabla, creacion_tabla_alquiler, creacion_tabla_presupuesto, # Placeholders, no hacen nada
    guardar_ajuste, obtener_historial_alquiler, borrar_calculo, borrar_historial_completo,
    guardar_cotizacion, obtener_cotizacion_anterior, obtener_historial_cotizacion,
    agregar_movimiento, obtener_movimientos, editar_movimiento, borrar_movimiento, reset_presupuesto
)

# --- Importaciones de Rutas Externas (no necesitan user_id por ahora) ---
from routes.dolar import obtener_todos
from routes.ipc import obtener_ipc
from routes.icl import obtener_icl
from routes.ripte import obtener_ripte

# --- Importaciones de Servicios ---
from services.calculos import calcular_ajuste
from services.asistente import consultar_asistente

# --- Importación del decorador de Autenticación ---
from auth import token_required

# --- Importaciones para exportación ---
import requests as req_interno
from flask import send_file
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
import os # Para la ruta de las fuentes del PDF
from fpdf import FPDF # Asegúrate de tener fpdf instalado: pip install fpdf2


# ── COLORES PDF/EXCEL — definidos globalmente ──
VERDE        = (22, 163, 74)
ROJO         = (220, 38, 38)
VERDE_OSCURO = (20, 83, 45)
GRIS_CLARO   = (243, 244, 246)
BLANCO       = (255, 255, 255)

app = Flask(__name__)


# --- Funciones de Scheduler ---
def actualizar_cotizaciones():
    """Actualiza y guarda las cotizaciones globales en la DB cada 30 minutos"""
    try:
        datos = obtener_todos()
        for dolar in datos:
            # guardar_cotizacion no necesita user_id
            guardar_cotizacion(dolar["casa"], dolar["venta"], dolar["compra"])
        print("Cotizaciones actualizadas en Supabase.")
    except Exception as e:
        print(f"Error actualizando cotizaciones: {e}")

def ping_propio():
    """Mantiene Railway despierto cada 14 minutos"""
    try:
        # Asegúrate de que esta URL sea la de tu backend desplegado
        req_interno.get(os.getenv("RAILWAY_APP_URL", "http://localhost:5000"))
        print("Ping enviado - servidor despierto.")
    except Exception as e:
        print(f"Error en ping: {e}")

# --- Contexto de la App (para inicialización) ---
with app.app_context():
    # Las funciones de creacion_tabla ahora son placeholders y no hacen nada.
    # La creación real es manual en el SQL Editor de Supabase.
    creacion_tabla()
    creacion_tabla_alquiler()
    creacion_tabla_presupuesto()
    actualizar_cotizaciones() # Todavía útil para cargar cotizaciones al inicio

# --- Scheduler ---
scheduler = BackgroundScheduler()
scheduler.add_job(actualizar_cotizaciones, 'interval', minutes=30)
scheduler.add_job(ping_propio, 'interval', minutes=14)
scheduler.start()


# --- Endpoints ---

@app.route("/")
def inicio():
    return jsonify({"mensaje": "API funcionando con Supabase!"})

@app.route("/dolar")
def dolar():
    datos = obtener_todos()
    for item in datos:
        if item.get("nombre") == "Bolsa":
            item["nombre"] = "MEP"
        if item.get("casa") == "bolsa":
            item["casa"] = "mep"
    return jsonify(datos)

@app.route("/asistente", methods=["POST"])
def asistente():
    body = request.get_json()
    mensaje = body.get("mensaje", "")
    historial = body.get("historial", [])
    nombre = body.get("nombre", "Usuario")

    if not mensaje:
        return jsonify({"error": "Mensaje vacío"}), 400

    respuesta = consultar_asistente(mensaje, historial, nombre)
    return jsonify({"respuesta": respuesta})

@app.route("/ipc")
def ipc():
    datos = obtener_ipc()
    return jsonify(datos)

@app.route("/icl")
def icl():
    datos = obtener_icl()
    return jsonify(datos)

@app.route("/ripte")
def ripte():
    datos = obtener_ripte()
    return jsonify(datos)

@app.route("/dolar/historial/<casa>")
def historial_cotizacion(casa):
    casa_db = "bolsa" if casa == "mep" else casa
    # obtener_historial_cotizacion no necesita user_id
    datos = obtener_historial_cotizacion(casa_db)
    if not datos:
        return jsonify({"error": "Sin historial"}), 404
    return jsonify(datos)

@app.route("/dolar/variacion/<casa>")
def obtener_variacion_dolar(casa):
    casa_db = "bolsa" if casa == "mep" else casa
    # obtener_cotizacion_anterior no necesita user_id
    datos = obtener_cotizacion_anterior(casa_db)

    if datos is None:
        return jsonify({"error": "Sin historial suficiente"}), 404

    variacion_venta = ((datos["actual"]["venta"] - datos["anterior"]["venta"])
                       / datos["anterior"]["venta"]) * 100

    return jsonify({
        "casa": casa,
        "venta_actual": datos["actual"]["venta"],
        "venta_anterior": datos["anterior"]["venta"],
        "compra_actual": datos["actual"]["compra"],
        "compra_anterior": datos["anterior"]["compra"],
        "variacion_porcentual": round(variacion_venta, 2),
        "fecha_actual": datos["actual"]["fecha"],
        "fecha_anterior": datos["anterior"]["fecha"]
    })

# --- Endpoints de Cálculo de Ajuste de Alquiler (Requieren user_id) ---
@app.route("/calcular-ajuste", methods=["POST"])
@token_required
def calcular_ajuste_endpoint(user_id): # Recibe user_id del decorador
    body = request.get_json()
    alquiler = float(body["alquiler"])
    fecha_inicio = body["fecha_inicio"]
    fecha_firma = body["fecha_firma"]
    periodo = int(body["periodo"])
    fecha_calculo = datetime.now().isoformat()
    indice = body.get("indice", "ipc")
    resultado = calcular_ajuste(alquiler, fecha_inicio, indice, fecha_firma, periodo)
    
    # guardar_ajuste ahora requiere user_id
    guardar_ajuste(user_id, alquiler, resultado["historial"][-1]["alquiler"], fecha_inicio, fecha_calculo, indice)
    return jsonify(resultado)

@app.route("/historial")
@token_required
def obtener_historial(user_id): # Recibe user_id
    # obtener_historial_alquiler ahora requiere user_id
    historial = obtener_historial_alquiler(user_id)
    return jsonify(historial)

@app.route("/historial/<id_str>", methods=["DELETE"]) # Cambiamos a <id_str> para manejar UUIDs como string
@token_required
def eliminar_calculo(user_id, id_str): # Recibe user_id y el ID como string
    # borrar_calculo ahora requiere user_id y el ID es string
    filas = borrar_calculo(user_id, id_str)
    if filas == 0:
        return jsonify({"error": f"No existe el calculo con id {id_str} para este usuario"}), 404
    return jsonify({"mensaje": f"Cálculo {id_str} eliminado"})

@app.route("/historial/completo", methods=["DELETE"]) # Cambiamos la ruta para evitar conflicto con /historial
@token_required
def eliminar_historial_completo_endpoint(user_id): # Recibe user_id
    # borrar_historial_completo ahora requiere user_id
    borrar_historial_completo(user_id)
    return jsonify({"mensaje": "Historial de cálculos eliminado"})

# --- Endpoints de guardar en card Categorías del Home ---
@app.route("/presupuestos-categorias", methods=["GET"])
@token_required
def obtener_presupuestos_categorias(user_id):
    from database import obtener_presupuestos_categorias
    return jsonify(obtener_presupuestos_categorias(user_id))

@app.route("/presupuestos-categorias", methods=["PUT"])
@token_required
def guardar_presupuesto_categoria(user_id):
    body = request.get_json()
    categoria = body.get("categoria")
    monto = float(body.get("monto"))
    from database import guardar_presupuesto_categoria
    guardar_presupuesto_categoria(user_id, categoria, monto)
    return jsonify({"mensaje": "ok"}), 200




# --- Endpoints de Presupuesto (Requieren user_id) ---
@app.route("/presupuesto")
@token_required
def obtener_presupuesto(user_id): # Recibe user_id
    filtro = request.args.get("filtro", "mensual")
    # obtener_movimientos ahora requiere user_id
    movimientos = obtener_movimientos(user_id, filtro)
    return jsonify(movimientos)

@app.route("/presupuesto", methods=["POST"])
@token_required
def agregar_presupuesto(user_id): # Recibe user_id
    body = request.get_json()
    tipo = body.get("tipo")
    categoria = body.get("categoria")
    descripcion = body.get("descripcion", "")
    monto = float(body.get("monto"))

    if not tipo or not categoria or not monto:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    # agregar_movimiento ahora requiere user_id
    resultado = agregar_movimiento(user_id, tipo, categoria, descripcion, monto)
    return jsonify(resultado), 201 # Retornamos el resultado de la inserción, incluyendo el ID

@app.route("/presupuesto/<id_str>", methods=["PUT"]) # Cambiamos a <id_str>
@token_required
def editar_presupuesto(user_id, id_str): # Recibe user_id y el ID como string
    body = request.get_json()
    tipo = body.get("tipo")
    categoria = body.get("categoria")
    descripcion = body.get("descripcion", "")
    monto = float(body.get("monto"))

    if not tipo or not categoria or not monto:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    # editar_movimiento ahora requiere user_id y el ID es string
    filas = editar_movimiento(user_id, id_str, tipo, categoria, descripcion, monto)
    if not filas.data: # Supabase devuelve data=[] si no hay filas afectadas
        return jsonify({"error": f"No existe el movimiento con id {id_str} para este usuario"}), 404
    return jsonify({"mensaje": f"Movimiento {id_str} actualizado"}), 200 # Devuelve 200 OK

@app.route("/presupuesto/<id_str>", methods=["DELETE"]) # Cambiamos a <id_str>
@token_required
def borrar_presupuesto(user_id, id_str): # Recibe user_id y el ID como string
    # borrar_movimiento ahora requiere user_id y el ID es string
    filas_afectadas = borrar_movimiento(user_id, id_str)
    if filas_afectadas == 0:
        return jsonify({"error": f"No existe el movimiento con id {id_str} para este usuario"}), 404
    return jsonify({"mensaje": f"Movimiento {id_str} eliminado"}), 200

@app.route("/presupuesto/reset", methods=["DELETE"])
@token_required
def reset_presupuesto_endpoint(user_id): # Recibe user_id
    # reset_presupuesto ahora requiere user_id
    reset_presupuesto(user_id)
    return jsonify({"mensaje": "Todos los movimientos fueron eliminados para este usuario"}), 200
# asset-link(verificacion entre app y railway)
@app.route("/.well-known/assetlinks.json")
def assetlinks():
    data = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.candlelabs.gestionpersonal",
                "sha256_cert_fingerprints": [
                    "39:1E:16:DA:C3:3E:04:1D:56:EC:03:71:57:C1:E0:29:98:01:11:26:A9:0D:91:19:57:75:38:85:8D:59:8F:AA"
                ]
            }
        }
    ]
    return app.response_class(
        response=json.dumps(data),
        mimetype="application/json"
    )

#respuesta de recuperacion de contraseña suapbase a la app
@app.route("/auth/reset-password")
def reset_password_redirect():
    token_hash = request.args.get("token_hash", "")
    type_ = request.args.get("type", "recovery")
    # Redirige a la app via deep link
    deep_link = f"com.candlelabs.gestionpersonal://reset-password?token_hash={token_hash}&type={type_}"
    return f'''
    <html>
    <head>
        <meta http-equiv="refresh" content="0;url={deep_link}" />
    </head>
    <body>
        <p>Redirigiendo a Plata Clara...</p>
        <a href="{deep_link}">Tocá acá si no abre automáticamente</a>
    </body>
    </html>
    '''

# --- Endpoints de Exportación (Requieren user_id) ---
@app.route("/presupuesto/exportar/excel")
@token_required
def exportar_excel(user_id): # Recibe user_id
    filtro = request.args.get("filtro", "mensual")
    # obtener_movimientos ahora requiere user_id
    movimientos = obtener_movimientos(user_id, filtro)

    wb = openpyxl.Workbook()

    # --- COLORES ---
    # Colores ya definidos en la función original, los mantenemos
    verde = "FF16A34A"
    rojo = "FFDC2626"
    verde_claro = "FFDCFCE7"
    rojo_claro = "FFFEE2E2"
    gris = "FFF3F4F6"
    blanco = "FFFFFFFF"
    header_font = Font(bold=True, color="FFFFFFFF", size=11)
    border = Border(
        left=Side(style='thin', color="FFE5E7EB"),
        right=Side(style='thin', color="FFE5E7EB"),
        top=Side(style='thin', color="FFE5E7EB"),
        bottom=Side(style='thin', color="FFE5E7EB")
    )

    # --- HOJA 1 — MOVIMIENTOS ---
    ws1 = wb.active
    ws1.title = "Movimientos"

    # Título
    ws1.merge_cells("A1:E1")
    titulo = ws1["A1"]
    titulo.value = f"Plata Clara — Movimientos ({filtro.capitalize()})"
    titulo.font = Font(bold=True, size=14, color="FF14532D")
    titulo.alignment = Alignment(horizontal="center")
    ws1.row_dimensions[1].height = 30

    # Fecha de exportación
    ws1.merge_cells("A2:E2")
    fecha_export = ws1["A2"]
    fecha_export.value = f"Exportado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    fecha_export.font = Font(size=9, color="FF6B7280")
    fecha_export.alignment = Alignment(horizontal="center")

    # Headers
    headers = ["Fecha", "Tipo", "Categoría", "Descripción", "Monto"]
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = PatternFill("solid", fgColor="FF14532D")
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    # Datos
    total_ingresos = 0
    total_gastos = 0
    for row_idx, mov in enumerate(movimientos, 5):
        es_ingreso = mov["tipo"] == "ingreso"
        color_fila = verde_claro if es_ingreso else rojo_claro

        fecha_cell = ws1.cell(row=row_idx, column=1, value=mov["fecha"][:10])
        tipo_cell = ws1.cell(row=row_idx, column=2, value="Ingreso" if es_ingreso else "Gasto")
        cat_cell = ws1.cell(row=row_idx, column=3, value=mov["categoria"])
        desc_cell = ws1.cell(row=row_idx, column=4, value=mov.get("descripcion", ""))
        monto_cell = ws1.cell(row=row_idx, column=5,
            value=mov["monto"] if es_ingreso else -mov["monto"])

        for cell in [fecha_cell, tipo_cell, cat_cell, desc_cell, monto_cell]:
            cell.fill = PatternFill("solid", fgColor=color_fila)
            cell.border = border
            cell.alignment = Alignment(horizontal="center")

        monto_cell.font = Font(
            bold=True,
            color=verde if es_ingreso else rojo
        )
        monto_cell.number_format = '#,##0.00'

        if es_ingreso:
            total_ingresos += mov["monto"]
        else:
            total_gastos += mov["monto"]

    # Totales
    fila_total = len(movimientos) + 5
    ws1.cell(row=fila_total, column=4, value="Total Ingresos:").font = Font(bold=True)
    ing_cell = ws1.cell(row=fila_total, column=5, value=total_ingresos)
    ing_cell.font = Font(bold=True, color=verde)
    ing_cell.number_format = '#,##0.00'

    ws1.cell(row=fila_total+1, column=4, value="Total Gastos:").font = Font(bold=True)
    gas_cell = ws1.cell(row=fila_total+1, column=5, value=-total_gastos)
    gas_cell.font = Font(bold=True, color=rojo)
    gas_cell.number_format = '#,##0.00'

    balance = total_ingresos - total_gastos
    ws1.cell(row=fila_total+2, column=4, value="Balance:").font = Font(bold=True, size=12)
    bal_cell = ws1.cell(row=fila_total+2, column=5, value=balance)
    bal_cell.font = Font(bold=True, size=12, color=verde if balance >= 0 else rojo)
    bal_cell.number_format = '#,##0.00'

    # Anchos de columna
    ws1.column_dimensions["A"].width = 14
    ws1.column_dimensions["B"].width = 12
    ws1.column_dimensions["C"].width = 20
    ws1.column_dimensions["D"].width = 25
    ws1.column_dimensions["E"].width = 18

    # --- HOJA 2 — RESUMEN POR CATEGORÍA ---
    ws2 = wb.create_sheet("Por Categoría")

    ws2.merge_cells("A1:C1")
    titulo2 = ws2["A1"]
    titulo2.value = "Resumen por Categoría"
    titulo2.font = Font(bold=True, size=14, color="FF14532D")
    titulo2.alignment = Alignment(horizontal="center")
    ws2.row_dimensions[1].height = 30

    for col, header in enumerate(["Categoría", "Total", "% del gasto"], 1):
        cell = ws2.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = PatternFill("solid", fgColor="FF14532D")
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    # Agrupar por categoría
    por_categoria = {}
    for mov in movimientos:
        if mov["tipo"] == "gasto":
            cat = mov["categoria"]
            por_categoria[cat] = por_categoria.get(cat, 0) + mov["monto"]

    por_categoria_ordenado = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)

    for row_idx, (cat, monto) in enumerate(por_categoria_ordenado, 4):
        porcentaje = (monto / total_gastos * 100) if total_gastos > 0 else 0
        color_fila = gris if row_idx % 2 == 0 else blanco

        cat_cell = ws2.cell(row=row_idx, column=1, value=cat)
        monto_cell = ws2.cell(row=row_idx, column=2, value=monto)
        pct_cell = ws2.cell(row=row_idx, column=3, value=f"{porcentaje:.1f}%")

        for cell in [cat_cell, monto_cell, pct_cell]:
            cell.fill = PatternFill("solid", fgColor=color_fila)
            cell.border = border
            cell.alignment = Alignment(horizontal="center")

        monto_cell.number_format = '#,##0.00'
        monto_cell.font = Font(color=rojo)

    ws2.column_dimensions["A"].width = 22
    ws2.column_dimensions["B"].width = 18
    ws2.column_dimensions["C"].width = 14

    # Guardar en memoria y devolver
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    nombre_archivo = f"PlataClara_{filtro}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=nombre_archivo
    )

@app.route("/presupuesto/exportar/pdf")
@token_required
def exportar_pdf(user_id): # Recibe user_id
    # fpdf y os ya importados arriba
    filtro = request.args.get("filtro", "mensual")
    # obtener_movimientos ahora requiere user_id
    movimientos = obtener_movimientos(user_id, filtro)

    # Ruta a las fuentes — relativa al archivo app.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fuente_regular = os.path.join(base_dir, "fonts", "DejaVuSans.ttf")
    fuente_bold = os.path.join(base_dir, "fonts", "DejaVuSans-Bold.ttf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cargamos la fuente con soporte Unicode completo
    pdf.add_font("DejaVu", style="", fname=fuente_regular)
    pdf.add_font("DejaVu", style="B", fname=fuente_bold)

    # ══════════════════════════════════════════
    # PÁGINA 1 — DETALLE DE MOVIMIENTOS
    # ══════════════════════════════════════════
    pdf.add_page()

    # — Encabezado —
    pdf.set_fill_color(*VERDE_OSCURO)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(*BLANCO)
    pdf.set_y(8)
    pdf.cell(0, 10, "Plata Clara", align="C", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, f"Movimientos {filtro.capitalize()} — {datetime.now().strftime('%d/%m/%Y')}", align="C", ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # — Totales rápidos —
    total_ingresos = sum(m["monto"] for m in movimientos if m["tipo"] == "ingreso")
    total_gastos = sum(m["monto"] for m in movimientos if m["tipo"] == "gasto")
    balance = total_ingresos - total_gastos

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_fill_color(*GRIS_CLARO)
    pdf.cell(63, 10, f"Ingresos: ${total_ingresos:,.0f}", border=0, fill=True, align="C")
    pdf.cell(63, 10, f"Gastos: ${total_gastos:,.0f}", border=0, fill=True, align="C")
    pdf.set_text_color(*color_balance)
    pdf.cell(63, 10, f"Balance: ${balance:,.0f}", border=0, fill=True, align="C", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # — Header de tabla —
    pdf.set_fill_color(*VERDE_OSCURO)
    pdf.set_text_color(*BLANCO)
    pdf.set_font("DejaVu", "B", 9)
    pdf.cell(30, 8, "Fecha", border=0, fill=True, align="C")
    pdf.cell(25, 8, "Tipo", border=0, fill=True, align="C")
    pdf.cell(45, 8, "Categoria", border=0, fill=True, align="C")
    pdf.cell(55, 8, "Descripcion", border=0, fill=True, align="C")
    pdf.cell(35, 8, "Monto", border=0, fill=True, align="C", ln=True)
    pdf.set_text_color(0, 0, 0)

    # — Filas de movimientos —
    pdf.set_font("DejaVu", "", 8)
    for i, mov in enumerate(movimientos):
        es_ingreso = mov["tipo"] == "ingreso"
        if es_ingreso:
            pdf.set_fill_color(220, 252, 231)
        else:
            pdf.set_fill_color(254, 226, 226)

        fecha = mov["fecha"][:10]
        tipo = "Ingreso" if es_ingreso else "Gasto"
        categoria = mov["categoria"][:20]
        descripcion = (mov.get("descripcion") or "")[:25]
        monto = f"${mov['monto']:,.0f}"

        pdf.cell(30, 7, fecha, border=0, fill=True, align="C")
        pdf.cell(25, 7, tipo, border=0, fill=True, align="C")
        pdf.cell(45, 7, categoria, border=0, fill=True, align="C")
        pdf.cell(55, 7, descripcion, border=0, fill=True, align="L")

        pdf.set_text_color(*(VERDE if es_ingreso else ROJO))
        pdf.cell(35, 7, monto, border=0, fill=True, align="C", ln=True)
        pdf.set_text_color(0, 0, 0)

    # ══════════════════════════════════════════
    # PÁGINA 2 — RESUMEN POR CATEGORÍA
    # ══════════════════════════════════════════
    pdf.add_page()

    # — Encabezado —
    pdf.set_fill_color(*VERDE_OSCURO)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(*BLANCO)
    pdf.set_y(8)
    pdf.cell(0, 10, "Plata Clara", align="C", ln=True)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 6, f"Resumen por Categoria — {filtro.capitalize()}", align="C", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # — Resumen general —
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_fill_color(*GRIS_CLARO)
    pdf.cell(63, 10, f"Ingresos: ${total_ingresos:,.0f}", border=0, fill=True, align="C")
    pdf.cell(63, 10, f"Gastos: ${total_gastos:,.0f}", border=0, fill=True, align="C")
    pdf.set_text_color(*color_balance)
    pdf.cell(63, 10, f"Balance: ${balance:,.0f}", border=0, fill=True, align="C", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # — Header tabla categorías —
    pdf.set_fill_color(*VERDE_OSCURO)
    pdf.set_text_color(*BLANCO)
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(90, 8, "Categoria", border=0, fill=True, align="C")
    pdf.cell(50, 8, "Total gastado", border=0, fill=True, align="C")
    pdf.cell(50, 8, "% del gasto", border=0, fill=True, align="C", ln=True)
    pdf.set_text_color(0, 0, 0)

    # — Agrupar gastos por categoría —
    por_categoria = {}
    for mov in movimientos:
        if mov["tipo"] == "gasto":
            cat = mov["categoria"]
            por_categoria[cat] = por_categoria.get(cat, 0) + mov["monto"]

    por_categoria_ordenado = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)

    pdf.set_font("DejaVu", "", 10)
    for i, (cat, monto) in enumerate(por_categoria_ordenado):
        porcentaje = (monto / total_gastos * 100) if total_gastos > 0 else 0
        fill_color = GRIS_CLARO if i % 2 == 0 else BLANCO
        pdf.set_fill_color(*fill_color)
        pdf.cell(90, 8, cat, border=0, fill=True, align="C")
        pdf.set_text_color(*ROJO)
        pdf.cell(50, 8, f"${monto:,.0f}", border=0, fill=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.cell(50, 8, f"{porcentaje:.1f}%", border=0, fill=True, align="C", ln=True)

    # — Pie de página —
    pdf.ln(10)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, f"Generado por Plata Clara — CandleLabs — {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C")

    # — Guardar en memoria y devolver —
    output = BytesIO()
    pdf.output(output)
    output.seek(0)

    nombre_archivo = f"PlataClara_{filtro}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nombre_archivo
    )

if __name__ == "__main__":
    # Las funciones de creacion_tabla ya no hacen nada, pero las dejamos por consistencia.
    # El app_context ya las llamó al inicio.
    app.run(debug=True)
