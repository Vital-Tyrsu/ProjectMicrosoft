#!/usr/bin/env python
"""
Script to add Google OAuth credentials to Django admin
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def add_google_credentials():
    """Add Google OAuth credentials to the database"""
    
    # Get or create the site
    site = Site.objects.get(id=1)
    
    # Google OAuth credentials
    # IMPORTANT: Replace these with your actual credentials
    # Get them from https://console.cloud.google.com/apis/credentials
    client_id = "YOUR_GOOGLE_CLIENT_ID_HERE"
    client_secret = "YOUR_GOOGLE_CLIENT_SECRET_HERE"
    
    # Create or update the Google SocialApp
    google_app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google',
            'client_id': client_id,
            'secret': client_secret,
        }
    )
    
    if not created:
        # Update existing app
        google_app.client_id = client_id
        google_app.secret = client_secret
        google_app.save()
        print("✅ Updated existing Google OAuth credentials")
    else:
        print("✅ Created new Google OAuth credentials")
    
    # Add the site to the social app
    if site not in google_app.sites.all():
        google_app.sites.add(site)
        print(f"✅ Linked to site: {site.domain}")
    else:
        print(f"✅ Already linked to site: {site.domain}")
    
    print("\n" + "="*60)
    print("🎉 Google OAuth Setup Complete!")
    print("="*60)
    print(f"\nClient ID: {client_id[:30]}...")
    print(f"Site: {site.domain}")
    print("\n✅ You can now test the 'Sign in with Google' button!")
    print("\nNext steps:")
    print("1. Start the server: python manage.py runserver")
    print("2. Go to: http://localhost:8000/accounts/login/")
    print("3. Click 'Sign in with Google'")
    print("4. Sign in with any Google account")
    print("5. You should be redirected back and logged in!")

if __name__ == '__main__':
    add_google_credentials()
