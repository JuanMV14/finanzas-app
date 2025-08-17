import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
import datetime

# ----------------- CONFIGURACIÓN -----------------
st.set_page_config(page_title="💰 Finanzas Personales", layout="wide")

SUPABASE_URL = "https://ejsakzzbgwymptqjoigs.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ----------------- FUNCIONES -----------------
def cargar_transacciones(user_id):
    try:
        res = supabase.table("transacciones").select("*").eq("user_id", user_id).order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data or [])
        if not df.empty:
            df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
            df["monto"] = pd.to_numeric(df["monto"])
        return df
    except Exception as e:
        st.error(f"Error al cargar transacciones: {e}")
        return pd.DataFrame()

def agregar_transaccion(fecha, tipo, categoria, monto, user_id):
    user_data = supabase.auth.get_user()
    if not user_data or not user_data.user:
        st.error("⚠️ No hay sesión activa. No se puede guardar la transacción.")
        return

    uid_actual = user_data.user.id
    if user_id != uid_actual:
        st.error("⚠️ UID no coincide con el usuario autenticado. Transacción bloqueada.")
        st.write("UID desde sesión:", user_id)
        st.write("UID desde Supabase:", uid_actual)
        return

    payload = {
        "fecha": fecha.isoformat(),
        "tipo": tipo,
        "categoria": categoria,
        "monto": float(monto),
        "user_id": user_id,
    }
    try:
        res = supabase.table("transacciones").insert([payload]).execute()
        if res.status_code == 201:
            st.success("✅ Transacción guardada correctamente")
        else:
            st.error("❌ Error al guardar transacción")
            st.write("Respuesta Supabase:", res)
    except Exception as e:
        st.error("❌ Error al guardar transacción")
        st.write(str(e))

def cargar_creditos(user_id):
    try:
        res = supabase.table("credito").select("*").eq("user_id", user_id).order("id", desc=True).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"Error al cargar créditos: {e}")
        return pd.DataFrame()

def agregar_credito(nombre, monto, tasa, plazo, user_id):
    payload = {
        "nombre": nombre,
        "monto": float(monto),
        "tasa_interes": float(tasa),
        "plazo_meses": int(plazo),
        "user_id": user_id,
    }
    try:
        supabase.table("credito").insert(payload).execute()
    except Exception as e:
        st.error(f"Error al guardar crédito: {e}")

# ----------------- AUTENTICACIÓN -----------------
if "user_id" not in st.session_state:
    st.sidebar.header("🔐 Iniciar sesión")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Contraseña", type="password")

    if st.sidebar.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            usuario = supabase.auth.get_user().user
            st.session_state["user_id"] = usuario.id
            st.sidebar.success(f"Bienvenido {email}")
            st.experimental_rerun()
        except Exception as e:
            st.sidebar.error(f"Error al iniciar sesión: {e}")

    st.sidebar.header("📝 Registrarse")
    new_email = st.sidebar.text_input("Nuevo email")
    new_password = st.sidebar.text_input("Nueva contraseña", type="password")

    if st.sidebar.button("Crear cuenta"):
        try:
            res = supabase.auth.sign_up({"email": new_email, "password": new_password})
            st.sidebar.success("✅ Cuenta creada. Ahora inicia sesión.")
        except Exception as e:
            st.sidebar.error(f"Error al registrar: {e}")
else:
    st.sidebar.success("🔓 Sesión iniciada")
    st.sidebar.write("Ya estás autenticado.")
    st.sidebar.write("🧠 Tu user_id:", st.session_state["user_id"])
    if st.sidebar.button("Cerrar sesión"):
        del st.session_state["user_id"]
        st.experimental_rerun()

# ----------------- APP PRINCIPAL -----------------
if "user_id" in st.session_state:
    user_id = st.session_state["user_id"]

    st.title("💰 Finanzas Personales App")
    st.subheader("Tus datos guardados en Supabase")

    # NUEVA TRANSACCIÓN
    st.sidebar.header("📥 Nueva Transacción")
    tipo = st.sidebar.selectbox("Tipo", ["Ingreso", "Gasto"])
    categoria = st.sidebar.selectbox("Categoría", ["Salario", "Comisiones", "Alimentación", "Transporte", "Ocio", "Servicios", "Deudas", "Otros"])
    monto = st.sidebar.number_input("Monto", min_value=0.0, format="%.2f")
    fecha = st.sidebar.date_input("Fecha", datetime.date.today())

    if st.sidebar.button("Agregar"):
        if monto <= 0:
            st.sidebar.error("El monto debe ser mayor que 0.")
        else:
            agregar_transaccion(fecha, tipo, categoria, monto, user_id)
            st.stop()

    # HISTORIAL DE TRANSACCIONES
    st.header("📋 Historial de Transacciones")
    df = cargar_transacciones(user_id)

    if df.empty:
        st.info("No hay transacciones registradas aún.")
    else:
        st.dataframe(df, use_container_width=True)

        ingresos = df[df["tipo"] == "Ingreso"]["monto"].sum()
        gastos = df[df["tipo"] == "Gasto"]["monto"].sum()
        ahorro = ingresos - gastos

        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos Totales", f"${ingresos:,.2f}")
        col2.metric("Gastos Totales", f"${gastos:,.2f}")
        col3.metric("Ahorro", f"${ahorro:,.2f}")

        st.subheader("📊 Distribución de Gastos por Categoría")
        gastos_df = df[df["tipo"] == "Gasto"]
        if not gastos_df.empty:
            fig, ax = plt.subplots()
            gastos_df.groupby("categoria")["monto"].sum().plot(kind="bar", ax=ax, color="salmon")
            ax.set_ylabel("Monto ($)")
            ax.set_title("Gastos por Categoría")
            st.pyplot(fig)

        st.download_button(
            "⬇️ Descargar CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="transacciones.csv",
            mime="text/csv"
        )

    # GESTIÓN DE CRÉDITOS
    st.header("💳 Gestión de Créditos")
    with st.expander("➕ Agregar nuevo crédito"):
        nombre_credito = st.text_input("Nombre del crédito")
        monto_credito = st.number_input("Monto del crédito", min_value=0.0, format="%.2f")
        tasa_interes = st.number_input("Tasa de interés anual (%)", min_value=0.0, format="%.2f")
        plazo_meses = st.number_input("Plazo en meses", min_value=1, step=1)

        if st.button("Guardar crédito"):
            if not nombre_credito or monto_credito <= 0 or plazo_meses <= 0:
                st.error("Completa todos los campos correctamente.")
            else:
                agregar_credito(nombre_credito, monto_credito, tasa_interes, plazo_meses, user_id)
                st.success("✅ Crédito guardado")
                st.experimental_rerun()

    cdf = cargar_creditos(user_id)
    if not cdf.empty:
        st.subheader("Mis créditos")
        st.dataframe(cdf[["nombre", "monto", "tasa_interes", "plazo_meses"]], use_container_width=True)

        st.subheader("🧮 Simulador de cuotas")
        sel = st.selectbox("Selecciona un crédito", cdf["nombre"].tolist())
        row = cdf[cdf["nombre"] == sel].iloc[0]
        principal = float(row["monto"])
        rate_annual = float(row["tasa_interes"])
        term = int(row["plazo_meses"])

        if rate_annual == 0:
            cuota = principal / term
        else:
            r = (rate_annual / 100.0) / 12.0
            cuota = principal * (r * (1 + r)**term) / ((1 + r)**term - 1)

        total_pagado = cuota * term
        interes_total = total_pagado - principal

        c1, c2, c3 = st.columns(3)
        c1.metric("Cuota mensual", f"${cuota:,.2f}")
