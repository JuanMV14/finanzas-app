import streamlit as st
from supabase import create_client
import pandas as pd

# Configuración de Supabase
SUPABASE_URL = "https://TU-PROJECT-URL.supabase.co"
SUPABASE_KEY = "TU-API-KEY"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finanzas Personales", page_icon="💰", layout="centered")

# --- LOGIN ---
if "user" not in st.session_state:
    st.session_state.user = None

st.title("💰 Finanzas Personales")

if st.session_state.user is None:
    st.subheader("Iniciar sesión")

    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = response.user
            st.success(f"Bienvenido {st.session_state.user.email}")
            st.rerun()
        except Exception as e:
            st.error("Error al iniciar sesión: " + str(e))

else:
    # Usuario autenticado
    user_id = st.session_state.user.id
    st.sidebar.success(f"Conectado como: {st.session_state.user.email}")

    if st.sidebar.button("Cerrar sesión"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # --- INGRESAR TRANSACCIÓN ---
    st.subheader("Registrar transacción")

    tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
    categoria = st.text_input("Categoría")
    monto = st.number_input("Monto", min_value=0.0, step=100.0)
    descripcion = st.text_area("Descripción")

    if st.button("Guardar transacción"):
        data = {
            "user_id": user_id,
            "tipo": tipo,
            "categoria": categoria,
            "monto": monto,
            "descripcion": descripcion,
        }
        supabase.table("transacciones").insert(data).execute()
        st.success("✅ Transacción registrada")

    # --- MOSTRAR TRANSACCIONES ---
    st.subheader("Historial de transacciones")

    resp = supabase.table("transacciones").select("*").eq("user_id", user_id).execute()
    transacciones = resp.data

    if transacciones:
        df = pd.DataFrame(transacciones)
        st.dataframe(df[["tipo", "categoria", "monto", "descripcion"]])
    else:
        st.info("No tienes transacciones registradas todavía.")
