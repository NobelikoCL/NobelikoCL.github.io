from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.contrib.auth.models import User
from .models import CustomUser, Product
from django.core.validators import RegexValidator

class RegisterForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre de usuario'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Correo electrónico'
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Contraseña'
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirmar contraseña'
    }))

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre de usuario'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Contraseña'
    }))

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre'
    }))
    last_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Apellido'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Correo electrónico'
    }))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class RecoveryForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Correo electrónico'
    }))

class GuestCheckoutForm(forms.Form):
    # Datos personales
    nombre = forms.CharField(
        label='Nombre',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    apellido = forms.CharField(
        label='Apellido',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    telefono = forms.CharField(
        label='Teléfono',
        validators=[
            RegexValidator(
                regex=r'^\+569\d{8}$',
                message='El número debe tener formato +569XXXXXXXX'
            )
        ],
        initial='+569',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+569XXXXXXXX'
        })
    )
    
    # Dirección
    region = forms.ChoiceField(
        label='Región',
        choices=[
            ('', 'Seleccione región'),
            ('metropolitana', 'Región Metropolitana'),
            ('valparaiso', 'Región de Valparaíso'),
            # Agregar más regiones
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    ciudad = forms.CharField(
        label='Ciudad',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    comuna = forms.CharField(
        label='Comuna',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    direccion = forms.CharField(
        label='Dirección de envío',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # Métodos de envío y pago
    shipping = forms.ChoiceField(
        label='Método de envío',
        choices=[
            ('pickup', 'Retiro en tienda'),
            ('starken', 'Envío Starken'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    payment_method = forms.ChoiceField(
        label='Método de pago',
        choices=[
            ('flow', 'Pago con Flow (WebPay)'),
            ('transfer', 'Transferencia Bancaria'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    # Campo opcional
    observaciones = forms.CharField(
        label='Observaciones',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones opcionales sobre tu pedido'
        })
    )

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if not telefono.startswith('+569'):
            raise forms.ValidationError('El número debe comenzar con +569')
        return telefono

class CheckoutForm(forms.Form):
    address = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Dirección de envío'
    }))
    city = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ciudad'
    }))
    region = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Región'
    }))
    postal_code = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Código Postal (opcional)'
    }))
    phone = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Teléfono de contacto'
    }))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': 'Notas adicionales para el envío',
        'rows': 3
    }))

class CheckoutUserInfoForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('rut', 'phone', 'shipping_address')
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RUT'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'shipping_address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Dirección de envío', 'rows': 3}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 
            'description', 
            'published_price',
            'discount_percentage',
            'category',
            'brand',
            'image',
            'stock',
            'active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'published_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
