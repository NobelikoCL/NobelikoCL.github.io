# Generated by Django 5.1.3 on 2024-11-27 01:56

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import phonenumber_field.modelfields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Marca',
                'verbose_name_plural': 'Marcas',
            },
        ),
        migrations.CreateModel(
            name='ConfiguracionTienda',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_tienda', models.CharField(max_length=100)),
                ('logo', models.ImageField(upload_to='tienda/')),
                ('favicon', models.ImageField(upload_to='tienda/')),
                ('descripcion', models.TextField()),
                ('email_contacto', models.EmailField(max_length=254)),
                ('telefono', models.CharField(max_length=20)),
                ('direccion', models.TextField()),
                ('meta_description', models.TextField(blank=True)),
                ('meta_keywords', models.TextField(blank=True)),
                ('google_analytics_id', models.CharField(blank=True, max_length=50)),
                ('facebook_pixel_id', models.CharField(blank=True, max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='FlowCredentials',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('is_sandbox', models.BooleanField(default=True, verbose_name='Modo Sandbox')),
                ('api_key', models.CharField(max_length=255, verbose_name='API Key')),
                ('secret_key', models.CharField(max_length=255, verbose_name='Secret Key')),
            ],
            options={
                'verbose_name': 'Credencial Flow',
                'verbose_name_plural': 'Credenciales Flow',
            },
        ),
        migrations.CreateModel(
            name='MetodoPago',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('activo', models.BooleanField(default=True)),
                ('comision', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('imagen', models.ImageField(upload_to='metodos_pago/')),
            ],
        ),
        migrations.CreateModel(
            name='Proveedor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('contacto', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('telefono', models.CharField(max_length=20)),
                ('direccion', models.TextField()),
                ('activo', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='RedSocial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50)),
                ('url', models.URLField()),
                ('activa', models.BooleanField(default=True)),
                ('pixel_id', models.CharField(blank=True, max_length=100)),
                ('tracking_code', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('codigo', models.CharField(max_length=10)),
                ('activa', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('rut', models.CharField(blank=True, max_length=12, null=True)),
                ('phone', models.CharField(blank=True, max_length=15, null=True)),
                ('shipping_address', models.TextField(blank=True, null=True)),
                ('email_verified', models.BooleanField(default=False)),
                ('verification_token', models.CharField(blank=True, max_length=100, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='custom_user_set', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='custom_user_set', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visitor_id', models.CharField(blank=True, max_length=36, null=True)),
                ('is_guest', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('slug', models.SlugField(blank=True, null=True, unique=True)),
                ('order', models.IntegerField(default=0)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='stock_smart.category')),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=50, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('first_name', models.CharField(default='', max_length=100)),
                ('last_name', models.CharField(default='', max_length=100)),
                ('email', models.EmailField(default='', max_length=254)),
                ('phone', models.CharField(default='', max_length=20)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('flow_token', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('PAID', 'Pagado'), ('FAILED', 'Fallido'), ('CANCELLED', 'Cancelado')], default='PENDING', max_length=20)),
                ('shipping_method', models.CharField(default='pickup', max_length=20)),
                ('shipping_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderTracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PENDING', 'Pendiente'), ('PAID', 'Pagado'), ('FAILED', 'Fallido'), ('CANCELLED', 'Cancelado')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracking_history', to='stock_smart.order')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variant', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('waiting', 'Waiting for confirmation'), ('preauth', 'Pre-authorized'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected'), ('refunded', 'Refunded'), ('error', 'Error'), ('input', 'Input')], default='waiting', max_length=10)),
                ('fraud_status', models.CharField(choices=[('unknown', 'Unknown'), ('accept', 'Passed'), ('reject', 'Rejected'), ('review', 'Review')], default='unknown', max_length=10, verbose_name='fraud check')),
                ('fraud_message', models.TextField(blank=True, default='')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('transaction_id', models.CharField(blank=True, max_length=255)),
                ('currency', models.CharField(max_length=10)),
                ('total', models.DecimalField(decimal_places=2, default='0.0', max_digits=9)),
                ('delivery', models.DecimalField(decimal_places=2, default='0.0', max_digits=9)),
                ('tax', models.DecimalField(decimal_places=2, default='0.0', max_digits=9)),
                ('description', models.TextField(blank=True, default='')),
                ('billing_first_name', models.CharField(blank=True, max_length=256)),
                ('billing_last_name', models.CharField(blank=True, max_length=256)),
                ('billing_address_1', models.CharField(blank=True, max_length=256)),
                ('billing_address_2', models.CharField(blank=True, max_length=256)),
                ('billing_city', models.CharField(blank=True, max_length=256)),
                ('billing_postcode', models.CharField(blank=True, max_length=256)),
                ('billing_country_code', models.CharField(blank=True, max_length=2)),
                ('billing_country_area', models.CharField(blank=True, max_length=256)),
                ('billing_email', models.EmailField(blank=True, max_length=254)),
                ('billing_phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region=None)),
                ('customer_ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('extra_data', models.TextField(blank=True, default='')),
                ('message', models.TextField(blank=True, default='')),
                ('token', models.CharField(blank=True, default='', max_length=36)),
                ('captured_amount', models.DecimalField(decimal_places=2, default='0.0', max_digits=9)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stock_smart.order')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_seguimiento', models.CharField(editable=False, max_length=15, unique=True, verbose_name='Número de seguimiento')),
                ('fecha_pedido', models.DateTimeField(auto_now_add=True, verbose_name='Fecha del pedido')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente de envío'), ('PREPARACION', 'En preparación'), ('ENVIADO', 'Enviado'), ('ENTREGADO', 'Entregado'), ('CANCELADO', 'Cancelado')], default='PENDIENTE', max_length=20, verbose_name='Estado del pedido')),
                ('direccion_envio', models.TextField(default='', verbose_name='Dirección de envío')),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Subtotal')),
                ('descuento', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Descuento')),
                ('iva', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='IVA')),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Total del pedido')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pedidos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pedido',
                'verbose_name_plural': 'Pedidos',
                'ordering': ['-fecha_pedido'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, null=True, unique=True)),
                ('description', models.TextField()),
                ('published_price', models.PositiveIntegerField(help_text='Precio final que verá el cliente (IVA incluido)', verbose_name='Precio publicado')),
                ('discount_percentage', models.PositiveIntegerField(default=0, help_text='Porcentaje de descuento (0-100)', validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Porcentaje de descuento')),
                ('stock', models.PositiveIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
                ('is_featured', models.BooleanField(default=False, verbose_name='Destacado')),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('brand', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='stock_smart.brand')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='stock_smart.category')),
            ],
            options={
                'verbose_name': 'Producto',
                'verbose_name_plural': 'Productos',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stock_smart.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='stock_smart.product')),
            ],
        ),
        migrations.CreateModel(
            name='Favorito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_agregado', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stock_smart.product')),
            ],
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stock_smart.cart')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stock_smart.product')),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=15)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ConfiguracionEnvio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tiempo_estimado', models.CharField(max_length=50)),
                ('activo', models.BooleanField(default=True)),
                ('precio_por_peso', models.BooleanField(default=False)),
                ('regiones', models.ManyToManyField(to='stock_smart.region')),
            ],
        ),
        migrations.CreateModel(
            name='SeguimientoPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de actualización')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente de envío'), ('PREPARACION', 'En preparación'), ('ENVIADO', 'Enviado'), ('ENTREGADO', 'Entregado'), ('CANCELADO', 'Cancelado')], max_length=20, verbose_name='Estado')),
                ('descripcion', models.TextField(verbose_name='Descripción del estado')),
                ('ubicacion', models.CharField(blank=True, max_length=100, null=True, verbose_name='Ubicación')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to='stock_smart.pedido')),
            ],
            options={
                'verbose_name': 'Seguimiento de pedido',
                'verbose_name_plural': 'Seguimientos de pedidos',
                'ordering': ['-fecha'],
            },
        ),
        migrations.AddIndex(
            model_name='cart',
            index=models.Index(fields=['visitor_id', 'is_active'], name='stock_smart_visitor_ad55ef_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='favorito',
            unique_together={('usuario', 'producto')},
        ),
    ]