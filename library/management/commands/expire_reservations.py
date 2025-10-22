from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from library.models import Reservation, ReservationLog

class Command(BaseCommand):
    help = 'Expires overdue assigned reservations and auto-assigns to next pending'

    def handle(self, *args, **kwargs):
        expired = Reservation.objects.filter(
            status='assigned',
            expiration_date__lt=timezone.now()
        )
        
        expired_count = 0
        reassigned_count = 0
        
        for reservation in expired:
            # Save the copy and book before expiring
            expired_copy = reservation.copy
            book = reservation.book
            
            # Expire the reservation
            reservation.status = 'expired'
            reservation.copy = None
            reservation.save()
            expired_count += 1
            
            self.stdout.write(self.style.WARNING(f'Expired reservation {reservation.id} for {reservation.user.username}'))
            
            # Log the expiration
            ReservationLog.objects.create(
                reservation=reservation,
                action='expired',
                details=f'Reservation expired after {reservation.expiration_date}'
            )
            
            # Try to auto-assign the copy to next pending reservation for the same book
            if expired_copy:
                next_pending = Reservation.objects.filter(
                    book=book,
                    status='pending'
                ).order_by('reservation_date').first()
                
                if next_pending:
                    next_pending.copy = expired_copy
                    next_pending.status = 'assigned'
                    next_pending.expiration_date = timezone.now() + timedelta(days=3)
                    next_pending.save()
                    reassigned_count += 1
                    
                    # Log the auto-assignment
                    ReservationLog.objects.create(
                        reservation=next_pending,
                        action='auto_assigned_on_expiration',
                        details=f'Auto-assigned copy {expired_copy.location} after reservation {reservation.id} expired'
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  → Auto-assigned copy {expired_copy.location} to {next_pending.user.username} (reservation {next_pending.id})'
                        )
                    )
        
        # Summary
        if expired_count > 0:
            summary = f'Processed {expired_count} expired reservation(s)'
            if reassigned_count > 0:
                summary += f', auto-assigned {reassigned_count} to pending reservations'
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.SUCCESS('No expired reservations found'))