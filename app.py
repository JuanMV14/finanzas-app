import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
import os
from queries import (
    registrar_pago, update_credito, insertar_transaccion, insertar_credito,
    borrar_transaccion, obtener_transacciones, obtener_creditos
)
from utils import login, signup, logout
from datetime import date, datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np
import io
import base64
import math

# =========================
# Config y cliente
# =========================
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finanzas Personales", layout="wide")

# =========================
# Estado
# =========================
if "user" not in st.session_state:
    st.session_state["user"] = None

if "metas" not in st.session_state:
    # metas: [{'nombre': str, 'monto_objetivo': float, 'fecha_objetivo': date, 'ahorrado': float}]
    st.session_state["metas"] = []

# Utils pequeños
def to_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def to_int(x, default=0):
    try:
        return int(x)
    except:
        return default

def mes_anio(dt):
    if isinstance(dt, (datetime, date)):
        return dt.strftime("%Y-%m")
    try:
        return datetime.fromisoformat(str(dt)).strftime("%Y-%m")
    except:
        return str(dt)

def descargar_bytes(nombre_archivo: str, data_bytes: bytes, label="Descargar"):
    b64 = base64.b64encode(data_bytes).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{nombre_archivo}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def generar_ics_evento(summary, dt_start: date, dt_end: date, description="", location=""):
    # Evento de todo el día (ical básico)
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

