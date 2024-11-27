from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.conf import settings
from django.core.exceptions import ValidationError
from unidecode import unidecode
from decimal import Decimal
import datetime
import uuid
from payments.models import BasePayment

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    rut = models.CharField(max_length=12, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    
    # Campos para verificación de email
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    # Agregar related_name para evitar conflictos
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.'
    )

    def __str__(self):
        return self.email

class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de envío'),
        ('PREPARACION', 'En preparación'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='pedidos'
    )
    numero_seguimiento = models.CharField(
        max_length=15, 
        unique=True,
        editable=False,
        verbose_name='Número de seguimiento'
    )
    fecha_pedido = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del pedido'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado del pedido'
    )
    direccion_envio = models.TextField(
        verbose_name='Dirección de envío',
        default=''
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Subtotal'
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Descuento'
    )
    iva = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='IVA'
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Total del pedido'
    )

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_pedido']

    def save(self, *args, **kwargs):
        if not self.numero_seguimiento:
            fecha = timezone.now()
            pedidos_hoy = Pedido.objects.filter(
                fecha_pedido__date=fecha.date()
            ).count()
            self.numero_seguimiento = f"{fecha.strftime('%d%m%Y')}{str(pedidos_hoy + 1).zfill(3)}"
        
        if not self.iva:
            self.iva = round(float(self.subtotal) * 0.19, 2)
        
        if not self.total:
            self.total = self.subtotal + self.iva - self.descuento
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pedido {self.numero_seguimiento}"

    @property
    def items(self):
        return self.pedidoitem_set.all()

def generate_order_number():
    """Genera un número de orden único"""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

