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
    resultados = datos.get("results", [])

    # mp_user_id del token — con esto sabemos si el usuario pagó o cobró
    mp_user_id = int(token_data["mp_user_id"])

    movimientos_limpios = []
    for p in resultados:
        
    # Filtrar rendimientos y pagos intermedios del banco
        operation_type = p.get("operation_type", "")
        if operation_type in ("money_transfer", "investment"):
            continue
        
         # ── DEBUG — loguear campos candidatos para el nombre ──
        print(
            p.get("id"), "|",
            p.get("statement_descriptor"), "|",
            p.get("description"), "|",
            (p.get("point_of_interaction") or {}).get("business_info")
        )
        payer_id = p.get("payer_id")
        es_gasto = (payer_id == mp_user_id)

        # Descripción: primero business_info, luego statement_descriptor, luego description
        poi      = p.get("point_of_interaction") or {}
        biz      = poi.get("business_info") or {}
        nombre   = (
        biz.get("branch")
        or p.get("statement_descriptor")
        or p.get("description")
        or "Pago"
        )

        # Traducción de nombres técnicos de MP al español
        traducciones = {
            "Transport - Public transport recharge": "SUBE - Carga",
            "Intra MP": "Transferencia MP",
        }
        nombre = traducciones.get(nombre, nombre)

        movimientos_limpios.append({
            "id":        p.get("id"),
            "nombre":    nombre,
            "monto":     p.get("transaction_amount", 0),
            "es_gasto":  es_gasto,
            "fecha":     (p.get("date_created") or "")[:10],
            "status":    p.get("status"),
        })

    return jsonify(movimientos_limpios)


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