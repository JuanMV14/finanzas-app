import streamlit as st
from supabase import create_client
from datetime import date
import pandas as pd
import plotly.express as px

# 🔐 Conexión a Supabase
url = "https://ejsakzzbgwymptqjoigs.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0"
supabase = create_client(url, key)

# 🔐 Inicio de sesión
if "supabase_session" not in st.session_state:
    st.markdown("## 🔐 Iniciar sesión")
    email = st.text_input("Correo electrónico")
    password = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.session:
            st.session_state["supabase_session"] = res.session
            st.success("✅ Sesión iniciada correctamente. Recarga la página.")
        else:
            st.error("❌ Error al iniciar sesión. Verifica tus credenciales.")
    st.stop()

# 🧩 Funciones auxiliares
def get_user_id():
    session = st.session_state.get("supabase_session")
    return session.user.id if session else None

def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    data = {
        "user_id": user_id,
        "tipo": tipo,
        "categoria": categoria,
        "monto": monto,
        "fecha": str(fecha)
    }
    supabase.table("transacciones").insert(data).execute()
    st.success("✅ Transacción guardada.")
    st.session_state["actualizar_resumen"] = True

def insertar_credito(user_id, nombre, monto, tasa, plazo, cuota, pagados):
    data = {
        "user_id": user_id,
        "nombre_credito": nombre,
        "monto_total": monto,
        "tasa_anual": tasa,
        "plazo_meses": plazo,
        "cuota_mensual": cuota,
        "meses_pagados": pagados
    }
    supabase.table("creditos").insert(data).execute()
    st.success("✅ Crédito guardado.")
    st.session_state["actualizar_resumen"] = True

def obtener_resumen_financiero(user_id):
    ingresos = gastos = balance = creditos = 0.0
    transacciones = supabase.table("transacciones").select("*").eq("user_id", user_id).execute().data
    for t in transacciones:
        if t["tipo"] == "Ingreso":
            ingresos += t["monto"]
        elif t["tipo"] == "Gasto":
            gastos += t["monto"]
    balance = ingresos - gastos
    creditos_data = supabase.table("creditos").select("monto_total").eq("user_id", user_id).execute().data
    creditos = sum(c["monto_total"] for c in creditos_data)
    return ingresos, gastos, balance, creditos

def eliminar_credito(id):
    supabase.table("creditos").delete().eq("id", id).execute()
    st.session_state["actualizar_resumen"] = True

def eliminar_transaccion(id):
    supabase.table("transacciones").delete().eq("id", id).execute()
    st.session_state["actualizar_resumen"] = True

def actualizar_credito(id, cuota, pagados):
    supabase.table("creditos").update({
        "cuota_mensual": cuota,
        "meses_pagados": pagados
    }).eq("id", id).execute()
    st.success("✏️ Crédito actualizado.")
    st.session_state["actualizar_resumen"] = True

def eliminar_creditos_saldados(user_id):
    creditos = supabase.table("creditos").select("*").eq("user_id", user_id).execute().data
    for c in creditos:
        id_credito = c.get("id", "desconocido")
        nombre_credito = c.get("nombre_credito", "Sin nombre")
        try:
            meses_pagados = c["meses_pagados"]
            plazo_meses = c["plazo_meses"]
            if meses_pagados >= plazo_meses:
                eliminar_credito(id_credito)
                st.info(f"✅ Crédito '{nombre_credito}' eliminado automáticamente (saldado).")
        except KeyError as e:
            campo_faltante = str(e).strip("'")
            st.warning(f"⚠️ Crédito con ID {id_credito} tiene campos faltantes: '{campo_faltante}'")

            # Validación de campos requeridos
            if "meses_pagados" not in c or "plazo_meses" not in c:
                campos_faltantes = []
                if "meses_pagados" not in c:
                    campos_faltantes.append("meses_pagados")
                if "plazo_meses" not in c:
                    campos_faltantes.append("plazo_meses")
                st.warning(f"⚠️ Crédito con ID {id_credito} tiene campos faltantes: {', '.join(campos_faltantes)}.")
                continue

            # Eliminación si está saldado
            if c["meses_pagados"] >= c["plazo_meses"]:
                eliminar_credito(id_credito)
                st.info(f"✅ Crédito '{nombre}' eliminado automáticamente (saldado).")

        except Exception as e:
            st.error("❌ Error al procesar créditos saldados.")
            st.write("Detalles del error:", e)

    for c in creditos:
        if c["meses_pagados"] >= c["plazo_meses"]:
            eliminar_credito(c["id"])
            st.info(f"💡 Crédito '{c['nombre_credito']}' eliminado automáticamente (saldado).")

def exportar_csv(nombre, data):
    df = pd.DataFrame(data)
    st.download_button(
        label=f"📤 Exportar {nombre} a CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{nombre}.csv",
        mime="text/csv"
    )

def mostrar_grafico_transacciones(transacciones):
    df = pd.DataFrame(transacciones)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    resumen = df.groupby(["mes", "tipo"])["monto"].sum().reset_index()
    fig = px.bar(resumen, x="mes", y="monto", color="tipo", barmode="group", title="📈 Evolución mensual")
    st.plotly_chart(fig, use_container_width=True)

