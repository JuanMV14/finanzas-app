from supabase import create_client
import streamlit as st

# Aquí van tus credenciales de Supabase
url = "https://ejsakzzbgwymptqjoigs.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0"
supabase = create_client(url, key)


import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Configuración de la página
st.set_page_config(page_title="💰 Finanzas Personales", layout="wide")

st.title("💰 Finanzas Personales App")
st.subheader("Tu asistente financiero personalizado")

# --- Sidebar para ingreso de transacciones ---
st.sidebar.header("📥 Nueva Transacción")
tipo = st.sidebar.selectbox("Tipo", ["Ingreso", "Gasto"])
categoria = st.sidebar.selectbox("Categoría", ["Salario", "Alimentación", "Transporte", "Ocio", "Otros"])
monto = st.sidebar.number_input("Monto", min_value=0.0, format="%.2f")
fecha = st.sidebar.date_input("Fecha")

if st.sidebar.button("Agregar"):
    nueva = {"Fecha": fecha, "Tipo": tipo, "Categoría": categoria, "Monto": monto}
    if "data" not in st.session_state:
        st.session_state.data = []
    st.session_state.data.append(nueva)
    st.sidebar.success("✅ Transacción agregada")

# --- Historial de transacciones ---
st.header("📋 Historial de Transacciones")
if "data" in st.session_state and st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    st.dataframe(df)

    # --- KPIs ---
    ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
    gastos = df[df["Tipo"] == "Gasto"]["Monto"].sum()
    ahorro = ingresos - gastos

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Totales", f"${ingresos:.2f}")
    col2.metric("Gastos Totales", f"${gastos:.2f}")
    col3.metric("Ahorro", f"${ahorro:.2f}")

    # --- Gráfico de gastos por categoría ---
    st.subheader("📊 Distribución de Gastos por Categoría")
    gastos_df = df[df["Tipo"] == "Gasto"]
    if not gastos_df.empty:
        fig, ax = plt.subplots()
        gastos_df.groupby("Categoría")["Monto"].sum().plot(kind="bar", ax=ax, color="salmon")
        ax.set_ylabel("Monto ($)")
        ax.set_title("Gastos por Categoría")
        st.pyplot(fig)
else:
    st.info("No hay transacciones registradas aún.")

# --- Módulo de créditos ---
st.header("💳 Gestión de Créditos")

with st.expander("➕ Agregar nuevo crédito"):
    nombre_credito = st.text_input("Nombre del crédito")
    monto_credito = st.number_input("Monto del crédito", min_value=0.0, format="%.2f")
    tasa_interes = st.number_input("Tasa de interés anual (%)", min_value=0.0, format="%.2f")
    plazo_meses = st.number_input("Plazo en meses", min_value=1)

    if st.button("Calcular cuota mensual"):
        if tasa_interes == 0:
            cuota = monto_credito / plazo_meses
        else:
            tasa_mensual = tasa_interes / 100 / 12
            cuota = monto_credito * (tasa_mensual * (1 + tasa_mensual)**plazo_meses) / ((1 + tasa_mensual)**plazo_meses - 1)

        total_pagado = cuota * plazo_meses
        interes_total = total_pagado - monto_credito

        st.success(f"📌 Cuota mensual: ${cuota:.2f}")
        st.write(f"💰 Total pagado: ${total_pagado:.2f}")
        st.write(f"📈 Interés total: ${interes_total:.2f}")

        # Simulación de pago acelerado
        st.subheader("⚡ Simulación de pago acelerado")
        pago_extra = st.number_input("Pago extra mensual", min_value=0.0, format="%.2f")
        if pago_extra > 0:
            nuevo_cuota = cuota + pago_extra
            saldo = monto_credito
            meses = 0
            while saldo > 0:
                interes_mes = saldo * (tasa_interes / 100 / 12)
                principal = nuevo_cuota - interes_mes
                saldo -= principal
                meses += 1
                if saldo <= 0:
                    break
            st.info(f"🏁 Con pago extra, terminarías en {meses} meses")
