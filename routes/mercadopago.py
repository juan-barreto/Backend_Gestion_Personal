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

# ── 1. Iniciar OAuth — la app redirige al usuario a MP ─────
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


# ── 2. Callback — MP redirige acá con el code ──────────────
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

    datos = respuesta.json()
    access_token  = datos.get("access_token")
    refresh_token = datos.get("refresh_token")
    mp_user_id    = datos.get("user_id")

    guardar_token_mp(user_id, access_token, refresh_token, mp_user_id)

    deep_link = f"com.candlelabs.gestionpersonal://mp-callback?status=ok"
    return redirect(deep_link)


# ── 3. Movimientos — trae los movimientos del usuario ──────
@mp_bp.route("/mp/movimientos")
@token_required
def mp_movimientos(user_id):
    token_data = obtener_token_mp(user_id)
    if not token_data:
        return jsonify({"error": "No hay cuenta de MP conectada"}), 404

    access_token = token_data["access_token"]
    mp_user_id   = token_data["mp_user_id"]

    offset = int(request.args.get("offset", 0))
    limit  = int(request.args.get("limit", 20))

    respuesta = requests.get(
        "https://api.mercadopago.com/v1/payments/search",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "sort":    "date_created",
            "criteria": "desc",
            "limit":   limit,
            "offset":  offset
        }
    )

    if respuesta.status_code == 401:
        return jsonify({"error": "Token expirado", "codigo": "token_expired"}), 401

    if respuesta.status_code != 200:
        # ── DEBUG — sacar después de resolver el 400 ──────
        print("=== ERROR MP ===")
        print("STATUS:", respuesta.status_code)
        print("BODY:", respuesta.text)
        print("================")
        return jsonify({"error": "Error al obtener movimientos", "detalle": respuesta.text}), 400

    # MP devuelve {"results": [...], "paging": {...}}
    # devolvemos solo la lista de pagos
    datos = respuesta.json()
# Logueamos el primer pago para ver la estructura real
    if datos.get("results"):
        print("=== PRIMER PAGO ===")
        print(datos["results"][0])
        print("===================")
        return jsonify(datos.get("results", []))


# ── 4. Estado — verifica si el usuario ya tiene MP conectado ──
@mp_bp.route("/mp/estado")
@token_required
def mp_estado(user_id):
    token_data = obtener_token_mp(user_id)
    return jsonify({"conectado": token_data is not None})


# ── 5. Desconectar MP ──────────────────────────────────────
@mp_bp.route("/mp/desconectar", methods=["DELETE"])
@token_required
def mp_desconectar(user_id):
    from database import borrar_token_mp
    borrar_token_mp(user_id)
    return jsonify({"mensaje": "Cuenta de Mercado Pago desconectada"}), 200