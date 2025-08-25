from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# TRANSACCIONES
# -------------------------
def insertar_transaccion(user_id, tipo, categoria, monto, fecha):
    return supabase.table("transacciones").insert({
        "user_id": str(user_id),
        "tipo": tipo,
        "categoria": categoria,
        "monto": float(monto),
        "fecha": str(fecha),
    }).execute()

def borrar_transaccion(user_id, trans_id):
    return supabase.table("transacciones").delete().eq("id", trans_id).eq("user_id", str(user_id)).execute()

def obtener_transacciones(user_id):
    return supabase.table("transacciones").select("*").eq("user_id", str(user_id)).order("fecha", desc=True).execute().data

# -------------------------
# CREDITOS
# -------------------------
def insertar_credito(user_id, nombre, monto, tasa, plazo_meses, cuotas_pagadas, cuota_mensual):
    return supabase.table("credito").insert({
        "user_id": str(user_id),
        "nombre": nombre,
        "monto": float(monto),
        "tasa_interes": float(tasa),
        "plazo_meses": int(plazo_meses),
        "cuotas_pagadas": int(cuotas_pagadas),
        "cuota_mensual": float(cuota_mensual),
    }).execute()

def obtener_creditos(user_id):
    return supabase.table("credito").select("*").eq("user_id", str(user_id)).execute().data

def update_credito(credito_id, fields: dict):
    return supabase.table("credito").update(fields).eq("id", credito_id).execute()

def registrar_pago(credito_id, monto, user_id):
    # 1. Insertar el pago en transacciones
    supabase.table("transacciones").insert({
        "user_id": str(user_id),
        "tipo": "Gasto",
        "categoria": "Pago crédito",
        "monto": float(monto),
        "fecha": str(date.today())
    }).execute()

    # 2. Actualizar cuotas pagadas
    credito = supabase.table("credito").select("*").eq("id", credito_id).single().execute().data
    if credito:
        nuevas = credito["cuotas_pagadas"] + 1
        return update_credito(credito_id, {"cuotas_pagadas": nuevas})
