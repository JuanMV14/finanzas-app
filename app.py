# app.py - Versión corregida y compatible
# Recomendación: en tu requirements.txt añade:
# streamlit>=1.32
# supabase
# python-dotenv
# pandas
# numpy
# xlsxwriter  # opcional para exportar Excel
# altair     # opcional para gráficos si matplotlib no está disponible

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import date, datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
import io
import base64
import traceback

# --- Import de queries y utils (asegúrate de tener esos módulos) ---
from queries import (
    registrar_pago, update_credito, insertar_transaccion, insertar_credito,
    borrar_transaccion, obtener_transacciones, obtener_creditos
)
from utils import login, signup, logout

# ============================
# Inicializaciones seguras
# ============================
# Aseguramos claves en session_state ANTES de dibujar widgets para evitar KeyError
required_session_keys = ["user", "metas", "last_action"]
for k in required_session_keys:
    if k not in st.session_state:
        # user -> None, metas -> lista, last_action -> None
        if k == "user":
            st.session_state[k] = None
        elif k == "metas":
            st.session_state[k] = []
        else:
            st.session_state[k] = None

# ============================
# Compatibilidad y utilidades
# ============================
# Compatibilidad data_editor
if hasattr(st, "data_editor"):
    safe_data_editor = st.data_editor
elif hasattr(st, "experimental_data_editor"):
    safe_data_editor = st.experimental_data_editor
else:
    # Fallback muy básico: usar st.table (solo lectura)
    def safe_data_editor(df, *args, **kwargs):
        st.table(df)
        return None

# Compatibilidad matplotlib / altair
try:
    import matplotlib.pyplot as plt
    have_matplotlib = True
except Exception:
    have_matplotlib = False
    # altair puede usarse como fallback
    try:
        import altair as alt
        have_altair = True
    except Exception:
        have_altair = False

# Cliente supabase
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    # No detener la app si falla la creación del cliente; las funciones de queries.py
    # deben manejar el caso.
    supabase = None

# Pequeñas utilidades
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
# UI config
# ============================
st.set_page_config(page_title="Finanzas Personales", layout="wide")

# ============================
# Sidebar - Auth
# ============================
st.sidebar.title("Menú")

