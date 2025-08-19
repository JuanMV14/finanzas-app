import streamlit as st
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

    try:
        if isinstance(auth_resp, dict):
            user_dict = auth_resp.get("user") or auth_resp.get("data") or auth_resp
            if isinstance(user_dict, dict):
                uid = user_dict.get("id") or user_dict.get("user", {}).get("id")
                email = user_dict.get("email") or (user_dict.get("user") or {}).get("email")
                if uid:
                    return {"id": str(uid), "email": email}
    except Exception:
        pass

    try:
        gu = supabase.auth.get_user()
        gu_user = getattr(gu, "user", None) or (gu.get("data", {}).get("user") if isinstance(gu, dict) else None)
        if gu_user:
            uid = getattr(gu_user, "id", None) or (gu_user.get("id") if isinstance(gu_user, dict) else None)
            email = getattr(gu_user, "email", None) or (gu_user.get("email") if isinstance(gu_user, dict) else None)
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
        user = _extract_user_from_auth_response(resp)
        if user:
            st.success("Cuenta creada. Revisa tu email para confirmar (si aplica).")
        else:
            st.success("Cuenta registrada. Inicia sesión.")
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
    try:
        return supabase.table("transacciones").insert(payload).execute()
    except Exception as e:
        return {"error": str(e)}

def insertar_credito(user_id, nombre, monto, tasa, plazo_meses):
    payload = {"user_id": str(user_id), "nombre": nombre, "monto": float(monto), "tasa_interes": float(tasa), "plazo_meses": int(plazo_meses)}
    try:
        return supabase.table("credito").insert(payload).execute()
    except Exception as e:
        return {"error": str(e)}

def borrar_transaccion(user_id, trans_id):
    try:
        return supabase.table("transacciones").delete().eq("id", trans_id).eq("user_id", str(user_id)).execute()
    except Exception as e:
        return {"error": str(e)}

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
    with st.form("form_trans"):
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Credito"])
        if tipo == "Ingreso":
            categoria = st.selectbox("Categoría", ["Salario", "Comisión", "Venta", "Otro"])
        elif tipo == "Gasto":
            categoria = st.selectbox("Categoría", ["Comida", "Transporte", "Servicios", "Entretenimiento", "Otro"])
        else:
            categoria = st.selectbox("Categoría", ["Tarjeta de crédito", "Préstamo", "Tecnomecánica", "Otro"])

        monto = st.number_input("Monto", min_value=0.01, step=0.01)
        fecha = st.date_input("Fecha", value=date.today())
        submitted = st.form_submit_button("Guardar transacción")

        if submitted:
            res = insertar_transaccion(user_id, tipo, categoria, monto, fecha)
            if isinstance(res, dict) and res.get("error"):
                st.error(f"❌ Error al guardar: {res['error']}")
            else:
                ok = getattr(res, "data", None) or (res.get("data") if isinstance(res, dict) else None)
                if ok:
                    st.success("✅ Transacción guardada")
                    st.rerun()
                else:
                    st.error(f"⚠️ No se pudo guardar. Respuesta: {res}")

with col_right:
    st.header("➕ Nuevo crédito")
    with st.form("form_credito"):
        nombre = st.text_input("Nombre del crédito")
        monto_c = st.number_input("Monto del crédito", min_value=0.01, step=0.01, key="monto_credito")
        tasa = st.number_input("Tasa anual (%)", min_value=0.0, step=0.01, key="tasa_credito")
        plazo = st.number_input("Plazo (meses)", min_value=1, step=1, key="plazo_credito")
        subc = st.form_submit_button("Guardar crédito")
        if subc:
            r = insertar_credito(user_id, nombre, monto_c, tasa, plazo)
            if isinstance(r, dict) and r.get("error"):
                st.error(f"❌ Error al guardar crédito: {r['error']}")
            else:
                ok = getattr(r, "data", None) or (r.get("data") if isinstance(r, dict) else None)
                if ok:
                    st.success("✅ Crédito guardado")
                    st.rerun()
                else:
                    st.error(f"⚠️ No se pudo guardar el crédito. Respuesta: {r}")

