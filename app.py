import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from queries import registrar_pago, update_credito, insertar_transaccion, insertar_credito, borrar_transaccion, obtener_transacciones, obtener_creditos
from utils import login, signup, logout
from datetime import date
from collections import defaultdict

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

    # Definir pestañas
    tabs = st.tabs(["Transacciones", "Créditos", "Historial"])

    # Función para borrar transacción y ajustar crédito si aplica
    def borrar_transaccion_y_ajustar_credito(user_id, transaccion):
        borrar_transaccion(user_id, transaccion["id"])
        if transaccion["tipo"] == "Crédito":
            creditos = obtener_creditos(user_id)
            for credito in creditos:
                if credito["nombre"] == transaccion["categoria"]:
                    cuotas_actuales = int(credito["cuotas_pagadas"])
                    if cuotas_actuales > 0:
                        update_credito(credito["id"], {"cuotas_pagadas": cuotas_actuales - 1})
                    break

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

        # 🔍 Visualización de resumen por categoría y tipo
        trans = obtener_transacciones(st.session_state["user"]["id"])

        if trans:
            st.subheader("📊 Resumen por categoría y tipo")

            resumen = defaultdict(float)
            for t in trans:
                clave = (t["tipo"], t["categoria"])
                resumen[clave] += float(t["monto"])

            total_ingresos = sum(monto for (tipo, _), monto in resumen.items() if tipo == "Ingreso")
            total_gastos = sum(monto for (tipo, _), monto in resumen.items() if tipo == "Gasto")
            total_creditos = sum(monto for (tipo, _), monto in resumen.items() if tipo == "Crédito")
            total_general = total_ingresos + total_gastos + total_creditos

            porcentaje_ingresos = total_ingresos / total_general if total_general > 0 else 0
            porcentaje_gastos = total_gastos / total_general if total_general > 0 else 0
            porcentaje_creditos = total_creditos / total_general if total_general > 0 else 0

            colores = {
                "Ingreso": "#4CAF50",
                "Gasto": "#F44336",
                "Crédito": "#2196F3"
            }

            # 🔷 Encabezado con barra progresiva
            st.markdown("### Resumen financiero")
            st.markdown(
                f"""
                <div style="display:flex;height:40px;border-radius:8px;overflow:hidden;margin-bottom:16px;">
                    <div style="width:{porcentaje_ingresos*100:.2f}%;background-color:{colores['Ingreso']};text-align:center;color:black;line-height:40px;">
                        Ingresos: ${total_ingresos:,.2f}
                    </div>
                    <div style="width:{porcentaje_gastos*100:.2f}%;background-color:{colores['Gasto']};text-align:center;color:black;line-height:40px;">
                        Gastos: ${total_gastos:,.2f}
                    </div>
                    <div style="width:{porcentaje_creditos*100:.2f}%;background-color:{colores['Crédito']};text-align:center;color:black;line-height:40px;">
                        Créditos: ${total_creditos:,.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 🔸 Barras por categoría
            for (tipo, categoria), monto in resumen.items():
                porcentaje = monto / total_general if total_general > 0 else 0
                st.markdown(f"**{categoria}** ({tipo})")
                st.markdown(
                    f"""
                    <div style="background-color:#eee;border-radius:8px;margin-bottom:8px;">
                        <div style="width:{porcentaje*100:.2f}%;background-color:{colores[tipo]};padding:6px 0;border-radius:8px;text-align:center;color:black;">
                            ${monto:,.2f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No hay transacciones registradas.")

# ==============================
# TAB 2: CRÉDITOS
# ==============================
with tabs[1]:
    st.header("💳 Créditos")

    creditos = obtener_creditos(st.session_state["user"]["id"])

    if creditos:
        for credito in creditos:
            st.subheader(f"🏦 {credito['nombre']}")

            monto = float(credito["monto"])
            plazo_meses = int(credito["plazo_meses"])
            tasa_anual = float(
                credito.get("tasa") or credito.get("Tasa de interés anual (%)") or 0
            )
            cuotas_pagadas = int(credito["cuotas_pagadas"])

            # ✅ Conversión EA → tasa efectiva mensual
            tasa_mensual = (1 + tasa_anual / 100) ** (1 / 12) - 1 if tasa_anual > 0 else 0

            # ======================
            # Validaciones especiales
            # ======================
            if plazo_meses <= 0:
                cuota = 0
                saldo_restante = monto
            elif tasa_mensual == 0:
                # Crédito sin intereses → cuota simple
                cuota = monto / plazo_meses
                saldo_restante = max(0, monto - (cuotas_pagadas * cuota))
            else:
                # Fórmula sistema francés (cuota fija)
                cuota = monto * (tasa_mensual / (1 - (1 + tasa_mensual) ** (-plazo_meses)))
                saldo_restante = monto * (
                    (1 + tasa_mensual) ** plazo_meses - (1 + tasa_mensual) ** cuotas_pagadas
                ) / ((1 + tasa_mensual) ** plazo_meses - 1)

            # ======================
            # Mostrar información
            # ======================
            st.write(f"💰 Monto del crédito: ${monto:,.0f}")
            st.write(f"📅 Plazo: {plazo_meses} meses")
            st.write(f"📈 Tasa anual: {tasa_anual:.2f}%")
            st.write(f"💳 Cuota mensual: ${cuota:,.2f}")
            st.write(f"📉 Saldo restante: ${saldo_restante:,.2f}")
            st.write(f"✅ Cuotas pagadas: {cuotas_pagadas}")
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
