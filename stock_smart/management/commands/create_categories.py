from django.core.management.base import BaseCommand
from stock_smart.models import Category
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Crea las categorías predefinidas'

    def handle(self, *args, **options):
        self.stdout.write('Creando categorías...')

        # Lista de categorías y sus subcategorías
        categories = {
            'Computación': [
                'Notebooks',
                'PC Escritorio',
                'Monitores',
                'Impresoras',
                'Accesorios Computación'
            ],
            'Smartphones': [
                'Apple iPhone',
                'Samsung Galaxy',
                'Xiaomi',
                'Accesorios Celulares',
                'Smartwatch'
            ],
            'Gaming': [
                'Consolas',
                'Videojuegos',
                'Accesorios Gaming',
                'Sillas Gamer',
                'Notebooks Gamer'
            ],
            'Audio': [
                'Audífonos',
                'Parlantes',
                'Audio Profesional',
                'Micrófonos',
                'Equipos de Sonido'
            ]
        }

        try:
            # Crear categorías principales
            for main_category, subcategories in categories.items():
                parent_category = Category.objects.create(
                    name=main_category,
                    slug=slugify(main_category),
                    order=list(categories.keys()).index(main_category),
                    is_active=True
                )
                
                # Crear subcategorías
                for index, subcategory in enumerate(subcategories):
                    Category.objects.create(
                        name=subcategory,
                        parent=parent_category,
                        slug=slugify(subcategory),
                        order=index,
                        is_active=True
                    )
                
            self.stdout.write(self.style.SUCCESS('Categorías creadas exitosamente'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creando categorías: {str(e)}')
            )