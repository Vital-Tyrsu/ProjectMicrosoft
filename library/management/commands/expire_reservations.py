from django.core.management.base import BaseCommand
from django.utils import timezone
from library.models import Reservation

class Command(BaseCommand):
    help = 'Expires overdue assigned reservations'

    def handle(self, *args, **kwargs):
        expired = Reservation.objects.filter(
            status='assigned',
            expiration_date__lt=timezone.now()
        )
        for reservation in expired:
            reservation.status = 'expired'
            reservation.copy = None
            reservation.save()
            self.stdout.write(self.style.SUCCESS(f'Expired reservation {reservation.id}'))