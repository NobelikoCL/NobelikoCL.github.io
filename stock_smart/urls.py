from django.urls import path, include
from . import views
from django.views.decorators.csrf import csrf_exempt

app_name = 'stock_smart'

urlpatterns = [
    # Páginas principales
    path('', views.productos_lista, name='productos_lista'),
    path('products/', views.productos_lista, name='products'),
    path('about/', views.about, name='about'),
    path('contacto/', views.contacto, name='contacto'),
    path('terminos/', views.terminos, name='terminos'),
    path('seguimiento/', views.tracking, name='tracking'),
    
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # Carrito y proceso de compra múltiple
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),
    path('cart/payment/', views.cart_payment, name='cart_payment'),
    path('cart/confirm/', views.cart_confirm, name='cart_confirm'),
    
    # Compra directa (un solo producto)
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('buy-now/checkout/<int:product_id>/', views.buy_now_checkout, name='buy_now_checkout'),
    path('buy-now/payment/<int:product_id>/', views.buy_now_payment, name='buy_now_payment'),
    path('buy-now/confirm/<int:product_id>/', views.buy_now_confirm, name='buy_now_confirm'),
    
    # API endpoints para carrito
    path('api/cart/update/', views.update_cart_api, name='update_cart_api'),
    
    # Proceso de compra
    path('checkout/options/', views.checkout_options, name='checkout_options'),
    path('checkout/', views.guest_checkout, name='guest_checkout'),
    path('checkout/process-payment/', views.process_payment, name='process_payment'),
    path('checkout/process-guest-order/', views.process_guest_order, name='process_guest_order'),
    path('checkout/flow-payment/<int:order_id>/', views.flow_payment, name='flow_payment'),
    path('checkout/transfer-instructions/<int:order_id>/', views.transfer_instructions, name='transfer_instructions'),
    path('checkout/flow/confirm/', views.flow_confirm, name='flow_confirm'),
    path('checkout/flow/return/', views.flow_return, name='flow_return'),
    path('checkout/process-flow-payment/', views.process_flow_payment, name='process_flow_payment'),
    path('payment/confirm/', views.flow_confirm, name='flow_confirm'),
    path('payment/return/', views.flow_return, name='flow_return'),
    path('payment/notify/', views.payment_notify, name='payment_notify'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),
    path('payments/', include('payments.urls')),
    
    # URLs para Flow
    path('flow/confirm/', csrf_exempt(views.flow_confirm), name='flow_confirm'),
    path('flow/return/', views.flow_return, name='flow_return'),
    path('checkout/<int:product_id>/', views.checkout_options, name='checkout'),
]
