"""
Debug script to check user emails and reservations
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import User, Reservation

print("=" * 60)
print("USER EMAIL CHECK")
print("=" * 60)

users = User.objects.all()
print(f"\nTotal users: {users.count()}\n")

for user in users:
    print(f"Username: {user.username}")
    print(f"  Email: {user.email or '❌ NO EMAIL SET'}")
    print(f"  Has email: {bool(user.email)}")
    
    # Check their reservations
    reservations = Reservation.objects.filter(user=user).order_by('-reservation_date')
    if reservations.exists():
        print(f"  Reservations: {reservations.count()}")
        for res in reservations[:3]:  # Show last 3
            print(f"    - {res.book.title} ({res.status}) on {res.reservation_date}")
    else:
        print(f"  Reservations: None")
    print()

print("=" * 60)
print("\nRECENT RESERVATIONS (All users)")
print("=" * 60)
recent = Reservation.objects.all().order_by('-reservation_date')[:10]
for res in recent:
    print(f"{res.reservation_date} | {res.user.username} ({res.user.email or 'NO EMAIL'}) | {res.book.title} | {res.status}")
