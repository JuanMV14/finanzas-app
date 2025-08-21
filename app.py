import streamlit as st

try:
except Exception as e:
    st.error(f"Error al iniciar la app: {e}")

from supabase import create_client, Client
import pandas as pd
from datetime import date
import plotly.graph_objs as go

# -------------------
# CONFIGURACIÓN SUPABASE
# -------------------
SUPABASE_URL = "https://ejsakzzbgwymptqjoigs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="💰 Finanzas Personales", layout="wide")

# -------------------
# SESIÓN
# -------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# -------------------
# HELPERS AUTH
# -------------------
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
            st.success("Sesión iniciada ✅")
            st.rerun()
        else:
            st.error("No se pudo extraer el usuario desde la respuesta de Supabase.")
    except Exception as e:
        st.error(f"Error al iniciar sesión: {e}")

def signup(email, password):
    try:
        resp = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Cuenta creada. Revisa tu email para confirmar (si aplica).")
    except Exception as e:
        st.error(f"Error al registrar: {e}")

def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state["user"] = None
    st.success("Sesión cerrada")
    st.rerun()

# -------------------
# FUNCIONES DE DB
# -------------------
def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    payload = {"user_id": str(user_id), "tipo": tipo, "categoria": categoria, "monto": float(monto), "fecha": str(fecha)}
    return supabase.table("transacciones").insert(payload).execute()

def insertar_credito(user_id, nombre, monto, tasa, plazo_meses, cuotas_pagadas):
    cuota_mensual = monto / plazo_meses if plazo_meses > 0 else monto
    payload = {
        "user_id": str(user_id),
        "nombre": nombre,
        "monto": float(monto),
        "tasa_interes": float(tasa),
        "plazo_meses": int(plazo_meses),
        "cuotas_pagadas": int(cuotas_pagadas),
        "cuota_mensual": cuota_mensual
    }
    return supabase.table("credito").insert(payload).execute()

def borrar_transaccion(user_id, trans_id):
    return supabase.table("transacciones").delete().eq("id", trans_id).eq("user_id", str(user_id)).execute()

# -------------------
# UI: LOGIN / SIGNUP
# -------------------
st.sidebar.title("🔐 Usuario")
if not st.session_state["user"]:
    st.sidebar.subheader("Iniciar sesión")
    in_email = st.sidebar.text_input("Email", key="login_email")
    in_password = st.sidebar.text_input("Contraseña", type="password", key="login_pass")
    if st.sidebar.button("Ingresar"):
        login(in_email, in_password)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Registrarse")
    reg_email = st.sidebar.text_input("Nuevo email", key="reg_email")
    reg_pass = st.sidebar.text_input("Nueva contraseña", type="password", key="reg_pass")
    if st.sidebar.button("Crear cuenta"):
        signup(reg_email, reg_pass)
else:
    user = st.session_state["user"]
    st.sidebar.success(f"Conectado: {user.get('email', 'Usuario')}")
    if st.sidebar.button("Cerrar sesión"):
        logout()

# -------------------
# APP PRINCIPAL
# -------------------
st.title("💰 Finanzas Personales - Dashboard")

if not st.session_state["user"]:
    st.info("Inicia sesión para ver y gestionar tus finanzas.")
    st.stop()

user = st.session_state["user"]
user_id = user.get("id")

# --- Panel para agregar transacción y crédito ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.header("➕ Nueva transacción")
    tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Credito"])
    categorias_por_tipo = {
        "Ingreso": ["Salario", "Comisión", "Venta", "Otro"],
        "Gasto": ["Comida", "Transporte", "Entretenimiento", "Servicios públicos", "Ocio", "Gasolina", "Ropa", "Otro"],
        "Credito": ["Tarjeta de crédito", "Préstamo", "Otro"]
    }
    categoria = st.selectbox("Categoría", categorias_por_tipo[tipo])
    if categoria == "Otro":
        categoria = st.text_input("Categoría personalizada")

    with st.form("form_trans"):
        monto = st.number_input("Monto", min_value=0.01, step=0.01)
        fecha = st.date_input("Fecha", value=date.today())
        if st.form_submit_button("Guardar transacción"):
            insertar_transaccion(user_id, tipo, categoria, monto, fecha)
            st.success("✅ Transacción guardada")
            st.rerun()

