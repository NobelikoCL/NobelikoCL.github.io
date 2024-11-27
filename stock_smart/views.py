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
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            
            # Obtener el producto
            product = get_object_or_404(Product, id=product_id)
            
            # Inicializar o obtener el carrito de la sesión
            cart = request.session.get('cart', {})
            
            # Convertir el ID a string ya que las keys de session deben ser strings
            product_id_str = str(product_id)
            
            # Si el producto ya está en el carrito, incrementar cantidad
            if product_id_str in cart:
                # Verificar stock disponible
                if cart[product_id_str]['quantity'] < product.stock:
                    cart[product_id_str]['quantity'] += 1
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Stock no disponible'
                    })
            else:
                # Agregar nuevo producto al carrito
                if product.stock > 0:
                    cart[product_id_str] = {
                        'quantity': 1,
                        'price': str(product.get_final_price),
                        'name': product.name
                    }
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Producto sin stock'
                    })
            
            # Guardar carrito actualizado en la sesión
            request.session['cart'] = cart
            request.session.modified = True
            
            # Calcular total de items en el carrito
            cart_count = sum(item['quantity'] for item in cart.values())
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count,
                'message': 'Producto agregado al carrito'
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado'
            })
        except Exception as e:
            print(f"Error en add_to_cart: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False})

def products(request):
    products_list = Product.objects.all()
    
    # Búsqueda
    query = request.GET.get('q')
    if query:
        products_list = products_list.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )  # Aquí faltaba cerrar el paréntesis
    
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
        try:
            # Obtener el producto
            product = get_object_or_404(Product, id=product_id)
            
            # Debug del producto
            logger.debug("="*50)
            logger.debug("INFORMACIÓN DEL PRODUCTO")
            logger.debug(f"ID: {product.id}")
            logger.debug(f"Nombre: {product.name}")
            logger.debug(f"Precio publicado: {product.published_price}")
            logger.debug(f"Tipo de precio publicado: {type(product.published_price)}")
            logger.debug(f"Descuento %: {product.discount_percentage}")
            logger.debug(f"Tipo de descuento: {type(product.discount_percentage)}")
            
            # Calcular valores
            precio_original = Decimal(str(product.published_price))
            
            # Debug de cálculos
            logger.debug("\nCÁLCULOS DE PRECIOS")
            logger.debug(f"Precio original: {precio_original}")
            
            # Calcular descuento
            if product.discount_percentage and product.discount_percentage > 0:
                descuento_decimal = Decimal(str(product.discount_percentage)) / Decimal('100')
                descuento_monto = precio_original * descuento_decimal
                precio_con_descuento = precio_original - descuento_monto
                
                logger.debug(f"Descuento decimal: {descuento_decimal}")
                logger.debug(f"Monto descuento: {descuento_monto}")
            else:
                descuento_monto = Decimal('0')
                precio_con_descuento = precio_original
                
                logger.debug("No hay descuento aplicado")
            
            # Calcular IVA y total
            iva = precio_con_descuento * Decimal('0.19')
            total = precio_con_descuento + iva
            
            logger.debug(f"Precio con descuento: {precio_con_descuento}")
            logger.debug(f"IVA: {iva}")
            logger.debug(f"Total: {total}")
            logger.debug("="*50)
            
            # También imprimir en consola para desarrollo
            print("\n=== DEBUG INFORMACIÓN PRODUCTO ===")
            print(f"ID: {product.id}")
            print(f"Nombre: {product.name}")
            print(f"Precio publicado: {product.published_price}")
            print(f"Descuento %: {product.discount_percentage}")
            print(f"\n=== CÁLCULOS ===")
            print(f"Precio original: {precio_original}")
            print(f"Descuento: {descuento_monto}")
            print(f"Precio con descuento: {precio_con_descuento}")
            print(f"IVA: {iva}")
            print(f"Total: {total}")
            print("="*30)

            context = {
                'product': product,
                'precio_original': precio_original,
                'descuento': descuento_monto,
                'precio_con_descuento': precio_con_descuento,
                'iva': iva,
                'total': total,
                'cart_count': get_cart_count(request),
            }
            
            return render(request, 'stock_smart/checkout_options.html', context)
            
        except Exception as e:
            logger.error(f"Error en checkout_options: {str(e)}")
            print(f"Error en checkout_options: {str(e)}")
            return redirect('stock_smart:home')
    
    return redirect('stock_smart:home')

