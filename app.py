import streamlit as st
import pandas as pd
import plotly.graph_objs as go
from datetime import date
from queries import (
    insertar_transaccion,
    insertar_credito,
    borrar_transaccion,
    obtener_transacciones,
    obtener_creditos,
    registrar_pago,
    update_credito,
    insertar_meta,
    obtener_metas,
    actualizar_meta
)
from utils import login, signup, logout

# -------------------------
# CONFIG STREAMLIT
# -------------------------
st.set_page_config(page_title="💰 Finanzas Personales", layout="wide")

# -------------------------
# SESIÓN
# -------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.title("🔐 Usuario")

if st.session_state["user"] is None:
    menu = st.sidebar.radio("Selecciona una opción:", ["Login", "Registro"])
    if menu == "Login":
        email = st.sidebar.text_input("Correo electrónico")
        password = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Ingresar"):
            login(email, password)

    elif menu == "Registro":
        email = st.sidebar.text_input("Correo electrónico")
        password = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Registrarse"):
            signup(email, password)

else:
    st.sidebar.success(f"Conectado: {st.session_state['user']['email']}")
    if st.sidebar.button("Cerrar sesión"):
        logout()

# -------------------------
# APP PRINCIPAL
# -------------------------
if not st.session_state["user"]:
    st.info("Inicia sesión para ver tu panel financiero.")
    st.stop()

user = st.session_state["user"]
user_id = user["id"]

# ==============================
# TABS
# ==============================
tabs = st.tabs(["📊 Dashboard", "💸 Transacciones", "💳 Créditos", "🎯 Metas de ahorro"])

# ==============================
# TAB 1: DASHBOARD
# ==============================
with tabs[0]:
    st.header("📊 Dashboard Financiero")

    transacciones = obtener_transacciones(user_id)
    creditos = obtener_creditos(user_id)

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

        # Gráfico de ingresos vs gastos
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["periodo"] = df["fecha"].dt.to_period("M").astype(str)
        resumen = df.groupby(["periodo", "tipo"])["monto"].sum().reset_index()

        fig = go.Figure()
        for tipo in ["Ingreso", "Gasto"]:
            subset = resumen[resumen["tipo"] == tipo]
            if not subset.empty:
                fig.add_trace(go.Bar(x=subset["periodo"], y=subset["monto"], name=tipo))

        fig.update_layout(
            barmode="group",
            title="Ingresos vs Gastos por Mes",
            xaxis_title="Periodo",
            yaxis_title="Monto"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No hay transacciones aún.")

# ==============================
# TAB 2: TRANSACCIONES
# ==============================
with tabs[1]:
    st.header("📊 Transacciones")

    with st.form("nueva_transaccion"):
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])

        # Categorías dinámicas según tipo
        if tipo == "Ingreso":
            categorias = ["Sueldo", "Préstamo", "Comisión", "Otros"]
        else:
            categorias = ["Comida", "Ocio", "Gasolina", "Servicios Públicos", 
                          "Entretenimiento", "Pago Crédito", "Pago TC", "Otros"]

        categoria = st.selectbox("Categoría", categorias)

        # Campo extra si selecciona "Otros"
        if categoria == "Otros":
            categoria = st.text_input("Especifica la categoría")

        monto = st.number_input("Monto", min_value=0.01)
        fecha = st.date_input("Fecha")

        submitted = st.form_submit_button("Guardar")
        if submitted:
            resp = insertar_transaccion(user_id, tipo, categoria, monto, fecha)
            if resp.data:
                st.success("Transacción guardada ✅")
                st.rerun()
            else:
                st.error("Error al guardar la transacción")

    # Mostrar transacciones
    trans = obtener_transacciones(user_id)
    if trans:
        st.subheader("Historial de transacciones")
        st.dataframe(trans)
    else:
        st.info("No tienes transacciones registradas.")

# ==============================
# TAB 3: CRÉDITOS
# ==============================
with tabs[2]:
    st.header("💳 Créditos")

    with st.form("nuevo_credito"):
        nombre = st.text_input("Nombre del crédito")
        monto = st.number_input("Monto", min_value=0.01)
        tasa = st.number_input("Tasa de interés (%)", min_value=0.0)
        plazo_meses = st.number_input("Plazo (meses)", min_value=1, step=1)
        cuotas_pagadas = st.number_input("Cuotas pagadas", min_value=0, step=1)
        cuota_mensual = st.number_input("Cuota mensual", min_value=0.01)
        submitted = st.form_submit_button("Guardar crédito")
        if submitted:
            resp = insertar_credito(user_id, nombre, monto, tasa, plazo_meses, cuotas_pagadas, cuota_mensual)
            if resp.data:
                st.success("Crédito guardado ✅")
                st.rerun()
            else:
                st.error("Error al guardar el crédito")

    creditos = obtener_creditos(user_id)
    if creditos:
        for c in creditos:
            st.subheader(f"📌 {c['nombre']}")
            progreso = c["cuotas_pagadas"] / c["plazo_meses"]
            st.progress(progreso)
            st.write(f"Pagadas: {c['cuotas_pagadas']} / {c['plazo_meses']}")
            st.write(f"💰 Cuota mensual: {c['cuota_mensual']:.2f}")

            if st.button(f"Registrar pago ➕", key=c['id']):
                registrar_pago(c['id'])
                st.success("✅ Pago registrado correctamente")
                st.rerun()
    else:
        st.info("No tienes créditos registrados.")

# ==============================
# TAB 4: METAS DE AHORRO
# ==============================
with tabs[3]:
    st.header("🎯 Metas de ahorro")

    with st.form("nueva_meta"):
        nombre = st.text_input("Nombre de la meta")
        monto = st.number_input("Monto objetivo", min_value=0.01)
        ahorrado = st.number_input("Monto ahorrado inicial", min_value=0.0)
        submitted = st.form_submit_button("Guardar meta")
        if submitted:
            insertar_meta(user_id, nombre, monto, ahorrado)
            st.success("Meta guardada ✅")
            st.rerun()

    metas = obtener_metas(user_id)
    if metas:
        for m in metas:
            st.subheader(f"🎯 {m['nombre']}")
            progreso = m["ahorrado"] / m["monto"]
            st.progress(progreso)
            st.write(f"💰 Ahorrado: {m['ahorrado']} / {m['monto']}")

            extra = st.number_input(f"Agregar ahorro a {m['nombre']}", min_value=0.0, key=f"extra_{m['id']}")
            if st.button(f"➕ Aumentar ahorro {m['nombre']}", key=f"btn_{m['id']}"):
                actualizar_meta(m["id"], m["ahorrado"] + extra)
                st.success("✅ Ahorro actualizado")
                st.rerun()
    else:
        st.info("No tienes metas registradas.")
