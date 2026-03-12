import sqlite3
from datetime import datetime


def creacion_tabla():
    
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS cotizaciones (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               fuente TEXT,
               venta REAL,
               compra REAL,
               fecha TEXT
               
               
               )
    """)
    conexion.commit()
    conexion.close()

def guardar_cotizacion(fuente,venta,compra):
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    fecha = datetime.now().isoformat()

    cursor.execute("""
               INSERT INTO cotizaciones (fuente, venta, compra, fecha)
               VALUES (?, ?, ?, ?)
               """, (fuente, venta, compra, fecha))

    conexion.commit()
    conexion.close()

def mostrar_cotizacion():
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM cotizaciones")
    resultados = cursor.fetchall()

    for fila in resultados:
        print(fila)
    conexion.close()


if __name__ == "__main__":
    creacion_tabla()
    mostrar_cotizacion()