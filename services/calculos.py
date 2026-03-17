from routes.ipc import obtener_ipc
from routes.icl import obtener_icl
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

# Constantes de fechas límite según DNUs
FECHA_CORTE_1 = datetime(2023, 10, 17)
FECHA_CORTE_2 = datetime(2023, 12, 29)

#Función que determina índice y periodo según contrato
def determinar_contrato(fecha_firma_str, indice_elegido, periodo_elegido):
    fecha_firma = datetime.strptime(fecha_firma_str, "%Y-%m-%d")
    
    if fecha_firma < FECHA_CORTE_1:
        # Pre 17/10/2023 — ICL y anual obligatorio por ley
        indice_final = "icl"
        periodo_meses = 12
    elif fecha_firma < FECHA_CORTE_2:
        # Transición Oct-Dic 2023 — ICL y semestral
        indice_final = "icl"
        periodo_meses = 6
    else:
        # Post DNU — el usuario elige libremente
        indice_final = indice_elegido
        periodo_meses = periodo_elegido

    return indice_final, periodo_meses


def calcular_ajuste(alquiler_inicial, fecha_inicio_str, tipo_indice, fecha_firma, periodo):
     # Determina índice y período según la ley que aplica
    indice_final, periodo_meses = determinar_contrato(fecha_firma, tipo_indice, periodo)

    if indice_final == "ipc":
        datos = obtener_ipc()
    else:
        datos = obtener_icl()

    fecha_actual = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
    alquiler_actual = alquiler_inicial
    historial = [{"periodo": fecha_inicio_str, "alquiler": round(alquiler_actual,2)}]
    while True:
        fecha_siguiente = fecha_actual + relativedelta(months=periodo_meses)

        valor_inicio = buscar_valor(datos, fecha_actual.strftime("%Y-%m-%d"), indice_final)
        valor_fin = buscar_valor(datos, fecha_siguiente.strftime("%Y-%m-%d"), indice_final)

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