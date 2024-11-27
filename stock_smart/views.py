from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.core.paginator import Paginator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from .forms import RegisterForm, GuestCheckoutForm, UserProfileForm
from .models import CustomUser, Product, Category, Cart, CartItem, Order, FlowCredentials, OrderTracking, OrderItem
import json
from decimal import Decimal
from django.utils import timezone
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .utils.pdf_generator import InvoiceGenerator
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .services.flow_service import FlowPaymentService
import uuid
from django.contrib.humanize.templatetags.humanize import intcomma
import requests
from django.urls import reverse
import hashlib
import hmac
from datetime import datetime
import logging
import traceback
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from payments import get_payment_model, PaymentStatus, RedirectNeeded
from django.conf import settings

logger = logging.getLogger(__name__)
Payment = get_payment_model()

def get_cart_count(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        return cart.get_total_items() if cart else 0
    else:
        return len(request.session.get('cart', {}))

def index(request):
    offer_products = Product.objects.filter(discount_percentage__gt=0, active=True)[:8]
    featured_products = Product.objects.filter(active=True)[:8]
    
    context = {
        'offer_products': offer_products,
        'featured_products': featured_products,
        'main_categories': Category.objects.filter(parent=None, is_active=True)
    }
    return render(request, 'stock_smart/home.html', context)

def register_view(request):
    if request.user.is_authenticated:
        return redirect('stock_smart:account')
        
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.email  # Usamos el email como username
            user.verification_token = get_random_string(64)
            user.save()
            
            messages.success(request, 'Registro exitoso. Por favor verifica tu correo electrónico.')
            return redirect('stock_smart:login')
    else:
        form = RegisterForm()
    
    return render(request, 'stock_smart/auth/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('stock_smart:account')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.email_verified:
                login(request, user)
                messages.success(request, '¡Bienvenido de vuelta!')
                return redirect('stock_smart:account')
            else:
                messages.warning(request, 'Por favor verifica tu correo electrónico.')
        else:
            messages.error(request, 'Correo o contraseña incorrectos.')
    
    return render(request, 'stock_smart/auth/login.html')

@login_required
def account_view(request):
    return render(request, 'stock_smart/auth/account.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('stock_smart:home')

def verify_email(request, token):
    try:
        user = CustomUser.objects.get(verification_token=token)
        user.email_verified = True
        user.verification_token = None
        user.save()
        messages.success(request, '¡Email verificado exitosamente!')
    except CustomUser.DoesNotExist:
        messages.error(request, 'El enlace de verificación es inválido.')
    
    return redirect('stock_smart:login')

def search(request):
    """
    Vista para la búsqueda de productos
    """
    query = request.GET.get('q', '')
    products = []  # Lista vacía temporal
    
    # Cuando tengas el modelo Product implementado, descomenta esto:
    # if query:
    #     products = Product.objects.filter(
    #         Q(name__icontains=query) |
    #         Q(description__icontains=query)
    #     )
    
    context = {
        'query': query,
        'products': products,
    }
    return render(request, 'stock_smart/search.html', context)

def about_view(request):
    return render(request, 'stock_smart/about.html')

def contact_view(request):
    return render(request, 'stock_smart/contacto.html')

def terms_view(request):
    return render(request, 'stock_smart/terminos.html')

def tracking_view(request):
    return render(request, 'stock_smart/seguimiento.html')

def help_view(request):
    return render(request, 'stock_smart/ayuda.html')

def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Obtener productos de la categoría
    products = Product.objects.filter(
        category=category,
        stock__gt=0
    ).order_by('-created_at')
    
    # Obtener categorías para el mega menú
    main_categories = Category.objects.filter(
        parent__isnull=True,
        is_active=True
    ).prefetch_related('children')
    
    context = {
        'category': category,
        'products': products,
        'main_categories': main_categories,
    }
    return render(request, 'stock_smart/category.html', context)

@require_POST
@ensure_csrf_cookie
def add_to_cart(request):
    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        if not product_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Product ID is required'
            }, status=400)
        
        # Obtener el producto
        product = get_object_or_404(Product, id=product_id)
        
        # Obtener o crear carrito
        cart = Cart.get_active_cart(request.visitor_id)
        
        # Agregar o actualizar item en el carrito
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Obtener el nuevo total de items
        cart_count = CartItem.objects.filter(cart=cart).count()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Producto agregado al carrito',
            'cart_count': cart_count
        })
        
    except Exception as e:
        print(f"Error en add_to_cart: {str(e)}")  # Para debugging
        return JsonResponse({
            'status': 'error',
            'message': 'Error al agregar el producto al carrito'
        }, status=500)

def products(request):
    products_list = Product.objects.all()
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        products_list = products_list.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Ordenamiento
    order = request.GET.get('order')
    if order:
        if order == 'price_asc':
            products_list = products_list.order_by('price')
        elif order == 'price_desc':
            products_list = products_list.order_by('-price')
        elif order == 'name':
            products_list = products_list.order_by('name')
    
    # Paginación
    paginator = Paginator(products_list, 9)  # 9 productos por página
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
    }
    return render(request, 'stock_smart/products.html', context)

def buy_now_checkout(request, product_id):
    """Checkout para compra directa de un producto"""
    product = get_object_or_404(Product, id=product_id)
    
    # Calcular totales
    subtotal = product.final_price
    iva = subtotal * Decimal('0.19')
    total = subtotal + iva
    
    context = {
        'is_buy_now': True,
        'product': product,
        'subtotal': subtotal,
        'iva': iva,
        'total': total,
    }
    
    return render(request, 'stock_smart/checkout_options.html', context)

