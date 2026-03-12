import requests


#Llama por única vez a la API

def obtener_todos():
    respuesta = requests.get("https://dolarapi.com/v1/dolares")
    return respuesta.json()

#Me devuelve el valor de venta del dolar blue
def obtener_dolar_blue(datos):
    for dolar in datos:
        if dolar["casa"] == "blue":
            return dolar["venta"], dolar["compra"]

#Me devuelve el valor de venta del dolar cripto
def obtener_dolar_cripto(datos):
    for dolar in datos:
        if dolar["casa"] == "cripto":
            return dolar["venta"] , dolar["compra"]

#Me devuelve el valor de venta del dolar tarjeta
def obtener_dolar_tarjeta(datos):
    for dolar in datos:
        if dolar["casa"] == "tarjeta":
            return dolar["venta"], dolar["compra"]
        
#Me devuelve el valor de venta del dolar Oficial
def obtener_dolar_oficial(datos):
    for dolar in datos:
        if dolar["casa"] == "oficial":
            return dolar["venta"], dolar["compra"]



if __name__ == "__main__":
   datos = obtener_todos()
   blue = obtener_dolar_blue(datos)
   oficial = obtener_dolar_oficial(datos)
   cripto = obtener_dolar_cripto(datos)
   tarjeta = obtener_dolar_tarjeta(datos)
   lista = [blue,oficial,cripto,tarjeta]
   for n in lista:
       print(n)