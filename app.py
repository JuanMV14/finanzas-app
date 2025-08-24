import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from queries import registrar_pago, update_credito, insertar_transaccion, insertar_credito, borrar_transaccion, obtener_transacciones, obtener_creditos
from utils import login, signup, logout
from datetime import date

# Cargar variables de entorno
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    tabs = st.tabs(["Transacciones", "Créditos", "Historial"])

# ==============================
# TAB 1: TRANSACCIONES
# ==============================
with tabs[0]:
    st.header("📊 Transacciones")

    tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Crédito"])

    categorias = {
        "Ingreso": ["Salario", "Comisiones", "Ventas", "Otros"],
        "Gasto": ["Comida", "Gasolina", "Pago TC", "Servicios Públicos", "Ocio", "Entretenimiento", "Otros"],
        "Crédito": ["Otros"]
    }

    categoria_seleccionada = st.selectbox("Categoría", categorias[tipo])
    categoria_personalizada = ""
    if categoria_seleccionada == "Otros":
        categoria_personalizada = st.text_input("Especifica la categoría")

    categoria_final = categoria_personalizada if categoria_seleccionada == "Otros" else categoria_seleccionada

    with st.form("nueva_transaccion"):
        monto = st.number_input("Monto", min_value=0.01)
        fecha = st.date_input("Fecha")
        submitted = st.form_submit_button("Guardar")

        if submitted:
            resp = insertar_transaccion(
                st.session_state["user"]["id"], tipo, categoria_final, monto, fecha
            )
            if resp.data:
                st.success("Transacción guardada ✅")
                st.rerun()
            else:
                st.error("Error al guardar la transacción")

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
        if creditos:
            st.subheader("Tus créditos")
            for credito in creditos:
                st.markdown(f"### 💳 {credito['nombre']}")

                monto_total = float(credito["monto"])
                cuotas_pagadas = int(credito["cuotas_pagadas"])
                plazo_meses = int(credito["plazo_meses"])
                cuota_mensual = float(credito["cuota_mensual"])

                monto_pagado = cuotas_pagadas * cuota_mensual
                monto_restante = monto_total - monto_pagado
                progreso = cuotas_pagadas / plazo_meses

                st.progress(progreso)

                col1, col2, col3 = st.columns(3)
                col1.metric("📅 Cuotas pagadas", f"{cuotas_pagadas} / {plazo_meses}")
                col2.metric("💰 Monto pagado", f"${monto_pagado:,.2f}")
                col3.metric("🧾 Monto restante", f"${monto_restante:,.2f}")

                st.write(f"💵 Monto total del crédito: ${monto_total:,.2f}")
                st.write(f"💸 Cuota mensual: ${cuota_mensual:,.2f}")

                if st.button(f"Registrar pago {credito['nombre']}", key=credito["id"]):
                    if cuotas_pagadas < plazo_meses:
                        update_credito(
                            credito["id"],
                            {"cuotas_pagadas": cuotas_pagadas + 1}
                        )
                        insertar_transaccion(
                            st.session_state["user"]["id"],
                            "Crédito",
                            credito["nombre"],
                            cuota_mensual,
                            date.today()
                        )
                        st.success("✅ Pago registrado")
                        st.experimental_rerun()
                    else:
                        st.warning("⚠️ Este crédito ya está totalmente pagado.")
        else:
            st.info("No tienes créditos registrados.")

# ==============================
# TAB 3: HISTORIAL COMPLETO
# ==============================
with tabs[2]:
    st.header("📜 Historial completo de transacciones")

    trans_all = obtener_transacciones(st.session_state["user"]["id"])
    if trans_all:
        for t in trans_all:
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.write(t["tipo"])
            col2.write(t["categoria"])
            col3.write(t["monto"])
            col4.write(t["fecha"])
            if col5.button("🗑️", key=f"hist_{t['id']}"):
                borrar_transaccion(st.session_state["user"]["id"], t["id"])
                st.rerun()
    else:
        st.info("No hay transacciones registradas.")
