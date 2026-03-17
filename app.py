from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from database import creacion_tabla, creacion_tabla_alquiler,guardar_ajuste,obtener_historial_alquiler,borrar_calculo, borrar_historial_completo
from routes.dolar import obtener_todos
from routes.ipc import obtener_ipc
from routes.icl import obtener_icl
from routes.ripte import obtener_ripte
from services.calculos import calcular_ajuste
from database import guardar_cotizacion, obtener_cotizacion_anterior
from datetime import datetime
import requests as req_interno

app = Flask(__name__)

# Paso 1 — contexto: crea las tablas al arrancar

with app.app_context():
    creacion_tabla()
    creacion_tabla_alquiler()


# Paso 2 — funciones que va a ejecutar el scheduler

def actualizar_cotizaciones():
    """Actualiza y guarda las cotizaciones en la DB cada 30 minutos"""
    try:
        datos = obtener_todos()
        for dolar in datos:
            guardar_cotizacion(dolar["casa"],dolar["venta"],dolar["compra"])
        print("Cotizaciones actualizadas")
    except Exception as e:
        print(f"Error actualizando cotizaciones: {e}")

def ping_propio():
    """Mantiene Railway despierto cada 14 minutos"""
    try:
        req_interno.get("https://web-production-f82cf.up.railway.app/")
        print("Ping enviado - servidor despierto")
    except Exception as e:
        print(f"Error en ping: {e}")

# Paso 3 — crear y arrancar el scheduler

scheduler = BackgroundScheduler()
scheduler.add_job(actualizar_cotizaciones, 'interval', minutes=30)
scheduler.add_job(ping_propio, 'interval', minutes= 14)
scheduler.start()

# Paso 4 — los endpoints 

@app.route("/")
def inicio():
    return jsonify({"mensaje": "API funcionando"})


@app.route("/dolar")
def dolar():
    datos = obtener_todos()
    return jsonify(datos)


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

@app.route("/dolar/variacion/<casa>")
def obtener_variacion_dolar(casa):
    """Devuelve el valor actual vs anterior para calcular la flecha"""
    datos = obtener_cotizacion_anterior(casa)
    
    if datos is None:
        return jsonify({"error": "Sin historial suficiente"}), 404
    
    # Calculamos la variación porcentual
    # ((actual - anterior) / anterior) * 100
    variacion_venta = ((datos["actual"]["venta"] - datos["anterior"]["venta"]) 
                       / datos["anterior"]["venta"]) * 100
    
    return jsonify({
        "casa": casa,
        "venta_actual": datos["actual"]["venta"],
        "venta_anterior": datos["anterior"]["venta"],
        "variacion_porcentual": round(variacion_venta, 2),
        "fecha_actual": datos["actual"]["fecha"],
        "fecha_anterior": datos["anterior"]["fecha"]
    })

@app.route("/calcular-ajuste", methods=["POST"])
def calcular_ajuste_endpoint():
    body = request.get_json()
    alquiler = float(body["alquiler"])
    fecha_inicio = body["fecha_inicio"]
    fecha_firma = body["fecha_firma"]        # ← nuevo
    periodo = int(body["periodo"])           # ← nuevo, llega como número
    fecha_calculo = datetime.now().isoformat()
    indice = body.get("indice", "ipc")
    resultado = calcular_ajuste(alquiler, fecha_inicio, indice, fecha_firma, periodo)
    guardar_ajuste(alquiler, resultado["historial"][-1]["alquiler"], fecha_inicio, fecha_calculo, indice)
    return jsonify(resultado)

@app.route("/historial")
def obtener_historial():
    historial = obtener_historial_alquiler()
    return jsonify(historial)
#<int:id> toma el id de la URL y lo convierte en entero, no es una indicacion simplemente
@app.route("/historial/<int:id>", methods=["DELETE"])
def eliminar_calculo(id):
    filas = borrar_calculo(id)
    if filas == 0:
            return jsonify({"error": f"No existe el calculo con id {id}"}), 404
    return jsonify({"mensaje": f"Cálculo {id} eliminado"})

@app.route("/historial", methods=["DELETE"])
def eliminar_historial():
    borrar_historial_completo()
    return jsonify({"mensaje": "Historial eliminado"})


if __name__ == "__main__":
    creacion_tabla_alquiler()
    creacion_tabla()
    app.run(debug=True)

