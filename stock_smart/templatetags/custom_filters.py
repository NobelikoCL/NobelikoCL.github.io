from django import template
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

register = template.Library()

@register.filter
def groupby(value, n):
    """
    Agrupa los caracteres de un string en grupos de n
    Ejemplo: "1234567" con n=3 retorna ["1", "234", "567"]
    """
    try:
        value = str(value)
        result = []
        for i in range(0, len(value), n):
            result.append(value[i:i+n])
        return result
    except Exception as e:
        return value

@register.filter
def format_price(value):
    """
    Formatea un precio en formato chileno
    Ejemplo: 1234567 -> 1.234.567
    """
    try:
        logger.info(f"Formateando precio: {value} (tipo: {type(value)})")
        
        if value is None or value == '':
            logger.warning("Valor vacío o None")
            return '0'
            
        # Si es Decimal, usarlo directamente
        if isinstance(value, Decimal):
            number = value
        # Si es float, convertir a Decimal
        elif isinstance(value, float):
            number = Decimal(str(value))
        # Si es string, limpiar y convertir
        elif isinstance(value, str):
            cleaned = value.replace('$', '').replace('.', '').replace(',', '.')
            if cleaned:
                number = Decimal(cleaned)
            else:
                logger.warning("String vacío después de limpieza")
                return '0'
        else:
            number = Decimal(str(value))
            
        logger.info(f"Número procesado: {number}")
        formatted = '{:,.0f}'.format(float(number)).replace(',', '.')
        logger.info(f"Resultado formateado: {formatted}")
        return formatted
        
    except Exception as e:
        logger.error(f"Error formateando precio: {str(e)}")
        return '0'

@register.filter
def multiply(value, arg):
    return float(value) * float(arg)

@register.filter(name='add_class')
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})

@register.filter
def status_color(status):
    colors = {
        'pending': 'warning',
        'processing': 'info',
        'shipped': 'primary',
        'delivered': 'success',
        'cancelled': 'danger'
    }
    return colors.get(status, 'secondary')

@register.filter
def payment_status_color(status):
    colors = {
        'pending': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'refunded': 'info'
    }
    return colors.get(status, 'secondary')

@register.filter
def status_progress(status):
    progress = {
        'pending': 20,
        'processing': 40,
        'shipped': 60,
        'delivered': 100,
        'cancelled': 0
    }
    return progress.get(status, 0)

@register.filter
def shipping_method_display(method):
    methods = {
        'pickup': 'Retiro en tienda',
        'starken': 'Envío Starken'
    }
    return methods.get(method, method)
