import streamlit as st
from supabase import create_client, Client
from datetime import date

# -----------------------------
# CONFIGURACIÓN SUPABASE
# -----------------------------
SUPABASE_URL = "https://ejsakzzbgwymptqjoigs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Control Financiero", layout="centered")

# -----------------------------
# AUTENTICACIÓN (SIMPLIFICADA)
# -----------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    st.title("Login")
    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        try:
            auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["user"] = auth_response.user
            st.rerun()
        except Exception as e:
            st.error(f"Error al iniciar sesión: {e}")
else:
    st.sidebar.success(f"Usuario: {st.session_state['user'].email}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["user"] = None
        st.rerun()

    user_id = st.session_state["user"].id

    # -----------------------------
    # AGREGAR TRANSACCIÓN
    # -----------------------------
    st.subheader("Agregar nueva transacción")
    with st.form("nueva_transaccion"):
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Credito"])
        
        if tipo == "Ingreso":
            categoria = st.selectbox("Categoría", ["Salario", "Comisión", "Ventas", "Otro"])
        elif tipo == "Gasto":
            categoria = st.selectbox("Categoría", ["Comida", "Transporte", "Servicios", "Entretenimiento", "Otro"])
        else:  # Crédito
            categoria = st.selectbox("Categoría", ["Tarjeta de crédito", "Préstamo personal", "Hipoteca", "Otro"])
        
        monto = st.number_input("Monto", min_value=0.01, step=0.01)
        fecha = st.date_input("Fecha", value=date.today())
        submitted = st.form_submit_button("Guardar")

        if submitted:
            data = {
                "tipo": tipo,
                "categoria": categoria,
                "monto": monto,
                "fecha": str(fecha),
                "user_id": user_id
            }
            try:
                response = supabase.table("transacciones").insert(data).execute()
                if response.data:
                    st.success("✅ Transacción guardada")
                    st.rerun()
                else:
                    st.error("⚠️ No se pudo guardar")
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

    # -----------------------------
    # LISTADO DE TRANSACCIONES
    # -----------------------------
    st.subheader("Tus transacciones")
    try:
        transacciones = supabase.table("transacciones").select("*").eq("user_id", user_id).order("fecha", desc=True).execute()
        if transacciones.data:
            for t in transacciones.data:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                col1.write(f"📌 {t['tipo']}")
                col2.write(f"🏷 {t['categoria']}")
                col3.write(f"💲 {t['monto']}")
                col4.write(f"📅 {t['fecha']}")
                if col5.button("🗑️", key=f"del_{t['id']}"):
                    try:
                        supabase.table("transacciones").delete().eq("id", t["id"]).eq("user_id", user_id).execute()
                        st.success("Transacción eliminada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")
        else:
            st.info("No tienes transacciones registradas.")
    except Exception as e:
        st.error(f"Error al cargar transacciones: {e}")

    # -----------------------------
    # SECCIÓN DE CRÉDITOS
    # -----------------------------
    st.subheader("Créditos activos")
    try:
        creditos = supabase.table("transacciones").select("*").eq("user_id", user_id).eq("tipo", "Credito").execute()
        if creditos.data:
            for c in creditos.data:
                st.write(f"💳 {c['categoria']} - Monto: {c['monto']} - Fecha: {c['fecha']}")
        else:
            st.info("No tienes créditos activos.")
    except Exception as e:
        st.error(f"Error al cargar créditos: {e}")
