import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from queries import (
    registrar_pago, update_credito, insertar_transaccion,
    insertar_credito, borrar_transaccion, obtener_transacciones, obtener_creditos
)
from utils import login, signup, logout
from datetime import date

# Cargar variables de entorno
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Gestor Financiero", layout="wide")

# ==============================
# AUTENTICACIÓN
# ==============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
    with tab1:
        email = st.text_input("Correo electrónico", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar"):
            if login(supabase, email, password):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

    with tab2:
        email = st.text_input("Correo electrónico", key="signup_email")
        password = st.text_input("Contraseña", type="password", key="signup_pass")
        if st.button("Registrarse"):
            if signup(supabase, email, password):
                st.success("Usuario registrado. Inicia sesión.")
            else:
                st.error("Error al registrar usuario")
else:
    st.sidebar.title("Menú")
    page = st.sidebar.radio("Ir a:", ["Transacciones", "Créditos", "Cerrar Sesión"])

    if page == "Cerrar Sesión":
        logout()
        st.session_state.logged_in = False
        st.rerun()

    # ==============================
    # TRANSACCIONES
    # ==============================
    if page == "Transacciones":
        st.title("Gestión de Transacciones")

        with st.form("transaccion_form"):
            descripcion = st.text_input("Descripción")
            monto = st.number_input("Monto", min_value=0.0, format="%.2f")
            fecha = st.date_input("Fecha", value=date.today())
            categoria = st.selectbox("Categoría", ["Ingreso", "Gasto", "Ahorro"])
            submitted = st.form_submit_button("Agregar Transacción")
            if submitted:
                insertar_transaccion(supabase, descripcion, monto, str(fecha), categoria)
                st.success("Transacción agregada correctamente")
                st.rerun()

        st.subheader("Historial de transacciones")
        transacciones = obtener_transacciones(supabase)

        if transacciones:
            for transaccion in transacciones:
                with st.expander(f"{transaccion['descripcion']} - {transaccion['monto']}"):
                    st.write(f"Fecha: {transaccion['fecha']}")
                    st.write(f"Categoría: {transaccion['categoria']}")

                    new_desc = st.text_input(
                        "Editar descripción", value=transaccion["descripcion"], key=f"desc_{transaccion['id']}"
                    )
                    new_monto = st.number_input(
                        "Editar monto", min_value=0.0, value=float(transaccion["monto"]), key=f"monto_{transaccion['id']}"
                    )
                    new_fecha = st.date_input(
                        "Editar fecha", value=date.fromisoformat(transaccion["fecha"]), key=f"fecha_{transaccion['id']}"
                    )
                    # 🔥 CORRECCIÓN: forzar el valor actual como "index" de la lista
                    categorias = ["Ingreso", "Gasto", "Ahorro"]
                    new_categoria = st.selectbox(
                        "Editar categoría",
                        categorias,
                        index=categorias.index(transaccion["categoria"]),
                        key=f"cat_{transaccion['id']}"
                    )

                    if st.button("Guardar cambios", key=f"guardar_{transaccion['id']}"):
                        update_credito(
                            supabase,
                            transaccion["id"],
                            new_desc,
                            new_monto,
                            str(new_fecha),
                            new_categoria  # 🔥 Ahora sí se guarda el cambio en categoría
                        )
                        st.success("Transacción actualizada")
                        st.rerun()

                    if st.button("Eliminar", key=f"eliminar_{transaccion['id']}"):
                        borrar_transaccion(supabase, transaccion["id"])
                        st.warning("Transacción eliminada")
                        st.rerun()
        else:
            st.info("No hay transacciones registradas.")

    # ==============================
    # CRÉDITOS
    # ==============================
    if page == "Créditos":
        st.title("Gestión de Créditos")

        with st.form("credito_form"):
            nombre = st.text_input("Nombre del crédito")
            deuda_total = st.number_input("Deuda total", min_value=0.0, format="%.2f")
            cuota_mensual = st.number_input("Cuota mensual", min_value=0.0, format="%.2f")
            fecha_pago = st.date_input("Fecha de pago", value=date.today())
            submitted = st.form_submit_button("Agregar Crédito")
            if submitted:
                insertar_credito(supabase, nombre, deuda_total, cuota_mensual, str(fecha_pago))
                st.success("Crédito agregado correctamente")
                st.rerun()

        st.subheader("Lista de créditos")
        creditos = obtener_creditos(supabase)

        if creditos:
            for credito in creditos:
                with st.expander(f"{credito['nombre']} - Deuda: {credito['deuda_total']}"):
                    st.write(f"Cuota mensual: {credito['cuota_mensual']}")
                    st.write(f"Fecha de pago: {credito['fecha_pago']}")

                    pago = st.number_input("Monto del pago", min_value=0.0, format="%.2f", key=f"pago_{credito['id']}")
                    if st.button("Registrar pago", key=f"registrar_{credito['id']}"):
                        registrar_pago(supabase, credito["id"], pago)
                        st.success("Pago registrado correctamente")
                        st.rerun()
        else:
            st.info("No hay créditos registrados.")
