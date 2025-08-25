from supabase import create_client, Client
import os
from dotenv import load_dotenv

# -------------------------
# CONFIG
# -------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# TRANSACCIONES
# -------------------------
def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    payload = {
        "user_id": str(user_id),
        "tipo": tipo,
        "categoria": categoria,
        "monto": float(monto),
        "fecha": str(fecha),
    }
    return supabase.table("transacciones").insert(payload).execute()

def obtener_transacciones(user_id):
    return (
        supabase.table("transacciones")
        .select("*")
        .eq("user_id", str(user_id))
        .order("fecha", desc=True)
        .execute()
        .data
    )

def borrar_transaccion(user_id, trans_id):
    return (
        supabase.table("transacciones")
        .delete()
        .eq("id", trans_id)
        .eq("user_id", str(user_id))
        .execute()
    )

# -------------------------
# CRÉDITOS
# -------------------------
def insertar_credito(user_id, nombre, monto, tasa, plazo_meses, cuotas_pagadas, cuota_mensual):
    payload = {
        "user_id": str(user_id),
        "nombre": nombre,
        "monto": float(monto),
        "tasa_interes": float(tasa),
        "plazo_meses": int(plazo_meses),
        "cuotas_pagadas": int(cuotas_pagadas),
        "cuota_mensual": float(cuota_mensual),
    }
    return supabase.table("credito").insert(payload).execute()

def obtener_creditos(user_id):
    return (
        supabase.table("credito")
        .select("*")
        .eq("user_id", str(user_id))
        .execute()
        .data
    )

def update_credito(credito_id, data: dict):
    return (
        supabase.table("credito")
        .update(data)
        .eq("id", credito_id)
        .execute()
    )

def registrar_pago(credito_id):
    """
    Aumenta en 1 la cuota pagada de un crédito.
    """
    credito = (
        supabase.table("credito")
        .select("cuotas_pagadas")
        .eq("id", credito_id)
        .single()
        .execute()
    )
    if credito.data:
        nuevas_cuotas = credito.data["cuotas_pagadas"] + 1
        return (
            supabase.table("credito")
            .update({"cuotas_pagadas": nuevas_cuotas})
            .eq("id", credito_id)
            .execute()
        )
    return None

# -------------------------
# METAS DE AHORRO
# -------------------------
def insertar_meta(user_id, nombre, monto, ahorrado):
    payload = {
        "user_id": str(user_id),
        "nombre": nombre,
        "monto": float(monto),
        "ahorrado": float(ahorrado),
    }
    return supabase.table("metas").insert(payload).execute()

def obtener_metas(user_id):
    return (
        supabase.table("metas")
        .select("*")
        .eq("user_id", str(user_id))
        .execute()
        .data
    )

def actualizar_meta(meta_id, nuevo_valor):
    return (
        supabase.table("metas")
        .update({"ahorrado": float(nuevo_valor)})
        .eq("id", meta_id)
        .execute()
    )
