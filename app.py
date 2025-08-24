# =====================================
# app.py - Finanzas Personales (versión corregida)
# =====================================

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import io
import base64
import traceback

# --- Import de queries y utils ---
from queries import (
    registrar_pago, update_credito, insertar_transaccion, insertar_credito,
    borrar_transaccion, obtener_transacciones, obtener_creditos
)
from utils import login, signup, logout

# ============================
# Inicialización de session_state
# ============================
required_session_keys = ["user", "metas", "last_action"]
for k in required_session_keys:
    if k not in st.session_state:
        st.session_state[k] = None if k != "metas" else []

# ============================
# Cliente Supabase
# ============================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# ============================
# Utilidades
# ============================
def to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def to_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def descargar_bytes(nombre_archivo: str, data_bytes: bytes, label="Descargar"):
    b64 = base64.b64encode(data_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{nombre_archivo}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def generar_ics_evento(summary, dt_start: date, dt_end: date, description="", location=""):
    uid = f"{summary}-{dt_start.isoformat()}"
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Tu App Finanzas//ES
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}
DTSTART;VALUE=DATE:{dt_start.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{dt_end.strftime("%Y%m%d")}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location}
END:VEVENT
END:VCALENDAR
"""
    return ics.encode("utf-8")

# ============================
# Configuración de página
# ============================
st.set_page_config(page_title="Finanzas Personales", layout="wide")
st.sidebar.title("Menú")

# ============================
# Autenticación
# ============================
if st.session_state["user"] is None:
    menu = st.sidebar.radio("Selecciona una opción:", ["Login", "Registro"], index=0)

    if menu == "Login":
        st.subheader("Iniciar Sesión")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            try:
                login(supabase, email, password)
            except Exception as e:
                st.error("Error en login.")
                st.exception(e)

    elif menu == "Registro":
        st.subheader("Crear Cuenta")
        email = st.text_input("Correo electrónico (registro)")
        password = st.text_input("Contraseña (registro)", type="password")
        if st.button("Registrarse"):
            try:
                signup(supabase, email, password)
            except Exception as e:
                st.error("Error en registro.")
                st.exception(e)

else:
    st.sidebar.write(f"👤 {st.session_state['user'].get('email', 'Usuario')}")
    if st.sidebar.button("Cerrar Sesión"):
        try:
            logout(supabase)
            st.session_state["user"] = None
            st.experimental_rerun()
        except Exception as e:
            st.error("Error al cerrar sesión.")
            st.exception(e)

    # ============================
    # Tabs principales
    # ============================
    tabs = st.tabs(["Dashboard", "Transacciones", "Créditos", "Historial", "Metas", "Configuración"])

    # -------- Helper safe queries --------
    def safe_obtener_transacciones(user_id):
        try:
            res = obtener_transacciones(user_id)
            return res if isinstance(res, list) else (res.data if getattr(res, "data", None) else [])
        except Exception:
            traceback.print_exc()
            return []

    def safe_obtener_creditos(user_id):
        try:
            res = obtener_creditos(user_id)
            return res if isinstance(res, list) else (res.data if getattr(res, "data", None) else [])
        except Exception:
            traceback.print_exc()
            return []

    # ============================
    # 1. Dashboard
    # ============================
    with tabs[0]:
        st.header("📈 Dashboard")

        trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            df = pd.DataFrame(trans)
            if "monto" in df.columns:
                df["monto"] = df["monto"].apply(lambda x: to_float(x, 0.0))
            if "fecha" in df.columns:
                try:
                    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
                except Exception:
                    pass

            total_ingresos = df[df["tipo"] == "Ingreso"]["monto"].sum()
            total_gastos = df[df["tipo"] == "Gasto"]["monto"].sum()
            total_creditos = df[df["tipo"] == "Crédito"]["monto"].sum()
            saldo_total = total_ingresos - (total_gastos + total_creditos)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos", f"${total_ingresos:,.2f}")
            c2.metric("Gastos", f"${total_gastos:,.2f}")
            c3.metric("Créditos", f"${total_creditos:,.2f}")
            c4.metric("Saldo", f"${saldo_total:,.2f}")

            st.subheader("Transacciones recientes")
            st.dataframe(df.sort_values("fecha", ascending=False).head(10), use_container_width=True)

        else:
            st.info("Aún no hay transacciones.")

    # ============================
    # 2. Transacciones
    # ============================
    with tabs[1]:
        st.header("📊 Transacciones")

        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Crédito"])
        categoria = st.text_input("Categoría")
        with st.form("nueva_transaccion"):
            monto = st.number_input("Monto", min_value=0.01, step=1000.0, format="%.2f")
            fecha = st.date_input("Fecha", value=date.today())
            submitted = st.form_submit_button("Guardar")
            if submitted:
                try:
                    insertar_transaccion(st.session_state["user"]["id"], tipo, categoria, float(monto), fecha)
                    st.success("Transacción guardada ✅")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Error al guardar la transacción")
                    st.exception(e)

        trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            st.subheader("Todas las transacciones")
            df = pd.DataFrame(trans).sort_values("fecha", ascending=False)
            st.dataframe(df, use_container_width=True)

    # ============================
    # 3. Créditos
    # ============================
    with tabs[2]:
        st.header("💳 Créditos")
        with st.form("nuevo_credito"):
            nombre = st.text_input("Nombre del crédito")
            monto = st.number_input("Monto total", min_value=0.0, step=1000.0)
            plazo = st.number_input("Plazo (meses)", min_value=1, step=1)
            tasa = st.number_input("Tasa anual (%)", min_value=0.0, step=0.1)
            cuota = st.number_input("Cuota mensual", min_value=0.0, step=1000.0)
            dia_pago = st.number_input("Día de pago (1-28)", min_value=1, max_value=28, step=1, value=14)
            submitted = st.form_submit_button("Guardar crédito")
            if submitted:
                try:
                    insertar_credito(st.session_state["user"]["id"], nombre, monto, plazo, tasa, cuota, dia_pago)
                    st.success("Crédito guardado ✅")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Error al guardar crédito")
                    st.exception(e)

        creditos = safe_obtener_creditos(st.session_state["user"]["id"]) or []
        if creditos:
            for c in creditos:
                st.write(f"🏦 {c.get('nombre')} — ${c.get('monto'):,.2f}")

    # ============================
    # 4. Historial
    # ============================
    with tabs[3]:
        st.header("📜 Historial")
        trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            df = pd.DataFrame(trans).sort_values("fecha", ascending=False)
            st.dataframe(df, use_container_width=True)

    # ============================
    # 5. Metas
    # ============================
    with tabs[4]:
        st.header("🎯 Metas de ahorro")
        nombre = st.text_input("Nombre de la meta")
        monto = st.number_input("Monto objetivo", min_value=0.0, step=10000.0)
        if st.button("Guardar meta"):
            if nombre and monto > 0:
                st.session_state["metas"].append({"nombre": nombre, "monto": monto, "ahorrado": 0})
                st.success("Meta guardada ✅")
                st.experimental_rerun()

        if st.session_state["metas"]:
            for m in st.session_state["metas"]:
                st.write(f"💡 {m['nombre']} — Objetivo ${m['monto']:,.2f}, Ahorrado ${m['ahorrado']:,.2f}")

    # ============================
    # 6. Configuración
    # ============================
    with tabs[5]:
        st.header("⚙️ Configuración")
        st.write("Opciones avanzadas próximamente.")
