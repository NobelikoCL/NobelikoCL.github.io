"""
WSGI config for ecommerce project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from django.conf import settings
from whitenoise import WhiteNoise

# Obtener la ruta absoluta del directorio actual
current_path = Path(__file__).resolve().parent
base_path = current_path.parent

# Agregar las rutas al sys.path
sys.path.append(str(base_path))
sys.path.append(str(current_path))

# Configurar la variable de entorno
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

# Crear la aplicación WSGI
application = get_wsgi_application()

# Servir archivos estáticos y media con WhiteNoise
application = WhiteNoise(application, root=settings.STATIC_ROOT)
application.add_files(settings.MEDIA_ROOT, prefix='media/')
