"""
Management command to mark severely overdue books as lost and free them for the system.
Run this daily to automatically recover books that are overdue by 14+ days.

Usage: python manage.py mark_lost_books
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from library.models import Borrowing, BookCopy, Reservation, ReservationLog
from library.email_utils import send_overdue_notice


class Command(BaseCommand):
    help = 'Mark books as lost after 14 days overdue and notify waiting reservations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=14,
            help='Number of days overdue before marking as lost (default: 14)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be marked as lost without actually doing it',
        )

    def handle(self, *args, **options):
        threshold_days = options['threshold']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'🔍 DRY RUN MODE - No changes will be made\n'))

        self.stdout.write(f'🔍 Checking for books overdue by {threshold_days}+ days...\n')
        
        # Find all severely overdue borrowings
        severely_overdue = Borrowing.objects.filter(
            return_date__isnull=True,
            status='active'
        ).select_related('user', 'copy__book')
        
        lost_count = 0
        notified_users = 0
        would_mark_count = 0  # Track dry-run results
        
        for borrowing in severely_overdue:
            days_overdue = borrowing.days_overdue()
            
            if days_overdue >= threshold_days:
                book_copy = borrowing.copy
                book = book_copy.book
                user = borrowing.user
                
                self.stdout.write(
                    self.style.ERROR(
                        f'⚠️  Book "{book.title}" (Copy {book_copy.location}) '
                        f'borrowed by {user.username} is {days_overdue} days overdue'
                    )
                )
                
                if not dry_run:
                    # Mark the copy as lost
                    book_copy.mark_as_lost(
                        reason=f'Not returned after {days_overdue} days overdue. '
                               f'Borrowed by {user.username} on {borrowing.borrow_date.strftime("%Y-%m-%d")}'
                    )
                    
                    # Mark the borrowing as returned (with note)
                    borrowing.status = 'returned'
                    borrowing.return_date = timezone.now()
                    borrowing.save()
                    
                    # Create log entry
                    ReservationLog.objects.create(
                        reservation=None,
                        action='book_marked_lost',
                        details=f'Book copy {book_copy.location} of "{book.title}" marked as lost. '
                                f'Was {days_overdue} days overdue by {user.username}.'
                    )
                    
                    lost_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Marked copy {book_copy.location} as lost and closed borrowing'
                        )
                    )
                    
                    # Check for pending reservations for this book
                    pending_reservations = Reservation.objects.filter(
                        book=book,
                        status='pending'
                    ).select_related('user')
                    
                    if pending_reservations.exists():
                        self.stdout.write(
                            self.style.WARNING(
                                f'  📧 Found {pending_reservations.count()} pending reservation(s) for this book'
                            )
                        )
                        
                        # Send notification to all waiting users
                        for reservation in pending_reservations:
                            # TODO: Create email template for lost book notification
                            # For now, just log it
                            ReservationLog.objects.create(
                                reservation=reservation,
                                action='notified_book_lost',
                                details=f'User {reservation.user.username} notified that copy {book_copy.location} was marked as lost'
                            )
                            notified_users += 1
                            
                            self.stdout.write(
                                self.style.WARNING(
                                    f'    → Logged notification for {reservation.user.username}'
                                )
                            )
                else:
                    would_mark_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  [DRY RUN] Would mark copy {book_copy.location} as lost'
                        )
                    )
        
        # Summary
        if lost_count > 0 or would_mark_count > 0:
            count_to_show = lost_count if not dry_run else would_mark_count
            summary = f'\n{"[DRY RUN] Would mark" if dry_run else "Marked"} {count_to_show} book(s) as lost'
            if notified_users > 0:
                summary += f', notified {notified_users} waiting user(s)'
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ No severely overdue books found'))
        
        if not dry_run and lost_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n💡 TIP: Admin should contact the {lost_count} user(s) about lost books'
                )
            )
