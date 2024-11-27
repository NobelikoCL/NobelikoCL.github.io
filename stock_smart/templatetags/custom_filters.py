from django import template

register = template.Library()

@register.filter
def format_price(value):
    try:
        value = str(int(float(value)))
        if len(value) > 3:
            return f"{value[:-3]}.{value[-3:]}"
        return value
    except (ValueError, TypeError):
        return "0"

@register.filter
def multiply(value, arg):
    return float(value) * float(arg)