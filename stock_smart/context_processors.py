from .models import Category, Cart, CartItem
from django.db import models
import logging

logger = logging.getLogger(__name__)

def categories_processor(request):
    try:
        # Obtener solo categorías padre (parent=None) que estén activas
        categories = Category.objects.filter(
            parent__isnull=True,
            is_active=True
        ).prefetch_related(
            'children'
        ).order_by('order', 'name')
        
        logger.info(f"Categorías principales cargadas: {categories.count()}")
        return {'categories': categories}
    
    except Exception as e:
        logger.error(f"Error al cargar categorías: {str(e)}")
        return {'categories': []}

def cart_count(request):
    count = 0
    if hasattr(request, 'visitor_id'):
        cart = Cart.objects.filter(
            visitor_id=request.visitor_id,
            is_active=True
        ).first()
        
        if cart:
            count = CartItem.objects.filter(cart=cart).aggregate(
                total_items=models.Sum('quantity')
            )['total_items'] or 0
    
    return {'cart_count': count}