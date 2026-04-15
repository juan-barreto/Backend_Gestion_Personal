import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# --- Configuración de Supabase ---
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # service_role key

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funciones de Creación de Tablas (Placeholders) ---
def creacion_tabla():
    pass

def creacion_tabla_alquiler():
    pass

def creacion_tabla_presupuesto():
    pass

# --- Movimientos de Presupuesto ---

def agregar_movimiento(user_id: str, tipo: str, categoria: str, descripcion: str, monto: float):
    data = {
        "user_id": user_id,
        "tipo": tipo,
        "categoria": categoria,
        "descripcion": descripcion,
        "monto": monto,
        "fecha": datetime.now().isoformat()
    }
    response = supabase.table("presupuesto").insert(data).execute()
    if response.data and not response.data[0]:
        print(f"Error al agregar movimiento: {response.data}")
    return response.data

def editar_movimiento(user_id: str, id: str, tipo: str, categoria: str, descripcion: str, monto: float):
    data = {
        "tipo": tipo,
        "categoria": categoria,
        "descripcion": descripcion,
        "monto": monto
    }
    response = supabase.table("presupuesto").update(data).eq("id", id).eq("user_id", user_id).execute()
    return response

def obtener_movimientos(user_id: str, filtro: str = "mensual") -> list:
    query = supabase.table("presupuesto").select("*").eq("user_id", user_id)

    now = datetime.now()
    if filtro == "semanal":
        seven_days_ago = now - timedelta(days=7)
        query = query.gte("fecha", seven_days_ago.isoformat())
    elif filtro == "anual":
        start_of_year = datetime(now.year, 1, 1)
        query = query.gte("fecha", start_of_year.isoformat())
    elif filtro == "mensual_anterior":
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        primer_dia_mes_actual = datetime(now_utc.year, now_utc.month, 1, tzinfo=timezone.utc)
        ultimo_mes = primer_dia_mes_actual - timedelta(days=1)
        inicio_mes_anterior = datetime(ultimo_mes.year, ultimo_mes.month, 1, tzinfo=timezone.utc)
        query = query.gte("fecha", inicio_mes_anterior.isoformat())
        query = query.lt("fecha", primer_dia_mes_actual.isoformat())
    else:  # mensual por defecto
        start_of_month = datetime(now.year, now.month, 1)
        query = query.gte("fecha", start_of_month.isoformat())

    response = query.order("fecha", desc=True).execute()
    return response.data

def borrar_movimiento(user_id: str, id: str) -> int:
    response = supabase.table("presupuesto").delete().eq("id", id).eq("user_id", user_id).execute()
    return len(response.data) if response.data else 0

def reset_presupuesto(user_id: str):
    response = supabase.table("presupuesto").delete().eq("user_id", user_id).execute()
    return response.data

# --- Alquiler ---

def guardar_ajuste(user_id: str, alquiler_inicial: float, alquiler_final: float, fecha_inicio: str, fecha_calculo: str, indice: str):
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
    response = supabase.table("calculo_alquiler").select("*").eq("user_id", user_id).order("fecha_calculo", desc=True).execute()
    return response.data

def borrar_calculo(user_id: str, id: str) -> int:
    response = supabase.table("calculo_alquiler").delete().eq("id", id).eq("user_id", user_id).execute()
    return len(response.data) if response.data else 0

def borrar_historial_completo(user_id: str):
    response = supabase.table("calculo_alquiler").delete().eq("user_id", user_id).execute()
    return response.data

# --- Cotizaciones (datos globales, sin user_id) ---

def guardar_cotizacion(fuente: str, venta: float, compra: float):
    data = {
        "fuente": fuente,
        "venta": venta,
        "compra": compra,
        "fecha": datetime.now().isoformat()
    }
    response = supabase.table("cotizaciones").insert(data).execute()
    return response.data

def obtener_cotizacion_anterior(fuente: str):
    response = supabase.table("cotizaciones").select("venta, compra, fecha").eq("fuente", fuente).order("fecha", desc=True).limit(2).execute()
    resultados = response.data
    if len(resultados) < 2:
        return None
    return {"actual": resultados[0], "anterior": resultados[1]}

def mostrar_cotizacion():
    response = supabase.table("cotizaciones").select("*").execute()
    for fila in response.data:
        print(fila)
    return response.data

def obtener_historial_cotizacion(fuente: str, limite: int = 30):
    response = supabase.table("cotizaciones").select("venta, compra, fecha").eq("fuente", fuente).order("fecha", desc=True).limit(limite).execute()
    resultados = response.data
    resultados.reverse()
    return resultados

# --- Presupuestos por categoría ---

def obtener_presupuestos_categorias(user_id):
    res = supabase.table("presupuestos_categorias").select("*").eq("user_id", user_id).execute()
    return {row["categoria"]: row["monto"] for row in res.data}

def guardar_presupuesto_categoria(user_id, categoria, monto):
    supabase.table("presupuestos_categorias").upsert({
        "user_id": user_id,
        "categoria": categoria,
        "monto": monto
    }, on_conflict="user_id,categoria").execute()

# ── Mercado Pago — tokens OAuth por usuario ────────────────

def guardar_token_mp(user_id: str, access_token: str, refresh_token: str, mp_user_id: int):
    """
    Guarda o actualiza el token de MP del usuario.
    Usa upsert para que si ya existe lo actualice.
    """
    data = {
        "user_id":      user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "mp_user_id":   mp_user_id,
        "updated_at":   datetime.now().isoformat()
    }
    supabase.table("mercadopago_tokens").upsert(
        data, on_conflict="user_id"
    ).execute()

def obtener_token_mp(user_id: str):
    """
    Devuelve el token de MP del usuario, o None si no tiene cuenta conectada.
    """
    response = supabase.table("mercadopago_tokens").select("*").eq("user_id", user_id).limit(1).execute()
    if response.data:
        return response.data[0]
    return None

def borrar_token_mp(user_id: str):
    """
    Elimina el token de MP del usuario — desconecta la cuenta.
    """
    supabase.table("mercadopago_tokens").delete().eq("user_id", user_id).execute()

# --- Main ---
if __name__ == "__main__":
    print("database.py — funciones de Supabase listas.")