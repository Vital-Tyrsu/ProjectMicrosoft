from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Reservation, ReservationLog

@receiver(post_save, sender=Reservation)
def handle_reservation_save(sender, instance, created, **kwargs):
    if created:
        instance.assign_copy()
        ReservationLog.objects.create(
            reservation=instance,
            action='created',
            details=f"Reservation created with status {instance.status}"
        )
    else:
        ReservationLog.objects.create(
            reservation=instance,
            action='updated',
            details=f"Status changed to {instance.status}"
        )