from .models import Category, Cart, CartItem
from django.db import models

def categories_processor(request):
    main_categories = Category.objects.filter(parent=None, is_active=True)
    return {
        'main_categories': main_categories
    }

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