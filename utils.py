import streamlit as st
from queries import supabase

def _extract_user_from_auth_response(auth_resp):
    try:
        user_obj = getattr(auth_resp, "user", None)
        if user_obj:
            uid = getattr(user_obj, "id", None)
            email = getattr(user_obj, "email", None) or getattr(user_obj, "user_metadata", {}).get("email")
            if uid:
                return {"id": str(uid), "email": email}
    except Exception:
        pass
    return None

def login(email, password):
    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = _extract_user_from_auth_response(resp)
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("No se pudo iniciar sesión.")
    except Exception as e:
        st.error(f"Error: {e}")

def signup(email, password):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        st.success("Cuenta creada. Revisa tu correo para confirmar.")
    except Exception as e:
        st.error(f"Error: {e}")

def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state["user"] = None
    st.rerun()
