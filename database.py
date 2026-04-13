import os
from datetime import datetime, timedelta # Agregado timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# --- Configuración de Supabase ---
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # service_role key

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funciones de Creación de Tablas (Ahora gestionadas en Supabase directamente) ---
# Estas funciones ya no crean tablas, solo sirven como placeholders.
# La creación y gestión del esquema se hace en el SQL Editor de Supabase.
def creacion_tabla():
    """Placeholder para la creación de la tabla de cotizaciones en Supabase."""
    pass

def creacion_tabla_alquiler():
    """Placeholder para la creación de la tabla de cálculo de alquiler en Supabase."""
    pass

def creacion_tabla_presupuesto():
    """Placeholder para la creación de la tabla de movimientos de presupuesto en Supabase."""
    pass

# --- Funcionalidades Migradas a Supabase ---

def agregar_movimiento(user_id: str, tipo: str, categoria: str, descripcion: str, monto: float):
    """
    Inserta un movimiento en PostgreSQL (tabla presupuesto) asociado al user_id.
    """
    data = {
        "user_id": user_id,
        "tipo": tipo,
        "categoria": categoria,
        "descripcion": descripcion,
        "monto": monto,
        "fecha": datetime.now().isoformat() # Usamos la fecha actual en ISO format
    }
    response = supabase.table("presupuesto").insert(data).execute()
    # Verificamos si hay error en la respuesta de Supabase
    if response.data and not response.data[0]:
        print(f"Error al agregar movimiento: {response.data}")
    return response.data

def editar_movimiento(user_id: str, id: str, tipo: str, categoria: str, descripcion: str, monto: float):
    """
    Edita un movimiento existente por su id, asegurando que pertenezca al user_id.
    """
    data = {
        "tipo": tipo,
        "categoria": categoria,
        "descripcion": descripcion,
        "monto": monto
    }
    # Filtramos por id Y user_id para seguridad de multi-tenancy
    response = supabase.table("presupuesto").update(data).eq("id", id).eq("user_id", user_id).execute()
    return response.data

def obtener_movimientos(user_id: str, filtro: str = "mensual") -> list:
    """
    Devuelve los movimientos del user_id según el filtro temporal desde Supabase.
    """
    query = supabase.table("presupuesto").select("*").eq("user_id", user_id)

    now = datetime.now()
    if filtro == "semanal":
        # Filtra por la última semana
        seven_days_ago = now - timedelta(days=7)
        query = query.gte("fecha", seven_days_ago.isoformat())
    elif filtro == "anual":
        # Filtra por el año actual
        start_of_year = datetime(now.year, 1, 1)
        query = query.gte("fecha", start_of_year.isoformat())
    else:  # mensual por defecto
        # Filtra por el mes actual
        start_of_month = datetime(now.year, now.month, 1)
        query = query.gte("fecha", start_of_month.isoformat())

    response = query.order("fecha", desc=True).execute()
    return response.data

def borrar_movimiento(user_id: str, id: str) -> int:
    """
    Borra un movimiento por su id, asegurando que pertenezca al user_id.
    Devuelve la cantidad de filas borradas.
    """
    # Filtramos por id Y user_id para seguridad
    response = supabase.table("presupuesto").delete().eq("id", id).eq("user_id", user_id).execute()
    return len(response.data) if response.data else 0

def reset_presupuesto(user_id: str):
    """
    Borra todos los movimientos de presupuesto para un user_id específico.
    """
    response = supabase.table("presupuesto").delete().eq("user_id", user_id).execute()
    return response.data


def guardar_ajuste(user_id: str, alquiler_inicial: float, alquiler_final: float, fecha_inicio: str, fecha_calculo: str, indice: str):
    """
    Guarda un ajuste de cálculo de alquiler asociado al user_id.
    """
    data = {
        "user_id": user_id,
        "alquiler_inicial": alquiler_inicial,
        "alquiler_final": alquiler_final,
        "fecha_inicio": fecha_inicio,
        "fecha_calculo": fecha_calculo,
        "tipo_indice": indice
    }
    response = supabase.table("calculo_alquiler").insert(data).execute()
    return response.data

def obtener_historial_alquiler(user_id: str) -> list:
    """
    Devuelve el historial de cálculos de alquiler para un user_id específico.
    """
    response = supabase.table("calculo_alquiler").select("*").eq("user_id", user_id).order("fecha_calculo", desc=True).execute()
    return response.data

def borrar_calculo(user_id: str, id: str) -> int:
    """
    Borra un registro específico del historial de alquiler por su id y user_id.
    Devuelve la cantidad de filas borradas.
    """
    response = supabase.table("calculo_alquiler").delete().eq("id", id).eq("user_id", user_id).execute()
    return len(response.data) if response.data else 0

def borrar_historial_completo(user_id: str):
    """
    Borra todos los registros del historial de alquiler para un user_id específico.
    """
    response = supabase.table("calculo_alquiler").delete().eq("user_id", user_id).execute()
    return response.data


# --- Funciones de Cotizaciones (Datos Globales - SIN user_id) ---

def guardar_cotizacion(fuente: str, venta: float, compra: float):
    """
    Guarda una cotización global. No requiere user_id.
    """
    data = {
        "fuente": fuente,
        "venta": venta,
        "compra": compra,
        "fecha": datetime.now().isoformat()
    }
    response = supabase.table("cotizaciones").insert(data).execute()
    return response.data

def obtener_cotizacion_anterior(fuente: str):
    """
    Devuelve las últimas DOS cotizaciones de una fuente para calcular variación. No requiere user_id.
    """
    # Ordenamos por fecha descendente y limitamos a 2.
    response = supabase.table("cotizaciones").select("venta, compra, fecha").eq("fuente", fuente).order("fecha", desc=True).limit(2).execute()
    resultados = response.data

    if len(resultados) < 2:
        return None

    return {
        "actual": resultados[0],
        "anterior": resultados[1]
    }

def mostrar_cotizacion():
    """
    Muestra todas las cotizaciones globales.
    """
    response = supabase.table("cotizaciones").select("*").execute()
    for fila in response.data:
        print(fila)
    return response.data # Devolvemos los datos para un uso más programático

def obtener_historial_cotizacion(fuente: str, limite: int = 30):
    """
    Devuelve los últimos N registros de una fuente para graficar. No requiere user_id.
    """
    response = supabase.table("cotizaciones").select("venta, compra, fecha").eq("fuente", fuente).order("fecha", desc=True).limit(limite).execute()
    resultados = response.data
    resultados.reverse() # Invertimos para que el gráfico vaya de más viejo a más nuevo
    return resultados

def obtener_presupuestos_categorias(user_id):
    res = supabase.table("presupuestos_categorias").select("*").eq("user_id", user_id).execute()
    return {row["categoria"]: row["monto"] for row in res.data}

def guardar_presupuesto_categoria(user_id, categoria, monto):
    supabase.table("presupuestos_categorias").upsert({
        "user_id": user_id,
        "categoria": categoria,
        "monto": monto
    }, on_conflict="user_id,categoria").execute()

# --- Bloque de ejecución principal (solo para pruebas locales, adaptado) ---
if __name__ == "__main__":
    print("Iniciando pruebas de Supabase (las funciones de creación de tablas no hacen nada aquí).")
    # Para probar, deberías interactuar con tus endpoints de Flask o usar el cliente directamente
    # de forma interactiva, asegurándote de tener un usuario y un token válidos.
    print("Recuerda que la creación de tablas se realiza directamente en Supabase SQL Editor.")
    print("También es crucial habilitar y configurar Row Level Security (RLS) en Supabase para tus tablas de usuario.")