@login_required
def cart_checkout(request):
    """Checkout para compra de carrito completo"""
    try:
        cart = Cart.objects.get(user=request.user, is_active=True)
        
        if not cart.cartitem_set.exists():
            messages.warning(request, 'Tu carrito está vacío')
            return redirect('stock_smart:cart')
        
        # Calcular totales
        subtotal = sum(item.total for item in cart.cartitem_set.all())
        iva = subtotal * Decimal('0.19')
        total = subtotal + iva
        
        context = {
            'is_buy_now': False,
            'cart': cart,
            'cart_items': cart.cartitem_set.all(),
            'subtotal': subtotal,
            'iva': iva,
            'total': total,
        }
        
        return render(request, 'stock_smart/checkout_options.html', context)
        
    except Cart.DoesNotExist:
        messages.error(request, 'No se encontró un carrito activo')
        return redirect('stock_smart:productos_lista')

def checkout_options(request, product_id=None):
    if product_id:
        # Obtener el producto
        product = get_object_or_404(Product, id=product_id)
        
        # Calcular precios
        precio_original = product.published_price
        precio_con_descuento = product.get_final_price
        descuento = precio_original - precio_con_descuento if product.discount_percentage > 0 else Decimal('0')
        iva = precio_con_descuento * Decimal('0.19')
        total = precio_con_descuento + iva

        context = {
            'product': product,
            'precio_original': precio_original,
            'descuento': descuento,
            'precio_con_descuento': precio_con_descuento,
            'iva': iva,
            'total': total,
            'cart_count': get_cart_count(request),
        }
        
        return render(request, 'stock_smart/checkout_options.html', context)
    
    return redirect('stock_smart:home')  # Redirigir si no hay product_id

def process_payment(request):
    """Procesar el pago y crear la orden"""
    if request.method == 'POST':
        # Generar número de orden
        order_number = generate_order_number()
        
        # Obtener método de pago y envío
        payment_method = request.POST.get('payment_method')
        shipping_method = request.POST.get('shipping_method')
        
        # Crear la orden
        order = Order.objects.create(
            order_number=order_number,
            user=request.user if request.user.is_authenticated else None,
            payment_method=payment_method,
            shipping_method=shipping_method,
            status='PENDING',
            # ... otros campos ...
        )
        
        # Crear el primer evento de tracking
        OrderTracking.objects.create(
            order=order,
            status='PENDING',
            description='Orden creada, esperando pago'
        )
        
        # Guardar número de orden en sesión
        request.session['order_number'] = order_number
        
        # Redireccionar según método de pago
        if payment_method == 'FLOW':
            return redirect('stock_smart:flow_payment')
        else:  # Transferencia
            return redirect('stock_smart:transfer_instructions')
            
    return redirect('stock_smart:checkout')

def auth_page(request):
    """Página única para login/registro/recuperación"""
    if request.user.is_authenticated:
        return redirect('stock_smart:productos_lista')
    
    return render(request, 'stock_smart/auth_page.html', {
        'titulo': 'Acceso'
    })

def checkout(request):
    """Checkout para usuarios registrados"""
    if not request.user.is_authenticated:
        return redirect('stock_smart:checkout_options')
    
    cart = get_or_create_cart(request)
    if not cart.cartitem_set.exists():
        messages.warning(request, 'Tu carrito está vacío')
        return redirect('stock_smart:productos_lista')
    
    return render(request, 'stock_smart/checkout.html', {
        'titulo': 'Checkout',
        'cart': cart
    })

def guest_checkout(request):
    """Vista para proceso de checkout como invitado"""
    try:
        logger.info("Iniciando proceso de guest checkout")
        
        # Verificar si viene de compra rápida
        buy_now_data = request.session.get('buy_now_data')
        
        if request.method == 'POST':
            # Procesar el formulario
            form = GuestCheckoutForm(request.POST)
            if form.is_valid():
                # Crear el pago
                payment = Payment.objects.create(
                    variant='flow',
                    description='Compra en Stock Smart',
                    total=Decimal(str(buy_now_data.get('total', '0'))),
                    currency='CLP',
                    billing_first_name=form.cleaned_data['first_name'],
                    billing_last_name=form.cleaned_data['last_name'],
                    billing_email=form.cleaned_data['email']
                )
                
                try:
                    # Esto redirigirá automáticamente a Flow
                    return redirect(payment.get_payment_url())
                except RedirectNeeded as redirect_to:
                    return redirect(str(redirect_to))

        else:
            # GET request - mostrar formulario
            form = GuestCheckoutForm()

        # Preparar contexto
        context = {
            'form': form,
            'is_buy_now': bool(buy_now_data)
        }

        if buy_now_data:
            product = get_object_or_404(Product, id=buy_now_data['product_id'])
            context.update({
                'product': product,
                'total': buy_now_data['total']
            })
        else:
            cart = Cart.get_active_cart(request)
            if not cart or not cart.cartitem_set.exists():
                messages.warning(request, 'No hay productos en el carrito')
                return redirect('stock_smart:productos_lista')
            
            context.update({
                'cart': cart,
                'cart_items': cart.cartitem_set.all(),
                'total': cart.get_total()
            })

        return render(request, 'stock_smart/guest_checkout.html', context)

    except Exception as e:
        logger.error(f"Error en guest_checkout: {str(e)}\n{traceback.format_exc()}")
        messages.error(request, 'Error al procesar el checkout. Por favor, intente nuevamente.')
        return redirect('stock_smart:productos_lista')

def categories(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'stock_smart/categories.html', context)

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    
    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'stock_smart/categoria_detalle.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'stock_smart/producto_detalle.html', context)

@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
        # Puedes agregar más información del usuario aquí
        'orders': user.order_set.all() if hasattr(user, 'order_set') else [],
    }
    return render(request, 'stock_smart/profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('stock_smart:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'stock_smart/edit_profile.html', {
        'form': form,
        'titulo': 'Editar Perfil'
    })

@login_required
def order_history(request):
    # Aquí irá la lógica para mostrar el historial de pedidos
    return render(request, 'stock_smart/order_history.html', {
        'titulo': 'Historial de Pedidos'
    })