def process_payment(request):
    try:
        logger.info("Iniciando process_payment")
        
        order_id = request.session.get('order_id')
        logger.info(f"ID de orden en sesión: {order_id}")
        
        if not order_id:
            messages.error(request, 'No se encontró la orden')
            return redirect('stock_smart:productos_lista')
        
        try:
            order = Order.objects.get(id=order_id)
            logger.info(f"Orden encontrada: {order.order_number}")
        except Order.DoesNotExist:
            logger.error(f"No se encontró la orden con ID: {order_id}")
            messages.error(request, 'Orden no encontrada')
            return redirect('stock_smart:productos_lista')
        
        # Crear pago en Flow
        flow_service = FlowPaymentService()
        payment_url = flow_service.create_payment(order)
        
        if payment_url:
            logger.info(f"URL de pago generada: {payment_url}")
            return redirect(payment_url)
        else:
            logger.error("No se pudo generar la URL de pago")
            messages.error(request, 'Error al procesar el pago')
            return redirect('stock_smart:productos_lista')
            
    except Exception as e:
        logger.error(f"Error en process_payment: {str(e)}")
        messages.error(request, 'Error al procesar el pago')
        return redirect('stock_smart:productos_lista')

def auth_page(request):
    try:
        return render(request, 'stock_smart/auth.html')
    except Exception as e:
        print(f"Error en auth_page: {str(e)}")
        return redirect('stock_smart:productos_lista')

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
    try:
        # Obtener producto de la sesión
        product_id = request.session.get('product_id')
        logger.info(f"ID de producto en sesión: {product_id}")
        
        if not product_id:
            messages.error(request, 'No se encontró el producto en la sesión')
            return redirect('stock_smart:productos_lista')
        
        # Obtener el producto
        product = get_object_or_404(Product, id=product_id)
        logger.info(f"Producto encontrado: {product.nombre}")
        
        if request.method == 'POST':
            form = GuestCheckoutForm(request.POST)
            if form.is_valid():
                # Crear la orden
                order = Order(
                    customer_name=f"{form.cleaned_data['nombre']} {form.cleaned_data['apellido']}",
                    customer_email=form.cleaned_data['email'],
                    customer_phone=form.cleaned_data['telefono'],
                    region=form.cleaned_data['region'],
                    ciudad=form.cleaned_data['ciudad'],
                    comuna=form.cleaned_data['comuna'],
                    shipping_method=form.cleaned_data['shipping'],
                    payment_method=form.cleaned_data['payment_method'],
                    total_amount=product.precio_final
                )
                
                if form.cleaned_data['shipping'] == 'starken':
                    order.shipping_address = form.cleaned_data['direccion']
                
                if form.cleaned_data['observaciones']:
                    order.observaciones = form.cleaned_data['observaciones']
                
                order.save()
                
                # Guardar ID de orden en sesión
                request.session['order_id'] = order.id
                logger.info(f"Orden creada y guardada en sesión: {order.id}")
                
                # Redireccionar según método de pago
                if form.cleaned_data['payment_method'] == 'flow':
                    return redirect('stock_smart:process_payment')
                else:
                    return redirect('stock_smart:transfer_instructions')
        else:
            form = GuestCheckoutForm()
        
        context = {
            'form': form,
            'product': product
        }
        
        return render(request, 'stock_smart/guest_checkout.html', context)
        
    except Exception as e:
        logger.error(f"Error en guest_checkout: {str(e)}")
        messages.error(request, 'Error al procesar el checkout')
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
    
    # Si el usuario est autenticado, prellenar datos
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
    return HttpResponse(status=405)

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

def transfer_instructions(request):
    try:
        order_id = request.session.get('order_id')
        if not order_id:
            messages.error(request, 'No se encontró la orden')
            return redirect('stock_smart:productos_lista')
            
        order = get_object_or_404(Order, id=order_id)
        
        bank_info = {
            'banco': 'Banco Estado',
            'tipo_cuenta': 'Cuenta Corriente',
            'numero_cuenta': '123456789',
            'rut': '76.543.210-K',
            'nombre': 'Tu Empresa SPA',
            'email': 'pagos@tuempresa.cl'
        }
        
        return render(request, 'stock_smart/transfer_instructions.html', {
            'order': order,
            'bank_info': bank_info
        })
        
    except Exception as e:
        logger.error(f"Error en transfer_instructions: {str(e)}")
        messages.error(request, 'Error al mostrar instrucciones de pago')
        return redirect('stock_smart:productos_lista')

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
    try:
        token = request.GET.get('token')
        if not token:
            messages.error(request, 'Token no válido')
            return redirect('stock_smart:productos_lista')
            
        order = get_object_or_404(Order, flow_token=token)
        
        # Actualizar estado de la orden
        order.status = 'paid'
        order.save()
        
        # Limpiar sesión
        if 'order_id' in request.session:
            del request.session['order_id']
        
        messages.success(request, '¡Pago exitoso!')
        return render(request, 'stock_smart/payment_success.html', {'order': order})
        
    except Exception as e:
        print(f"Error en payment_success: {str(e)}")
        messages.error(request, 'Error al procesar el pago')
        return redirect('stock_smart:productos_lista')

