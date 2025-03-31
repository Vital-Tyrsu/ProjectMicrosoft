from django.db.models.signals import post_save
from django.dispatch import receiver  # Add this import
from django.utils import timezone
from datetime import timedelta
from .models import Reservation, ReservationLog, Borrowing


@receiver(post_save, sender=Reservation)
def handle_reservation_save(sender, instance, created, **kwargs):
    print(f"Signal triggered for reservation {instance.id}, status: {instance.status}, created: {created}")
    if created:
        print(f"New reservation created, assigning copy for reservation {instance.id}")
        instance.assign_copy()
        ReservationLog.objects.create(
            reservation=instance,
            action='created',
            details=f"Reservation created with status {instance.status}"
        )
    else:
        print(f"Reservation {instance.id} updated, new status: {instance.status}")
        ReservationLog.objects.create(
            reservation=instance,
            action='updated',
            details=f"Status changed to {instance.status}"
        )
        if instance.status == 'picked_up' and instance.copy:
            print(f"Reservation {instance.id} is picked up, checking for existing Borrowing")
            # Check if a Borrowing already exists for this reservation
            existing_borrowing = Borrowing.objects.filter(
                user=instance.user,
                copy=instance.copy,
                return_date__isnull=True
            ).first()
            if not existing_borrowing:
                try:
                    borrowing = Borrowing.objects.create(
                        user=instance.user,
                        copy=instance.copy,
                        borrow_date=timezone.now(),
                        return_date=timezone.now() + timedelta(days=14),
                        renewal_count=0  # Explicitly set to 0
                    )
                    print(f"Borrowing created: {borrowing.id} for user {instance.user} and copy {instance.copy}")
                    ReservationLog.objects.create(
                        reservation=instance,
                        action='borrowing_created',
                        details=f"Borrowing {borrowing.id} created for user {instance.user.username} and copy {instance.copy}"
                    )
                except Exception as e:
                    print(f"Error creating Borrowing for reservation {instance.id}: {str(e)}")
                    ReservationLog.objects.create(
                        reservation=instance,
                        action='borrowing_failed',
                        details=f"Failed to create Borrowing: {str(e)}"
                    )
            else:
                print(f"Existing Borrowing found: {existing_borrowing.id} for user {instance.user} and copy {instance.copy}")
                ReservationLog.objects.create(
                    reservation=instance,
                    action='borrowing_skipped',
                    details=f"Existing Borrowing {existing_borrowing.id} already exists for this user and copy"
                )
        else:
            print(f"No Borrowing created for reservation {instance.id}: status={instance.status}, copy={instance.copy}")