@login_required
def dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'No tienes permiso para acceder al panel de administración.')
        return redirect('stock_smart:productos_lista')
    
    return render(request, 'stock_smart/dashboard/index.html', {
        'titulo': 'Panel de Administración'
    })

@login_required
def manage_products(request):
    if not request.user.is_staff:
        return redirect('stock_smart:productos_lista')
    
    products = Product.objects.all()
    return render(request, 'stock_smart/dashboard/products.html', {
        'products': products,
        'titulo': 'Gestión de Productos'
    })

@login_required
def manage_orders(request):
    if not request.user.is_staff:
        return redirect('stock_smart:productos_lista')
    
    return render(request, 'stock_smart/dashboard/orders.html', {
        'titulo': 'Gestión de Pedidos'
    })

@login_required
def manage_users(request):
    if not request.user.is_staff:
        return redirect('stock_smart:productos_lista')
    
    return render(request, 'stock_smart/dashboard/users.html', {
        'titulo': 'Gestión de Usuarios'
    })

def search_products(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    ).filter(active=True)
    
    return render(request, 'stock_smart/productos_lista.html', {
        'productos': products,
        'query': query,
        'titulo': f'Resultados para: {query}'
    })

def filter_products(request):
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    products = Product.objects.filter(active=True)
    
    if category_id:
        products = products.filter(category_id=category_id)
    if min_price:
        products = products.filter(published_price__gte=min_price)
    if max_price:
        products = products.filter(published_price__lte=max_price)
    
    return render(request, 'stock_smart/productos_lista.html', {
        'productos': products,
        'titulo': 'Productos Filtrados'
    })

def get_flow_credentials():
    """Obtener credenciales activas de Flow"""
    return FlowCredentials.objects.filter(is_active=True).first()

def flow_payment(request):
    """Iniciar el proceso de pago con Flow"""
    cart = get_or_create_cart(request)
    flow_creds = get_flow_credentials()
    
    if not flow_creds:
        messages.error(request, 'Error en la configuración de pagos.')
        return redirect('stock_smart:checkout')
    
    # Crear orden en nuestra base de datos
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        cart=cart,
        total=cart.total
    )
    
    # Datos para Flow
    payment_data = {
        "commerceOrder": str(order.id),
        "subject": "Compra en Stock Smart",
        "currency": "CLP",
        "amount": int(order.total),
        "email": request.user.email if request.user.is_authenticated else request.POST.get('email'),
        "urlConfirmation": request.build_absolute_uri(reverse('stock_smart:flow_confirm')),
        "urlReturn": request.build_absolute_uri(reverse('stock_smart:flow_success')),
    }
    
    # Llamada a la API de Flow
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {flow_creds.api_key}"
    }
    
    api_url = "https://sandbox.flow.cl/api" if flow_creds.is_sandbox else "https://www.flow.cl/api"
    
    response = requests.post(
        f"{api_url}/payment/create",
        json=payment_data,
        headers=headers
    )
    
    if response.status_code == 200:
        flow_data = response.json()
        order.flow_token = flow_data['token']
        order.save()
        return redirect(flow_data['url'] + "?token=" + flow_data['token'])
    else:
        messages.error(request, 'Error al procesar el pago. Por favor, intente nuevamente.')
        return redirect('stock_smart:checkout')

@csrf_exempt
def flow_confirm(request):
    """Confirmación de pago desde Flow"""
    if request.method == "POST":
        token = request.POST.get('token')
        flow_creds = get_flow_credentials()
        
        if not flow_creds:
            return HttpResponse(status=500)
        
        # Verificar el pago con Flow
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {flow_creds.api_key}"
        }
        
        api_url = "https://sandbox.flow.cl/api" if flow_creds.is_sandbox else "https://www.flow.cl/api"
        
        response = requests.get(
            f"{api_url}/payment/getStatus",
            params={"token": token},
            headers=headers
        )
        
        if response.status_code == 200:
            payment_data = response.json()
            order = Order.objects.get(id=payment_data['commerceOrder'])
            
            if payment_data['status'] == 2:  # Pago exitoso
                order.status = 'PAID'
                order.payment_date = timezone.now()
                order.save()
                
                # Actualizar stock
                cart = order.cart
                for item in cart.cartitem_set.all():
                    product = item.product
                    product.stock -= item.quantity
                    product.save()
                
                cart.completed = True
                cart.save()
                
            return HttpResponse(status=200)
    
    return HttpResponse(status=400)

def flow_success(request):
    """Página de éxito después del pago"""
    token = request.GET.get('token')
    try:
        order = Order.objects.get(flow_token=token)
        messages.success(request, '¡Pago realizado con éxito! Gracias por tu compra.')
        return render(request, 'stock_smart/flow_success.html', {
            'order': order,
            'titulo': 'Pago Exitoso'
        })
    except Order.DoesNotExist:
        messages.error(request, 'Orden no encontrada.')
        return redirect('stock_smart:productos_lista')

def flow_failure(request):
    """Página de fallo de pago"""
    messages.error(request, 'El pago no pudo ser procesado. Por favor, intente nuevamente.')
    return render(request, 'stock_smart/flow_failure.html', {
        'titulo': 'Error en el Pago'
    })

def about(request):
    """Vista para la página Acerca de"""
    return render(request, 'stock_smart/about.html', {
        'titulo': 'Acerca de Nosotros'
    })

def contacto(request):
    """Vista para la página de contacto"""
    if request.method == 'POST':
        # Aquí puedes agregar la lógica para procesar el formulario
        messages.success(request, 'Mensaje enviado correctamente. Nos pondremos en contacto contigo pronto.')
        return redirect('stock_smart:contacto')
        
    return render(request, 'stock_smart/contacto.html', {
        'titulo': 'Contacto'
    })

