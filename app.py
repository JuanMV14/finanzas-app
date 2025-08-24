# ===============================
# app.py - Finanzas Personales
# ===============================

import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os
from supabase import create_client, Client

# 🔐 Cargar variables de entorno
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 🧠 Inicializar cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ⚙️ Configuración de página
st.set_page_config(page_title="Finanzas Personales", layout="wide")

# ===============================
# 🔐 Autenticación
# ===============================

def autenticar_usuario(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res.user
    except Exception:
        return None

# ===============================
# 📦 Funciones de base de datos
# ===============================

def obtener_transacciones(user_id):
    try:
        res = supabase.from("transacciones").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception:
        return []

def obtener_metas(user_id):
    try:
        res = supabase.from("metas").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except Exception:
        return []

def crear_meta(user_id, nombre, monto):
    try:
        nueva_meta = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "nombre": nombre,
            "monto": monto,
            "ahorrado": 0,
            "creada_en": datetime.utcnow().isoformat()
        }
        supabase.from("metas").insert(nueva_meta).execute()
        return True
    except Exception:
        return False

def actualizar_ahorro(meta_id, nuevo_valor):
    try:
        supabase.from("metas").update({"ahorrado": nuevo_valor}).eq("id", meta_id).execute()
        return True
    except Exception:
        return False

# ===============================
# 🧭 Sidebar de sesión
# ===============================

if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    st.sidebar.title("🔐 Iniciar sesión")
    email = st.sidebar.text_input("Correo electrónico")
    password = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Acceder"):
        user = autenticar_usuario(email, password)
        if user:
            st.session_state["user"] = user
            st.experimental_rerun()
        else:
            st.sidebar.error("Credenciales inválidas")
