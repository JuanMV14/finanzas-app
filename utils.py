import streamlit as st
from supabase import Client

def extract_user_from_auth_response(auth_resp):
    try:
        user_obj = getattr(auth_resp, "user", None)
        if user_obj:
            uid = getattr(user_obj, "id", None)
            email = getattr(user_obj, "email", None) or getattr(
                user_obj, "user_metadata", {}
            ).get("email")
            if uid:
                return {"id": str(uid), "email": email}
    except Exception:
        pass
    return None

def login(supabase: Client, email, password):
    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = extract_user_from_auth_response(resp)
        if user:
            st.session_state["user"] = user
            st.success("Sesión iniciada ✅")
            st.rerun()
        else:
            st.error("No se pudo extraer el usuario desde la respuesta de Supabase.")
    except Exception as e:
        st.error(f"Error al iniciar sesión: {e}")

def signup(supabase: Client, email, password):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        st.success("Cuenta creada. Revisa tu email para confirmar (si aplica).")
    except Exception as e:
        st.error(f"Error al registrar: {e}")

def logout(supabase: Client):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state["user"] = None
    st.success("Sesión cerrada")
    st.rerun()