def terminos(request):
    """Vista para la página de términos y condiciones"""
    return render(request, 'stock_smart/terminos.html', {
        'titulo': 'Términos y Condiciones'
    })

def tracking(request):
    """Vista para el seguimiento de pedidos"""
    order_number = request.GET.get('order_number')
    order = None
    status_info = None
    
    if order_number:
        try:
            order = Order.objects.prefetch_related(
                'tracking_history',
                'cart__cartitem_set__product'
            ).get(id=order_number)
            
            # Definir información del estado
            status_info = {
                'PENDING': {
                    'progress': 25,
                    'class': 'bg-warning',
                    'text': 'Pendiente de pago',
                    'icon': 'fa-clock'
                },
                'PAID': {
                    'progress': 50,
                    'class': 'bg-info',
                    'text': 'Pago confirmado',
                    'icon': 'fa-check-circle'
                },
                'SHIPPED': {
                    'progress': 75,
                    'class': 'bg-primary',
                    'text': 'En camino',
                    'icon': 'fa-truck'
                },
                'DELIVERED': {
                    'progress': 100,
                    'class': 'bg-success',
                    'text': 'Entregado',
                    'icon': 'fa-box-open'
                },
                'CANCELLED': {
                    'progress': 0,
                    'class': 'bg-danger',
                    'text': 'Cancelado',
                    'icon': 'fa-times-circle'
                }
            }[order.status]
            
            if not request.user.is_authenticated and order.user is not None:
                messages.error(request, 'Debes iniciar sesión para ver este pedido.')
                return redirect('stock_smart:auth_page')
                
        except Order.DoesNotExist:
            messages.error(request, 'Pedido no encontrado.')
    
    return render(request, 'stock_smart/seguimiento.html', {
        'titulo': 'Seguimiento de Pedido',
        'order': order,
        'status_info': status_info
    })

def update_cart_item(request, item_id):
    """
    Vista para actualizar la cantidad de un item en el carrito
    """
    if request.method == 'POST':
        try:
            cart_item = get_object_or_404(CartItem, id=item_id)
            quantity = int(request.POST.get('quantity', 1))
            
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Cantidad actualizada',
                    'new_quantity': quantity,
                    'new_total': cart_item.total
                })
            else:
                cart_item.delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Item eliminado del carrito'
                })
                
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Cantidad inválida'
            }, status=400)
            
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

@login_required
def cart_checkout(request):
    """
    Vista para el proceso de checkout del carrito completo
    """
    try:
        # Obtener el carrito activo del usuario
        cart = Cart.objects.get(
            user=request.user,
            is_active=True
        )
        
        # Verificar que haya items en el carrito
        if not cart.cartitem_set.exists():
            messages.warning(request, 'Tu carrito está vacío')
            return redirect('stock_smart:cart')
        
        # Calcular totales
        subtotal = sum(item.total for item in cart.cartitem_set.all())
        iva = subtotal * 0.19
        total = subtotal + iva
        
        context = {
            'cart': cart,
            'cart_items': cart.cartitem_set.all(),
            'subtotal': subtotal,
            'iva': iva,
            'total': total,
        }
        
        return render(request, 'stock_smart/cart_checkout.html', context)
        
    except Cart.DoesNotExist:
        messages.error(request, 'No se encontró un carrito activo')
        return redirect('stock_smart:productos_lista')

def generate_order_number():
    """Genera un número de orden único"""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

def cart_payment(request):
    """Vista común para proceso de pago (registrado y guest)"""
    # Obtener datos de la sesión
    checkout_data = request.session.get('checkout_data', {})
    
    if not checkout_data:
        messages.error(request, 'No hay información de checkout')
        return redirect('stock_smart:productos_lista')
    
    # Si el usuario est�� autenticado, prellenar datos
    if request.user.is_authenticated:
        context = {
            'user_data': {
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone': request.user.profile.phone,
                'address': request.user.profile.address,
                'city': request.user.profile.city,
                'region': request.user.profile.region,
            }
        }
    else:
        context = {}
    
    # Agregar datos del checkout
    context.update(checkout_data)
    
    return render(request, 'stock_smart/payment.html', context)

