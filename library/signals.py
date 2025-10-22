from django.db.models.signals import post_save
from django.dispatch import receiver  # Add this import
from django.utils import timezone
from datetime import timedelta
from .models import Reservation, ReservationLog, Borrowing
from django.conf import settings

# allauth pre-social-login hook
try:
    from allauth.socialaccount.signals import pre_social_login
    from allauth.core.exceptions import ImmediateHttpResponse  # Updated import path
    from django.http import HttpResponseRedirect

    @receiver(pre_social_login)
    def restrict_social_signup(sender, sociallogin, request, **kwargs):
        """Restrict social signups to allowed domains if configured.

        Set environment variable ALLOWED_SIGNUP_DOMAINS to a comma-separated list
        (for example: 'school.edu,school.org') to enable domain restriction.
        """
        allowed = getattr(settings, 'ALLOWED_SIGNUP_DOMAINS', '')
        if not allowed:
            return  # no restriction configured

        allowed_domains = [d.strip().lower() for d in allowed.split(',') if d.strip()]
        email = ''
        if sociallogin and sociallogin.account and sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get('email', '')
        if not email and hasattr(sociallogin.user, 'email'):
            email = sociallogin.user.email or ''

        domain = email.split('@')[-1].lower() if '@' in email else ''
        if domain and domain not in allowed_domains:
            # Redirect back to login with an error message
            raise ImmediateHttpResponse(HttpResponseRedirect('/login/?error=domain'))
except Exception:
    # allauth not installed or import failed - skip domain restriction
    pass


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
        # Note: Borrowing creation is now handled in the confirm_pickup view
        # to prevent race conditions and duplicate borrowing records