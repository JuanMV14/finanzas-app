# app.py
import streamlit as st
from supabase import create_client, Client
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px

# --- CONFIGURACIÓN DE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- TÍTULO DE LA APP ---
st.title("📊 Finanzas Personales - Demo")

# --- FORMULARIO PARA REGISTRAR TRANSACCIÓN ---
with st.form("nueva_transaccion"):
    monto = st.number_input("Monto", min_value=0.0, format="%.2f")
    categoria = st.text_input("Categoría")
    tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])
    submit = st.form_submit_button("Guardar")

    if submit:
        data = {
            "monto": monto,
            "categoria": categoria,
            "tipo": tipo
        }
        supabase.table("transacciones").insert(data).execute()
        st.success("✅ Transacción guardada con éxito.")
        st.rerun()  # 👈 reemplazo de experimental_rerun

# --- MOSTRAR DATOS ---
st.subheader("📂 Mis Transacciones")
response = supabase.table("transacciones").select("*").execute()

if response.data:
    df = pd.DataFrame(response.data)
    st.dataframe(df)

    # --- GRÁFICO DE PASTEL ---
    fig = px.pie(df, names="categoria", values="monto", title="Distribución por Categoría")
    st.plotly_chart(fig)

    # --- GRÁFICO DE BARRAS ---
    fig2 = px.bar(df, x="categoria", y="monto", color="tipo", title="Ingresos vs Gastos")
    st.plotly_chart(fig2)
else:
    st.info("Aún no tienes transacciones registradas.")
