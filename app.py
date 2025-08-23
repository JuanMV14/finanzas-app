import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from queries import registrar_pago
from queries import update_credito

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Importar funciones separadas
from queries import (
    insertar_transaccion,
    insertar_credito,
    borrar_transaccion,
    obtener_transacciones,
    obtener_creditos,
)
from utils import login, signup, logout

# Configuración inicial
st.set_page_config(page_title="Finanzas Personales", layout="wide")

# Inicializar estado de sesión
if "user" not in st.session_state:
    st.session_state["user"] = None

# Sidebar
st.sidebar.title("Menú")

if st.session_state["user"] is None:
    menu = st.sidebar.radio("Selecciona una opción:", ["Login", "Registro"])
    if menu == "Login":
        st.subheader("Iniciar Sesión")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            login(supabase, email, password)

    elif menu == "Registro":
        st.subheader("Crear Cuenta")
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        if st.button("Registrarse"):
            signup(supabase, email, password)

else:
    st.sidebar.write(f"👤 {st.session_state['user']['email']}")
    if st.sidebar.button("Cerrar Sesión"):
        logout(supabase)

    # Contenido principal
    tabs = st.tabs(["Transacciones", "Créditos"])

    # ==============================
    # TAB 1: TRANSACCIONES
    # ==============================
    with tabs[0]:
        st.header("📊 Transacciones")

        with st.form("nueva_transaccion"):
            tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])
            categoria = st.text_input("Categoría")
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

        trans = obtener_transacciones(st.session_state["user"]["id"])
        if trans:
            st.subheader("Tus transacciones")
            for t in trans:
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.write(t["tipo"])
                col2.write(t["categoria"])
                col3.write(t["monto"])
                col4.write(t["fecha"])
                if col5.button("🗑️", key=t["id"]):
                    borrar_transaccion(st.session_state["user"]["id"], t["id"])
                    st.rerun()
        else:
            st.info("No tienes transacciones registradas.")

    # ==============================
    # TAB 2: CRÉDITOS
    # ==============================
    with tabs[1]:
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
                resp = insertar_credito(
                    st.session_state["user"]["id"],
                    nombre,
                    monto,
                    tasa,
                    plazo_meses,
                    cuotas_pagadas,
                    cuota_mensual,
                )
                if resp.data:
                    st.success("Crédito guardado ✅")
                    st.rerun()
                else:
                    st.error("Error al guardar el crédito")

        creditos = obtener_creditos(st.session_state["user"]["id"])
        #if creditos:
            #st.subheader("Tus créditos")
            #for c in creditos:
                #st.write(f"📌 {c['nombre']} - {c['monto']} - {c['plazo_meses']} meses")
        else:
            st.info("No tienes créditos registrados.")
def mostrar_credito(supabase, credito):
    st.subheader(f"💳 {credito['nombre']}")
    
    progreso = credito['cuotas_pagadas'] / credito['plazo_meses']
    st.progress(progreso)

    st.write(f"📊 Pagadas: {credito['cuotas_pagadas']} de {credito['plazo_meses']}")
    st.write(f"📅 Faltan: {credito['plazo_meses'] - credito['cuotas_pagadas']} meses")
    st.write(f"💰 Cuota mensual: {credito['cuota_mensual']:.2f}")

    if st.button(f"Registrar pago ➕", key=credito['id']):
        registrar_pago(supabase, credito['id'])
        st.success("✅ Pago registrado correctamente")
        st.experimental_rerun()  # refresca la pantalla para ver el cambio

for credito in creditos:
    st.write(f"📌 {credito['nombre']} - {credito['monto']} - {credito['plazo_meses']} meses")

    # Barra de progreso
    progreso = credito["cuotas_pagadas"] / credito["plazo_meses"]
    st.progress(progreso)

    # Botón para registrar pago
    if st.button(f"Registrar pago {credito['nombre']}", key=credito["id"]):
        if credito["cuotas_pagadas"] < credito["plazo_meses"]:
            update_credito(
                credito["id"],
                {"cuotas_pagadas": credito["cuotas_pagadas"] + 1}
            )
            st.success("✅ Pago registrado")
            st.experimental_rerun()
        else:
            st.warning("⚠️ Este crédito ya está totalmente pagado.")