def cart_confirm(request):
    """
    Vista para confirmar el pedido después del pago
    """
    # Obtener el número de orden de la sesión
    order_number = request.session.get('order_number')
    
    if not order_number:
        messages.error(request, 'No se encontró información del pedido')
        return redirect('stock_smart:productos_lista')
    
    try:
        # Obtener la orden
        order = Order.objects.get(order_number=order_number)
        
        # Limpiar la sesión
        if 'order_number' in request.session:
            del request.session['order_number']
        if 'checkout_data' in request.session:
            del request.session['checkout_data']
            
        context = {
            'order': order,
            'payment_method': order.get_payment_method_display(),
            'shipping_method': order.get_shipping_method_display(),
        }
        
        return render(request, 'stock_smart/order_confirmation.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'No se encontró la orden especificada')
        return redirect('stock_smart:productos_lista')

def buy_now(request, product_id):
    """
    Vista para compra directa de un producto
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        
        if product.stock <= 0:
            messages.error(request, 'Lo sentimos, este producto está agotado.')
            return redirect('stock_smart:productos_lista')
        
        # El precio ya incluye IVA
        total = product.final_price
        
        # Guardar información en la sesión
        request.session['buy_now_data'] = {
            'product_id': product_id,
            'product_name': product.name,
            'product_price': float(product.final_price),
            'quantity': 1,
            'total': float(total),
            'timestamp': str(timezone.now())
        }
        
        context = {
            'product': product,
            'total': total,
            'is_buy_now': True
        }
        
        return render(request, 'stock_smart/checkout_options.html', context)
        
    except Product.DoesNotExist:
        messages.error(request, 'El producto no existe.')
        return redirect('stock_smart:productos_lista')
    except Exception as e:
        logger.error(f"Error en buy_now: {str(e)}")
        messages.error(request, f'Ocurrió un error al procesar la compra: {str(e)}')
        return redirect('stock_smart:productos_lista')

def buy_now_payment(request, product_id):
    """
    Procesa el pago de compra directa mediante Flow
    """
    try:
        # Obtener datos de la sesión
        buy_data = request.session.get('buy_now_data')
        if not buy_data:
            raise ValueError("No hay datos de compra en la sesión")

        # Crear orden en nuestro sistema
        order = Order.objects.create(
            order_number=generate_order_number(),
            user=request.user if request.user.is_authenticated else None,
            total_amount=buy_data['total'],
            payment_method='FLOW',
            status='PENDING'
        )

        # Preparar datos para Flow
        commerceOrder = order.order_number
        subject = f"Pago Stock Smart - Orden {commerceOrder}"
        amount = int(float(buy_data['total']))
        email = request.user.email if request.user.is_authenticated else request.POST.get('email')
        
        # URLs de respuesta
        urlConfirmation = request.build_absolute_uri(reverse('stock_smart:flow_confirm'))
        urlReturn = request.build_absolute_uri(reverse('stock_smart:flow_return'))

        # Datos para Flow
        payment_data = {
            "commerceOrder": commerceOrder,
            "subject": subject,
            "currency": "CLP",
            "amount": amount,
            "email": email,
            "urlConfirmation": urlConfirmation,
            "urlReturn": urlReturn,
            "optional": json.dumps({
                "order_type": "buy_now",
                "product_id": product_id
            })
        }

        # Firmar datos
        sign = create_flow_signature(payment_data)
        payment_data["s"] = sign

        # Enviar a Flow
        flow_response = requests.post(
            f"{settings.FLOW_API_URL}/payment/create",
            json=payment_data,
            headers={"Content-Type": "application/json"}
        )

        if flow_response.status_code == 200:
            flow_data = flow_response.json()
            if flow_data.get("url"):
                return redirect(flow_data["url"])
            else:
                raise ValueError("No se recibió URL de pago de Flow")
        else:
            raise ValueError(f"Error en Flow: {flow_response.text}")

    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('stock_smart:checkout_options')

def cart_payment(request):
    """
    Procesa el pago del carrito mediante Flow
    """
    try:
        cart = Cart.get_active_cart(request)
        if not cart or not cart.cartitem_set.exists():
            raise ValueError("Carrito vacío")

        # Crear orden
        order = Order.objects.create(
            order_number=generate_order_number(),
            user=request.user if request.user.is_authenticated else None,
            total_amount=cart.total,
            payment_method='FLOW',
            status='PENDING'
        )

        # Preparar datos para Flow
        commerceOrder = order.order_number
        subject = f"Pago Stock Smart - Orden {commerceOrder}"
        amount = int(float(cart.total))
        email = request.user.email if request.user.is_authenticated else request.POST.get('email')

        # URLs de respuesta
        urlConfirmation = request.build_absolute_uri(reverse('stock_smart:flow_confirm'))
        urlReturn = request.build_absolute_uri(reverse('stock_smart:flow_return'))

        # Datos para Flow
        payment_data = {
            "commerceOrder": commerceOrder,
            "subject": subject,
            "currency": "CLP",
            "amount": amount,
            "email": email,
            "urlConfirmation": urlConfirmation,
            "urlReturn": urlReturn,
            "optional": json.dumps({
                "order_type": "cart",
                "cart_id": cart.id
            })
        }

        # Firmar datos
        sign = create_flow_signature(payment_data)
        payment_data["s"] = sign

        # Enviar a Flow
        flow_response = requests.post(
            f"{settings.FLOW_API_URL}/payment/create",
            json=payment_data,
            headers={"Content-Type": "application/json"}
        )

        if flow_response.status_code == 200:
            flow_data = flow_response.json()
            if flow_data.get("url"):
                return redirect(flow_data["url"])
            else:
                raise ValueError("No se recibió URL de pago de Flow")
        else:
            raise ValueError(f"Error en Flow: {flow_response.text}")

    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect('stock_smart:cart')

def create_flow_signature(data):
    """
    Crea la firma para Flow
    """
    # Ordenar keys alfabéticamente
    sorted_data = dict(sorted(data.items()))
    
    # Concatenar valores
    values_string = ''.join(str(value) for value in sorted_data.values())
    
    # Crear firma
    secret_key = settings.FLOW_SECRET_KEY.encode('utf-8')
    signature = hmac.new(secret_key, 
                        values_string.encode('utf-8'), 
                        hashlib.sha256).hexdigest()
    
    return signature

def flow_return(request):
    """
    Vista de retorno después del pago en Flow
    """
    try:
        token = request.GET.get('token')
        if not token:
            token = request.POST.get('token')
        
        # Verificar el estado del pago
        params = {
            'apiKey': settings.FLOW_API_KEY,
            'token': token
        }
        params['s'] = generate_signature(params)
        
        response = requests.get(
            'https://sandbox.flow.cl/api/payment/getStatus',
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            try:
                order = Order.objects.get(flow_token=token)
                
                if data['status'] == 2:  # Pago exitoso
                    order.status = 'PAID'
                    order.save()
                    
                    # Actualizar stock
                    for item in order.orderitem_set.all():
                        product = item.product
                        product.stock -= item.quantity
                        product.save()
                    
                    # Limpiar carrito
                    if 'cart_id' in request.session:
                        del request.session['cart_id']
                    
                    messages.success(request, '¡Pago realizado con éxito!')
                    return render(request, 'stock_smart/payment_success.html', {
                        'order': order
                    })
                else:
                    order.status = 'FAILED'
                    order.save()
                    messages.error(request, 'El pago no pudo ser procesado')
                    return render(request, 'stock_smart/payment_failed.html', {
                        'order': order
                    })
                    
            except Order.DoesNotExist:
                messages.error(request, 'Orden no encontrada')
                return redirect('stock_smart:guest_checkout')
                
        else:
            raise ValueError(f"Error en la respuesta de Flow: {response.text}")
            
    except Exception as e:
        logger.error(f"Error en flow_return: {str(e)}")
        messages.error(request, 'Error al procesar el pago')
        return redirect('stock_smart:guest_checkout')

@csrf_exempt
def flow_confirm(request):
    """Webhook para confirmación de Flow"""
    try:
        token = request.POST.get('token')
        
        # Verificar el pago
        params = {
            'apiKey': settings.FLOW_API_KEY,
            'token': token
        }
        params['s'] = generate_signature(params)
        
        response = requests.get(
            'https://sandbox.flow.cl/api/payment/getStatus',
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            try:
                order = Order.objects.get(flow_token=token)
                order.status = 'PAID' if data['status'] == 2 else 'FAILED'
                order.save()
                
                return HttpResponse(status=200)
            except Order.DoesNotExist:
                return HttpResponse(status=404)
        else:
            return HttpResponse(status=400)
            
    except Exception as e:
        logger.error(f"Error en flow_confirm: {str(e)}")
        return HttpResponse(status=500)

def buy_now_confirm(request, product_id):
    """
    Vista para confirmar la compra rápida de un producto
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Verificar stock
        if product.stock <= 0:
            messages.error(request, 'Lo sentimos, este producto está agotado.')
            return redirect('stock_smart:productos_lista')
        
        # Calcular total
        total = product.final_price
        
        # Guardar información en la sesión
        request.session['buy_now_data'] = {
            'product_id': product_id,
            'total': float(total),
            'is_buy_now': True
        }
        
        # Redirigir al checkout
        return redirect('stock_smart:guest_checkout')
        
    except Exception as e:
        logger.error(f"Error en buy_now_confirm: {str(e)}")
        messages.error(request, 'Error al procesar la compra rápida. Por favor, intente nuevamente.')
        return redirect('stock_smart:productos_lista')

@require_http_methods(["POST"])
def update_cart_api(request):
    """
    API endpoint para actualizar el carrito de forma asíncrona
    """
    try:
        data = json.loads(request.body)
        action = data.get('action')
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))

        # Obtener o crear carrito
        cart = Cart.get_active_cart(request)
        product = get_object_or_404(Product, id=product_id)

        if action == 'add':
            # Agregar o actualizar item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

        elif action == 'update':
            # Actualizar cantidad
            cart_item = get_object_or_404(CartItem, cart=cart, product=product)
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()

        elif action == 'remove':
            # Eliminar item
            CartItem.objects.filter(cart=cart, product=product).delete()

        # Calcular totales
        cart_total = sum(item.total for item in cart.cartitem_set.all())
        cart_count = cart.cartitem_set.count()

        return JsonResponse({
            'success': True,
            'cart_total': float(cart_total),
            'cart_count': cart_count,
            'message': 'Carrito actualizado exitosamente'
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Producto no encontrado'
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Error al actualizar el carrito'
        }, status=500)

