# =====================================
# queries.py - Funciones para Supabase
# =====================================

import streamlit as st

# -----------------------------
# TRANSACCIONES
# -----------------------------
def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    try:
        from app import supabase  # supabase ya creado en app.py
        res = supabase.table("transacciones").insert({
            "user_id": user_id,
            "tipo": tipo,
            "categoria": categoria,
            "monto": monto,
            "fecha": str(fecha)
        }).execute()
        # SDK nuevo retorna dict-like con .data
        return getattr(res, "data", None)
    except Exception as e:
        st.error(f"Excepción al insertar transacción: {e}")
        return None

def obtener_transacciones(user_id):
    try:
        from app import supabase
        res = supabase.table("transacciones").select("*").eq("user_id", user_id).order("fecha", desc=True).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al obtener transacciones: {e}")
        return []

def borrar_transaccion(transaccion_id):
    try:
        from app import supabase
        res = supabase.table("transacciones").delete().eq("id", transaccion_id).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al borrar transacción: {e}")
        return []

# -----------------------------
# CRÉDITOS
# -----------------------------
def insertar_credito(user_id, nombre, monto, plazo, tasa, cuota, dia_pago):
    try:
        from app import supabase
        res = supabase.table("creditos").insert({
            "user_id": user_id,
            "nombre": nombre,
            "monto": monto,
            "plazo": plazo,
            "tasa": tasa,
            "cuota": cuota,
            "dia_pago": dia_pago,
            "cuotas_pagadas": 0
        }).execute()
        return getattr(res, "data", None)
    except Exception as e:
        st.error(f"Excepción al insertar crédito: {e}")
        return None

def obtener_creditos(user_id):
    try:
        from app import supabase
        res = supabase.table("creditos").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al obtener créditos: {e}")
        return []

def update_credito(credito_id, campos):
    try:
        from app import supabase
        res = supabase.table("creditos").update(campos).eq("id", credito_id).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al actualizar crédito: {e}")
        return []

def registrar_pago(credito_id, user_id, monto, fecha):
    """Registrar un pago de un crédito: inserta gasto y aumenta cuotas_pagadas."""
    try:
        from app import supabase
        # 1) Insertar gasto
        supabase.table("transacciones").insert({
            "user_id": user_id,
            "tipo": "Gasto",
            "categoria": "Pago crédito",
            "monto": monto,
            "fecha": str(fecha)
        }).execute()
        # 2) Incrementar cuotas_pagadas
        res = supabase.table("creditos").select("cuotas_pagadas").eq("id", credito_id).single().execute()
        actuales = (getattr(res, "data", {}) or {}).get("cuotas_pagadas", 0)
        supabase.table("creditos").update({"cuotas_pagadas": (actuales or 0) + 1}).eq("id", credito_id).execute()
        return True
    except Exception as e:
        st.error(f"Error al registrar pago: {e}")
        return False

# -----------------------------
# METAS (tabla: metas)
# -----------------------------
def insertar_meta(user_id, nombre, monto, ahorrado=0):
    try:
        from app import supabase
        res = supabase.table("metas").insert({
            "user_id": user_id,
            "nombre": nombre,
            "monto": monto,
            "ahorrado": ahorrado
        }).execute()
        return getattr(res, "data", None)
    except Exception as e:
        st.error(f"Excepción al insertar meta: {e}")
        return None

def obtener_metas(user_id):
    try:
        from app import supabase
        res = supabase.table("metas").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al obtener metas: {e}")
        return []

def update_meta(meta_id, campos):
    try:
        from app import supabase
        res = supabase.table("metas").update(campos).eq("id", meta_id).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al actualizar meta: {e}")
        return []

def borrar_meta(meta_id):
    try:
        from app import supabase
        res = supabase.table("metas").delete().eq("id", meta_id).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        st.error(f"Error al borrar meta: {e}")
        return []