else:
    st.sidebar.success(f"Sesión iniciada: {st.session_state['user']['email']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["user"] = None
        st.experimental_rerun()

# ===============================
# 🧩 Validación de sesión
# ===============================

if st.session_state["user"] is None:
    st.stop()

user_id = st.session_state["user"]["id"]

# ===============================
# 🏠 Interfaz principal
# ===============================

st.title("💰 Panel Financiero Personal")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🎯 Metas de Ahorro", "⚙️ Configuración"])

# ===============================
# 📊 Tab: Dashboard
# ===============================

with tab1:
    st.header("Resumen de Transacciones")
    transacciones = obtener_transacciones(user_id)

    if not transacciones:
        st.info("No hay transacciones registradas.")
    else:
        df = pd.DataFrame(transacciones)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.sort_values("fecha", ascending=False)

        st.dataframe(df, use_container_width=True)

        ingresos = df[df["tipo"] == "ingreso"]["monto"].sum()
        gastos = df[df["tipo"] == "gasto"]["monto"].sum()
        creditos = df[df["tipo"] == "credito"]["monto"].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Ingresos", f"${ingresos:,.2f}")
        col2.metric("Gastos", f"${gastos:,.2f}")
        col3.metric("Créditos", f"${creditos:,.2f}")

# ===============================
# 🎯 Tab: Metas de Ahorro
# ===============================

with tab2:
    st.header("Tus Metas de Ahorro")

    metas = obtener_metas(user_id)

    if not metas:
        st.info("No tienes metas registradas.")
    else:
        for meta in metas:
            nombre = meta["nombre"]
            monto = meta["monto"]
            ahorrado = meta["ahorrado"]
            progreso = min(ahorrado / monto, 1.0)

            st.subheader(f"💼 {nombre}")
            st.write(f"Monto objetivo: **${monto:,.2f}**")
            st.write(f"Ahorrado: **${ahorrado:,.2f}**")

            st.progress(progreso)

            nuevo_ahorro = st.number_input(
                f"Actualizar ahorro para '{nombre}'",
                min_value=0.0,
                value=ahorrado,
                step=100.0,
                key=f"ahorro_{meta['id']}"
            )

            if st.button(f"Guardar nuevo ahorro para '{nombre}'", key=f"guardar_{meta['id']}"):
                if nuevo_ahorro > monto:
                    st.warning("El ahorro no puede superar el monto objetivo.")
                else:
                    ok = actualizar_ahorro(meta["id"], nuevo_ahorro)
                    if ok:
                        st.success("Ahorro actualizado correctamente.")
                        st.experimental_rerun()
                    else:
                        st.error("No se pudo actualizar el ahorro.")

    st.divider()
    st.subheader("➕ Crear nueva meta")

    with st.form("form_meta"):
        nombre_meta = st.text_input("Nombre de la meta")
        monto_meta = st.number_input("Monto objetivo", min_value=0.0, step=100.0)
        submitted = st.form_submit_button("Crear meta")

        if submitted:
            if not nombre_meta or monto_meta <= 0:
                st.warning("Completa todos los campos correctamente.")
            else:
                ok = crear_meta(user_id, nombre_meta, monto_meta)
                if ok:
                    st.success("Meta creada exitosamente.")
                    st.experimental_rerun()
                else:
                    st.error("No se pudo crear la meta.")

# ===============================
# ⚙️ Tab: Configuración
# ===============================

with tab3:
    st.header("Configuración y Herramientas")

    st.markdown("Aquí podrás personalizar tu experiencia, exportar datos o activar funciones avanzadas.")

    st.subheader("🔔 Alertas inteligentes")
    activar_alertas = st.checkbox("Activar alertas por exceso de gasto")
    if activar_alertas:
        st.info("Esta función está en desarrollo. Pronto podrás recibir notificaciones automáticas.")

    st.subheader("📤 Exportar transacciones")
    if st.button("Descargar CSV"):
        df_export = pd.DataFrame(transacciones)
        st.download_button(
            label="Descargar archivo",
            data=df_export.to_csv(index=False).encode("utf-8"),
            file_name="transacciones.csv",
            mime="text/csv"
        )

    st.subheader("🎨 Personalización visual")
    tema = st.selectbox("Selecciona un tema", ["Claro", "Oscuro", "Sistema"])
    st.info(f"Has seleccionado el tema: {tema}. Esta opción será aplicada en futuras versiones.")

    st.subheader("🧠 Asistente financiero")
    st.markdown("¿Quieres que el sistema te sugiera cómo ahorrar más?")
    if st.button("Activar recomendaciones"):
        st.success("Función activada. Pronto recibirás sugerencias personalizadas.")

# ===============================
# 🧪 Funciones adicionales (extensibles)
# ===============================

def clasificar_transacciones(df):
    # Clasificación básica por palabra clave
    categorias = {
        "comida": ["restaurante", "supermercado", "mercado"],
        "transporte": ["uber", "taxi", "bus", "gasolina"],
        "servicios": ["luz", "agua", "internet", "teléfono"],
        "entretenimiento": ["cine", "spotify", "netflix"],
        "otros": []
    }

    def asignar_categoria(descripcion):
        descripcion = descripcion.lower()
        for categoria, palabras in categorias.items():
            if any(palabra in descripcion for palabra in palabras):
                return categoria
        return "otros"

    df["categoria"] = df["descripcion"].apply(asignar_categoria)
    return df

def simulador_credito(monto, tasa_anual, cuotas):
    tasa_mensual = tasa_anual / 12 / 100
    if tasa_mensual == 0:
        cuota = monto / cuotas
    else:
        cuota = monto * (tasa_mensual * (1 + tasa_mensual) ** cuotas) / ((1 + tasa_mensual) ** cuotas - 1)
    return round(cuota, 2)

# ===============================
# 🧮 Simulador de crédito (opcional)
# ===============================

with tab3:
    st.subheader("🧮 Simulador de Crédito")

    monto_credito = st.number_input("Monto del crédito", min_value=0.0, step=100.0)
    tasa_interes = st.number_input("Tasa de interés anual (%)", min_value=0.0, step=0.1)
    cuotas = st.number_input("Número de cuotas mensuales", min_value=1, step=1)

    if st.button("Calcular cuota mensual"):
        cuota = simulador_credito(monto_credito, tasa_interes, cuotas)
        st.success(f"Cuota mensual estimada: ${cuota:,.2f}")

# ===============================
# 🧼 Limpieza de sesión (debug)
# ===============================

def resetear_sesion():
    for key in st.session_state.keys():
        del st.session_state[key]

# ===============================
# 🧾 Footer
# ===============================

st.markdown("---")
st.caption("App desarrollada por Juan • Datos seguros con Supabase • Streamlit v1.33+")
