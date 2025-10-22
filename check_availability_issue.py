"""
Check why books remain unavailable after return
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import Borrowing, BookCopy, Reservation
from django.db.models import Q

print("=" * 70)
print("CHECKING BORROWING STATUS AFTER RETURNS")
print("=" * 70)

# Check all borrowings
borrowings = Borrowing.objects.all()[:20]
print(f"\n📚 Total Borrowings in DB: {Borrowing.objects.count()}")
print("\n--- Recent Borrowings ---")
for b in borrowings:
    print(f"ID: {b.id}")
    print(f"  Book: {b.copy.book.title}")
    print(f"  User: {b.user.username}")
    print(f"  Status: {b.status}")
    print(f"  Return Date: {b.return_date}")
    print(f"  Borrow Date: {b.borrow_date}")
    print()

print("\n" + "=" * 70)
print("TESTING AVAILABILITY QUERY")
print("=" * 70)

# Test a specific book copy
test_copies = BookCopy.objects.all()[:5]
for copy in test_copies:
    print(f"\n📖 Testing: {copy}")
    
    # Check if it has any borrowings
    all_borrowings = Borrowing.objects.filter(copy=copy)
    print(f"  Total borrowings for this copy: {all_borrowings.count()}")
    
    for b in all_borrowings:
        print(f"    - Status: {b.status}, Return Date: {b.return_date}")
    
    # Check the availability query (same as in views.py)
    unavailable = BookCopy.objects.filter(
        id=copy.id
    ).filter(
        Q(borrowing__return_date__isnull=True, borrowing__status='active') |
        Q(reservation__status__in=['assigned', 'picked_up'])
    ).exists()
    
    print(f"  ❓ Is unavailable (per query)? {unavailable}")
    
    # Check what makes it unavailable
    has_active_borrowing = Borrowing.objects.filter(
        copy=copy,
        return_date__isnull=True,
        status='active'
    ).exists()
    
    has_active_reservation = Reservation.objects.filter(
        copy=copy,
        status__in=['assigned', 'picked_up']
    ).exists()
    
    print(f"  🔍 Has active borrowing (return_date=NULL, status=active)? {has_active_borrowing}")
    print(f"  🔍 Has active reservation (assigned/picked_up)? {has_active_reservation}")

print("\n" + "=" * 70)
print("CHECKING FOR 'return_pending' ISSUES")
print("=" * 70)

# Check if there are any return_pending borrowings
return_pending = Borrowing.objects.filter(status='return_pending')
print(f"\n⏳ Return Pending Borrowings: {return_pending.count()}")
for b in return_pending:
    print(f"  - {b.copy.book.title} by {b.user.username}")
    print(f"    Return Date: {b.return_date}")
    print(f"    Status: {b.status}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total Borrowings: {Borrowing.objects.count()}")
print(f"Active (not returned): {Borrowing.objects.filter(return_date__isnull=True).count()}")
print(f"Status='active': {Borrowing.objects.filter(status='active').count()}")
print(f"Status='return_pending': {Borrowing.objects.filter(status='return_pending').count()}")
print(f"Status='returned': {Borrowing.objects.filter(status='returned').count()}")
print(f"Returned (has return_date): {Borrowing.objects.filter(return_date__isnull=False).count()}")
