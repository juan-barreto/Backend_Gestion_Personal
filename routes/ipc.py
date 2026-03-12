import requests


def obtener_ipc():
    url = "https://apis.datos.gob.ar/series/api/series/?ids=103.1_I2N_2016_M_15&limit=36&start_date=2024-01-01&format=json"
    respuesta = requests.get(url)
    datos = respuesta.json()
    return datos["data"]

if __name__ == "__main__":
    print(obtener_ipc())