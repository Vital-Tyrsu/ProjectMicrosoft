"""
Management command to restore a lost book copy when it's returned.
This makes it available for circulation again.

Usage: python manage.py restore_lost_book <location>
Example: python manage.py restore_lost_book 3-B-4
"""

from django.core.management.base import BaseCommand
from library.models import BookCopy, Reservation


class Command(BaseCommand):
    help = 'Restore a lost book copy when student returns it'

    def add_arguments(self, parser):
        parser.add_argument(
            'location',
            type=str,
            help='Physical location of the book copy (e.g., 3-B-4)',
        )
        parser.add_argument(
            '--condition',
            type=str,
            default='fair',
            choices=['new', 'good', 'fair', 'poor'],
            help='Condition of the returned book (default: fair)',
        )

    def handle(self, *args, **options):
        location = options['location']
        condition = options['condition']
        
        try:
            book_copy = BookCopy.objects.get(location=location)
        except BookCopy.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ No book copy found at location "{location}"')
            )
            return
        
        if book_copy.condition != 'lost':
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Book copy at {location} is not marked as lost '
                    f'(current condition: {book_copy.condition})'
                )
            )
            return
        
        book = book_copy.book
        
        self.stdout.write(
            self.style.WARNING(
                f'\n📚 Found lost book: "{book.title}" at {location}\n'
                f'   Lost Date: {book_copy.lost_date}\n'
                f'   Lost Reason: {book_copy.lost_reason}\n'
            )
        )
        
        # Restore the book
        old_condition = book_copy.condition
        old_reason = book_copy.lost_reason
        
        book_copy.condition = condition
        book_copy.lost_date = None
        book_copy.lost_reason = None
        book_copy.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Book restored!\n'
                f'   Location: {location}\n'
                f'   Condition: {old_condition} → {condition}\n'
            )
        )
        
        # Check for pending reservations
        pending_reservations = Reservation.objects.filter(
            book=book,
            status='pending'
        ).order_by('reservation_date')
        
        if pending_reservations.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Great news! {pending_reservations.count()} user(s) waiting for this book:'
                )
            )
            for i, reservation in enumerate(pending_reservations, 1):
                self.stdout.write(
                    f'   {i}. {reservation.user.username} (reserved {reservation.reservation_date.strftime("%Y-%m-%d")})'
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n💡 The book will be auto-assigned to {pending_reservations.first().user.username} '
                    f'(oldest reservation) when you run the assignment system.'
                )
            )
            
            # Try to auto-assign immediately
            first_pending = pending_reservations.first()
            first_pending.assign_copy()
            
            if first_pending.status == 'assigned':
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ AUTO-ASSIGNED to {first_pending.user.username}! '
                        f'They have been notified by email.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n⚠️  Could not auto-assign. Please check reservations manually.'
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n📖 Book is now available for new reservations'
                )
            )
        
        # Log the restoration
        from library.models import ReservationLog
        ReservationLog.objects.create(
            reservation=None,
            action='lost_book_restored',
            details=f'Book copy {location} of "{book.title}" was restored. '
                   f'Previous reason: {old_reason}'
        )