def payment_cancel(request):
    try:
        messages.warning(request, 'El pago ha sido cancelado')
        return redirect('stock_smart:productos_lista')
    except Exception as e:
        print(f"Error en payment_cancel: {str(e)}")
        return redirect('stock_smart:productos_lista')

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
    try:
        cart = request.session.get('cart', {})
        cart_items = []
        total = Decimal('0')
        
        # Procesar cada item en el carrito
        for product_id, item_data in cart.items():
            try:
                product = Product.objects.get(id=product_id)
                quantity = item_data['quantity']
                
                # Calcular precio con descuento si aplica
                if product.discount_percentage:
                    discount = (product.published_price * product.discount_percentage) / Decimal('100')
                    price = product.published_price - discount
                else:
                    price = product.published_price
                
                item_total = price * quantity
                
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'total': item_total
                })
                
                total += item_total
                
            except Product.DoesNotExist:
                continue
        
        context = {
            'cart_items': cart_items,
            'total': total,
            'cart_count': sum(item['quantity'] for item in cart.values())
        }
        
        return render(request, 'stock_smart/cart.html', context)
        
    except Exception as e:
        print(f"Error en cart_view: {str(e)}")
        return render(request, 'stock_smart/cart.html', {
            'error': 'Error al cargar el carrito'
        })

