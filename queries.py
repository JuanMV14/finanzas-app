from supabase import create_client, Client
import os

# Conexión a Supabase (usa variables de entorno)
SUPABASE_URL = os.getenv("https://ejsakzzbgwymptqjoigs.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqc2FrenpiZ3d5bXB0cWpvaWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzOTQwOTMsImV4cCI6MjA3MDk3MDA5M30.IwadYpEJyQAR0zT4Qm6Ae1Q4ac3gqRkGVz0xzhRe3m0")

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