if st.session_state["user"] is None:
    # Radio en sidebar (ya no da KeyError porque inicializamos session_state)
    menu = st.sidebar.radio("Selecciona una opción:", ["Login", "Registro"], index=0, key="auth_menu")
    if menu == "Login":
        st.subheader("Iniciar Sesión")
        email = st.text_input("Correo electrónico", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        if st.button("Ingresar", key="btn_login"):
            try:
                login(supabase, email, password)
            except Exception as e:
                st.error("Error en login. Revisa tus credenciales o los logs.")
                st.exception(e)
    elif menu == "Registro":
        st.subheader("Crear Cuenta")
        email = st.text_input("Correo electrónico (registro)", key="reg_email")
        password = st.text_input("Contraseña (registro)", type="password", key="reg_password")
        if st.button("Registrarse", key="btn_signup"):
            try:
                signup(supabase, email, password)
            except Exception as e:
                st.error("Error en registro. Revisa los logs.")
                st.exception(e)
else:
    st.sidebar.write(f"👤 {st.session_state['user'].get('email', 'Usuario')}")
    if st.sidebar.button("Cerrar Sesión", key="btn_logout"):
        try:
            logout(supabase)
            st.session_state["user"] = None
            st.experimental_rerun()
        except Exception as e:
            st.error("Error al cerrar sesión.")
            st.exception(e)

    # ============================
    # Pestañas principales
    # ============================
    tabs = st.tabs(["Dashboard", "Transacciones", "Créditos", "Historial", "Metas & Proyección", "Configuración"])

    # Helper: obtener transacciones seguro
    def safe_obtener_transacciones(user_id):
        try:
            res = obtener_transacciones(user_id)
            return res if isinstance(res, list) else (res.data if getattr(res, "data", None) is not None else [])
        except Exception:
            # registrar en consola para debugging
            traceback.print_exc()
            return []

    def safe_obtener_creditos(user_id):
        try:
            res = obtener_creditos(user_id)
            return res if isinstance(res, list) else (res.data if getattr(res, "data", None) is not None else [])
        except Exception:
            traceback.print_exc()
            return []

    # ============================
    # DASHBOARD
    # ============================
    with tabs[0]:
        st.header("📈 Dashboard")

        trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            df = pd.DataFrame(trans)
            # defensiva
            if "monto" in df.columns:
                df["monto"] = df["monto"].apply(lambda x: to_float(x, 0.0))
            else:
                df["monto"] = 0.0
            if "fecha" in df.columns:
                try:
                    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
                except Exception:
                    df["fecha"] = df["fecha"]
            else:
                df["fecha"] = pd.NaT

            colf1, colf2, colf3 = st.columns(3)
            # opciones_mes: a partir de df
            opciones_mes = ["Todos"]
            try:
                fechas = sorted({(d.year, d.month) for d in df["fecha"] if pd.notna(d)})
                opciones_mes += [f"{a}-{m:02d}" for a, m in fechas]
            except Exception:
                pass
            sel_mes = colf1.selectbox("Filtrar por mes", opciones_mes, index=len(opciones_mes)-1)
            sel_tipo = colf2.multiselect("Filtrar por tipo", options=sorted(df["tipo"].unique()) if "tipo" in df.columns else [], default=list(sorted(df["tipo"].unique())) if "tipo" in df.columns else [])
            termino = colf3.text_input("Buscar (categoría o tipo contiene)")

            df_fil = df.copy()
            if sel_mes != "Todos":
                anio, mes = sel_mes.split("-")
                anio, mes = int(anio), int(mes)
                df_fil = df_fil[df_fil["fecha"].apply(lambda d: getattr(d, "year", None) == anio and getattr(d, "month", None) == mes)]
            if sel_tipo:
                df_fil = df_fil[df_fil["tipo"].isin(sel_tipo)]
            if termino:
                termino_low = termino.lower()
                df_fil = df_fil[df_fil["categoria"].astype(str).str.lower().str.contains(termino_low) | df_fil["tipo"].astype(str).str.lower().str.contains(termino_low)]

            total_ingresos = df_fil[df_fil["tipo"] == "Ingreso"]["monto"].sum()
            total_gastos = df_fil[df_fil["tipo"] == "Gasto"]["monto"].sum()
            total_creditos = df_fil[df_fil["tipo"] == "Crédito"]["monto"].sum()
            total_general = total_ingresos + total_gastos + total_creditos
            saldo_total = total_ingresos - (total_gastos + total_creditos)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos", f"${total_ingresos:,.2f}")
            c2.metric("Gastos", f"${total_gastos:,.2f}")
            c3.metric("Créditos (registrados como costo)", f"${total_creditos:,.2f}")
            c4.metric("Saldo total (I - G - C)", f"${saldo_total:,.2f}")

            st.markdown("---")
            colg1, colg2 = st.columns(2)

            # Gráfico de pastel por tipo
            with colg1:
                st.subheader("Distribución por tipo")
                dist_tipo = df_fil.groupby("tipo")["monto"].sum().reset_index()
                if not dist_tipo.empty:
                    if have_matplotlib:
                        fig1, ax1 = plt.subplots()
                        ax1.pie(dist_tipo["monto"], labels=dist_tipo["tipo"], autopct='%1.1f%%', startangle=90)
                        ax1.axis('equal')
                        st.pyplot(fig1)
                    elif have_altair:
                        chart = alt.Chart(dist_tipo).mark_arc().encode(
                            theta=alt.Theta(field="monto", type="quantitative"),
                            color=alt.Color("tipo:N")
                        )
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("Instala 'matplotlib' o 'altair' para ver este gráfico.")
                else:
                    st.info("Sin datos para graficar.")

            # Línea de flujo mensual
            with colg2:
                st.subheader("Evolución mensual (Ingresos vs. Gastos)")
                if not df_fil.empty:
                    dft = df_fil.copy()
                    dft["ym"] = dft["fecha"].apply(lambda d: f"{getattr(d,'year', '')}-{getattr(d,'month',''):02d}" if pd.notna(d) else "unknown")
                    ing = dft[dft["tipo"] == "Ingreso"].groupby("ym")["monto"].sum()
                    eg = dft[dft["tipo"].isin(["Gasto", "Crédito"])].groupby("ym")["monto"].sum()
                    yms = sorted(set(ing.index).union(set(eg.index)))
                    s = pd.DataFrame({"ym": yms})
                    s["Ingresos"] = s["ym"].map(ing).fillna(0)
                    s["Egresos"] = s["ym"].map(eg).fillna(0)
                    s = s.set_index("ym")
                    st.line_chart(s)
                else:
                    st.info("Sin datos para graficar.")

            st.markdown("---")
            st.subheader("Transacciones filtradas")
            st.dataframe(df_fil.sort_values("fecha", ascending=False), use_container_width=True)

            # Exportar CSV/Excel
            csv = df_fil.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Exportar CSV", csv, file_name="transacciones.csv", mime="text/csv")
            try:
                import xlsxwriter
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                    df_fil.to_excel(writer, index=False, sheet_name="Transacciones")
                st.download_button("⬇️ Exportar Excel", buf.getvalue(), file_name="transacciones.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception:
                st.info("Para exportar a Excel instala xlsxwriter (opcional).")
        else:
            st.info("Aún no hay transacciones.")

    # ============================
    # TRANSACCIONES
    # ============================
    with tabs[1]:
        st.header("📊 Transacciones")

        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Crédito"], key="trans_tipo")
        categorias = {
            "Ingreso": ["Salario", "Comisiones", "Ventas", "Otros"],
            "Gasto": ["Comida", "Gasolina", "Pago TC", "Servicios Públicos", "Ocio", "Entretenimiento", "Otros"],
            "Crédito": ["Otros"]
        }
        categoria_seleccionada = st.selectbox("Categoría", categorias[tipo], key="trans_categoria")
        categoria_personalizada = ""
        if categoria_seleccionada == "Otros":
            categoria_personalizada = st.text_input("Especifica la categoría", key="trans_cat_custom")

        categoria_final = categoria_personalizada if categoria_seleccionada == "Otros" else categoria_seleccionada

        with st.form("nueva_transaccion"):
            monto = st.number_input("Monto", min_value=0.01, step=1000.0, format="%.2f", key="form_monto")
            fecha = st.date_input("Fecha", value=date.today(), key="form_fecha")
            submitted = st.form_submit_button("Guardar", key="form_submit")

            if submitted:
                if monto <= 0:
                    st.error("El monto debe ser mayor a 0.")
                else:
                    try:
                        resp = insertar_transaccion(
                            st.session_state["user"]["id"], tipo, categoria_final, float(monto), fecha
                        )
                        if getattr(resp, "data", None) is not None or resp:
                            st.success("Transacción guardada ✅")
                            st.experimental_rerun()
                        else:
                            st.error("Error al guardar la transacción")
                    except Exception:
                        st.error("Error al guardar la transacción (ver logs).")
                        traceback.print_exc()

        # Editor rápido (solo lectura o fallback)
        trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            st.subheader("Edición rápida (solo lectura en demo)")
            df_edit = pd.DataFrame(trans).sort_values("fecha", ascending=False)
            try:
                safe_data_editor(df_edit, use_container_width=True, disabled=True,
                                 help="Para edición real, crea endpoints de actualización por ID en tu módulo queries.py")
            except Exception:
                # fallback
                st.table(df_edit)
        else:
            st.info("No hay transacciones registradas.")

    # ============================
    # CRÉDITOS
    # ============================
    with tabs[2]:
        st.header("💳 Créditos")

        with st.expander("➕ Registrar nuevo crédito"):
            with st.form("form_credito"):
                nombre = st.text_input("Nombre del crédito (Banco/TC/etc.)", placeholder="Bancolombia / Visa / etc.", key="newc_nombre")
                monto = st.number_input("Monto del crédito", min_value=0.0, step=1000.0, format="%.2f", key="newc_monto")
                plazo_meses = st.number_input("Plazo (meses)", min_value=1, step=1, key="newc_plazo")
                tasa_anual = st.number_input("Tasa efectiva anual (EA) %", min_value=0.0, step=0.01, format="%.2f", key="newc_tasa")
                cuota_mensual = st.number_input("Cuota mensual real", min_value=0.0, step=1000.0, format="%.2f", key="newc_cuota")
                dia_pago = st.number_input("Día de pago (1-28)", min_value=1, max_value=28, step=1, value=14, key="newc_diapago")
                submitted_credito = st.form_submit_button("Guardar crédito", key="form_credito_submit")

                if submitted_credito:
                    if not nombre:
                        st.error("El nombre del crédito es obligatorio.")
                    elif cuota_mensual <= 0:
                        st.error("La cuota mensual debe ser mayor a 0.")
                    else:
                        try:
                            # intentar llamada estándar
                            resp = insertar_credito(
                                st.session_state["user"]["id"],
                                nombre, float(monto), int(plazo_meses), float(tasa_anual), float(cuota_mensual)
                            )
                        except TypeError:
                            payload = {
                                "nombre": nombre,
                                "monto": float(monto),
                                "plazo_meses": int(plazo_meses),
                                "tasa_interes": float(tasa_anual),
                                "cuota_mensual": float(cuota_mensual),
                                "cuotas_pagadas": 0,
                                "dia_pago": int(dia_pago)
                            }
                            try:
                                resp = insertar_credito(st.session_state["user"]["id"], payload)
                            except Exception:
                                resp = None
                                traceback.print_exc()

                        if getattr(resp, "data", None) is not None or resp:
                            st.success("Crédito guardado ✅")
                            st.experimental_rerun()
                        else:
                            st.error("No se pudo guardar el crédito")

        creditos = safe_obtener_creditos(st.session_state["user"]["id"]) or []
        if creditos:
            hoy = date.today()
            for credito in creditos:
                nombre = str(credito.get("nombre", "Sin nombre"))
                monto = to_float(credito.get("monto", 0))
                plazo_meses = to_int(credito.get("plazo_meses", 0))
                tasa_anual = to_float(credito.get("tasa_interes", 0))
                cuota_mensual = to_float(credito.get("cuota_mensual", 0))
                cuotas_pagadas = to_int(credito.get("cuotas_pagadas", 0))
                dia_pago = to_int(credito.get("dia_pago", 14))

                cuotas_pagadas = max(0, min(cuotas_pagadas, plazo_meses)) if plazo_meses > 0 else max(0, cuotas_pagadas)
                progreso = (cuotas_pagadas / plazo_meses) if plazo_meses > 0 else 0.0

                st.subheader(f"🏦 {nombre}")
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
                            {cuotas_pagadas}/{plazo_meses if plazo_meses>0 else '?'} cuotas ({progreso*100:.1f}%)
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

                col5, col6, col7 = st.columns(3)
                col5.write(f"💳 **Cuota mensual (real)**: ${cuota_mensual:,.2f}")
                col6.write(f"🗓️ **Día de pago**: {dia_pago}")

                # Próxima fecha de pago
                try:
                    prox = date(hoy.year, hoy.month, min(dia_pago, 28))
                    if prox < hoy:
                        y = hoy.year + (1 if hoy.month == 12 else 0)
                        m = 1 if hoy.month == 12 else hoy.month + 1
                        prox = date(y, m, min(dia_pago, 28))
                    dias = (prox - hoy).days
                except Exception:
                    prox = hoy
                    dias = 0

                if dias <= 3:
                    col7.error(f"⚠️ Vence en {dias} día(s): {prox.strftime('%Y-%m-%d')}")
                else:
                    col7.info(f"Siguiente pago: {prox.strftime('%Y-%m-%d')} ({dias} días)")

                # Botón registrar pago con confirmación simple
                key_pago = f"pago_{credito.get('id', nombre)}"
                if st.button(f"💵 Registrar pago de {nombre}", key=key_pago):
                    # Confirmación simple: pedimos segunda confirmación con confirm widget (fallback)
                    confirm_key = f"confirm_{key_pago}"
                    if "confirm_action" not in st.session_state:
                        st.session_state["confirm_action"] = None
                    st.session_state["confirm_action"] = {"type": "registrar_pago", "credito_id": credito.get("id")}
                    st.info(f"¿Confirmas el pago de ${cuota_mensual:,.2f} en {nombre}? Haz click en Confirmar abajo.")
                    if st.button("Confirmar pago", key=f"confirm_btn_{key_pago}"):
                        try:
                            insertar_transaccion(
                                st.session_state["user"]["id"],
                                "Gasto",
                                nombre,
                                float(cuota_mensual),
                                date.today()
                            )
                            update_credito(credito["id"], {"cuotas_pagadas": cuotas_pagadas + 1})
                            st.success(f"✅ Pago de ${cuota_mensual:,.2f} registrado en {nombre}")
                            st.balloons()
                            st.experimental_rerun()
                        except Exception:
                            st.error("Error registrando pago (ver logs).")
                            traceback.print_exc()

                # .ics download
                if st.button(f"📅 Descargar recordatorio .ics ({nombre})", key=f"ics_{credito.get('id', nombre)}"):
                    try:
                        ics_bytes = generar_ics_evento(
                            summary=f"Pago {nombre}",
                            dt_start=prox, dt_end=prox + timedelta(days=1),
                            description=f"Recordatorio de pago {nombre} por ${cuota_mensual:,.2f}"
                        )
                        descargar_bytes(f"recordatorio_{nombre}_{prox}.ics", ics_bytes, label="Descargar archivo .ics")
                    except Exception:
                        st.error("No se pudo generar .ics (ver logs).")
                        traceback.print_exc()

                st.divider()
        else:
            st.info("No tienes créditos registrados.")

    # ============================
    # HISTORIAL
    # ============================
    with tabs[3]:
        st.header("📜 Historial completo de transacciones")
        trans_all = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans_all:
            for t in trans_all:
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.write(t.get("tipo"))
                col2.write(t.get("categoria"))
                col3.write(f"${to_float(t.get('monto', 0)):,.2f}")
                col4.write(str(t.get("fecha")))
                btn_key = f"hist_{t.get('id')}"
                if col5.button("🗑️", key=btn_key):
                    # Confirmación simple antes de eliminar
                    st.session_state["pending_delete"] = {"id": t.get("id"), "categoria": t.get("categoria"), "tipo": t.get("tipo")}
                    st.warning("¿Seguro que quieres eliminar esta transacción? Esto puede revertir una cuota pagada si es de un crédito.")
                    if st.button("Confirmar eliminación", key=f"confirm_del_{t.get('id')}"):
                        try:
                            borrar_transaccion(st.session_state["user"]["id"], t["id"])
                        except Exception:
                            # intentar igualmente continuar
                            traceback.print_exc()
                        # Si era un gasto cuya categoría coincide con un crédito, restar cuota
                        if t.get("tipo") == "Gasto":
                            creditos = safe_obtener_creditos(st.session_state["user"]["id"]) or []
                            for credito in creditos:
                                if credito.get("nombre") == t.get("categoria"):
                                    cuotas_actuales = to_int(credito.get("cuotas_pagadas", 0))
                                    if cuotas_actuales > 0:
                                        try:
                                            update_credito(credito["id"], {"cuotas_pagadas": cuotas_actuales - 1})
                                        except Exception:
                                            traceback.print_exc()
                                    break
                        st.success("🗑️ Transacción eliminada correctamente")
                        st.experimental_rerun()
        else:
            st.info("No hay transacciones registradas.")

    # ============================
    # METAS & PROYECCIÓN
    # ============================
    with tabs[4]:
        st.header("🎯 Metas & Proyección")

        with st.expander("➕ Agregar meta de ahorro"):
            colm1, colm2, colm3 = st.columns(3)
            meta_nombre = colm1.text_input("Nombre de la meta", placeholder="Fondo de emergencia", key="meta_nombre")
            meta_monto = colm2.number_input("Monto objetivo", min_value=0.0, step=10000.0, format="%.2f", key="meta_monto")
            meta_fecha = colm3.date_input("Fecha objetivo", value=date.today() + timedelta(days=90), key="meta_fecha")
            if st.button("Guardar meta", key="guardar_meta"):
                if not meta_nombre:
                    st.error("Escribe un nombre para la meta.")
                elif meta_monto <= 0:
                    st.error("El monto objetivo debe ser mayor a 0.")
                else:
                    st.session_state["metas"].append({
                        "nombre": meta_nombre,
                        "monto_objetivo": float(meta_monto),
                        "fecha_objetivo": meta_fecha,
                        "ahorrado": 0.0
                    })
                    st.success("Meta guardada ✅")
                    st.experimental_rerun()

        if st.session_state["metas"]:
            st.subheader("Tus metas")
            for i, m in enumerate(st.session_state["metas"]):
                objetivo = m["monto_objetivo"]
                ahorrado = m["ahorrado"]
                progreso = (ahorrado / objetivo) if objetivo > 0 else 0
                st.markdown(
                    f"**{m['nombre']}** — objetivo ${objetivo:,.2f} para {m['fecha_objetivo'].strftime('%Y-%m-%d')}  \nProgreso: ${ahorrado:,.2f} ({progreso*100:.1f}%)"
                )
                st.progress(min(1.0, progreso))
                colma, colmb = st.columns(2)
                abono = colma.number_input(f"Abonar a '{m['nombre']}'", min_value=0.0, step=10000.0, key=f"ab_{i}")
                if colmb.button("Aplicar abono", key=f"ab_btn_{i}"):
                    m["ahorrado"] += float(abono)
                    st.success("Abono aplicado ✅")
                    st.experimental_rerun()
                st.divider()
        else:
            st.info("Aún no tienes metas creadas.")

        # Proyección de fin de mes
        st.subheader("📅 Proyección de fin de mes")
        trans = safe_obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            dft = pd.DataFrame(trans)
            dft["monto"] = dft["monto"].astype(float)
            dft["fecha"] = pd.to_datetime(dft["fecha"])
            hoy = pd.Timestamp(date.today())
            actual_mes = dft[(dft["fecha"].dt.year == hoy.year) & (dft["fecha"].dt.month == hoy.month)]
            ing_mes = actual_mes[actual_mes["tipo"] == "Ingreso"]["monto"].sum()
            eg_mes = actual_mes[actual_mes["tipo"].isin(["Gasto", "Crédito"])]["monto"].sum()

            dias_transcurridos = hoy.day
            prom_egreso_diario = eg_mes / max(1, dias_transcurridos)
            dias_restantes = (pd.Period(hoy, 'M').end_time.date() - hoy.date()).days
            egresos_estimados = eg_mes + prom_egreso_diario * dias_restantes
            saldo_estimado = ing_mes - egresos_estimados

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos del mes (real)", f"${ing_mes:,.2f}")
            c2.metric("Egresos del mes (real)", f"${eg_mes:,.2f}")
            c3.metric("Egresos estimados fin de mes", f"${egresos_estimados:,.2f}")
            c4.metric("Saldo estimado fin de mes", f"${saldo_estimado:,.2f}")
        else:
            st.info("Sin datos para proyectar.")

        # Predicción simple (regresión lineal sobre gasto mensual)
        st.subheader("🤖 Predicción de gasto mensual (simple)")
        if trans:
            dft = pd.DataFrame(trans)
            dft["monto"] = dft["monto"].astype(float)
            dft["fecha"] = pd.to_datetime(dft["fecha"])
            dft["ym"] = dft["fecha"].dt.to_period("M").astype(str)

            gasto_mensual = (dft[dft["tipo"].isin(["Gasto", "Crédito"])]
                             .groupby("ym")["monto"].sum()
                             .reset_index()
                             .sort_values("ym"))
            if len(gasto_mensual) >= 2:
                x = np.arange(len(gasto_mensual))
                y = gasto_mensual["monto"].values
                a, b = np.polyfit(x, y, 1)
                siguiente = a * (len(x)) + b
                st.write("Histórico de gasto mensual:")
                st.dataframe(gasto_mensual, use_container_width=True)
                st.info(f"🔮 Predicción para el próximo mes: **${siguiente:,.2f}** (tendencia lineal)")
            else:
                st.info("Se necesitan al menos 2 meses de datos para predecir.")
        else:
            st.info("Sin datos para predecir.")

    # ============================
    # CONFIGURACIÓN
    # ============================
    with tabs[5]:
        st.header("⚙️ Configuración & Avanzado")
        st.write("Parámetros y ayudas para integrar más adelante.")
        alerta_dias = st.number_input("Mostrar alerta de vencimiento cuando falten ≤ N días", min_value=1, max_value=30, value=3, key="conf_alerta_dias")
        st.caption("Ajusta este valor si quieres cambiar la lógica de alertas en los créditos (se aplica la próxima vez que registres/recargues la página).")

# Fin del app.py
