from django.contrib import admin
from .models import Order, OrderItem, Category, Product, Brand

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 
        'full_name', 
        'total_with_shipping',
        'status', 
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'order_number', 
        'first_name', 
        'last_name', 
        'email'
    ]
    readonly_fields = [
        'order_number',
        'created_at',
        'updated_at',
        'flow_token',
        'total_with_shipping'
    ]
    fieldsets = [
        ('Información de la Orden', {
            'fields': [
                'order_number',
                'status',
                'created_at',
                'updated_at'
            ]
        }),
        ('Información del Cliente', {
            'fields': [
                'first_name',
                'last_name',
                'email',
                'phone'
            ]
        }),
        ('Información de Pago', {
            'fields': [
                'total_amount',
                'shipping_method',
                'shipping_cost',
                'flow_token'
            ]
        })
    ]
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order',
        'product',
        'quantity',
        'price',
        'total'
    ]
    list_filter = ['order__status']
    search_fields = [
        'order__order_number',
        'product__name'
    ]
    readonly_fields = [
        'order',
        'product',
        'quantity',
        'price'
    ]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'order', 'is_active', 'slug']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'brand', 'published_price', 'discount_percentage', 'stock', 'active', 'is_featured']
    list_filter = ['active', 'is_featured', 'category', 'brand']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['published_price', 'discount_percentage', 'stock', 'active', 'is_featured']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        ('Categorización', {
            'fields': ('category', 'brand'),
            'description': 'La categoría es obligatoria'
        }),
        ('Precios y Stock', {
            'fields': ('published_price', 'discount_percentage', 'stock')
        }),
        ('Estado', {
            'fields': ('active', 'is_featured')
        }),
    )

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