def update_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            new_quantity = int(data.get('quantity'))
            
            # Verificar stock disponible
            product = get_object_or_404(Product, id=product_id)
            if new_quantity > product.stock:
                return JsonResponse({
                    'success': False,
                    'error': 'Stock no disponible'
                })
            
            # Actualizar carrito
            cart = request.session.get('cart', {})
            if product_id in cart:
                cart[product_id]['quantity'] = new_quantity
                request.session['cart'] = cart
                request.session.modified = True
                
                # Calcular nuevos totales
                item_total = int(float(cart[product_id]['price']) * new_quantity)
                cart_total = sum(int(float(item['price']) * item['quantity']) for item in cart.values())
                cart_count = sum(item['quantity'] for item in cart.values())
                
                # Formatear números con separador de miles
                from django.contrib.humanize.templatetags.humanize import intcomma
                return JsonResponse({
                    'success': True,
                    'new_quantity': new_quantity,
                    'item_total': intcomma(item_total),
                    'cart_total': intcomma(cart_total),
                    'cart_count': cart_count
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado en el carrito'
            })
            
        except Exception as e:
            print(f"Error en update_cart: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False})

def remove_from_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            
            # Eliminar del carrito
            cart = request.session.get('cart', {})
            if product_id in cart:
                del cart[product_id]
                request.session['cart'] = cart
                request.session.modified = True
                
                # Calcular nuevo total
                cart_total = sum(float(item['price']) * item['quantity'] for item in cart.values())
                cart_count = sum(item['quantity'] for item in cart.values())
                
                return JsonResponse({
                    'success': True,
                    'cart_total': f"{cart_total:,.0f}",
                    'cart_count': cart_count
                })
            
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado en el carrito'
            })
            
        except Exception as e:
            print(f"Error en remove_from_cart: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
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

def checkout_options(request, product_id=None):
    try:
        if not product_id:
            messages.error(request, 'No se especificó un producto')
            return redirect('stock_smart:productos_lista')
            
        product = get_object_or_404(Product, id=product_id)
        request.session['quick_buy_product_id'] = product_id
        
        # 1. Precio base (incluye IVA)
        base_price = product.published_price
        
        # 2. Aplicar descuento si existe
        if product.discount_percentage > 0:
            discount = (base_price * Decimal(str(product.discount_percentage))) / Decimal('100')
            final_price = base_price - discount
        else:
            final_price = base_price
            
        # 3. Calcular IVA (que ya está incluido)
        # Precio sin IVA = Precio final / 1.19
        price_without_iva = final_price / Decimal('1.19')
        iva_amount = final_price - price_without_iva
        
        # Debug de cálculos
        print(f"Precio base (con IVA): ${base_price}")
        print(f"Descuento: {product.discount_percentage}%")
        print(f"Precio final (con IVA): ${final_price}")
        print(f"Precio sin IVA: ${price_without_iva}")
        print(f"Monto IVA: ${iva_amount}")
        
        context = {
            'product': product,
            'base_price': base_price,
            'final_price': final_price,
            'price_without_iva': price_without_iva,
            'iva': iva_amount,
            'total': final_price,  # Este es el precio final que incluye IVA
            'is_quick_buy': True
        }
        
        return render(request, 'stock_smart/checkout_options.html', context)
        
    except Exception as e:
        print(f"Error en checkout_options: {str(e)}")
        return redirect('stock_smart:productos_lista')

def checkout_guest(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    context = {
        'product': product,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'stock_smart/guest_checkout.html', context)

def add_to_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            
            print("\n=== DEBUG ADD TO CART ===")
            print(f"Sesión ID: {request.session.session_key}")
            print(f"Product ID recibido: {product_id}")
            
            product = get_object_or_404(Product, id=product_id)
            print(f"Producto encontrado: {product.name}")
            
            # Asegurarse de que existe un carrito en la sesión
            if 'cart' not in request.session:
                request.session['cart'] = {}
                print("Nuevo carrito creado en sesión")
            
            cart = request.session.get('cart', {})
            print(f"Carrito actual: {cart}")
            
            # Agregar o actualizar producto
            if product_id in cart:
                cart[product_id]['quantity'] += 1
                print(f"Incrementada cantidad para producto {product_id}")
            else:
                cart[product_id] = {
                    'quantity': 1,
                    'price': str(product.get_final_price),
                    'name': product.name
                }
                print(f"Nuevo producto agregado al carrito: {cart[product_id]}")
            
            # Guardar carrito actualizado
            request.session['cart'] = cart
            request.session.modified = True
            
            print(f"Carrito actualizado: {cart}")
            cart_count = sum(item['quantity'] for item in cart.values())
            print(f"Total items en carrito: {cart_count}")
            print("=== FIN DEBUG ===\n")
            
            return JsonResponse({
                'success': True,
                'cart_count': cart_count
            })
            
        except Exception as e:
            print(f"ERROR en add_to_cart: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

@login_required
def user_checkout(request):
    try:
        # Obtener el carrito
        cart = request.session.get('cart', {})
        cart_items = []
        total = Decimal('0')
        
        # Procesar items del carrito
        for product_id, item_data in cart.items():
            product = get_object_or_404(Product, id=product_id)
            quantity = item_data['quantity']
            price = Decimal(item_data['price'])
            item_total = price * quantity
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'price': price,
                'total': item_total
            })
            total += item_total
        
        # Obtener datos del usuario
        user = request.user
        context = {
            'cart_items': cart_items,
            'total': total,
            'user': user,
            'cart_count': sum(item['quantity'] for item in cart.values())
        }
        
        return render(request, 'stock_smart/user_checkout.html', context)
        
    except Exception as e:
        print(f"Error en user_checkout: {str(e)}")
        return redirect('stock_smart:cart')

def cart_checkout_options(request):
    try:
        cart = request.session.get('cart', {})
        if not cart:
            messages.warning(request, 'Tu carrito está vacío')
            return redirect('stock_smart:cart')
            
        cart_items = []
        total = Decimal('0')
        
        # Procesar items del carrito
        for product_id, item_data in cart.items():
            try:
                product = Product.objects.get(id=product_id)
                quantity = item_data['quantity']
                price = Decimal(item_data['price'])
                item_total = price * quantity
                
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'total': item_total
                })
                
                total += item_total
                
            except Product.DoesNotExist:
                continue
        
        # Calcular IVA
        iva = total * Decimal('0.19')
        total_con_iva = total + iva
        
        context = {
            'cart_items': cart_items,
            'subtotal': total,
            'iva': iva,
            'total': total_con_iva,
            'cart_count': sum(item['quantity'] for item in cart.values())
        }
        
        return render(request, 'stock_smart/cart_checkout_options.html', context)
        
    except Exception as e:
        print(f"Error en cart_checkout_options: {str(e)}")
        return redirect('stock_smart:cart')

