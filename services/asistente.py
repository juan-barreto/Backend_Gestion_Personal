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
    Construye el contexto completo del usuario para inyectar en el system prompt.
    Usa todos los datos disponibles en la DB.
    """
    contexto = f"\n\nCONTEXTO DEL USUARIO '{nombre}':\n"

    try:
        conexion = sqlite3.connect("dolar.db")
        cursor = conexion.cursor()

        # — HISTORIAL DE ALQUILERES —
        cursor.execute("""
            SELECT alquiler_inicial, alquiler_final, fecha_inicio, 
                   fecha_calculo, tipo_indice
            FROM calculo_alquiler 
            ORDER BY fecha_calculo DESC 
            LIMIT 5
        """)
        alquileres = cursor.fetchall()

        if alquileres:
            contexto += "\nALQUILERES CALCULADOS (últimos 5):\n"
            for a in alquileres:
                # Calculamos variación porcentual
                variacion = ((a[1] - a[0]) / a[0]) * 100
                contexto += (
                    f"  · Inicial: ${a[0]:,.0f} → Ajustado: ${a[1]:,.0f} "
                    f"(+{variacion:.1f}%) | Índice: {a[4].upper()} | "
                    f"Desde: {a[2]} | Calculado: {a[3][:10]}\n"
                )

            # Próximo ajuste estimado basado en el último
            ultimo = alquileres[0]
            try:
                from datetime import datetime, timedelta
                fecha_inicio = datetime.strptime(ultimo[2], "%Y-%m-%d")
                proximo = fecha_inicio + timedelta(days=90)  # asume trimestral
                hoy = datetime.now()
                dias = (proximo - hoy).days
                if dias > 0:
                    contexto += f"  · Próximo ajuste estimado: en {dias} días ({proximo.strftime('%Y-%m-%d')})\n"
                else:
                    contexto += f"  · Próximo ajuste: vencido hace {abs(dias)} días\n"
            except:
                pass
        else:
            contexto += "\nALQUILERES: Sin cálculos registrados todavía.\n"

        # — PRESUPUESTO DEL MES —
        try:
            cursor.execute("""
                SELECT tipo, categoria, monto
                FROM presupuesto
                WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
            """)
            movimientos = cursor.fetchall()

            if movimientos:
                # Calculamos totales
                # Equivalente en Python:
                # total_ingresos = sum(m[2] for m in movimientos if m[0] == 'ingreso')
                total_ingresos = sum(m[2] for m in movimientos if m[0] == "ingreso")
                total_gastos = sum(m[2] for m in movimientos if m[0] == "gasto")
                balance = total_ingresos - total_gastos
                cantidad = len(movimientos)

                # Agrupamos gastos por categoría para el top 3
                # Equivalente en Python:
                # {cat: sum(m[2] for m in movimientos if m[1] == cat)}
                por_categoria = {}
                for m in movimientos:
                    if m[0] == "gasto":
                        cat = m[1]
                        por_categoria[cat] = por_categoria.get(cat, 0) + m[2]

                # Ordenamos de mayor a menor y tomamos los 3 primeros
                top3 = sorted(por_categoria.items(), key=lambda x: x[1], reverse=True)[:3]

                contexto += f"\nPRESUPUESTO DEL MES ACTUAL:\n"
                contexto += f"  · Ingresos: ${total_ingresos:,.0f}\n"
                contexto += f"  · Gastos: ${total_gastos:,.0f}\n"
                contexto += f"  · Balance: {'+'if balance >= 0 else ''}${balance:,.0f}\n"
                contexto += f"  · Movimientos registrados: {cantidad}\n"

                if top3:
                    contexto += f"  · Top categorías de gasto:\n"
                    for cat, monto in top3:
                        porcentaje = (monto / total_gastos * 100) if total_gastos > 0 else 0
                        contexto += f"      - {cat}: ${monto:,.0f} ({porcentaje:.1f}%)\n"

                # Estado del balance para que Clara pueda dar consejos contextualizados
                if balance > 0:
                    contexto += f"  · Estado: superávit — el usuario está ahorrando\n"
                elif balance == 0:
                    contexto += f"  · Estado: equilibrio — ingresos igualan gastos\n"
                else:
                    contexto += f"  · Estado: déficit — el usuario gasta más de lo que gana\n"
            else:
                contexto += "\nPRESUPUESTO: Sin movimientos registrados este mes.\n"

        except Exception as e:
            contexto += f"\nPRESUPUESTO: Error cargando datos ({str(e)})\n"
        
        # — COTIZACIONES DEL DÓLAR —
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
            contexto += "\nCOTIZACIONES DEL DÓLAR (actuales):\n"
            for d in dolares:
                contexto += f"  · {d[0].capitalize()}: compra ${d[2]:,.0f} / venta ${d[1]:,.0f}\n"
        else:
            contexto += "\nCOTIZACIONES: Sin datos todavía.\n"

        # — IPC —
        try:
            import requests
            url = "https://apis.datos.gob.ar/series/api/series/?ids=103.1_I2N_2016_M_15&limit=3&format=json"
            respuesta = requests.get(url, timeout=5)
            datos = respuesta.json()["data"]
            if len(datos) >= 2:
                ultimo_ipc = datos[-1]
                penultimo_ipc = datos[-2]
                variacion_ipc = ((ultimo_ipc[1] - penultimo_ipc[1]) / penultimo_ipc[1]) * 100
                contexto += f"\nIPC (inflación mensual):\n"
                contexto += f"  · Último disponible: {variacion_ipc:.1f}% ({ultimo_ipc[0][:7]})\n"
        except:
            contexto += "\nIPC: No disponible en este momento.\n"

        conexion.close()

    except Exception as e:
        contexto += f"\nError cargando contexto: {str(e)}\n"

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