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
tabs = st.tabs(["📊 Dashboard", "💸 Transacciones", "💳 Créditos"])

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
            resp = insertar_transaccion(
                st.session_state["user"]["id"], tipo, categoria, monto, fecha
            )
            if resp.data:
                st.success("Transacción guardada ✅")
                st.rerun()
            else:
                st.error("Error al guardar la transacción")

    # Mostrar transacciones
    trans = obtener_transacciones(st.session_state["user"]["id"])
    if trans:
        st.subheader("Historial de transacciones")
        st.dataframe(trans)  # Tabla bonita con todo
    else:
        st.info("No tienes transacciones registradas.")

    # Gráfico histórico mejorado
    if trans:
        import pandas as pd
        import plotly.express as px

        df = pd.DataFrame(trans)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["mes"] = df["fecha"].dt.to_period("M").astype(str)

        resumen = df.groupby(["mes", "tipo"])["monto"].sum().reset_index()

        fig = px.line(resumen, x="mes", y="monto", color="tipo", markers=True,
                      title="Evolución de Ingresos y Gastos")
        st.plotly_chart(fig, use_container_width=True)


# ==============================
# TAB 3: METAS DE AHORRO
# ==============================
with st.tabs[2]:
    st.header("🎯 Metas de ahorro")

    # Formulario para nueva meta
    with st.form("nueva_meta"):
        nombre = st.text_input("Nombre de la meta")
        monto = st.number_input("Monto objetivo", min_value=0.01)
        ahorrado = st.number_input("Monto ahorrado inicial", min_value=0.0)
        submitted = st.form_submit_button("Guardar meta")
        if submitted:
            supabase.table("metas").insert({
                "user_id": st.session_state["user"]["id"],
                "nombre": nombre,
                "monto": monto,
                "ahorrado": ahorrado
            }).execute()
            st.success("Meta guardada ✅")
            st.rerun()

    # Mostrar metas existentes
    metas = supabase.table("metas").select("*").eq("user_id", st.session_state["user"]["id"]).execute().data
    if metas:
        for m in metas:
            st.subheader(f"🎯 {m['nombre']}")
            progreso = m["ahorrado"] / m["monto"]
            st.progress(progreso)
            st.write(f"💰 Ahorrado: {m['ahorrado']} / {m['monto']}")

            # Botón para aumentar ahorro
            extra = st.number_input(f"Agregar ahorro a {m['nombre']}", min_value=0.0, key=f"extra_{m['id']}")
            if st.button(f"➕ Aumentar ahorro {m['nombre']}", key=f"btn_{m['id']}"):
                nuevo = m["ahorrado"] + extra
                supabase.table("metas").update({"ahorrado": nuevo}).eq("id", m["id"]).execute()
                st.success("✅ Ahorro actualizado")
                st.rerun()
    else:
        st.info("No tienes metas registradas.")
