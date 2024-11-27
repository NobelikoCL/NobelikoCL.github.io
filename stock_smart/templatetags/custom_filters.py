from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def format_price(value):
    """
    Formatea un precio con punto como separador de miles
    Ejemplo: 1234567 -> 1.234.567
    """
    try:
        # Convertir a Decimal si es string
        if isinstance(value, str):
            value = Decimal(value)
            
        # Formatear el número
        value = '{:,.0f}'.format(value)
        # Reemplazar la coma por punto
        value = value.replace(',', '.')
        
        return value
    except:
        return value

@register.filter
def multiply(value, arg):
    return float(value) * float(arg)