def generate_order_number():
    """Genera un número de orden único"""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

def process_guest_order(request):
    """
    Procesa la orden de un invitado y redirige al pago
    """
    if request.method == 'POST':
        try:
            # Obtener datos de la sesión
            checkout_data = request.session.get('checkout_data', {})
            if not checkout_data:
                raise ValueError("No hay datos de checkout")

            # Crear la orden
            order = Order.objects.create(
                order_number=generate_order_number(),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                total_amount=checkout_data.get('total'),
                status='PENDING'
            )

            # Crear items de la orden
            if checkout_data.get('is_buy_now'):
                product = Product.objects.get(id=checkout_data['product_id'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=1,
                    price=product.final_price
                )
            else:
                cart = Cart.objects.get(id=checkout_data['cart_id'])
                for item in cart.cartitem_set.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.final_price
                    )

            # Preparar datos para Flow
            flow_data = {
                'commerceOrder': order.order_number,
                'subject': f'Orden #{order.order_number}',
                'currency': 'CLP',
                'amount': int(float(order.total_amount)),
                'email': order.email,
                'urlConfirmation': request.build_absolute_uri(reverse('stock_smart:flow_confirm')),
                'urlReturn': request.build_absolute_uri(reverse('stock_smart:flow_return')),
                'apiKey': settings.FLOW_API_KEY
            }

            # Ordenar y firmar
            sorted_params = dict(sorted(flow_data.items()))
            sign_string = ''
            for key, value in sorted_params.items():
                sign_string += str(value)

            # Generar firma
            secret_key = settings.FLOW_SECRET_KEY.encode('utf-8')
            signature = hmac.new(
                secret_key,
                sign_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Agregar firma a los datos
            flow_data['s'] = signature

            # Llamada a Flow
            response = requests.post(
                'https://sandbox.flow.cl/api/payment/create',
                json=flow_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                flow_response = response.json()
                order.flow_token = flow_response.get('token')
                order.save()
                
                # Redirigir a Flow
                return redirect(f"https://sandbox.flow.cl/app/web/pay.php?token={flow_response['token']}")
            else:
                logger.error(f"Error de Flow: {response.text}")
                raise ValueError(f"Error al crear pago en Flow: {response.text}")

        except Product.DoesNotExist:
            messages.error(request, 'Producto no encontrado')
            return redirect('stock_smart:productos_lista')
        except Exception as e:
            logger.error(f"Error en process_guest_order: {str(e)}")
            messages.error(request, f'Error al procesar la orden: {str(e)}')
            return redirect('stock_smart:productos_lista')

    return redirect('stock_smart:productos_lista')

def transfer_instructions(request, order_id):
    """
    Muestra las instrucciones para transferencia bancaria
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        context = {
            'order': order,
            'bank_info': {
                'bank_name': 'Banco Estado',
                'account_type': 'Cuenta Corriente',
                'account_number': '123456789',
                'rut': '76.543.210-K',
                'name': 'Stock Smart SpA',
                'email': 'pagos@stocksmart.cl'
            }
        }
        
        return render(request, 'stock_smart/transfer_instructions.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'Orden no encontrada')
        return redirect('stock_smart:checkout_options')
    except Exception as e:
        logger.error(f"Error al mostrar instrucciones de transferencia: {str(e)}")
        messages.error(request, 'Error al procesar la solicitud')
        return redirect('stock_smart:checkout_options')

@csrf_exempt
def flow_confirmation(request):
    """Endpoint que recibe la confirmación de Flow"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('commerceOrder')
            flow_status = data.get('status')
            
            # Actualizar el estado de la orden según la respuesta de Flow
            order = Order.objects.get(id=order_id)
            if flow_status == 'READY':  # Pago exitoso
                order.status = 'paid'
                order.save()
                return HttpResponse(status=200)
            else:
                order.status = 'failed'
                order.save()
                return HttpResponse(status=200)
                
        except Exception as e:
            logger.error(f"Error en flow_confirmation: {str(e)}")
            return HttpResponse(status=500)
    return HttpResponse(status=405)

def flow_return(request):
    """Vista que maneja el retorno del usuario desde Flow"""
    try:
        token = request.GET.get('token')
        if not token:
            token = request.POST.get('token')
        
        # Verificar el estado del pago
        params = {
            'apiKey': settings.FLOW_API_KEY,
            'token': token
        }
        params['s'] = generate_signature(params)
        
        response = requests.get(
            'https://sandbox.flow.cl/api/payment/getStatus',
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            try:
                order = Order.objects.get(flow_token=token)
                
                if data['status'] == 2:  # Pago exitoso
                    order.status = 'PAID'
                    order.save()
                    
                    # Actualizar stock
                    for item in order.orderitem_set.all():
                        product = item.product
                        product.stock -= item.quantity
                        product.save()
                    
                    # Limpiar carrito
                    if 'cart_id' in request.session:
                        del request.session['cart_id']
                    
                    messages.success(request, '¡Pago realizado con éxito!')
                    return render(request, 'stock_smart/payment_success.html', {
                        'order': order
                    })
                else:
                    order.status = 'FAILED'
                    order.save()
                    messages.error(request, 'El pago no pudo ser procesado')
                    return render(request, 'stock_smart/payment_failed.html', {
                        'order': order
                    })
                    
            except Order.DoesNotExist:
                messages.error(request, 'Orden no encontrada')
                return redirect('stock_smart:guest_checkout')
                
        else:
            raise ValueError(f"Error en la respuesta de Flow: {response.text}")
            
    except Exception as e:
        logger.error(f"Error en flow_return: {str(e)}")
        messages.error(request, 'Error al procesar el pago')
        return redirect('stock_smart:guest_checkout')

def process_flow_payment(request):
    """
    Procesa el pago con Flow en modo sandbox
    """
    try:
        logger.info("Iniciando proceso de pago con Flow")
        
        # Obtener datos del checkout
        checkout_data = request.session.get('checkout_data', {})
        if not checkout_data:
            raise ValueError("No hay datos de checkout disponibles")

        # Convertir el total a un entero sin decimales
        total = checkout_data.get('total', 0)
        if isinstance(total, str):
            total = total.replace(',', '').replace('.', '')
        else:
            total = int(float(total))
        
        logger.info(f"Total formateado para Flow: {total}")

        # Generar número de orden único
        order_number = str(uuid.uuid4())[:20]
        
        # Preparar datos para Flow
        payment_data = {
            'apiKey': settings.FLOW_API_KEY,
            'commerceOrder': order_number,
            'subject': f'Compra Stock Smart #{order_number}',
            'currency': 'CLP',
            'amount': total,  # Ahora es un entero limpio
            'email': request.POST.get('email'),
            'urlConfirmation': request.build_absolute_uri(reverse('stock_smart:flow_confirm')),
            'urlReturn': request.build_absolute_uri(reverse('stock_smart:flow_return')),
        }

        logger.info(f"Datos de pago preparados: {payment_data}")
        
        # Ordenar parámetros alfabéticamente
        sorted_params = dict(sorted(payment_data.items()))
        
        # Crear string para firma
        sign_string = ''
        for key, value in sorted_params.items():
            sign_string += str(value)

        # Generar firma
        secret_key = settings.FLOW_SECRET_KEY.encode('utf-8')
        signature = hmac.new(
            secret_key,
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Agregar firma a los datos
        payment_data['s'] = signature

        logger.info("Enviando solicitud a Flow")
        
        # Hacer petición a Flow
        response = requests.post(
            'https://sandbox.flow.cl/api/payment/create',
            json=payment_data,
            headers={'Content-Type': 'application/json'}
        )

        logger.info(f"Respuesta de Flow: {response.status_code} - {response.text}")

        if response.status_code == 200:
            flow_response = response.json()
            
            # Guardar información del pago en la sesión
            request.session['flow_payment'] = {
                'token': flow_response['token'],
                'order_number': order_number
            }
            
            # Crear orden en la base de datos
            order = Order.objects.create(
                order_number=order_number,
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                total_amount=Decimal(str(checkout_data.get('total', 0))),
                flow_token=flow_response['token'],
                status='PENDING'
            )

            # Guardar items de la orden
            if checkout_data.get('is_buy_now'):
                product = Product.objects.get(id=checkout_data['product_id'])
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=1,
                    price=product.final_price
                )
            else:
                cart = Cart.get_active_cart(request)
                for item in cart.cartitem_set.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.final_price
                    )

            # Redirigir a la página de pago de Flow
            payment_url = f"{flow_response['url']}?token={flow_response['token']}"
            logger.info(f"Redirigiendo a Flow: {payment_url}")
            return redirect(payment_url)

        else:
            raise ValueError(f"Error en la respuesta de Flow: {response.text}")

    except Exception as e:
        logger.error(f"Error en process_flow_payment: {str(e)}")
        messages.error(request, 'Error al procesar el pago. Por favor, intente nuevamente.')
        return redirect('stock_smart:guest_checkout')

@csrf_exempt
def payment_notify(request):
    """Webhook para notificaciones de Flow"""
    Payment = get_payment_model()
    try:
        payment_id = request.POST.get('payment_id')
        payment = Payment.objects.get(id=payment_id)
        payment.status = PaymentStatus.CONFIRMED
        payment.save()
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(f"Error en payment_notify: {str(e)}")
        return HttpResponse(status=500)

def payment_success(request):
    """Vista para pago exitoso"""
    payment_id = request.GET.get('payment_id')
    try:
        payment = Payment.objects.get(id=payment_id)
        messages.success(request, '¡Pago procesado exitosamente!')
        return render(request, 'stock_smart/payment_success.html', {'payment': payment})
    except Payment.DoesNotExist:
        messages.error(request, 'Pago no encontrado')
        return redirect('stock_smart:checkout')

def payment_failed(request):
    """Vista para pago fallido"""
    messages.error(request, 'El pago no pudo ser procesado')
    return redirect('stock_smart:checkout')

def generate_signature(params):
    """Genera la firma HMAC para Flow"""
    sorted_params = ''.join(f"{key}{value}" for key, value in sorted(params.items()))
    signature = hmac.new(
        settings.FLOW_SECRET_KEY.encode('utf-8'), 
        sorted_params.encode('utf-8'), 
        hashlib.sha256
    ).hexdigest()
    return signature

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            completed=False
        )
    else:
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart = Cart.objects.filter(id=cart_id, completed=False).first()
            if not cart:
                cart = Cart.objects.create()
                request.session['cart_id'] = cart.id
        else:
            cart = Cart.objects.create()
            request.session['cart_id'] = cart.id
    return cart

def cart_view(request):
    cart = Cart.get_active_cart(request.visitor_id)
    cart_items = CartItem.objects.filter(cart=cart)
    
    # Calcular totales
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    total_discount = sum(
        (item.product.price - item.product.get_final_price) * item.quantity 
        for item in cart_items
    )
    total = subtotal - total_discount

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'total_discount': total_discount,
        'total': total,
        'main_categories': Category.objects.filter(parent=None, is_active=True)
    }
    
    return render(request, 'stock_smart/cart.html', context)

