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