with col_right:
    st.header("➕ Nuevo crédito")
    with st.form("form_credito"):
        nombre = st.text_input("Nombre del crédito")
        monto_c = st.number_input("Monto del crédito", min_value=0.01, step=0.01)
        tasa = st.number_input("Tasa anual (%)", min_value=0.0, step=0.01)
        plazo = st.number_input("Plazo (meses)", min_value=1, step=1)
        cuotas_pagadas = st.number_input("Cuotas pagadas", min_value=0, step=1)
        if st.form_submit_button("Guardar crédito"):
            insertar_credito(user_id, nombre, monto_c, tasa, plazo, cuotas_pagadas)
            st.success("✅ Crédito guardado")
            st.rerun()

# -------------------
# CARGAR DATOS
# -------------------
transacciones = supabase.table("transacciones").select("*").eq("user_id", str(user_id)).order("fecha", desc=True).execute().data
creditos = supabase.table("credito").select("*").eq("user_id", str(user_id)).execute().data

# ==============================
# RESUMEN RÁPIDO
# ==============================
st.subheader("📊 Resumen financiero")
if transacciones:
    df = pd.DataFrame(transacciones)
    total_ingresos = df[df["tipo"] == "Ingreso"]["monto"].sum()
    total_gastos = df[df["tipo"] == "Gasto"]["monto"].sum()
    balance = total_ingresos - total_gastos
    total_creditos = sum([c["monto"] for c in creditos]) if creditos else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos", f"${total_ingresos:,.2f}")
    col2.metric("Gastos", f"${total_gastos:,.2f}")
    col3.metric("Balance", f"${balance:,.2f}")
    col4.metric("Créditos", f"${total_creditos:,.2f}")
else:
    st.info("No hay transacciones registradas aún.")

# ==============================
# GRAFICOS
# ==============================
if transacciones:
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["periodo"] = df["fecha"].dt.to_period("M").astype(str)

    resumen = df.groupby(["periodo", "tipo"])["monto"].sum().reset_index()

    # 📈 Línea de ingresos/gastos
    fig = go.Figure()
    for tipo in ["Ingreso", "Gasto", "Credito"]:
        subset = resumen[resumen["tipo"] == tipo]
        if not subset.empty:
            fig.add_trace(go.Scatter(x=subset["periodo"], y=subset["monto"], mode="lines+markers", name=tipo))
    st.plotly_chart(fig, use_container_width=True)

    # 📊 Gastos por categoría
    df_gastos = df[df["tipo"] == "Gasto"].groupby("categoria")["monto"].sum().reset_index()
    if not df_gastos.empty:
        fig_cat = go.Figure([go.Bar(x=df_gastos["categoria"], y=df_gastos["monto"])])
        fig_cat.update_layout(title="Distribución de gastos por categoría")
        st.plotly_chart(fig_cat, use_container_width=True)

# ==============================
# CRÉDITOS
# ==============================
st.header("💳 Mis créditos")
if creditos:
    for c in creditos:
        cuota_mensual = c["cuota_mensual"]
        cuotas_pagadas = c["cuotas_pagadas"]
        plazo = c["plazo_meses"]
        progreso = cuotas_pagadas / plazo if plazo > 0 else 0

        st.subheader(c["nombre"])
        st.write(f"Monto: ${c['monto']:,.2f}")
        st.write(f"Tasa interés: {c['tasa_interes']}%")
        st.write(f"Plazo: {plazo} meses")
        st.write(f"Cuota mensual: ${cuota_mensual:,.2f}")
        st.progress(progreso)
else:
    st.info("No hay créditos registrados.")

# -------------------
# FIRMA
# -------------------
st.markdown("<div style='text-align:center; color:gray; margin-top:30px;'>BY <b>J-J Solutions</b></div>", unsafe_allow_html=True)