def update_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        change = data.get('change')
        
        cart = Cart.get_active_cart(request.visitor_id)
        product = get_object_or_404(Product, id=product_id)
        cart_item = get_object_or_404(CartItem, cart=cart, product=product)
        
        # Actualizar cantidad
        cart_item.quantity = max(1, cart_item.quantity + change)
        cart_item.save()
        
        # Recalcular totales
        cart_items = CartItem.objects.filter(cart=cart)
        subtotal = sum(item.product.price * item.quantity for item in cart_items)
        total_discount = sum(
            (item.product.price - item.product.get_final_price) * item.quantity 
            for item in cart_items
        )
        total = subtotal - total_discount
        
        return JsonResponse({
            'success': True,
            'item_total': cart_item.product.get_final_price * cart_item.quantity,
            'subtotal': subtotal,
            'total_discount': total_discount,
            'total': total,
            'cart_count': sum(item.quantity for item in cart_items)
        })
    
    return JsonResponse({'success': False}, status=400)

def remove_from_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if request.user.is_authenticated:
            cart = Cart.objects.get(user=request.user)
            cart.cartitem_set.filter(product_id=product_id).delete()
        else:
            cart = request.session.get('cart', {})
            if str(product_id) in cart:
                del cart[str(product_id)]
                request.session['cart'] = cart
                request.session.modified = True
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    # Obtener productos de la categoría actual y sus subcategorías
    categories = [category]
    if category.children.exists():
        categories.extend(category.children.all())
        for child in category.children.all():
            if child.children.exists():
                categories.extend(child.children.all())
    
    products = Product.objects.filter(
        category__in=categories,
        active=True
    ).distinct()
    
    context = {
        'category': category,
        'products': products,
        'main_categories': Category.objects.filter(parent=None, is_active=True)
    }
    return render(request, 'stock_smart/category_products.html', context)

