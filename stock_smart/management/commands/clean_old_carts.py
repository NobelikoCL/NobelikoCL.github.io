from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from stock_smart.models import Cart

class Command(BaseCommand):
    help = 'Clean old inactive carts'

    def handle(self, *args, **options):
        # Eliminar carritos inactivos más antiguos que 30 días
        threshold = timezone.now() - timedelta(days=30)
        old_carts = Cart.objects.filter(
            updated_at__lt=threshold,
            is_active=True,
            user__isnull=True  # Solo carritos de visitantes
        )
        
        count = old_carts.count()
        old_carts.update(is_active=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deactivated {count} old carts')
        )