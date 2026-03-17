import requests

def obtener_icl():
    # limit=2000 trae ~5 años de datos diarios sin filtro de fecha
    url = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/40?limit=2000"
    respuesta = requests.get(url, verify=False)
    datos = respuesta.json()
    return datos["results"][0]["detalle"]

if __name__ == "__main__":
    print(obtener_icl())