def view_cart(request):
    # Obtener carrito del visitante
    cart = Cart.get_cart_for_visitor(request.visitor_id)
    cart_items = CartItem.objects.filter(cart=cart)
    
    context = {
        'cart_items': cart_items,
        'cart_total': sum(item.subtotal for item in cart_items),
        'main_categories': Category.objects.filter(parent=None, is_active=True)
    }
    return render(request, 'stock_smart/cart.html', context)

def productos_lista(request):
    featured_products = Product.objects.filter(
        is_featured=True,
        active=True
    )[:8]  # Limitar a 8 productos destacados

    discounted_products = Product.objects.filter(
        discount_percentage__gt=0,
        active=True
    )[:8]  # Limitar a 8 productos con descuento

    context = {
        'featured_products': featured_products,
        'discounted_products': discounted_products,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'stock_smart/products.html', context)

@login_required
def checkout_direct(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Crear un CartItem temporal o redirigir directamente al checkout
    cart_item = CartItem.objects.create(
        user=request.user,
        product=product,
        quantity=1
    )
    # Redirigir al proceso de checkout
    return redirect('stock_smart:cart_view')  # O a tu vista de checkout existente

def checkout_options(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product,
        'final_price': product.get_final_price,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'stock_smart/checkout_options.html', context)

def checkout_guest(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'stock_smart/guest_checkout.html', context)