@login_required
def user_cart_checkout(request):
    try:
        cart = request.session.get('cart', {})
        if not cart:
            return redirect('stock_smart:cart')
            
        # Reutilizar lógica existente pero con template específico
        cart_items = []
        total = Decimal('0')
        
        for product_id, item_data in cart.items():
            product = get_object_or_404(Product, id=product_id)
            quantity = item_data['quantity']
            price = Decimal(item_data['price'])
            item_total = price * quantity
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'price': price,
                'total': item_total
            })
            total += item_total
        
        context = {
            'cart_items': cart_items,
            'total': total,
            'user': request.user,
            'cart_count': sum(item['quantity'] for item in cart.values())
        }
        
        return render(request, 'stock_smart/user_cart_checkout.html', context)
        
    except Exception as e:
        print(f"Error en user_cart_checkout: {str(e)}")
        return redirect('stock_smart:cart')

def guest_cart_checkout(request):
    try:
        cart = request.session.get('cart', {})
        if not cart:
            return redirect('stock_smart:cart')
            
        # Similar a guest_checkout pero con template específico
        cart_items = []
        total = Decimal('0')
        
        for product_id, item_data in cart.items():
            product = get_object_or_404(Product, id=product_id)
            quantity = item_data['quantity']
            price = Decimal(item_data['price'])
            item_total = price * quantity
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'price': price,
                'total': item_total
            })
            total += item_total
        
        context = {
            'cart_items': cart_items,
            'total': total,
            'cart_count': sum(item['quantity'] for item in cart.values())
        }
        
        return render(request, 'stock_smart/guest_cart_checkout.html', context)
        
    except Exception as e:
        print(f"Error en guest_cart_checkout: {str(e)}")
        return redirect('stock_smart:cart')

def validate_product(request, product_id):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # Validar stock
            if product.stock <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Producto sin stock disponible'
                })
            
            # Calcular precio final
            price = product.published_price
            if product.discount_percentage > 0:
                discount = (price * product.discount_percentage) / Decimal('100')
                price = price - discount
            
            # Validar precio
            if price <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Precio no válido'
                })
            
            return JsonResponse({
                'success': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'price': float(price),
                    'stock': product.stock,
                    'discount': product.discount_percentage
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@csrf_exempt  # Necesario para recibir POST de Flow
def payment_confirm(request):
    try:
        logger.info("Iniciando payment_confirm")
        logger.info(f"Método: {request.method}")
        logger.info(f"POST data: {request.POST}")
        
        if request.method != 'POST':
            return HttpResponse('Método no permitido', status=405)
        
        # Obtener token de Flow
        token = request.POST.get('token')
        if not token:
            logger.error("No se recibió token de Flow")
            return HttpResponse('Token no recibido', status=400)
            
        try:
            # Buscar orden por token
            order = Order.objects.get(flow_token=token)
            
            # Verificar estado del pago
            flow_service = FlowPaymentService()
            payment_status = flow_service.get_payment_status(token)
            
            if payment_status.get('status') == 2:  # Pago exitoso
                # Actualizar estado de la orden
                order.status = 'paid'
                order.save()
                
                logger.info(f"Pago confirmado para orden: {order.order_number}")
                return HttpResponse('OK', status=200)
            else:
                logger.error(f"Estado de pago inválido: {payment_status}")
                return HttpResponse('Estado de pago inválido', status=400)
                
        except Order.DoesNotExist:
            logger.error(f"No se encontró orden para el token: {token}")
            return HttpResponse('Orden no encontrada', status=404)
            
    except Exception as e:
        logger.error(f"Error en payment_confirm: {str(e)}")
        return HttpResponse('Error interno', status=500)

def detalle_producto(request, producto_id):
    try:
        product = get_object_or_404(Product, id=producto_id)
        
        # Guardar el producto en la sesión cuando se ve el detalle
        request.session['product_id'] = product.id
        logger.info(f"Producto guardado en sesión: {product.id}")
        
        context = {
            'product': product,
        }
        
        return render(request, 'stock_smart/detalle_producto.html', context)
        
    except Exception as e:
        logger.error(f"Error en detalle_producto: {str(e)}")
        messages.error(request, 'Error al mostrar el producto')
        return redirect('stock_smart:productos_lista')

def iniciar_checkout(request, producto_id):
    try:
        # Obtener el producto
        product = get_object_or_404(Product, id=producto_id)
        
        # Guardar en sesión
        request.session['product_id'] = product.id
        logger.info(f"Producto guardado en sesión: {product.id}")
        
        # Redirigir al checkout
        return redirect('stock_smart:guest_checkout')
        
    except Exception as e:
        logger.error(f"Error al iniciar checkout: {str(e)}")
        messages.error(request, 'Error al iniciar el proceso de compra')
        return redirect('stock_smart:productos_lista')
