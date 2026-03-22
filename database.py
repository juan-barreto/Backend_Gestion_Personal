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

def creacion_tabla_presupuesto():
    """Crea la tabla de movimientos de presupuesto si no existe"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS presupuesto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,         -- 'ingreso' o 'gasto'
            categoria TEXT NOT NULL,    -- 'Sueldo', 'Alquiler', etc
            descripcion TEXT,           -- detalle opcional del usuario
            monto REAL NOT NULL,        -- siempre positivo, el tipo define si suma o resta
            fecha TEXT NOT NULL         -- formato ISO: '2026-03-18T22:00:00'
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
def reset_presupuesto():
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM presupuesto")
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

def obtener_historial_cotizacion(fuente: str, limite: int = 30):
    """Devuelve los últimos N registros de una casa para graficar"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    
    cursor.execute("""
        SELECT venta, compra, fecha 
        FROM cotizaciones 
        WHERE fuente = ? 
        ORDER BY fecha DESC 
        LIMIT ?
    """, (fuente, limite))
    
    resultados = cursor.fetchall()
    conexion.close()
    
    # Invertimos para que el gráfico vaya de más viejo a más nuevo
    resultados.reverse()
    
    return [
        {
            "venta": fila[0],
            "compra": fila[1],
            "fecha": fila[2]
        }
        for fila in resultados
    ]
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
#----------------------------------------------------------------------------------------------------------------
#Funcionalidades CRUD para tabla presupuesto:
def agregar_movimiento(tipo: str, categoria: str, descripcion: str, monto: float):
    """Agrega un ingreso o gasto al presupuesto"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    fecha = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO presupuesto (tipo, categoria, descripcion, monto, fecha)
        VALUES (?, ?, ?, ?, ?)
    """, (tipo, categoria, descripcion, monto, fecha))

    conexion.commit()
    conexion.close()

def editar_movimiento(id: int, tipo: str, categoria: str, descripcion: str, monto: float):
    """Edita un movimiento existente por su id"""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE presupuesto
        SET tipo = ?, categoria = ?, descripcion = ?, monto = ?
        WHERE id = ?
    """, (tipo, categoria, descripcion, monto, id))

    filas = cursor.rowcount  # 0 si el id no existía
    conexion.commit()
    conexion.close()
    return filas

def obtener_movimientos(filtro: str = "mensual") -> list:
    """
    Devuelve los movimientos según el filtro temporal.
    filtro: 'semanal', 'mensual' o 'anual'
    
    Equivalente en Python:
    [m for m in movimientos if m['fecha'] >= fecha_inicio]
    """
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()

    # Definimos el filtro de fecha según la opción elegida
    if filtro == "semanal":
        condicion = "fecha >= datetime('now', '-7 days')"
    elif filtro == "anual":
        condicion = "strftime('%Y', fecha) = strftime('%Y', 'now')"
    else:  # mensual por defecto
        condicion = "strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')"

    cursor.execute(f"""
        SELECT id, tipo, categoria, descripcion, monto, fecha
        FROM presupuesto
        WHERE {condicion}
        ORDER BY fecha DESC
    """)

    resultados = cursor.fetchall()
    conexion.close()

    return [
        {
            "id": fila[0],
            "tipo": fila[1],
            "categoria": fila[2],
            "descripcion": fila[3],
            "monto": fila[4],
            "fecha": fila[5]
        }
        for fila in resultados
    ]

def borrar_movimiento(id: int) -> int:
    """Borra un movimiento por su id. Devuelve 0 si no existía."""
    conexion = sqlite3.connect("dolar.db")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM presupuesto WHERE id = ?", (id,))
    filas = cursor.rowcount
    conexion.commit()
    conexion.close()
    return filas

if __name__ == "__main__":
    creacion_tabla()
    creacion_tabla_alquiler()
    mostrar_cotizacion()
    obtener_historial_alquiler()



