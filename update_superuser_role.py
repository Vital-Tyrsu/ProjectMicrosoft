"""
Script to update existing superusers to have 'admin' role
Run this with: python update_superuser_role.py
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import User

# Find all superusers
superusers = User.objects.filter(is_superuser=True)

print(f"Found {superusers.count()} superuser(s):")
for user in superusers:
    print(f"  - {user.username}: current role = '{user.role}'")

# Update all superusers to admin role
updated_count = superusers.update(role='admin')

print(f"\n✅ Updated {updated_count} superuser(s) to 'admin' role")

# Verify the update
print("\nVerifying updated superusers:")
for user in User.objects.filter(is_superuser=True):
    print(f"  - {user.username}: role = '{user.role}'")
