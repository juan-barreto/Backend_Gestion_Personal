import requests

def obtener_ripte():
    url = "https://apis.datos.gob.ar/series/api/series/?ids=158.1_REPTE_0_0_5&limit=24&start_date=2024-01-01&format=json"
    respuesta = requests.get(url)
    datos = respuesta.json()
    return datos["data"]