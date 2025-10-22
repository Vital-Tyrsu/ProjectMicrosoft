"""
Quick test to check if email sending is working
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=" * 60)
print("EMAIL CONFIGURATION TEST")
print("=" * 60)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {'*' * 10} (set: {bool(settings.EMAIL_HOST_PASSWORD)})")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("=" * 60)

# Try to send a test email
print("\n📧 Attempting to send test email...")
try:
    result = send_mail(
        subject='Test Email from Library System',
        message='This is a test email. If you receive this, email sending is working!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['vital.tyrsu@gmail.com'],
        fail_silently=False,  # Raise errors so we can see them
    )
    print(f"✅ Email sent successfully! Result: {result}")
except Exception as e:
    print(f"❌ Error sending email: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
