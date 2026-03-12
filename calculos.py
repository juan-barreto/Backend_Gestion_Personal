from ipc import obtener_ipc
from icl import obtener_icl
from datetime import datetime
from dateutil.relativedelta import relativedelta


#Funcion que busca el valor ipc o icl

def buscar_valor(datos, fecha_str, tipo):
    mes = fecha_str[:7] #Largo 7 ,es decir solo "YYYY-MM"
    if tipo == "ipc":
        for item in datos:
            if item[0][:7] == mes:
                return item[1]
    elif tipo == "icl":
        for item in datos:
            if item["fecha"][:7] == mes:
                return item["valor"]
    return None

def calcular_ajuste(alquler_incial, fecha_inicio_str, tipo_indice):
    if tipo_indice == "ipc":
        datos = obtener_ipc()
    else:
        datos = obtener_icl()

    fecha_actual = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
    alquiler_actual = alquler_incial
    historial = [{"periodo": fecha_inicio_str, "alquiler": round(alquiler_actual,2)}]
    while True:
        fecha_siguiente = fecha_actual + relativedelta(months=3)

        valor_inicio = buscar_valor(datos, fecha_actual.strftime("%Y-%m-%d"), tipo_indice)
        valor_fin = buscar_valor(datos, fecha_siguiente.strftime("%Y-%m-%d"), tipo_indice)

        if valor_inicio is None or valor_fin is None:
            proximo_ajuste = {
                "fecha": fecha_siguiente.strftime("%Y-%m-%d"),
                "alquiler_proyectado":None,
                "nota": "Sin datos suficientes para proyectar"
            }
            break
        alquiler_actual = alquiler_actual * (valor_fin/valor_inicio)
        historial.append({"periodo": fecha_siguiente.strftime("%Y-%m-%d"), "alquiler": round(alquiler_actual,2)})
        fecha_actual = fecha_siguiente

    return {"historial": historial, "proximo_ajuste": proximo_ajuste }