import requests

def obtener_icl():
    url = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/40?limit=30"
    respuesta = requests.get(url)
    datos = respuesta.json()
    return datos["results"][0]["detalle"]

if __name__ == "__main__":
    print(obtener_icl())