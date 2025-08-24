# =====================================
# app.py - Finanzas Personales (versión corregida sin key en form_submit_button)
# =====================================

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import date, datetime
import pandas as pd
import base64
import traceback
import altair as alt

# --- Import de queries y utils ---
from queries import (
    registrar_pago, update_credito, insertar_transaccion, insertar_credito,
    borrar_transaccion, obtener_transacciones, obtener_creditos,
    insertar_meta, obtener_metas, update_meta, borrar_meta
)
from utils import login, signup, logout

# ============================
# Inicialización de session_state
# ============================
required_session_keys = ["user"]
for k in required_session_keys:
    if k not in st.session_state:
        st.session_state[k] = None

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

# ============================
# Configuración de página
# ============================
st.set_page_config(page_title="Finanzas Personales", layout="wide")

# ============================
# Sidebar único
# ============================
def dibujar_sidebar():
    with st.sidebar:
        st.title("Menú")

        if st.session_state["user"] is None:
            menu_auth = st.radio("Selecciona una opción:", ["Login", "Registro"], index=0, key="menu_auth")

            if menu_auth == "Login":
                st.subheader("Iniciar Sesión")
                with st.form("login_form", clear_on_submit=True):
                    email = st.text_input("Correo electrónico", key="login_email")
                    password = st.text_input("Contraseña", type="password", key="login_pass")
                    submitted = st.form_submit_button("Ingresar")
                    if submitted:
                        login(supabase, email, password)

            else:
                st.subheader("Crear Cuenta")
                with st.form("signup_form", clear_on_submit=True):
                    email_reg = st.text_input("Correo electrónico (registro)", key="reg_email")
                    password_reg = st.text_input("Contraseña (registro)", type="password", key="reg_pass")
                    submitted = st.form_submit_button("Registrarse")
                    if submitted:
                        signup(supabase, email_reg, password_reg)

        else:
            st.write(f"👤 {st.session_state['user'].get('email', 'Usuario')}")
            if st.button("Cerrar Sesión", use_container_width=True, key="btn_logout"):
                logout(supabase)

dibujar_sidebar()

# Si no hay usuario logueado, parar aquí
if st.session_state["user"] is None:
    st.stop()

# ============================
# Helpers seguros
# ============================
def safe_obtener_transacciones(user_id):
    try:
        return obtener_transacciones(user_id)
    except Exception:
        traceback.print_exc()
        return []

def safe_obtener_creditos(user_id):
    try:
        return obtener_creditos(user_id)
    except Exception:
        traceback.print_exc()
        return []

def safe_obtener_metas(user_id):
    try:
        return obtener_metas(user_id)
    except Exception:
        traceback.print_exc()
        return []

# ============================
# Tabs principales
# ============================
tabs = st.tabs(["Dashboard", "Transacciones", "Créditos", "Historial", "Metas", "Configuración"])

