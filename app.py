from flask import Flask, jsonify, request
from database import creacion_tabla, creacion_tabla_alquiler,guardar_ajuste
from routes.dolar import obtener_todos
from routes.ipc import obtener_ipc
from routes.icl import obtener_icl
from routes.ripte import obtener_ripte
from services.calculos import calcular_ajuste
from datetime import datetime

app = Flask(__name__)


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


@app.route("/calcular-ajuste", methods = ["POST"])
def calcular_ajuste_endpoint():
    body = request.get_json()
    alquiler = float(body["alquiler"])
    fecha_inicio = body["fecha_inicio"]
    fecha_calculo = datetime.now().isoformat()
    indice =  body.get("indice", "ipc")#al tener dos valors, funciona como un if, si el primer key no aparece ,toma el valor del segundo por defecto sin buscar key
    resultado = calcular_ajuste(alquiler, fecha_inicio, indice)
    guardar_ajuste(alquiler,resultado["historial"][-1]["alquiler"],fecha_inicio,fecha_calculo,indice)
    return jsonify(resultado)

if __name__ == "__main__":
    creacion_tabla_alquiler()
    creacion_tabla()
    app.run(debug=True)

