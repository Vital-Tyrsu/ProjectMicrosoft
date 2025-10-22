"""
Script to make test1 a staff user so they can access admin panel
Run this with: python make_test1_staff.py
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import User

try:
    user = User.objects.get(username='test1')
    user.is_staff = True
    user.save()
    print(f"✅ User 'test1' is now staff and can access admin panel at http://localhost:8000/admin/")
    print(f"   Username: test1")
    print(f"   Role: {user.role}")
except User.DoesNotExist:
    print("❌ User 'test1' does not exist. Please create it first.")
