web: python manage.py collectstatic --no-input && python manage.py migrate && gunicorn ecommerce.wsgi --timeout 60 --keep-alive 5 --log-level debug