class Order(models.Model):
    SHIPPING_CHOICES = [
        ('pickup', 'Retiro en tienda'),
        ('starken', 'Envío Starken'),
    ]
    
    PAYMENT_CHOICES = [
        ('flow', 'Pago con Flow'),
        ('transfer', 'Transferencia Bancaria'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ]

    order_number = models.CharField(max_length=11, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Campos de Flow
    flow_token = models.CharField(max_length=100, blank=True, null=True)
    flow_order = models.CharField(max_length=100, blank=True, null=True)
    payment_url = models.URLField(max_length=300, blank=True, null=True)
    
    # Campos de envío
    shipping_method = models.CharField(max_length=10, choices=SHIPPING_CHOICES)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    shipping_address = models.TextField(null=True, blank=True)
    
    # Campos de cliente
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=15)
    
    # Campos de precio (todos con defaults)
    base_price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    iva_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Relación con el producto (permitir null para órdenes existentes)
    product = models.ForeignKey(
        'Product', 
        on_delete=models.PROTECT,
        null=True,  # Permitir null para órdenes existentes
        blank=True
    )

    # Nuevos campos
    region = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    comuna = models.CharField(max_length=100)
    shipping_address = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    observaciones = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            today = timezone.now()
            date_prefix = today.strftime('%d%m%y')
            
            last_order = Order.objects.filter(
                order_number__startswith=date_prefix
            ).order_by('-order_number').first()
            
            if last_order:
                last_number = int(last_order.order_number[-3:])
                new_number = str(last_number + 1).zfill(3)
            else:
                new_number = '001'
            
            self.order_number = f"{date_prefix}{new_number}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden {self.order_number} - {self.customer_name}"

    class Meta:
        ordering = ['-created_at']

    @property
    def full_name(self):
        return f"{self.customer_name} {self.customer_email}"

    @property
    def total_with_shipping(self):
        return self.total_amount + self.shipping_cost

    # Agregar método para calcular total
    def calculate_total(self):
        return sum(item.total for item in self.orderitem_set.all())

class OrderTracking(models.Model):
    """Modelo para registrar el historial de estados de una orden"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.id} - {self.status} - {self.created_at}'

class SeguimientoPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='seguimientos'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de actualización'
    )
    estado = models.CharField(
        max_length=20,
        choices=Pedido.ESTADO_CHOICES,
        verbose_name='Estado'
    )
    descripcion = models.TextField(
        verbose_name='Descripción del estado'
    )
    ubicacion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Ubicación'
    )

    class Meta:
        verbose_name = 'Seguimiento de pedido'
        verbose_name_plural = 'Seguimientos de pedidos'
        ordering = ['-fecha']

    def __str__(self):
        return f"Seguimiento {self.pedido.numero_seguimiento} - {self.estado}"

class Favorito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        'stock_smart.Product',
        on_delete=models.CASCADE
    )
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'producto')

    def __str__(self):
        return f"{self.usuario.username} - {self.producto.name}"

class ConfiguracionTienda(models.Model):
    nombre_tienda = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='tienda/')
    favicon = models.ImageField(upload_to='tienda/')
    descripcion = models.TextField()
    email_contacto = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.TextField()
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True)
    facebook_pixel_id = models.CharField(max_length=50, blank=True)

class RedSocial(models.Model):
    nombre = models.CharField(max_length=50)
    url = models.URLField()
    activa = models.BooleanField(default=True)
    pixel_id = models.CharField(max_length=100, blank=True)
    tracking_code = models.TextField(blank=True)

class ConfiguracionEnvio(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    tiempo_estimado = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)
    regiones = models.ManyToManyField('Region')
    precio_por_peso = models.BooleanField(default=False)

class Region(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    
class MetodoPago(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    activo = models.BooleanField(default=True)
    comision = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    imagen = models.ImageField(upload_to='metodos_pago/')

class Proveedor(models.Model):
    nombre = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.TextField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, null=True)
    description = models.TextField()
    published_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True)
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, verbose_name="Destacado")
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def net_price(self):
        """Calcula el precio neto (sin IVA)"""
        return int(self.published_price / 1.19)

    @property
    def iva_amount(self):
        """Calcula el monto del IVA"""
        return int(self.published_price - self.net_price)

    @property
    def discount_amount(self):
        """Calcula el monto del descuento"""
        if self.discount_percentage > 0:
            return int((self.published_price * self.discount_percentage) / 100)
        return 0

    @property
    def final_price(self):
        """Calcula el precio final con descuento"""
        return self.published_price - self.discount_amount

    @property
    def get_final_price(self):
        try:
            if self.discount_percentage and self.discount_percentage > 0:
                discount = (self.published_price * self.discount_percentage) / Decimal('100')
                return self.published_price - discount
            return self.published_price
        except Exception as e:
            print(f"Error calculando precio final: {str(e)}")
            return Decimal('0')

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    phone = models.CharField(max_length=15)

    def __str__(self):
        return f'Profile of {self.user.username}'

class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    visitor_id = models.CharField(max_length=36, null=True, blank=True)
    is_guest = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['visitor_id', 'is_active']),
        ]

    def __str__(self):
        return f"Cart {self.id} - {self.visitor_id}"

    @classmethod
    def get_cart_for_visitor(cls, visitor_id):
        """Obtener o crear carrito para un visitante"""
        # Primero, desactivar cualquier carrito antiguo
        cls.objects.filter(
            visitor_id=visitor_id,
            is_active=True
        ).update(is_active=False)
        
        # Crear un nuevo carrito activo
        cart = cls.objects.create(
            visitor_id=visitor_id,
            is_active=True
        )
        
        return cart

    @classmethod
    def get_active_cart(cls, visitor_id):
        """Obtener el carrito activo más reciente"""
        cart = cls.objects.filter(
            visitor_id=visitor_id,
            is_active=True
        ).order_by('-created_at').first()
        
        if not cart:
            cart = cls.objects.create(
                visitor_id=visitor_id,
                is_active=True
            )
        
        return cart

    # Agregar método para calcular total
    @property
    def total(self):
        return sum(item.total for item in self.cartitem_set.all())
    
    # Agregar método para contar items
    @property
    def item_count(self):
        return self.cartitem_set.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

class CartItem(models.Model):
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total(self):
        if self.product.discount_percentage > 0:
            return self.product.final_price * self.quantity
        return self.product.published_price * self.quantity

class FlowCredentials(models.Model):
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    is_sandbox = models.BooleanField(default=True, verbose_name="Modo Sandbox")
    api_key = models.CharField(max_length=255, verbose_name="API Key")
    secret_key = models.CharField(max_length=255, verbose_name="Secret Key")
    
    class Meta:
        verbose_name = "Credencial Flow"
        verbose_name_plural = "Credenciales Flow"

    def __str__(self):
        environment = "Sandbox" if self.is_sandbox else "Producción"
        status = "Activo" if self.is_active else "Inactivo"
        return f"Flow {environment} - {status}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Desactivar otras credenciales activas
            FlowCredentials.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """
    Modelo para items individuales de una orden
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} en Orden #{self.order.order_number}"

    @property
    def total(self):
        return self.quantity * self.price

class Payment(BasePayment):
    def get_failure_url(self):
        return 'http://' + settings.PAYMENT_HOST + reverse('payment:failed')

    def get_success_url(self):
        return 'http://' + settings.PAYMENT_HOST + reverse('payment:success')

    # Agregar relación con Order
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
