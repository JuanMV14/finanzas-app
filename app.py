import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from queries import registrar_pago, update_credito, insertar_transaccion, insertar_credito, borrar_transaccion, obtener_transacciones, obtener_creditos
from utils import login, signup, logout
from datetime import date
from collections import defaultdict

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finanzas Personales", layout="wide")

if "user" not in st.session_state:
    st.session_state["user"] = None

# ==============================
# SIDEBAR
# ==============================
st.sidebar.title("Menú")

if st.session_state["user"] is None:
    menu = st.sidebar.radio("Selecciona una opción:", ["Login", "Registro"], key="menu_auth")
    if menu == "Login":
        st.subheader("Iniciar Sesión")
        email = st.text_input("Correo electrónico", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        if st.button("Ingresar", key="btn_login"):
            login(supabase, email, password)

    elif menu == "Registro":
        st.subheader("Crear Cuenta")
        email = st.text_input("Correo electrónico", key="signup_email")
        password = st.text_input("Contraseña", type="password", key="signup_password")
        if st.button("Registrarse", key="btn_signup"):
            signup(supabase, email, password)

else:
    st.sidebar.write(f"👤 {st.session_state['user']['email']}")
    if st.sidebar.button("Cerrar Sesión", key="btn_logout"):
        logout(supabase)

    # Definir pestañas
    tabs = st.tabs(["Transacciones", "Créditos", "Historial"])

    # ==============================
    # FUNCIÓN: BORRAR TRANSACCIÓN Y AJUSTAR CRÉDITO
    # ==============================
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

        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Crédito"], key="tipo_transaccion")

        categorias = {
            "Ingreso": ["Salario", "Comisiones", "Ventas", "Otros"],
            "Gasto": ["Comida", "Gasolina", "Pago TC", "Servicios Públicos", "Ocio", "Entretenimiento", "Otros"],
            "Crédito": ["Otros"]
        }

        categoria_seleccionada = st.selectbox("Categoría", categorias[tipo], key="categoria_transaccion")
        categoria_personalizada = ""
        if categoria_seleccionada == "Otros":
            categoria_personalizada = st.text_input("Especifica la categoría", key="categoria_custom")

        categoria_final = categoria_personalizada if categoria_seleccionada == "Otros" else categoria_seleccionada

        with st.form("nueva_transaccion", clear_on_submit=True):
            monto = st.number_input("Monto", min_value=0.01, step=1000.0, format="%.2f", key="monto_transaccion")
            fecha = st.date_input("Fecha", value=date.today(), key="fecha_transaccion")
            submitted = st.form_submit_button("Guardar", key="guardar_transaccion")

            if submitted:
                resp = insertar_transaccion(
                    st.session_state["user"]["id"], tipo, categoria_final, monto, fecha
                )
                if resp.data:
                    st.success("✅ Transacción guardada")
                    st.rerun()
                else:
                    st.error("❌ Error al guardar la transacción")

        # Mostrar resumen
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

            colores = {"Ingreso": "#4CAF50", "Gasto": "#F44336", "Crédito": "#2196F3"}

            # Barra principal
            st.markdown("### Resumen financiero")
            st.markdown(
                f"""
                <div style="display:flex;height:40px;border-radius:8px;overflow:hidden;margin-bottom:16px;">
                    <div style="width:{(total_ingresos/total_general*100) if total_general else 0:.2f}%;
                                background-color:{colores['Ingreso']};
                                text-align:center;color:black;line-height:40px;">
                        Ingresos: ${total_ingresos:,.2f}
                    </div>
                    <div style="width:{(total_gastos/total_general*100) if total_general else 0:.2f}%;
                                background-color:{colores['Gasto']};
                                text-align:center;color:black;line-height:40px;">
                        Gastos: ${total_gastos:,.2f}
                    </div>
                    <div style="width:{(total_creditos/total_general*100) if total_general else 0:.2f}%;
                                background-color:{colores['Crédito']};
                                text-align:center;color:black;line-height:40px;">
                        Créditos: ${total_creditos:,.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Barras por categoría
            for (tipo, categoria), monto in resumen.items():
                porcentaje = monto / total_general if total_general > 0 else 0
                st.markdown(f"**{categoria}** ({tipo})")
                st.markdown(
                    f"""
                    <div style="background-color:#eee;border-radius:8px;margin-bottom:8px;">
                        <div style="width:{porcentaje*100:.2f}%;background-color:{colores[tipo]};
                                    padding:6px 0;border-radius:8px;text-align:center;color:black;">
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

        with st.expander("➕ Registrar nuevo crédito"):
            with st.form("form_credito", clear_on_submit=True):
                nombre = st.text_input("Nombre del crédito", placeholder="Bancolombia / Visa / etc.", key="nombre_credito")
                monto = st.number_input("Monto del crédito", min_value=0.0, step=1000.0, format="%.2f", key="monto_credito")
                plazo_meses = st.number_input("Plazo (meses)", min_value=1, step=1, key="plazo_credito")
                tasa_anual = st.number_input("Tasa efectiva anual (EA) %", min_value=0.0, step=0.01, format="%.2f", key="tasa_credito")
                cuota_mensual = st.number_input("Cuota mensual real", min_value=0.0, step=1000.0, format="%.2f", key="cuota_credito")
                submitted_credito = st.form_submit_button("Guardar crédito", key="guardar_credito")

                if submitted_credito:
                    try:
                        resp = insertar_credito(
                            st.session_state["user"]["id"], nombre, monto, plazo_meses, tasa_anual, cuota_mensual
                        )
                    except TypeError:
                        payload = {
                            "nombre": nombre,
                            "monto": monto,
                            "plazo_meses": plazo_meses,
                            "tasa_interes": tasa_anual,
                            "cuota_mensual": cuota_mensual,
                            "cuotas_pagadas": 0
                        }
                        resp = insertar_credito(st.session_state["user"]["id"], payload)

                    if getattr(resp, "data", None) is not None or resp:
                        st.success("✅ Crédito guardado")
                        st.rerun()
                    else:
                        st.error("❌ No se pudo guardar el crédito")

        creditos = obtener_creditos(st.session_state["user"]["id"])

        def calcular_saldo_insoluto(cuota, tasa_anual, plazo_total, cuotas_pagadas):
            tasa_mensual = (1 + tasa_anual / 100) ** (1 / 12) - 1 if tasa_anual > 0 else 0.0
            n_restantes = plazo_total - cuotas_pagadas
            if n_restantes <= 0:
                return 0.0
            if tasa_mensual == 0:
                return max(0.0, cuota * n_restantes)
            saldo = cuota * (1 - (1 + tasa_mensual) ** (-n_restantes)) / tasa_mensual
            return round(saldo, 2)

        if creditos:
            for credito in creditos:
                nombre = str(credito.get("nombre", "Sin nombre"))
                monto = float(credito.get("monto", 0) or 0)
                plazo_meses = int(credito.get("plazo_meses", 0) or 0)
                tasa_anual = float(credito.get("tasa_interes") or 0)
                cuota_mensual = float(credito.get("cuota_mensual") or 0)
                cuotas_pagadas = int(credito.get("cuotas_pagadas", 0) or 0)

                progreso = (cuotas_pagadas / plazo_meses) if plazo_meses > 0 else 0.0
                saldo_restante = calcular_saldo_insoluto(cuota_mensual, tasa_anual, plazo_meses, cuotas_pagadas)

                st.subheader(f"🏦 {nombre}")

                # Barra progreso
                st.markdown(
                    f"""
                    <div style="background:#eee;border-radius:10px;overflow:hidden;height:22px;margin:6px 0 12px 0;">
                        <div style="width:{progreso*100:.2f}%;
                                    background:#2196F3;
                                    height:22px;
                                    display:flex;
                                    align-items:center;
                                    justify-content:center;
                                    color:white;
                                    font-size:12px;">
                            {cuotas_pagadas}/{plazo_meses} cuotas ({progreso*100:.1f}%)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2, col3, col4 = st.columns(4)
                col1.write(f"💰 **Monto**: ${monto:,.2f}")
                col2.write(f"📅 **Plazo**: {plazo_meses} meses")
                col3.write(f"📈 **Tasa EA**: {tasa_anual:.2f}%")
                col4.write(f"✅ **Cuotas pagadas**: {cuotas_pagadas}")

                col5, col6 = st.columns(2)
                col5.write(f"💳 **Cuota mensual (real)**: ${cuota_mensual:,.2f}")
                col6.write(f"📉 **Saldo restante (estimado)**: ${saldo_restante:,.2f}")

                # Botón registrar pago
                if st.button("Registrar pago", key=f"pago_{credito['id']}"):
                    # Registrar como transacción
                    resp = insertar_transaccion(
                        st.session_state["user"]["id"], "Gasto", nombre, cuota_mensual, date.today()
                    )
                    if resp.data:
                        update_credito(credito["id"], {"cuotas_pagadas": cuotas_pagadas + 1})
                        st.success("✅ Pago registrado y cuota actualizada")
                        st.rerun()
                    else:
                        st.error("❌ Error al registrar el pago")

                st.divider()
        else:
            st.info("No tienes créditos registrados.")

    # ==============================
    # TAB 3: HISTORIAL
    # ==============================
    with tabs[2]:
        st.header("📜 Historial completo de transacciones")

        trans_all = obtener_transacciones(st.session_state["user"]["id"])
        if trans_all:
            for t in trans_all:
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.write(t["tipo"])
                col2.write(t["categoria"])
                col3.write(f"${t['monto']:,.2f}")
                col4.write(t["fecha"])
                if col5.button("🗑️", key=f"hist_{t['id']}"):
                    borrar_transaccion_y_ajustar_credito(st.session_state["user"]["id"], t)
                    st.rerun()
        else:
            st.info("No hay transacciones registradas.")
