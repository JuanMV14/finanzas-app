import streamlit as st
from supabase import create_client, Client
import pandas as pd

# -----------------------------
# CONFIGURACIÓN SUPABASE
# -----------------------------
SUPABASE_URL = "https://ejsakzzbgwymptqjoigs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finanzas Personales", page_icon="💰", layout="centered")

# -----------------------------
# SESIÓN DE USUARIO
# -----------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# -----------------------------
# LOGIN
# -----------------------------
def login(email, password):
    try:
        auth_resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state["user"] = {
            "id": auth_resp.user.id,
            "email": auth_resp.user.email
        }
        st.success("✅ Sesión iniciada correctamente")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error al iniciar sesión: {e}")

# -----------------------------
# LOGOUT
# -----------------------------
def logout():
    supabase.auth.sign_out()
    st.session_state["user"] = None
    st.success("✅ Sesión cerrada")
    st.rerun()

# -----------------------------
# REGISTRO
# -----------------------------
def register(email, password):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
        st.success("✅ Usuario registrado. Ahora puedes iniciar sesión.")
    except Exception as e:
        st.error(f"❌ Error al registrarse: {e}")

# -----------------------------
# APP PRINCIPAL
# -----------------------------
st.title("💰 Finanzas Personales")

if not st.session_state["user"]:
    st.subheader("Iniciar sesión")
    email = st.text_input("Email")
    password = st.text_input("Contraseña", type="password")
    if st.button("Login"):
        login(email, password)

    st.subheader("Registrarse")
    email_reg = st.text_input("Nuevo Email")
    password_reg = st.text_input("Nueva Contraseña", type="password")
    if st.button("Registrarse"):
        register(email_reg, password_reg)

else:
    st.write(f"👤 Sesión iniciada como: **{st.session_state['user']['email']}**")
    if st.button("Cerrar sesión"):
        logout()

    st.divider()

    # -----------------------------
    # AGREGAR TRANSACCIÓN
    # -----------------------------
    st.subheader("Agregar nueva transacción")
    with st.form("nueva_transaccion"):
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Credito"])
        categoria = st.text_input("Categoría")
        monto = st.number_input("Monto", min_value=0.01, step=0.01)
        fecha = st.date_input("Fecha")
        submitted = st.form_submit_button("Guardar")

        if submitted:
            user_id = st.session_state["user"]["id"]
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
                    st.error(f"⚠️ No se pudo guardar: {response}")
            except Exception as e:
                st.error(f"❌ Error al guardar: {e}")

    st.divider()

    # -----------------------------
    # LISTAR TRANSACCIONES
    # -----------------------------
    st.subheader("Tus transacciones")
    try:
        user_id = st.session_state["user"]["id"]
        response = supabase.table("transacciones").select("*").eq("user_id", user_id).execute()
        transacciones = response.data

        if transacciones:
            df = pd.DataFrame(transacciones)

            # Mostrar tabla con botón de eliminar
            for i, row in df.iterrows():
                col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
                col1.write(row["fecha"])
                col2.write(row["tipo"])
                col3.write(row["categoria"])
                col4.write(f"${row['monto']:,.2f}")
                col5.write(row["id"])
                if col6.button("🗑️", key=f"delete_{row['id']}"):
                    try:
                        supabase.table("transacciones").delete().eq("id", row["id"]).execute()
                        st.success("✅ Transacción eliminada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al eliminar: {e}")

            # Totales
            total_ingresos = df[df["tipo"] == "Ingreso"]["monto"].sum()
            total_gastos = df[df["tipo"] == "Gasto"]["monto"].sum()
            total_creditos = df[df["tipo"] == "Credito"]["monto"].sum()
            balance = total_ingresos - total_gastos - total_creditos

            st.metric("Ingresos", f"${total_ingresos:,.2f}")
            st.metric("Gastos", f"${total_gastos:,.2f}")
            st.metric("Créditos (deudas)", f"${total_creditos:,.2f}")
            st.metric("Balance final", f"${balance:,.2f}")
        else:
            st.info("No tienes transacciones registradas.")

    except Exception as e:
        st.error(f"❌ Error al leer transacciones: {e}")
