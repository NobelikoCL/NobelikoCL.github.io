from django import template

register = template.Library()

@register.filter
def format_price(value):
    try:
        # Convertir a string y remover decimales
        num_str = f"{float(value):,.0f}"
        # Reemplazar la coma por punto
        return num_str.replace(',', '.')
    except:
        return value

@register.filter
def multiply(value, arg):
    return float(value) * float(arg)