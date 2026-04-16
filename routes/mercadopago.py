import os
import requests
from flask import Blueprint, request, jsonify, redirect
from auth import token_required
from database import guardar_token_mp, obtener_token_mp

mp_bp = Blueprint("mercadopago", __name__)

# ── Credenciales desde variables de entorno ────────────────
MP_CLIENT_ID     = os.getenv("MP_CLIENT_ID")
MP_CLIENT_SECRET = os.getenv("MP_CLIENT_SECRET")
MP_REDIRECT_URI  = os.getenv("MP_REDIRECT_URI")


# ── 1. Iniciar OAuth — la app abre esta URL en el navegador ─
# GET /mp/auth?user_id=<supabase_user_id>
@mp_bp.route("/mp/auth")
def mp_auth():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Falta user_id"}), 400

    url = (
        f"https://auth.mercadopago.com/authorization"
        f"?client_id={MP_CLIENT_ID}"
        f"&response_type=code"
        f"&platform_id=mp"
        f"&redirect_uri={MP_REDIRECT_URI}"
        f"&state={user_id}"
    )
    return redirect(url)


# ── 2. Callback — MP redirige acá con el code de autorización ─
# MP llama GET /mp/callback?code=xxx&state=<user_id>
# Intercambiamos el code por access_token y lo guardamos en Supabase
@mp_bp.route("/mp/callback")
def mp_callback():
    code    = request.args.get("code")
    user_id = request.args.get("state")

    if not code or not user_id:
        return jsonify({"error": "Faltan parámetros"}), 400

    respuesta = requests.post(
        "https://api.mercadopago.com/oauth/token",
        json={
            "client_id":     MP_CLIENT_ID,
            "client_secret": MP_CLIENT_SECRET,
            "code":          code,
            "grant_type":    "authorization_code",
            "redirect_uri":  MP_REDIRECT_URI
        }
    )

    if respuesta.status_code != 200:
        return jsonify({"error": "Error al obtener token", "detalle": respuesta.json()}), 400

    datos         = respuesta.json()
    access_token  = datos.get("access_token")
    refresh_token = datos.get("refresh_token")
    mp_user_id    = datos.get("user_id")

    guardar_token_mp(user_id, access_token, refresh_token, mp_user_id)

    # Redirigimos a la app via deep link para cerrar el navegador
    deep_link = "com.candlelabs.gestionpersonal://mp-callback?status=ok"
    return redirect(deep_link)


# ── 3. Movimientos — trae y limpia los pagos del usuario ───
# Llama a /v1/payments/search de MP y devuelve una lista simplificada
# Los campos de nombre se resuelven en este orden:
#   1. description  → nombre más legible ("Edenor", "Compra en DIA", "SUBE")
#   2. statement_descriptor → fallback para pagos con tarjeta ("MERPAGO*SUPERDIA")
#   3. branch → categoría genérica de MP ("QR", "Bill Payments - Agenda")
#   4. "Pago" → último recurso
@mp_bp.route("/mp/movimientos")
@token_required
def mp_movimientos(user_id):
    token_data = obtener_token_mp(user_id)
    if not token_data:
        return jsonify({"error": "No hay cuenta de MP conectada"}), 404

    access_token = token_data["access_token"]
    mp_user_id   = int(token_data["mp_user_id"])

    offset = int(request.args.get("offset", 0))
    limit  = int(request.args.get("limit", 20))

    respuesta = requests.get(
        "https://api.mercadopago.com/v1/payments/search",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "sort":     "date_created",
            "criteria": "desc",
            "limit":    limit,
            "offset":   offset
        }
    )

    if respuesta.status_code == 401:
        return jsonify({"error": "Token expirado", "codigo": "token_expired"}), 401

    if respuesta.status_code != 200:
        return jsonify({"error": "Error al obtener movimientos", "detalle": respuesta.text}), 400

    resultados = respuesta.json().get("results", [])

    movimientos_limpios = []
    for p in resultados:
        # Filtrar transferencias internas de MP y rendimientos
        operation_type = p.get("operation_type", "")
        if operation_type in ("money_transfer", "investment"):
            continue

        # Si payer_id es el usuario → él pagó → gasto. Si no → le pagaron → ingreso
        es_gasto = (p.get("payer_id") == mp_user_id)

        # ── DEBUG — ver qué trae additional_info ──
        print(
            p.get("id"), "|",
            p.get("description"), "|",
            p.get("additional_info")
        )

        # Resolver nombre del pago
        poi    = p.get("point_of_interaction") or {}
        biz    = poi.get("business_info") or {}
        nombre = (
            p.get("description")
            or p.get("statement_descriptor")
            or biz.get("branch")
            or "Pago"
        )

        # Traducir los pocos casos donde description es un ID numérico o código técnico
        traducciones = {
            "238244854":    "SUBE - Carga",
            "Bank Transfer": "Transferencia bancaria",
        }
        nombre = traducciones.get(nombre, nombre)

        movimientos_limpios.append({
            "id":       p.get("id"),
            "nombre":   nombre,
            "monto":    p.get("transaction_amount", 0),
            "es_gasto": es_gasto,
            "fecha":    (p.get("date_created") or "")[:10],
            "status":   p.get("status"),
        })

    return jsonify(movimientos_limpios)


# ── 4. Estado — verifica si el usuario ya tiene MP conectado ─
# Solo consulta Supabase, no llama a la API de MP
@mp_bp.route("/mp/estado")
@token_required
def mp_estado(user_id):
    token_data = obtener_token_mp(user_id)
    return jsonify({"conectado": token_data is not None})


# ── 5. Desconectar — borra el token de Supabase ────────────
@mp_bp.route("/mp/desconectar", methods=["DELETE"])
@token_required
def mp_desconectar(user_id):
    from database import borrar_token_mp
    borrar_token_mp(user_id)
    return jsonify({"mensaje": "Cuenta de Mercado Pago desconectada"}), 200