# =========================
# Sidebar auth
# =========================
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

    # =========================
    # Pestañas
    # =========================
    tabs = st.tabs(["Dashboard", "Transacciones", "Créditos", "Historial", "Metas & Proyección", "Configuración"])

    # ============================================
    # DASHBOARD (Fase 1 y 2: resumen + gráficas)
    # ============================================
    with tabs[0]:
        st.header("📈 Dashboard")

        trans = obtener_transacciones(st.session_state["user"]["id"]) or []
        # DataFrame cómodo
        df = pd.DataFrame(trans) if trans else pd.DataFrame(columns=["tipo", "categoria", "monto", "fecha"])
        if not df.empty:
            # Normalizar tipos
            df["monto"] = df["monto"].astype(float)
            df["fecha"] = pd.to_datetime(df["fecha"]).dt.date

            # Filtros rápidos (Fase 1)
            colf1, colf2, colf3 = st.columns(3)
            hoy = date.today()
            anio_mes = sorted({(d.year, d.month) for d in df["fecha"]})
            opciones_mes = ["Todos"] + [f"{a}-{m:02d}" for a, m in anio_mes]
            sel_mes = colf1.selectbox("Filtrar por mes", opciones_mes, index=len(opciones_mes)-1)
            sel_tipo = colf2.multiselect("Filtrar por tipo", options=sorted(df["tipo"].unique()), default=list(sorted(df["tipo"].unique())))
            termino = colf3.text_input("Buscar (categoría o tipo contiene)")

            df_fil = df.copy()
            if sel_mes != "Todos":
                anio, mes = sel_mes.split("-")
                anio, mes = int(anio), int(mes)
                df_fil = df_fil[df_fil["fecha"].apply(lambda d: d.year == anio and d.month == mes)]
            if sel_tipo:
                df_fil = df_fil[df_fil["tipo"].isin(sel_tipo)]
            if termino:
                termino_low = termino.lower()
                df_fil = df_fil[df_fil["categoria"].str.lower().str.contains(termino_low) | df_fil["tipo"].str.lower().str.contains(termino_low)]

            total_ingresos = df_fil[df_fil["tipo"] == "Ingreso"]["monto"].sum()
            total_gastos = df_fil[df_fil["tipo"] == "Gasto"]["monto"].sum()
            total_creditos = df_fil[df_fil["tipo"] == "Crédito"]["monto"].sum()
            saldo_total = total_ingresos - (total_gastos + total_creditos)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ingresos", f"${total_ingresos:,.2f}")
            c2.metric("Gastos", f"${total_gastos:,.2f}")
            c3.metric("Créditos (registrados como costo)", f"${total_creditos:,.2f}")
            c4.metric("Saldo total (I - G - C)", f"${saldo_total:,.2f}")

            st.markdown("---")
            colg1, colg2 = st.columns(2)

            # Gráfico de pastel por tipo (Fase 2)
            with colg1:
                st.subheader("Distribución por tipo")
                dist_tipo = df_fil.groupby("tipo")["monto"].sum().reset_index()
                if not dist_tipo.empty:
                    # pastel simple (matplotlib)
                    import matplotlib.pyplot as plt
                    fig1, ax1 = plt.subplots()
                    ax1.pie(dist_tipo["monto"], labels=dist_tipo["tipo"], autopct='%1.1f%%', startangle=90)
                    ax1.axis('equal')
                    st.pyplot(fig1)
                else:
                    st.info("Sin datos para graficar.")

            # Línea de flujo mensual (Fase 2)
            with colg2:
                st.subheader("Evolución mensual (Ingresos vs. Gastos)")
                if not df_fil.empty:
                    dft = df_fil.copy()
                    dft["ym"] = dft["fecha"].apply(lambda d: f"{d.year}-{d.month:02d}")
                    ing = dft[dft["tipo"] == "Ingreso"].groupby("ym")["monto"].sum()
                    eg = (dft[dft["tipo"].isin(["Gasto", "Crédito"])]
                          .groupby("ym")["monto"].sum())
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

            # Exportar (Fase 2)
            colx1, colx2 = st.columns(2)
            csv = df_fil.to_csv(index=False).encode("utf-8")
            colx1.download_button("⬇️ Exportar CSV", csv, file_name="transacciones.csv", mime="text/csv")

            try:
                import xlsxwriter  # si está disponible
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                    df_fil.to_excel(writer, index=False, sheet_name="Transacciones")
                colx2.download_button("⬇️ Exportar Excel", buf.getvalue(), file_name="transacciones.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except:
                colx2.info("Instala xlsxwriter para exportar a Excel (opcional).")
        else:
            st.info("Aún no hay transacciones.")

    # ============================================
    # TRANSACCIONES (Fase 1 y 2)
    # ============================================
    with tabs[1]:
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
            monto = st.number_input("Monto", min_value=0.01, step=1000.0, format="%.2f")
            fecha = st.date_input("Fecha", value=date.today())
            submitted = st.form_submit_button("Guardar")

            if submitted:
                if monto <= 0:
                    st.error("El monto debe ser mayor a 0.")
                else:
                    resp = insertar_transaccion(
                        st.session_state["user"]["id"], tipo, categoria_final, float(monto), fecha
                    )
                    if getattr(resp, "data", None) is not None or resp:
                        st.success("Transacción guardada ✅")
                        st.rerun()
                    else:
                        st.error("Error al guardar la transacción")

        # Editor rápido (Fase 2: edición en tabla)
        trans = obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            st.subheader("Edición rápida (solo visual / demo)")
            df_edit = pd.DataFrame(trans).sort_values("fecha", ascending=False)
            st.data_editor(df_edit, use_container_width=True, disabled=True,
                           help="Para edición real, crea endpoints de actualización por ID en tu módulo queries.py")
        else:
            st.info("No hay transacciones registradas.")

    # ============================================
    # CRÉDITOS (Fase 1: confirmaciones, Fase 3: recordatorios)
    # ============================================
    with tabs[2]:
        st.header("💳 Créditos")

        with st.expander("➕ Registrar nuevo crédito"):
            with st.form("form_credito"):
                nombre = st.text_input("Nombre del crédito (Banco/TC/etc.)", placeholder="Bancolombia / Visa / etc.")
                monto = st.number_input("Monto del crédito", min_value=0.0, step=1000.0, format="%.2f")
                plazo_meses = st.number_input("Plazo (meses)", min_value=1, step=1)
                tasa_anual = st.number_input("Tasa efectiva anual (EA) %", min_value=0.0, step=0.01, format="%.2f")
                cuota_mensual = st.number_input("Cuota mensual real", min_value=0.0, step=1000.0, format="%.2f")

                # Nuevo (Fase 3): día de pago (1..28 por seguridad)
                dia_pago = st.number_input("Día de pago (1-28)", min_value=1, max_value=28, step=1, value=14)
                submitted_credito = st.form_submit_button("Guardar crédito")

                if submitted_credito:
                    if not nombre:
                        st.error("El nombre del crédito es obligatorio.")
                    elif cuota_mensual <= 0:
                        st.error("La cuota mensual debe ser mayor a 0.")
                    else:
                        try:
                            resp = insertar_credito(
                                st.session_state["user"]["id"],
                                nombre, float(monto), int(plazo_meses), float(tasa_anual), float(cuota_mensual)
                            )
                            # si tu función insertar_credito no soporta estos args, usa payload alterno:
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
                            resp = insertar_credito(st.session_state["user"]["id"], payload)

                        if getattr(resp, "data", None) is not None or resp:
                            st.success("Crédito guardado ✅")
                            st.rerun()
                        else:
                            st.error("No se pudo guardar el crédito")

        # Listado
        creditos = obtener_creditos(st.session_state["user"]["id"]) or []

        if creditos:
            hoy = date.today()
            for credito in creditos:
                nombre = str(credito.get("nombre", "Sin nombre"))
                monto = to_float(credito.get("monto", 0))
                plazo_meses = to_int(credito.get("plazo_meses", 0))
                tasa_anual = to_float(credito.get("tasa_interes", 0))
                cuota_mensual = to_float(credito.get("cuota_mensual", 0))
                cuotas_pagadas = to_int(credito.get("cuotas_pagadas", 0))
                dia_pago = to_int(credito.get("dia_pago", 14))  # default 14

                cuotas_pagadas = max(0, min(cuotas_pagadas, plazo_meses))
                progreso = (cuotas_pagadas / plazo_meses) if plazo_meses > 0 else 0.0

                st.subheader(f"🏦 {nombre}")

                # Barra de progreso
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

                col5, col6, col7 = st.columns(3)
                col5.write(f"💳 **Cuota mensual (real)**: ${cuota_mensual:,.2f}")
                col6.write(f"🗓️ **Día de pago**: {dia_pago}")
                # Recordatorio de vencimiento (Fase 3)
                # Calcula próxima fecha de pago
                prox = date(hoy.year, hoy.month, min(dia_pago, 28))
                if prox < hoy:
                    # próximo mes
                    y = hoy.year + (1 if hoy.month == 12 else 0)
                    m = 1 if hoy.month == 12 else hoy.month + 1
                    prox = date(y, m, min(dia_pago, 28))
                dias = (prox - hoy).days
                if dias <= 3:
                    col7.error(f"⚠️ Vence en {dias} día(s): {prox.strftime('%Y-%m-%d')}")
                else:
                    col7.info(f"Siguiente pago: {prox.strftime('%Y-%m-%d')} ({dias} días)")

                # Botón: Registrar pago (con confirmación)
                if st.button(f"💵 Registrar pago de {nombre}", key=f"pago_{credito['id']}"):
                    # Confirmación simple
                    st.info(f"Confirmando pago de ${cuota_mensual:,.2f} en {nombre}…")
                    # 1. Insertar transacción como Gasto
                    resp = insertar_transaccion(
                        st.session_state["user"]["id"],
                        "Gasto",
                        nombre,
                        float(cuota_mensual),
                        date.today()
                    )
                    # 2. Aumentar cuotas pagadas
                    update_credito(credito["id"], {"cuotas_pagadas": cuotas_pagadas + 1})
                    st.success(f"✅ Pago de ${cuota_mensual:,.2f} registrado en {nombre}")
                    st.balloons()
                    st.rerun()

                # Descargar evento .ics para calendario (Fase 4)
                colics1, colics2 = st.columns(2)
                if colics1.button(f"📅 Descargar recordatorio .ics ({nombre})", key=f"ics_{credito['id']}"):
                    ics_bytes = generar_ics_evento(
                        summary=f"Pago {nombre}",
                        dt_start=prox, dt_end=prox + timedelta(days=1),
                        description=f"Recordatorio de pago {nombre} por ${cuota_mensual:,.2f}"
                    )
                    descargar_bytes(f"recordatorio_{nombre}_{prox}.ics", ics_bytes, label="Descargar archivo .ics")

                st.divider()
        else:
            st.info("No tienes créditos registrados.")

    # ============================================
    # HISTORIAL (Fase 1: confirmaciones + revertir cuotas)
    # ============================================
    with tabs[3]:
        st.header("📜 Historial completo de transacciones")
        trans_all = obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans_all:
            for t in trans_all:
                col1, col2, col3, col4, col5 = st.columns(5)
                col1.write(t.get("tipo"))
                col2.write(t.get("categoria"))
                col3.write(f"${to_float(t.get('monto', 0)):,.2f}")
                col4.write(t.get("fecha"))
                if col5.button("🗑️", key=f"hist_{t['id']}"):
                    # Borrar
                    borrar_transaccion(st.session_state["user"]["id"], t["id"])
                    # Si era un pago de crédito → restar cuota
                    creditos = obtener_creditos(st.session_state["user"]["id"]) or []
                    for credito in creditos:
                        if credito.get("nombre") == t.get("categoria"):
                            cuotas_actuales = to_int(credito.get("cuotas_pagadas", 0))
                            if cuotas_actuales > 0:
                                update_credito(credito["id"], {"cuotas_pagadas": cuotas_actuales - 1})
                            break
                    st.success("🗑️ Transacción eliminada y cuota revertida (si aplicaba).")
                    st.rerun()
        else:
            st.info("No hay transacciones registradas.")

    # ============================================
    # METAS & PROYECCIÓN (Fase 3 y 4)
    # ============================================
    with tabs[4]:
        st.header("🎯 Metas & Proyección")

        # --------- Metas simples en memoria (persistencia futura en DB) ----------
        with st.expander("➕ Agregar meta de ahorro"):
            colm1, colm2, colm3 = st.columns(3)
            meta_nombre = colm1.text_input("Nombre de la meta", placeholder="Fondo de emergencia")
            meta_monto = colm2.number_input("Monto objetivo", min_value=0.0, step=10000.0, format="%.2f")
            meta_fecha = colm3.date_input("Fecha objetivo", value=date.today() + timedelta(days=90))
            if st.button("Guardar meta"):
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

        if st.session_state["metas"]:
            st.subheader("Tus metas")
            for i, m in enumerate(st.session_state["metas"]):
                objetivo = m["monto_objetivo"]
                ahorrado = m["ahorrado"]
                progreso = (ahorrado / objetivo) if objetivo > 0 else 0
                st.markdown(
                    f"""
                    **{m['nombre']}** — objetivo ${objetivo:,.2f} para {m['fecha_objetivo'].strftime('%Y-%m-%d')}  
                    Progreso: ${ahorrado:,.2f} ({progreso*100:.1f}%)
                    """
                )
                st.progress(min(1.0, progreso))
                colma, colmb = st.columns(2)
                abono = colma.number_input(f"Abonar a '{m['nombre']}'", min_value=0.0, step=10000.0, key=f"ab_{i}")
                if colmb.button("Aplicar abono", key=f"ab_btn_{i}"):
                    m["ahorrado"] += float(abono)
                    st.success("Abono aplicado ✅")
                    st.rerun()
                st.divider()
        else:
            st.info("Aún no tienes metas creadas.")

        # --------- Proyección fin de mes (Fase 3) ----------
        st.subheader("📅 Proyección de fin de mes")
        trans = obtener_transacciones(st.session_state["user"]["id"]) or []
        if trans:
            dft = pd.DataFrame(trans)
            dft["monto"] = dft["monto"].astype(float)
            dft["fecha"] = pd.to_datetime(dft["fecha"])
            hoy = pd.Timestamp(date.today())
            actual_mes = dft[(dft["fecha"].dt.year == hoy.year) & (dft["fecha"].dt.month == hoy.month)]
            ing_mes = actual_mes[actual_mes["tipo"] == "Ingreso"]["monto"].sum()
            eg_mes = actual_mes[actual_mes["tipo"].isin(["Gasto", "Crédito"])]["monto"].sum()

            # Promedio diario de egresos del mes (hasta hoy)
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

        # --------- Predicción simple de gasto mensual (Fase 4) ----------
        st.subheader("🤖 Predicción de gasto mensual (simple)")
        if trans:
            dft = pd.DataFrame(trans)
            dft["monto"] = dft["monto"].astype(float)
            dft["fecha"] = pd.to_datetime(dft["fecha"])
            dft["ym"] = dft["fecha"].dt.to_period("M").astype(str)

            # gasto mensual = Gasto + Crédito
            gasto_mensual = (dft[dft["tipo"].isin(["Gasto", "Crédito"])]
                             .groupby("ym")["monto"].sum()
                             .reset_index()
                             .sort_values("ym"))
            if len(gasto_mensual) >= 2:
                # Regresión lineal simple y = a*x + b sobre índice temporal
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

    # ============================================
    # CONFIGURACIÓN (Fase 4: hooks integraciones)
    # ============================================
    with tabs[5]:
        st.header("⚙️ Configuración & Avanzado")

        st.write("Aquí puedes preparar integraciones y parámetros avanzados.")

        st.subheader("Integración con bancos / fintech (placeholder)")
        st.info("Cuando tengas APIs/bancos habilitados, agrega aquí tus tokens/keys y crea un job para sincronizar saldos.")

        st.subheader("Multiusuario (ya soportado con Supabase)")
        st.write("- Cada usuario ve sus propios datos (según tu RLS).")
        st.write("- Para compartir cuentas familiares, puedes crear una tabla `compartidos` con (owner_id, shared_user_id, recurso_id).")

        st.subheader("Parámetros generales")
        alerta_dias = st.number_input("Mostrar alerta de vencimiento cuando falten ≤ N días", min_value=1, max_value=10, value=3)
        st.caption("Actualmente el código usa 3 días por defecto; cambia el valor y aplica cuando actualices la lógica si deseas hacerlo dinámico.")
