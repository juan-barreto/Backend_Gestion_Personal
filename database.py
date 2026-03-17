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
def creacion_tabla_alquiler():
    
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculo_alquiler (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               alquiler_inicial REAL,
               alquiler_final REAL,
               fecha_inicio TEXT,
               fecha_calculo TEXT,
               tipo_indice TEXT
               
               
               )
    """)
    conexion.commit()
    conexion.close()
def guardar_ajuste(alquiler_inicial,alquiler_final,fecha_inicio,fecha_calculo,indice):
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()

    cursor.execute("""
               INSERT INTO calculo_alquiler (alquiler_inicial, alquiler_final, fecha_inicio, fecha_calculo, tipo_indice)
               VALUES (?, ?, ?, ?, ?)
               """, (alquiler_inicial, alquiler_final, fecha_inicio, fecha_calculo, indice))

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

def obtener_cotizacion_anterior(fuente: str):
    """Devuelve las últimas DOS cotizaciones de una casa para calcular variación"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    
    # Trae las últimas 2 entradas de esa casa ordenadas por fecha
    # El ORDER BY DESC trae primero la más reciente
    cursor.execute("""
        SELECT venta, compra, fecha 
        FROM cotizaciones 
        WHERE fuente = ? 
        ORDER BY fecha DESC 
        LIMIT 2
    """, (fuente,))
    
    resultados = cursor.fetchall()
    conexion.close()
    
    # Si hay menos de 2 registros no podemos calcular variación
    if len(resultados) < 2:
        return None
    
    # resultados[0] es el actual, resultados[1] es el anterior
    return {
        "actual": {
            "venta": resultados[0][0],
            "compra": resultados[0][1],
            "fecha": resultados[0][2]
        },
        "anterior": {
            "venta": resultados[1][0],
            "compra": resultados[1][1],
            "fecha": resultados[1][2]
        }
    }

def mostrar_cotizacion():
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM cotizaciones")
    resultados = cursor.fetchall()

    for fila in resultados:
        print(fila)
    conexion.close()

def obtener_historial_alquiler():
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM calculo_alquiler")
    resultados = cursor.fetchall()
    historial = []
    for fila in resultados:
        new_fila = {
           "id": fila[0],
           "alquiler_inicial": fila[1],
           "alquiler_final": fila[2],
           "fecha_inicio": fila[3],
           "fecha_calculo": fila[4],
           "tipo_indice": fila[5]
       }
        historial.append(new_fila)
    conexion.close()
    return historial
#(id: int) anotacion que indica el tipo de valor esperado
def borrar_calculo(id: int):
    """Borra un registro específico del historial por su id"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM calculo_alquiler WHERE id = ?" , (id,))
    filas_encontradas = cursor.rowcount # cuántas filas borró
    conexion.commit()
    conexion.close()
    return filas_encontradas # devuelve 0 si el id no existía

def borrar_historial_completo():
    """Borra todos los registros del historial"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM calculo_alquiler")
    conexion.commit()
    conexion.close()

if __name__ == "__main__":
    creacion_tabla()
    creacion_tabla_alquiler()
    mostrar_cotizacion()
    obtener_historial_alquiler()



