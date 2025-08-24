# =====================================
# queries.py - Funciones para Supabase
# =====================================

from supabase import Client
import streamlit as st

# -----------------------------
# TRANSACCIONES
# -----------------------------
def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    try:
        from app import supabase  # import dinámico (ya creado en app.py)
        data, error = supabase.table("transacciones").insert({
            "user_id": user_id,
            "tipo": tipo,
            "categoria": categoria,
            "monto": monto,
            "fecha": str(fecha)
        }).execute()

        if error:
            st.error(f"Error al insertar transacción: {error}")
        return data
    except Exception as e:
        st.error(f"Excepción al insertar transacción: {e}")
        return None


def obtener_transacciones(user_id):
    try:
        from app import supabase
        res = supabase.table("transacciones").select("*").eq("user_id", user_id).execute()
        return res.data if res and res.data else []
    except Exception as e:
        st.error(f"Error al obtener transacciones: {e}")
        return []


def borrar_transaccion(transaccion_id):
    try:
        from app import supabase
        res = supabase.table("transacciones").delete().eq("id", transaccion_id).execute()
        return res.data if res and res.data else []
    except Exception as e:
        st.error(f"Error al borrar transacción: {e}")
        return []


# -----------------------------
# CRÉDITOS
# -----------------------------
def insertar_credito(user_id, nombre, monto, plazo, tasa, cuota, dia_pago):
    try:
        from app import supabase
        data, error = supabase.table("creditos").insert({
            "user_id": user_id,
            "nombre": nombre,
            "monto": monto,
            "plazo": plazo,
            "tasa": tasa,
            "cuota": cuota,
            "dia_pago": dia_pago,
            "cuotas_pagadas": 0
        }).execute()

        if error:
            st.error(f"Error al insertar crédito: {error}")
        return data
    except Exception as e:
        st.error(f"Excepción al insertar crédito: {e}")
        return None


def obtener_creditos(user_id):
    try:
        from app import supabase
        res = supabase.table("creditos").select("*").eq("user_id", user_id).execute()
        return res.data if res and res.data else []
    except Exception as e:
        st.error(f"Error al obtener créditos: {e}")
        return []


def update_credito(credito_id, campos):
    """Actualizar un crédito con los campos dados en dict"""
    try:
        from app import supabase
        res = supabase.table("creditos").update(campos).eq("id", credito_id).execute()
        return res.data if res and res.data else []
    except Exception as e:
        st.error(f"Error al actualizar crédito: {e}")
        return []


def registrar_pago(credito_id, user_id, monto, fecha):
    """Registrar un pago de un crédito: inserta transacción y actualiza cuotas_pagadas"""
    try:
        from app import supabase
        # Insertamos el pago como gasto
        supabase.table("transacciones").insert({
            "user_id": user_id,
            "tipo": "Gasto",
            "categoria": "Pago crédito",
            "monto": monto,
            "fecha": str(fecha)
        }).execute()

        # Actualizamos cuotas pagadas
        credito = obtener_creditos(user_id)
        for c in credito:
            if c["id"] == credito_id:
                cuotas = c.get("cuotas_pagadas", 0) + 1
                update_credito(credito_id, {"cuotas_pagadas": cuotas})
                break
        return True
    except Exception as e:
        st.error(f"Error al registrar pago: {e}")
        return False
