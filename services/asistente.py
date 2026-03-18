from groq import Groq
import os
import sqlite3

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# System prompt BASE — lo que Clara siempre sabe
SYSTEM_PROMPT_BASE = """Sos Clara, asistente financiera de la app Plata Clara de CandleLabs.
Especializada en economía argentina: inflación, dólar, alquileres, IPC, ICL, RIPTE.

REGLAS ESTRICTAS:
- Respondé en máximo 3 oraciones. Si te piden una lista, podés extenderte.
- Usá español rioplatense, simple y directo. Sin tecnicismos innecesarios.
- NUNCA inventes datos ni busques en internet. Solo usá lo que tenés en este contexto.
- Si no sabés algo con certeza, decilo claramente.
- Si el usuario tiene datos en su perfil, usalos para personalizar la respuesta.

Podés ayudar con:
- Índices económicos: IPC, ICL, RIPTE, dólar blue, MEP, CCL
- Contratos de alquiler y ajustes según ley argentina (DNU 70/2023)
- Contexto económico argentino actual
- Finanzas personales adaptadas a la realidad argentina"""


def obtener_contexto_usuario(nombre: str) -> str:
    """
    Busca en la DB los datos reales del usuario y construye
    el bloque de contexto para inyectar en el system prompt.
    
    Equivalente en Python puro:
    contexto = f"El usuario se llama {nombre} y su último alquiler fue..."
    """
    contexto = f"\n\nCONTEXTO DEL USUARIO '{nombre}':\n"

    try:
        conexion = sqlite3.connect("dolar.db")
        cursor = conexion.cursor()

        # Último cálculo de alquiler
        cursor.execute("""
            SELECT alquiler_inicial, alquiler_final, fecha_inicio, 
                   fecha_calculo, tipo_indice
            FROM calculo_alquiler 
            ORDER BY fecha_calculo DESC 
            LIMIT 1
        """)
        alquiler = cursor.fetchone()

        if alquiler:
            contexto += (
                f"- Último alquiler calculado: inicial ${alquiler[0]:,.0f}, "
                f"ajustado ${alquiler[1]:,.0f}\n"
                f"- Índice usado: {alquiler[4].upper()}\n"
                f"- Fecha de inicio del período: {alquiler[2]}\n"
                f"- Calculado el: {alquiler[3][:10]}\n"
            )
        else:
            contexto += "- No tiene cálculos de alquiler registrados todavía.\n"


     # Últimas cotizaciones del dólar
    # Últimas cotizaciones del dólar — una query por casa para mayor confiabilidad
        casas = ['blue', 'oficial', 'mep']
        dolares = []
        for casa in casas:
            cursor.execute("""
                SELECT fuente, venta, compra, fecha
                FROM cotizaciones
                WHERE fuente = ?
                ORDER BY fecha DESC
                LIMIT 1
            """, (casa,))
            resultado = cursor.fetchone()
            if resultado:
                dolares.append(resultado)

        if dolares:
            contexto += "- Cotizaciones actuales del dólar:\n"
            for d in dolares:
                contexto += f"  · {d[0].capitalize()}: compra ${d[2]:,.0f} / venta ${d[1]:,.0f}\n"
        else:
            contexto += "- Sin cotizaciones del dólar en la base de datos todavía.\n"

        conexion.close()

    except Exception as e:
        # Si falla la DB, Clara sigue funcionando sin contexto
        contexto += f"- No se pudo cargar el contexto del usuario ({str(e)}).\n"

    return contexto



def construir_system_prompt(nombre: str) -> str:
    """
    Une el prompt base con el contexto dinámico del usuario.
    Equivalente en Python: f"{base}\n\n{contexto}"
    """
    contexto = obtener_contexto_usuario(nombre)
    return SYSTEM_PROMPT_BASE + contexto


def consultar_asistente(mensaje: str, historial: list = [], nombre: str = "Usuario") -> str:
    """
    Envía un mensaje a Groq con el contexto real del usuario inyectado.
    historial: últimos N mensajes para mantener contexto de conversación.
    nombre: nombre del usuario para personalizar el system prompt.
    """
    # Construimos el system prompt dinámico con los datos reales
    system_prompt = construir_system_prompt(nombre)

    mensajes = [{"role": "system", "content": system_prompt}]

    # Solo mandamos los últimos 10 mensajes para no superar el límite de tokens
    # Equivalente en Python: historial[-10:]
    for msg in historial[-10:]:
        mensajes.append(msg)

    mensajes.append({"role": "user", "content": mensaje})

    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=mensajes,
        max_tokens=500,
        temperature=0.7
    )

    return respuesta.choices[0].message.content