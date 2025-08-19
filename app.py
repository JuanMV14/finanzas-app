import streamlit as st
from supabase import create_client, Client
from datetime import date

# -------------------
# CONFIGURACIÓN SUPABASE
# -------------------
SUPABASE_URL = "https://ejsakzzbgwymptqjoigs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------
# SESIÓN DE USUARIO
# -------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

st.title("💰 Finanzas Personales")

# -------------------
# LOGIN
# -------------------
if not st.session_state["user"]:
    st.subheader("Iniciar sesión")
    email = st.text_input("Email")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            # Guardamos el objeto user completo
            st.session_state["user"] = auth_response.user
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error de inicio de sesión: {e}")

else:
    # Usuario autenticado
    user = st.session_state["user"]

    if isinstance(user, dict):
        user_email = user.get("email", "Usuario")
        user_id = user.get("id")
    else:
        user_email = getattr(user, "email", "Usuario")
        user_id = getattr(user, "id", None)

    st.sidebar.success(f"Usuario: {user_email}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["user"] = None
        st.rerun()

    # -------------------
    # AGREGAR TRANSACCIÓN
    # -------------------
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
            if user_id:
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
                        st.success("✅ Transacción guardada correctamente")
                        st.rerun()
                    else:
                        st.error(f"⚠️ No se pudo guardar: {response}")
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")
            else:
                st.error("⚠️ No se pudo determinar el usuario autenticado.")

    # -------------------
    # LISTAR TRANSACCIONES
    # -------------------
    st.subheader("📋 Mis transacciones")

    try:
        transacciones = supabase.table("transacciones") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("fecha", desc=True) \
            .execute()

        if transacciones.data:
            for t in transacciones.data:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                col1.write(f"**{t['tipo']}**")
                col2.write(t["categoria"])
                col3.write(f"${t['monto']:.2f}")
                col4.write(t["fecha"])
                if col5.button("🗑️", key=f"del_{t['id']}"):
                    try:
                        supabase.table("transacciones").delete().eq("id", t["id"]).execute()
                        st.success("✅ Transacción eliminada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al eliminar: {e}")
        else:
            st.info("No tienes transacciones registradas.")
    except Exception as e:
        st.error(f"⚠️ Error al cargar transacciones: {e}")

    # -------------------
    # CRÉDITOS
    # -------------------
    st.markdown("---")
    st.markdown("👨‍💻 App creada por **Tu Nombre** con Streamlit + Supabase 🚀")