def mostrar_notificaciones(creditos):
    for c in creditos:
        restante = c["plazo_meses"] - c["meses_pagados"]
        if restante <= 2 and restante > 0:
            st.warning(f"🔔 Crédito '{c['nombre_credito']}' está por vencer ({restante} meses restantes).")

# 🔐 Validación de sesión
user_id = get_user_id()
if not user_id:
    st.warning("🔒 Debes iniciar sesión para usar la app.")
    st.stop()

# 🧹 Eliminar créditos saldados al cargar
eliminar_creditos_saldados(user_id)

# 🏠 Banner principal con resumen dinámico
if "actualizar_resumen" not in st.session_state:
    st.session_state["actualizar_resumen"] = True

if st.session_state["actualizar_resumen"]:
    ingresos, gastos, balance, creditos = obtener_resumen_financiero(user_id)
    st.session_state["actualizar_resumen"] = False

with st.container():
    st.markdown("## 💰 Finanzas Personales - Dashboard")
    st.markdown("### 📊 Resumen financiero")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ingresos", f"${ingresos:,.2f}")
    col2.metric("Gastos", f"${gastos:,.2f}")
    col3.metric("Balance", f"${balance:,.2f}")
    col4.metric("Créditos", f"${creditos:,.2f}")
    st.markdown("---")

# 📂 Sección: Nueva transacción
with st.container():
    st.markdown("### ➕ Nueva transacción")
    tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])
    categoria = st.text_input("Categoría")
    monto = st.number_input("Monto", min_value=0.01, format="%.2f")
    fecha = st.date_input("Fecha", value=date.today())
    if st.button("Guardar transacción"):
        insertar_transaccion(user_id, tipo, categoria, monto, fecha)

# 💳 Sección: Nuevo crédito
with st.container():
    st.markdown("### 🏦 Nuevo crédito")
    nombre_credito = st.text_input("Nombre del crédito")
    monto_credito = st.number_input("Monto total del crédito", min_value=0.01, format="%.2f")
    tasa_anual = st.number_input("Tasa anual (%)", min_value=0.0, format="%.2f")
    plazo_meses = st.number_input("Plazo total (meses)", min_value=1)
    cuota_mensual = st.number_input("Valor de la cuota mensual", min_value=0.01, format="%.2f")
    meses_pagados = st.number_input("Meses pagados", min_value=0)
    if st.button("Guardar crédito"):
        insertar_credito(user_id, nombre_credito, monto_credito, tasa_anual, plazo_meses, cuota_mensual, meses_pagados)

# 🧾 Panel de gestión: Transacciones
with st.container():
    st.markdown("### 🧾 Tus transacciones")
    transacciones = supabase.table("transacciones").select("*").eq("user_id", user_id).order("fecha", desc=True).execute().data
    mostrar_grafico_transacciones(transacciones)
    exportar_csv("transacciones", transacciones)
    for t in transacciones:
        with st.expander(f"{t['tipo']} - {t['categoria']} - ${t['monto']:,.2f} ({t['fecha']})"):
            if st.button(f"🗑️ Eliminar transacción {t['id']}", key=f"del_tx_{t['id']}"):
                eliminar_transaccion(t["id"])
                st.success("Transacción eliminada.")

# 💼 Panel de gestión: Créditos
with st.container():
    st.markdown("### 💼 Tus créditos")

    # Obtener créditos del usuario
    creditos_data = supabase.table("creditos").select("*").eq("user_id", user_id).order("nombre_credito").execute().data

    # Mostrar notificaciones de créditos por vencer
    mostrar_notificaciones(creditos_data)

    # Exportar créditos a CSV
    exportar_csv("creditos", creditos_data)

    # Mostrar cada crédito en un expander
    for c in creditos_data:
        with st.expander(f"{c['nombre_credito']} - ${c['monto_total']:,.2f}"):
            st.write(f"Plazo: {c['plazo_meses']} meses")
            st.write(f"Meses pagados: {c['meses_pagados']}")
            st.write(f"Cuota mensual: ${c['cuota_mensual']:,.2f}")
            st.write(f"Tasa anual: {c['tasa_anual']}%")

            # Inputs para editar
            nueva_cuota = st.number_input(
                "Editar cuota mensual",
                value=c["cuota_mensual"],
                min_value=0.01,
                format="%.2f",
                key=f"cuota_{c['id']}"
            )
            nuevos_pagados = st.number_input(
                "Editar meses pagados",
                value=c["meses_pagados"],
                min_value=0,
                max_value=c["plazo_meses"],
                key=f"pagados_{c['id']}"
            )

            # Botón para actualizar
            if st.button(f"✏️ Actualizar crédito {c['id']}", key=f"edit_cr_{c['id']}"):
                actualizar_credito(c["id"], nueva_cuota, nuevos_pagados)

            # Botón para eliminar
            if st.button(f"🗑️ Eliminar crédito {c['id']}", key=f"del_cr_{c['id']}"):
                eliminar_credito(c["id"])
                st.success("Crédito eliminado.")


# -------------------
# FIRMA
# -------------------
st.markdown(
    "<div style='text-align:center; color:gray; margin-top:30px;'>BY <b>J-J Solutions</b></div>",
    unsafe_allow_html=True
)
