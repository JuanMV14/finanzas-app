from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    payload = {
        "user_id": str(user_id),
        "tipo": tipo,
        "categoria": categoria,
        "monto": float(monto),
        "fecha": str(fecha),
    }
    return supabase.table("transacciones").insert(payload).execute()

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

def borrar_transaccion(user_id, trans_id):
    return (
        supabase.table("transacciones")
        .delete()
        .eq("id", trans_id)
        .eq("user_id", str(user_id))
        .execute()
    )

def obtener_transacciones(user_id):
    return (
        supabase.table("transacciones")
        .select("*")
        .eq("user_id", str(user_id))
        .order("fecha", desc=True)
        .execute()
        .data
    )

def obtener_creditos(user_id):
    return (
        supabase.table("credito")
        .select("*")
        .eq("user_id", str(user_id))
        .execute()
        .data
    )

def update_credito(credito_id, fields: dict):
    """
    Actualiza cualquier campo de un crédito en la tabla 'credito'.
    Ejemplo: update_credito("uuid-del-credito", {"cuotas_pagadas": 5})
    """
    return (
        supabase.table("credito")
        .update(fields)
        .eq("id", str(credito_id))
        .execute()
    )

def registrar_pago(credito_id):
    """
    Aumenta en 1 la cuota pagada de un crédito.
    """
    # 1. Traer el crédito
    credito = (
        supabase.table("credito")
        .select("cuotas_pagadas, plazo_meses")
        .eq("id", str(credito_id))
        .single()
        .execute()
        .data
    )

    if not credito:
        return {"error": "Crédito no encontrado"}

    cuotas_actuales = credito["cuotas_pagadas"]
    plazo = credito["plazo_meses"]

    if cuotas_actuales >= plazo:
        return {"error": "El crédito ya está totalmente pagado"}

    # 2. Actualizar
    return (
        supabase.table("credito")
        .update({"cuotas_pagadas": cuotas_actuales + 1})
        .eq("id", str(credito_id))
        .execute()
    )
