"""
Django settings for ecommerce project.

Generated by 'django-admin startproject' using Django 5.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-b-wqkp()jp4#5#h6p^)&i0q^+xzv651hejh++mar1m_@3pfnrc'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'stock_smart',
    'payments',
    'django_payments_flow',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'stock_smart.middleware.VisitorMiddleware',
]

ROOT_URLCONF = 'ecommerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'stock_smart.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecommerce.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'stock_smart/static'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Añade estas líneas
AUTH_USER_MODEL = 'stock_smart.CustomUser'

LOGIN_URL = 'stock_smart:login'
LOGIN_REDIRECT_URL = 'stock_smart:account'
LOGOUT_REDIRECT_URL = 'index'

# Configuración de mensajes
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

X_FRAME_OPTIONS = 'SAMEORIGIN'
SILENCED_SYSTEM_CHECKS = ['security.W019']

# Configuración de correo
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # O tu servidor SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu_correo@gmail.com'
EMAIL_HOST_PASSWORD = 'tu_contraseña_de_aplicacion'
DEFAULT_FROM_EMAIL = 'Tu Tienda <tu_correo@gmail.com>'

# Configuración para producción
if not DEBUG:
    # Configuración de correo para producción
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'  # o tu proveedor SMTP
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

    # Información bancaria para transferencias
    BANK_INFO = {
        'bank_name': 'Banco Estado',
        'account_type': 'Cuenta Corriente',
        'account_number': '12345678',
        'rut': '12.345.678-9',
        'email': 'pagos@stocksmart.cl',
        'phone': '+56 9 12345678'
    }

    # Configuración de seguridad para Cloudflare
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True



LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'stock_smart': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    },
}

PAYMENT_VARIANTS = {
    "flow": ("django_payments_flow.FlowProvider", {
        "api_key": "4B00FE26-91DE-4BF0-83A7-577C6L8AA65A",
        "api_secret": "deef495f20d1307e2ebed5b1f9c5f33da3aeaee9",
        "api_endpoint": "sandbox"
    })
}

PAYMENT_HOST = 'localhost:8000'
PAYMENT_MODEL = 'stock_smart.Payment'
PAYMENT_USES_SSL = False  # Cambiar a True en producción

# Si estás usando HTTPS en desarrollo
if DEBUG:
    PAYMENT_HOST = 'localhost:8000'
else:
    PAYMENT_HOST = 'tudominio.com'  # Cambiar por tu dominio en producción

# Flow settings
FLOW_API_KEY = '4B00FE26-91DE-4BF0-83A7-577C6L8AA65A'
FLOW_SECRET_KEY = 'deef495f20d1307e2ebed5b1f9c5f33da3aeaee9'

# CSRF Settings
CSRF_TRUSTED_ORIGINS = [
    'https://sandbox.flow.cl',
    'https://www.flow.cl',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Configuración de CORS
CORS_ALLOWED_ORIGINS = [
    'https://sandbox.flow.cl',
    'https://www.flow.cl',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

CORS_ALLOW_CREDENTIALS = True

# Configuración de hosts permitidos
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']