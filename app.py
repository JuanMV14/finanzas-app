# =====================================
# app.py - Finanzas Personales (versión funcional)
# =====================================

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import date, datetime
import pandas as pd
import numpy as np
import base64
import io
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

# ========== Sidebar (única instancia, sin duplicados) ==========
with st.sidebar:
    st.title("Menú")

    if st.session_state["user"] is None:
        menu_auth = st.radio("Selecciona una opción:", ["Login", "Registro"], index=0)
        if menu_auth == "Login":
            st.subheader("Iniciar Sesión")
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            if st.button("Ingresar", use_container_width=True):
                try:
                    login(supabase, email, password)
                except Exception as e:
                    st.error("Error en login.")
                    st.exception(e)
        else:
            st.subheader("Crear Cuenta")
            email_reg = st.text_input("Correo electrónico (registro)")
            password_reg = st.text_input("Contraseña (registro)", type="password")
            if st.button("Registrarse", use_container_width=True):
                try:
                    signup(supabase, email_reg, password_reg)
                except Exception as e:
                    st.error("Error en registro.")
                    st.exception(e)
    else:
        st.write(f"👤 {st.session_state['user'].get('email', 'Usuario')}")
        if st.button("Cerrar Sesión", use_container_width=True):
            try:
                logout(supabase)
            except Exception as e:
                st.error("Error al cerrar sesión.")
                st.exception(e)

# Si no hay usuario logueado, parar aquí
if st.session_state["user"] is None:
    st.stop()

# ============================
# Helpers para consultas seguras
# ============================
def safe_obtener_transacciones(user_id):
    try:
        res = obtener_transacciones(user_id)
        return res if isinstance(res, list) else []
    except Exception:
        traceback.print_exc()
        return []

def safe_obtener_creditos(user_id):
    try:
        res = obtener_creditos(user_id)
        return res if isinstance(res, list) else []
    except Exception:
        traceback.print_exc()
        return []

def safe_obtener_metas(user_id):
    try:
        res = obtener_metas(user_id)
        return res if isinstance(res, list) else []
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
        # Limpieza de tipos
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
        df_chart = df.copy()
        # Forzar strings limpias en tipo
        df_chart["tipo"] = df_chart["tipo"].astype(str)
        chart = alt.Chart(pd.DataFrame(df_chart)).mark_bar().encode(
            x=alt.X("fecha:T", title="Fecha"),
            y=alt.Y("sum(monto):Q", title="Monto"),
            color=alt.Color("tipo:N", title="Tipo"),
            tooltip=["tipo:N", "categoria:N", "monto:Q", "fecha:T"]
        )
        st.altair_chart(chart, use_container_width=True)

        st.subheader("Transacciones recientes")
        st.dataframe(df.sort_values("fecha", ascending=False).head(10), use_container_width=True)

        # Exportación CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV", csv, "transacciones.csv", "text/csv")
    else:
        st.info("Aún no hay transacciones. Registra la primera desde la pestaña **Transacciones**.")

# ============================
# 2) Transacciones
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
                st.rerun()
            except Exception as e:
                st.error("Error al guardar la transacción")
                st.exception(e)

    trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
    if trans:
        st.subheader("Todas las transacciones")
        df = pd.DataFrame(trans).sort_values("fecha", ascending=False)
        st.dataframe(df, use_container_width=True)

# ============================
# 3) Créditos
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
                st.rerun()
            except Exception as e:
                st.error("Error al guardar crédito")
                st.exception(e)

    creditos = safe_obtener_creditos(st.session_state["user"]["id"]) or []
    if creditos:
        for c in creditos:
            cuotas_pagadas = to_int(c.get("cuotas_pagadas", 0))
            texto = f"🏦 {c.get('nombre')} — Monto ${to_float(c.get('monto',0)):,.2f} | Plazo {to_int(c.get('plazo',0))} meses | Cuota ${to_float(c.get('cuota',0)):,.2f} | Pagadas {cuotas_pagadas}"
            st.write(texto)

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
        st.info("Sin historial por ahora.")

# ============================
# 5) Metas
# ============================
with tabs[4]:
    st.header("🎯 Metas de ahorro")

    with st.form("form_meta"):
        nombre_meta = st.text_input("Nombre de la meta")
        monto_objetivo = st.number_input("Monto objetivo", min_value=0.0, step=10000.0)
        ahorrado_inicial = st.number_input("Ahorrado inicial", min_value=0.0, step=10000.0, value=0.0)
        submitted_meta = st.form_submit_button("Guardar meta")
        if submitted_meta:
            if nombre_meta and monto_objetivo > 0:
                try:
                    insertar_meta(st.session_state["user"]["id"], nombre_meta, float(monto_objetivo), float(ahorrado_inicial))
                    st.success("Meta guardada ✅")
                    st.rerun()
                except Exception as e:
                    st.error("Error al guardar meta")
                    st.exception(e)
            else:
                st.warning("Completa nombre y monto objetivo mayor a 0.")

    metas = safe_obtener_metas(st.session_state["user"]["id"]) or []
    if metas:
        for m in metas:
            nombre = m.get("nombre", "Meta")
            objetivo = to_float(m.get("monto", 0))
            ahorrado = to_float(m.get("ahorrado", 0))
            progreso = 0 if objetivo <= 0 else min(int((ahorrado / objetivo) * 100), 100)

            st.markdown(f"**{nombre}** — Objetivo: ${objetivo:,.2f} | Ahorrado: ${ahorrado:,.2f} | Progreso: {progreso}%")
            st.progress(progreso)

            # Actualizar ahorro rápido
            with st.expander(f"Actualizar {nombre}"):
                nuevo_ahorro = st.number_input(f"Nuevo valor ahorrado para '{nombre}'", min_value=0.0, step=10000.0, value=ahorrado, key=f"ah_{m.get('id')}")
                colu1, colu2 = st.columns(2)
                if colu1.button("💾 Guardar actualización", key=f"upd_{m.get('id')}"):
                    try:
                        update_meta(m.get("id"), {"ahorrado": float(nuevo_ahorro)})
                        st.success("Meta actualizada ✅")
                        st.rerun()
                    except Exception as e:
                        st.error("No se pudo actualizar la meta")
                        st.exception(e)
                if colu2.button("🗑️ Borrar meta", key=f"del_{m.get('id')}"):
                    try:
                        borrar_meta(m.get("id"))
                        st.success("Meta eliminada ✅")
                        st.rerun()
                    except Exception as e:
                        st.error("No se pudo borrar la meta")
                        st.exception(e)
    else:
        st.info("Aún no tienes metas. Crea la primera arriba.")

# ============================
# 6) Configuración
# ============================
with tabs[5]:
    st.header("⚙️ Configuración")
    st.write("Opciones sugeridas:")
    st.markdown("""
- **Asistente financiero (IA):** recomendaciones de ahorro/gasto según tus hábitos.
- **Alertas y recordatorios:** límites de gasto por categoría y recordatorio de pago de créditos.
- **Personalización:** moneda, formato numérico, tema visual.
- **Exportación/Importación:** CSV/Excel.
- **Predicción simple de flujo de caja:** media móvil o regresión lineal de gastos/ingresos.
""")
    st.info("Estas funciones se pueden activar gradualmente. Si quieres, en el siguiente paso te agrego un pequeño asistente de reglas y alertas.")
