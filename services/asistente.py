from groq import Groq
import os

# El cliente toma la API key de las variables de entorno
# En Railway la configurás en Settings → Variables
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# System prompt — le dice al modelo quién es y cómo debe responder
SYSTEM_PROMPT = """Sos un asistente financiero especializado en la economía argentina.
Tu nombre es Clara, sos parte de la app Plata Clara de CandleLabs.

Podés ayudar con:
- Explicar índices económicos: IPC, ICL, RIPTE, dólar blue, MEP, CCL
- Interpretar contratos de alquiler y ajustes según la ley argentina
- Responder sobre el contexto económico argentino actual
- Explicar cómo afectan las noticias económicas al bolsillo del argentino
- Dar consejos de finanzas personales adaptados a la realidad argentina

Respondé siempre en español rioplatense, de forma clara y sin tecnicismos innecesarios.
Sé conciso — máximo 3 párrafos por respuesta.
Si no sabés algo con certeza, decilo claramente."""

def consultar_asistente(mensaje: str, historial: list = []) -> str:
    """
    Envía un mensaje a Groq y devuelve la respuesta.
    historial: lista de mensajes anteriores para mantener contexto
    """
    # Construimos los mensajes — system + historial + mensaje nuevo
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Agregamos el historial de la conversación
    for msg in historial:
        mensajes.append(msg)
    
    # Agregamos el mensaje nuevo del usuario
    mensajes.append({"role": "user", "content": mensaje})
    
    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=mensajes,
        max_tokens=500,
        temperature=0.7
    )
    
    return respuesta.choices[0].message.content