"""
Management command to send due date reminders and overdue notices.
Run this daily via Windows Task Scheduler or cron job.

Usage: python manage.py send_due_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from library.models import Borrowing
from library.email_utils import send_due_date_reminder, send_overdue_notice
from django.conf import settings


class Command(BaseCommand):
    help = 'Send due date reminders (2 days before) and overdue notices for borrowings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what emails would be sent without actually sending them',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No emails will be sent\n'))

        # Get today's date
        today = timezone.now().date()
        
        # ===== DUE DATE REMINDERS (2 days before due date) =====
        if settings.SEND_DUE_DATE_REMINDERS:
            reminder_date = today + timedelta(days=2)
            
            # Find all borrowings due in 2 days that haven't been returned
            due_soon_borrowings = Borrowing.objects.filter(
                due_date=reminder_date,
                return_date__isnull=True,
                user__email__isnull=False  # Only users with email
            ).select_related('user', 'copy__book')
            
            reminder_count = 0
            self.stdout.write(f'\n📧 Checking for books due on {reminder_date}...')
            
            for borrowing in due_soon_borrowings:
                if borrowing.user.email:
                    if not dry_run:
                        send_due_date_reminder(borrowing.user, borrowing)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ {"[DRY RUN] Would send" if dry_run else "Sent"} reminder to {borrowing.user.email} '
                            f'for "{borrowing.copy.book.title}"'
                        )
                    )
                    reminder_count += 1
            
            if reminder_count == 0:
                self.stdout.write('  ℹ️  No due date reminders to send today')
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ {"Would send" if dry_run else "Sent"} {reminder_count} due date reminder(s)\n'
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Due date reminders are disabled in settings\n')
            )

        # ===== OVERDUE NOTICES =====
        if settings.SEND_OVERDUE_NOTIFICATIONS:
            # Find all borrowings that are overdue and haven't been returned
            overdue_borrowings = Borrowing.objects.filter(
                due_date__lt=today,
                return_date__isnull=True,
                user__email__isnull=False  # Only users with email
            ).select_related('user', 'copy__book')
            
            overdue_count = 0
            self.stdout.write(f'\n🚨 Checking for overdue books...')
            
            for borrowing in overdue_borrowings:
                if borrowing.user.email:
                    days_overdue = (today - borrowing.due_date).days
                    
                    if not dry_run:
                        send_overdue_notice(borrowing.user, borrowing)
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ⚠️  {"[DRY RUN] Would send" if dry_run else "Sent"} overdue notice to {borrowing.user.email} '
                            f'for "{borrowing.copy.book.title}" ({days_overdue} days overdue)'
                        )
                    )
                    overdue_count += 1
            
            if overdue_count == 0:
                self.stdout.write('  ✅ No overdue books - all good!')
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'\n⚠️  {"Would send" if dry_run else "Sent"} {overdue_count} overdue notice(s)\n'
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Overdue notifications are disabled in settings\n')
            )

        # ===== SUMMARY =====
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Email reminder job completed successfully!'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'\n✅ Dry run completed - no emails were actually sent'
                )
            )
