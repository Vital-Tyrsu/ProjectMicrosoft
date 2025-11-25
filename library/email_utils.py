"""
Email notification utilities for the library system.
Sends emails for reservations, borrowings, due dates, and overdue notices.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from datetime import datetime, timedelta


def get_site_url():
    """Get the site URL from settings or use a default"""
    # Try to get from environment variable or settings
    site_url = getattr(settings, 'SITE_URL', None)
    if not site_url:
        # Fallback to constructing from ALLOWED_HOSTS
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', ['localhost'])
        if allowed_hosts and allowed_hosts[0] != 'localhost':
            site_url = f'https://{allowed_hosts[0]}'
        else:
            site_url = 'http://localhost:8000'
    return site_url


def send_reservation_confirmation(user, reservation):
    """
    Send confirmation email when a user makes a reservation.
    
    Args:
        user: User who made the reservation
        reservation: Reservation object
    """
    if not settings.SEND_RESERVATION_EMAILS:
        return
    
    subject = f'✅ Reservation Confirmed - {reservation.book.title}'
    
    # Calculate expiry date (7 days from now)
    expiry_date = reservation.reservation_date + timedelta(days=7)
    
    context = {
        'user': user,
        'reservation': reservation,
        'book': reservation.book,
        'expiry_date': expiry_date,
        'site_url': get_site_url(),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/reservation_confirmed.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,  # Show errors during testing
        )
        print(f"✅ Reservation confirmation email sent to {user.email}")
    except Exception as e:
        print(f"❌ Failed to send reservation confirmation to {user.email}: {e}")


def send_reservation_assigned(user, reservation, book_copy):
    """
    Send email when an admin assigns a copy to a reservation.
    
    Args:
        user: User who made the reservation
        reservation: Reservation object
        book_copy: BookCopy that was assigned
    """
    if not settings.SEND_RESERVATION_EMAILS:
        return
    
    subject = f'📖 Your Book is Ready for Pickup - {reservation.book.title}'
    
    # Calculate pickup deadline (48 hours from now)
    pickup_deadline = datetime.now() + timedelta(hours=48)
    
    context = {
        'user': user,
        'reservation': reservation,
        'book': reservation.book,
        'book_copy': book_copy,
        'location': book_copy.location,
        'pickup_deadline': pickup_deadline,
        'site_url': get_site_url(),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/reservation_assigned.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,  # Show errors during testing
        )
        print(f"✅ Assignment notification email sent to {user.email}")
    except Exception as e:
        print(f"❌ Failed to send assignment notification to {user.email}: {e}")


def send_due_date_reminder(user, borrowing):
    """
    Send reminder email 2 days before book is due.
    
    Args:
        user: User who borrowed the book
        borrowing: Borrowing object
    """
    if not settings.SEND_DUE_DATE_REMINDERS:
        return
    
    subject = f'⏰ Due Date Reminder - {borrowing.copy.book.title}'
    
    # Calculate days until due
    days_until_due = (borrowing.due_date.date() - datetime.now().date()).days
    
    context = {
        'user': user,
        'borrowing': borrowing,
        'book': borrowing.copy.book,
        'due_date': borrowing.due_date,
        'days_until_due': days_until_due,
        'site_url': get_site_url(),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/due_reminder.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Due date reminder sent to {user.email}")
    except Exception as e:
        print(f"❌ Failed to send due date reminder to {user.email}: {e}")


def send_overdue_notice(user, borrowing):
    """
    Send overdue notice when book is past due date.
    
    Args:
        user: User who borrowed the book
        borrowing: Borrowing object
    """
    if not settings.SEND_OVERDUE_NOTIFICATIONS:
        return
    
    subject = f'⚠️ Overdue Book Notice - {borrowing.copy.book.title}'
    
    # Calculate days overdue
    days_overdue = (datetime.now().date() - borrowing.due_date.date()).days
    
    context = {
        'user': user,
        'borrowing': borrowing,
        'book': borrowing.copy.book,
        'due_date': borrowing.due_date,
        'days_overdue': days_overdue,
        'site_url': get_site_url(),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/overdue_notice.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Overdue notice sent to {user.email}")
    except Exception as e:
        print(f"❌ Failed to send overdue notice to {user.email}: {e}")


def send_pickup_confirmation(user, borrowing):
    """
    Send confirmation email when a user picks up a book.
    
    Args:
        user: User who picked up the book
        borrowing: Borrowing object that was created
    """
    subject = f'✅ Pickup Confirmed - {borrowing.copy.book.title}'
    
    context = {
        'user': user,
        'borrowing': borrowing,
        'book': borrowing.copy.book,
        'site_url': get_site_url(),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/pickup_confirmed.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Pickup confirmation email sent to {user.email}")
    except Exception as e:
        print(f"❌ Failed to send pickup confirmation to {user.email}: {e}")


def send_return_confirmation(user, borrowing):
    """
    Send confirmation email when a user returns a book.
    
    Args:
        user: User who returned the book
        borrowing: Borrowing object with return_date set
    """
    from datetime import date
    
    subject = f'✅ Return Confirmed - {borrowing.copy.book.title}'
    
    # Calculate if return was on time
    was_on_time = borrowing.return_date.date() <= borrowing.due_date.date()
    days_late = 0
    if not was_on_time:
        days_late = (borrowing.return_date.date() - borrowing.due_date.date()).days
    
    context = {
        'user': user,
        'borrowing': borrowing,
        'book': borrowing.copy.book,
        'was_on_time': was_on_time,
        'days_late': days_late,
        'site_url': get_site_url(),
    }
    
    # Render HTML email
    html_message = render_to_string('emails/return_confirmed.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"✅ Return confirmation email sent to {user.email}")
    except Exception as e:
        print(f"❌ Failed to send return confirmation to {user.email}: {e}")