st.markdown("---")

# -------------------
# CARGAR TRANSACCIONES Y CREDITOS
# -------------------
try:
    trs_resp = supabase.table("transacciones").select("*").eq("user_id", str(user_id)).order("fecha", desc=True).execute()
    transacciones = getattr(trs_resp, "data", None) or (trs_resp.get("data") if isinstance(trs_resp, dict) else None) or []
except Exception as e:
    st.error(f"Error al cargar transacciones: {e}")
    transacciones = []

try:
    cred_resp = supabase.table("credito").select("*").eq("user_id", str(user_id)).execute()
    creditos = getattr(cred_resp, "data", None) or (cred_resp.get("data") if isinstance(cred_resp, dict) else None) or []
except Exception as e:
    st.error(f"Error al cargar créditos: {e}")
    creditos = []

# -------------------
# TABLA Y DELETE
# -------------------
st.header("📋 Mis transacciones")
if transacciones:
    df = pd.DataFrame(transacciones)
    st.dataframe(df[["id", "fecha", "tipo", "categoria", "monto"]].sort_values(by="fecha", ascending=False), use_container_width=True)

    for t in transacciones:
        cols = st.columns([3, 2, 2, 1])
        cols[0].write(f"{t.get('fecha')} — **{t.get('tipo')}** — {t.get('categoria')}")
        cols[1].write(f"${float(t.get('monto')):,.2f}")
        if cols[3].button("Eliminar", key=f"del_{t.get('id')}"):
            r = borrar_transaccion(user_id, t.get("id"))
            if isinstance(r, dict) and r.get("error"):
                st.error(f"Error al eliminar: {r['error']}")
            else:
                st.success("Transacción eliminada")
                st.rerun()
else:
    st.info("No hay transacciones registradas.")
    df = pd.DataFrame()

# ==============================
# DASHBOARD
# ==============================
if not df.empty:
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["periodo"] = df["fecha"].dt.to_period("M").astype(str)
    resumen = df.groupby(["periodo", "tipo"])["monto"].sum().reset_index()

    fig = go.Figure()

    df_ingresos = resumen[resumen["tipo"] == "Ingreso"]
    if not df_ingresos.empty:
        fig.add_trace(go.Scatter(x=df_ingresos["periodo"], y=df_ingresos["monto"], mode="lines+markers", line=dict(color="#00CC96", width=3), marker=dict(size=10, color="#00CC96", line=dict(width=2, color="#FFFFFF")), name="Ingresos"))

    df_gastos = resumen[resumen["tipo"] == "Gasto"]
    if not df_gastos.empty:
        fig.add_trace(go.Scatter(x=df_gastos["periodo"], y=df_gastos["monto"], mode="lines+markers", line=dict(color="#EF553B", width=3), marker=dict(size=10, color="#EF553B", line=dict(width=2, color="#FFFFFF")), name="Gastos"))

    df_creditos = resumen[resumen["tipo"] == "Credito"]
    if not df_creditos.empty:
        fig.add_trace(go.Scatter(x=df_creditos["periodo"], y=df_creditos["monto"], mode="lines+markers", line=dict(color="#636EFA", width=3), marker=dict(size=10, color="#636EFA", line=dict(width=2, color="#FFFFFF")), name="Créditos"))

    fig.update_layout(template="plotly_dark", paper_bgcolor="#1E1E2F", plot_bgcolor="#1E1E2F", font=dict(color="#E4E4E7", family="Arial"), margin=dict(l=40, r=20, t=50, b=40), title=dict(text="📊 Ingresos, Gastos y Créditos", font=dict(size=22, color="#FFFFFF"), x=0.5), xaxis=dict(showgrid=False, zeroline=False, linecolor="#444"), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)", zeroline=False, linecolor="#444"))

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay transacciones registradas aún para mostrar el dashboard.")

# -------------------
# FIRMA
# -------------------
st.markdown("<div style='text-align:center; color:gray; margin-top:30px;'>BY <b>J-J Solutions</b></div>", unsafe_allow_html=True)
