from supabase import create_client, Client
import os

# Conexión a Supabase (usa variables de entorno)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# Funciones de consultas
# -------------------------

def get_user_transactions(user_id: str):
    """
    Obtiene todas las transacciones de un usuario específico.
    
    Args:
        user_id (str): ID del usuario.
    
    Returns:
        list: Lista de transacciones del usuario.
    """
    response = supabase.table("transacciones").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []


def add_transaction(user_id: str, descripcion: str, monto: float, tipo: str):
    """
    Agrega una nueva transacción para un usuario.
    
    Args:
        user_id (str): ID del usuario.
        descripcion (str): Descripción de la transacción.
        monto (float): Valor de la transacción.
        tipo (str): Tipo de transacción (ej: ingreso, egreso).
    
    Returns:
        dict: La transacción insertada o un dict vacío.
    """
    response = supabase.table("transacciones").insert({
        "user_id": user_id,
        "descripcion": descripcion,
        "monto": monto,
        "tipo": tipo
    }).execute()
    return response.data[0] if response.data else {}