# ============================
# 1) Dashboard
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

        st.subheader("Transacciones por fecha")
        chart = alt.Chart(df).mark_bar().encode(
            x="fecha:T",
            y="sum(monto):Q",
            color="tipo:N",
            tooltip=["tipo", "categoria", "monto", "fecha"]
        )
        st.altair_chart(chart, use_container_width=True)

        st.subheader("Transacciones recientes")
        st.dataframe(df.sort_values("fecha", ascending=False).head(10), use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV", csv, "transacciones.csv", "text/csv", key="btn_export_csv")
    else:
        st.info("Aún no hay transacciones.")

# ============================
# 2) Transacciones
# ============================
with tabs[1]:
    st.header("📊 Transacciones")

    with st.form("nueva_transaccion", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Crédito"], key="tipo_trans")
        categoria = st.text_input("Categoría", key="categoria_trans")
        monto = st.number_input("Monto", min_value=0.01, step=1000.0, format="%.2f", key="monto_trans")
        fecha = st.date_input("Fecha", value=date.today(), key="fecha_trans")
        submitted = st.form_submit_button("Guardar")

        if submitted:
            try:
                insertar_transaccion(st.session_state["user"]["id"], tipo, categoria, float(monto), fecha)
                st.success("Transacción guardada ✅")
                st.rerun()
            except Exception as e:
                st.error("Error al guardar la transacción")
                st.exception(e)

    trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
    if trans:
        df = pd.DataFrame(trans).sort_values("fecha", ascending=False)
        st.subheader("Todas las transacciones")
        st.dataframe(df, use_container_width=True)

# ============================
# 3) Créditos
# ============================
with tabs[2]:
    st.header("💳 Créditos")

    with st.form("nuevo_credito", clear_on_submit=True):
        nombre = st.text_input("Nombre del crédito", key="nombre_credito")
        monto = st.number_input("Monto total", min_value=0.0, step=1000.0, key="monto_credito")
        plazo = st.number_input("Plazo (meses)", min_value=1, step=1, key="plazo_credito")
        tasa = st.number_input("Tasa anual (%)", min_value=0.0, step=0.1, key="tasa_credito")
        cuota = st.number_input("Cuota mensual", min_value=0.0, step=1000.0, key="cuota_credito")
        dia_pago = st.number_input("Día de pago (1-28)", min_value=1, max_value=28, step=1, value=14, key="dia_pago_credito")
        submitted = st.form_submit_button("Guardar crédito")

        if submitted:
            try:
                insertar_credito(st.session_state["user"]["id"], nombre, monto, plazo, tasa, cuota, dia_pago)
                st.success("Crédito guardado ✅")
                st.rerun()
            except Exception as e:
                st.error("Error al guardar crédito")
                st.exception(e)

    creditos = safe_obtener_creditos(st.session_state["user"]["id"]) or []
    if creditos:
        for c in creditos:
            cuotas_pagadas = to_int(c.get("cuotas_pagadas", 0))
            st.write(f"🏦 {c.get('nombre')} — ${to_float(c.get('monto',0)):,.2f} | Plazo {c.get('plazo')} meses | Cuota ${c.get('cuota'):,.2f} | Pagadas {cuotas_pagadas}")

# ============================
# 4) Historial
# ============================
with tabs[3]:
    st.header("📜 Historial")
    trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
    if trans:
        df = pd.DataFrame(trans).sort_values("fecha", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sin historial aún.")

# ============================
# 5) Metas
# ============================
with tabs[4]:
    st.header("🎯 Metas de ahorro")

    with st.form("form_meta", clear_on_submit=True):
        nombre_meta = st.text_input("Nombre de la meta", key="nombre_meta")
        monto_objetivo = st.number_input("Monto objetivo", min_value=0.0, step=10000.0, key="monto_meta")
        ahorrado_inicial = st.number_input("Ahorrado inicial", min_value=0.0, step=10000.0, value=0.0, key="ahorrado_meta")
        submitted_meta = st.form_submit_button("Guardar meta")

        if submitted_meta:
            if nombre_meta and monto_objetivo > 0:
                insertar_meta(st.session_state["user"]["id"], nombre_meta, float(monto_objetivo), float(ahorrado_inicial))
                st.success("Meta guardada ✅")
                st.rerun()

    metas = safe_obtener_metas(st.session_state["user"]["id"]) or []
    if metas:
        for m in metas:
            nombre = m.get("nombre", "Meta")
            objetivo = to_float(m.get("monto", 0))
            ahorrado = to_float(m.get("ahorrado", 0))
            progreso = 0 if objetivo <= 0 else min(int((ahorrado / objetivo) * 100), 100)

            st.markdown(f"**{nombre}** — Objetivo: ${objetivo:,.2f} | Ahorrado: ${ahorrado:,.2f} | Progreso: {progreso}%")
            st.progress(progreso)

            with st.expander(f"Actualizar {nombre}"):
                nuevo_ahorro = st.number_input(f"Nuevo valor ahorrado", min_value=0.0, step=10000.0, value=ahorrado, key=f"ah_{m['id']}")
                col1, col2 = st.columns(2)
                if col1.button("💾 Guardar actualización", key=f"upd_{m['id']}"):
                    update_meta(m['id'], {"ahorrado": float(nuevo_ahorro)})
                    st.success("Meta actualizada ✅")
                    st.rerun()
                if col2.button("🗑️ Borrar meta", key=f"del_{m['id']}"):
                    borrar_meta(m['id'])
                    st.success("Meta eliminada ✅")
                    st.rerun()
    else:
        st.info("No tienes metas todavía.")

# ============================
# 6) Configuración
# ============================
with tabs[5]:
    st.header("⚙️ Configuración")
    st.markdown("""
- **Asistente financiero (IA):** recomendaciones de ahorro y gasto.
- **Alertas y recordatorios:** límites de gasto por categoría, recordatorio de pagos.
- **Personalización:** moneda, tema visual.
- **Exportación/Importación:** CSV/Excel.
""")
