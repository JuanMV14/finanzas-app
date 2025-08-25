from supabase import create_client
import os
from dotenv import load_dotenv
import streamlit as st

# -------------------------
# CONFIG
# -------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# AUTENTICACIÓN
# -------------------------
def login(email, password):
    try:
        auth = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if auth.user:
            st.session_state["user"] = {"id": auth.user.id, "email": auth.user.email}
            st.success("Inicio de sesión exitoso ✅")
            st.rerun()
        else:
            st.error("Correo o contraseña incorrectos ❌")
    except Exception as e:
        st.error(f"Error en login: {e}")

def signup(email, password):
    try:
        auth = supabase.auth.sign_up({"email": email, "password": password})
        if auth.user:
            st.success("Usuario registrado correctamente ✅")
        else:
            st.error("No se pudo registrar el usuario ❌")
    except Exception as e:
        st.error(f"Error en registro: {e}")

def logout():
    try:
        supabase.auth.sign_out()
        st.session_state["user"] = None
        st.success("Sesión cerrada correctamente ✅")
        st.rerun()
    except Exception as e:
        st.error(f"Error al cerrar sesión: {e}")
