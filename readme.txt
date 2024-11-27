===========================================
INSTRUCCIONES DE INSTALACIÓN - STOCK SMART
===========================================

1. REQUISITOS PREVIOS
--------------------
- Python 3.11.x o superior instalado
- pip (gestor de paquetes de Python)
- Git instalado
- Navegador web moderno (Chrome, Firefox, Edge)

2. CLONAR EL REPOSITORIO
------------------------
git clone https://github.com/NobelikoCL/proyecto_ecommerce.git
cd proyecto_ecommerce

3. CREAR Y ACTIVAR ENTORNO VIRTUAL (WINDOWS)
-------------------------------------------

1. Abrir PowerShell como Administrador:
   - Click derecho en el botón de Windows (Inicio)
   - Seleccionar "Windows PowerShell (Administrador)"
   - Click en "Sí" cuando pregunte por permisos

2. Habilitar la ejecución de scripts:
   - Ejecutar el siguiente comando:
     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
   - Escribir "S" o "Y" cuando pregunte por confirmación

3. Navegar al directorio del proyecto:
   cd "C:\ruta\a\tu\proyecto"

4. Crear el entorno virtual:
   python -m venv venv

5. Activar el entorno virtual:
   .\venv\Scripts\activate

6. Verificar la activación:
   - Deberías ver (venv) al inicio de la línea de comandos
   - Puedes verificar con: python -V

7. Si hay problemas de permisos adicionales:
   - Ejecutar:
     Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   - Escribir "S" o "Y" para confirmar

8. Para desactivar el entorno virtual cuando termines:
   deactivate

ERROR: "... no se puede cargar porque la ejecución de scripts está deshabilitada en este sistema"
SOLUCIÓN: 
1. Abrir PowerShell como administrador
2. Ejecutar: Set-ExecutionPolicy RemoteSigned
3. Confirmar con "S"

ERROR: "... venv\Scripts\activate.ps1 no existe"
SOLUCIÓN:
1. Eliminar carpeta venv
2. Volver a crear con: python -m venv venv
3. Intentar activar nuevamente

ERROR: Python no reconocido como comando
SOLUCIÓN:
1. Verificar que Python está instalado
2. Agregar Python al PATH del sistema
3. Reiniciar PowerShell

4. INSTALAR DEPENDENCIAS
-----------------------
pip install --upgrade pip
pip install -r requirements.txt

5. CONFIGURAR VARIABLES DE ENTORNO
--------------------------------
Crear archivo .env en la raíz del proyecto con:

DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1

6. CONFIGURAR LA BASE DE DATOS
-----------------------------
python manage.py makemigrations stock_smart
python manage.py migrate

7. CREAR SUPERUSUARIO
--------------------
python manage.py createsuperuser

Ingresar:
- Email (será el username)
- Contraseña segura
- Confirmar contraseña

8. INICIAR EL SERVIDOR
---------------------
python manage.py runserver

9. ACCEDER A LA APLICACIÓN
-------------------------
- Aplicación web: http://127.0.0.1:8000
- Panel de administración: http://127.0.0.1:8000/admin

===========================================
CARACTERÍSTICAS PRINCIPALES
===========================================
- Panel de administración personalizado con gráficos
- Gestión de inventario
- Sistema de pedidos
- Gestión de usuarios y roles
- Reportes en PDF
- Dashboard con estadísticas en tiempo real

===========================================
COMANDOS ÚTILES
===========================================
# Desactivar entorno virtual
deactivate

# Ver paquetes instalados
pip list

# Actualizar requirements.txt
pip freeze > requirements.txt

# Recolectar archivos estáticos
python manage.py collectstatic

# Crear nuevas migraciones después de cambios en modelos
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

===========================================
SOLUCIÓN DE PROBLEMAS COMUNES
===========================================

1. Error: "No module named 'nombre_modulo'"
   pip install nombre_modulo

2. Error con archivos estáticos:
   python manage.py collectstatic --noinput

3. Error con las migraciones:
   python manage.py migrate --run-syncdb

4. Error con el entorno virtual:
   - Verificar activación del entorno
   - Reinstalar virtualenv:
     pip install --upgrade virtualenv

5. Error con la base de datos:
   python manage.py migrate --fake-initial

===========================================
ESTRUCTURA DEL PROYECTO
===========================================
proyecto_ecommerce/
├── ecommerce/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── stock_smart/
│   ├── admin.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── templates/
│       ├── admin/
│       └── stock_smart/
├── static/
├── media/
├── manage.py
├── requirements.txt
└── .env

===========================================
CONTACTO Y SOPORTE
===========================================
Para soporte técnico:
- Email: hernan.villanueva.gutierrez@outlook.com
- GitHub: https://github.com/NobelikoCL
- Documentación: [Link a la documentación]

===========================================
LICENCIA
===========================================
Este proyecto está bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

======================================================================================
