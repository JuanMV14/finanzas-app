# -------------------------
# Funciones de utilidad
# -------------------------

def format_currency(value: float) -> str:
    """
    Formatea un número como moneda en pesos colombianos.
    
    Args:
        value (float): Valor numérico.
    
    Returns:
        str: Valor formateado en COP.
    """
    return f"${value:,.0f} COP"


def validate_amount(amount: float) -> bool:
    """
    Valida que el monto sea positivo.
    
    Args:
        amount (float): Valor numérico.
    
    Returns:
        bool: True si es válido, False si no.
    """
    return amount > 0


def calculate_balance(transactions: list) -> float:
    """
    Calcula el balance total de una lista de transacciones.
    
    Args:
        transactions (list): Lista de dicts con clave 'monto' y 'tipo'.
    
    Returns:
        float: Balance calculado.
    """
    balance = 0
    for tx in transactions:
        if tx["tipo"] == "ingreso":
            balance += tx["monto"]
        elif tx["tipo"] == "egreso":
            balance -= tx["monto"]
    return balance
