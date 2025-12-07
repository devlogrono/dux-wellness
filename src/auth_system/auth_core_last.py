# src/auth_system/auth_core.py

import datetime
import uuid
import bcrypt
import jwt
import streamlit as st

from src.auth_system import auth_config
from src.components.cookie_manager.cookie_manager import CookieManager

cookie = CookieManager()

def _auth_default_state():
    return {
        "is_logged_in": False,
        "username": "",
        "rol": "",
        "nombre": "",
        "token": "",
        "session_id": "",
    }


def ensure_state():
    if "auth" not in st.session_state:
        st.session_state["auth"] = _auth_default_state()


def init_app_state():
    ensure_state()


# ============================
# JWT
# ============================

def create_jwt(username, rol, session_id=None):
    if session_id is None:
        session_id = uuid.uuid4().hex

    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(seconds=auth_config.JWT_EXP_SECONDS)

    payload = {
        "user": username,
        "rol": rol,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    return jwt.encode(payload, auth_config.JWT_SECRET, algorithm=auth_config.JWT_ALGORITHM)


def decode_jwt(token):
    try:
        payload = jwt.decode(token, auth_config.JWT_SECRET, algorithms=[auth_config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        st.warning("Sesión expirada. Vuelve a iniciar sesión.")
        return None
    except Exception:
        return None


# ============================
# Manejo de sesión
# ============================

def set_auth_session(user, token, payload):
    st.session_state["auth"].update({
        "is_logged_in": True,
        "username": payload["user"],
        "rol": payload["rol"],
        "token": token,
        "session_id": payload["sid"],
        "nombre": f"{user.get('name','')} {user.get('lastname','')}".strip()
    })

    # Guardar cookie real del navegador
    cookie.set(auth_config.COOKIE_NAME, token, days=auth_config.COOKIE_EXP_DAYS)


def get_current_user():
    ensure_state()

    # 1: si hay token en memoria, validarlo
    token = st.session_state["auth"].get("token")
    if token:
        payload = decode_jwt(token)
        if payload:
            return payload
        else:
            logout()
            return None

    # 2: leer token desde cookie real del navegador
    raw = cookie.get(auth_config.COOKIE_NAME)
    if raw:
        payload = decode_jwt(raw)
        if payload:
            st.session_state["auth"]["token"] = raw
            st.session_state["auth"]["username"] = payload["user"]
            st.session_state["auth"]["rol"] = payload["rol"]
            st.session_state["auth"]["session_id"] = payload["sid"]
            return payload

    return None


def validate_login():
    return get_current_user() is not None


def logout():
    """
    Cierra sesión REAL:
    - Elimina cookie del navegador
    - Limpia session_state
    """
    cookie.delete(auth_config.COOKIE_NAME)
    st.session_state["auth"] = _auth_default_state()
    st.rerun()


# ============================
# Login (desde auth_ui)
# ============================

def validate_access(password, user):
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        st.error("Credenciales incorrectas")
        return

    permisos = [p.strip() for p in user.get("permissions", "").split(",")]
    if auth_config.APP_NAME not in permisos:
        st.error("No tienes permiso para usar esta app")
        return

    token = create_jwt(user["email"], user["role_name"])
    payload = decode_jwt(token)

    set_auth_session(user, token, payload)

    st.success("Inicio de sesión exitoso")
    st.rerun()
