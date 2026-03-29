from functools import wraps
from flask import request, jsonify
from database import supabase

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token faltante"}), 401
        
        token = auth_header.split(" ")[1]
        
        try:
            user = supabase.auth.get_user(token)
            user_id = user.user.id
        except Exception:
            return jsonify({"error": "Token inválido o expirado"}), 401
        
        return f(user_id, *args, **kwargs)
    
    return decorated
