"""
Setup Site for django-allauth
Run this once after migrations
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from django.contrib.sites.models import Site

# Create or update the Site
site, created = Site.objects.get_or_create(
    id=1,
    defaults={
        'domain': 'localhost:8000',
        'name': 'Library System (Development)'
    }
)

if not created:
    site.domain = 'localhost:8000'
    site.name = 'Library System (Development)'
    site.save()
    print(f"✅ Updated Site: {site.domain}")
else:
    print(f"✅ Created Site: {site.domain}")

print("\n📝 Next steps:")
print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
print("2. Create OAuth 2.0 credentials")
print("3. Add authorized redirect URI: http://localhost:8000/accounts/google/login/callback/")
print("4. Copy Client ID and Client Secret")
print("5. Set environment variables:")
print("   - SOCIAL_AUTH_GOOGLE_CLIENT_ID=your_client_id")
print("   - SOCIAL_AUTH_GOOGLE_CLIENT_SECRET=your_client_secret")
print("\n6. Or add them in Django admin:")
print("   - Run: python manage.py runserver")
print("   - Go to: http://localhost:8000/admin/socialaccount/socialapp/")
print("   - Add new Social application (Google)")
print("   - Select Site: Library System (Development)")
