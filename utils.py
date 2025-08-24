# ============================
# utils.py - Manejo de usuarios
# ============================

import streamlit as st

def login(supabase, email, password):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res and getattr(res, "user", None):
            st.session_state["user"] = {
                "id": res.user.id,
                "email": res.user.email
            }
            st.success("Inicio de sesión exitoso ✅")
            st.rerun()
        else:
            st.error("Correo o contraseña incorrectos ❌")
    except Exception as e:
        st.error(f"Error en login: {e}")

def signup(supabase, email, password):
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        if res and getattr(res, "user", None):
            st.success("Cuenta creada ✅. Ahora inicia sesión.")
        else:
            st.error("No se pudo registrar el usuario ❌")
    except Exception as e:
        st.error(f"Error en registro: {e}")

def logout(supabase):
    try:
        supabase.auth.sign_out()
        st.session_state["user"] = None
        st.success("Sesión cerrada ✅")
        st.rerun()
    except Exception as e:
        st.error(f"Error al cerrar sesión: {e}")
