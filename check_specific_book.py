"""
Check specific book availability
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import Borrowing, BookCopy, Book, Reservation
from django.db.models import Q

print("=" * 70)
print("CHECKING THE RETURNED BOOK AVAILABILITY")
print("=" * 70)

# Find the returned borrowing
returned_borrowing = Borrowing.objects.get(id=26)
print(f"\n📚 Returned Borrowing:")
print(f"  Book: {returned_borrowing.copy.book.title}")
print(f"  Copy Location: {returned_borrowing.copy.location}")
print(f"  User: {returned_borrowing.user.username}")
print(f"  Status: {returned_borrowing.status}")
print(f"  Return Date: {returned_borrowing.return_date}")

# Get the book
book = returned_borrowing.copy.book
print(f"\n📖 Book Details: {book.title}")

# Count total copies
total_copies = BookCopy.objects.filter(book=book).count()
print(f"  Total copies: {total_copies}")

# List all copies
print(f"\n  All copies:")
for copy in BookCopy.objects.filter(book=book):
    print(f"    - {copy.location}")

# Count unavailable copies (same logic as views.py - UPDATED)
# Now we only count 'assigned' reservations, not 'picked_up' (already borrowed)
unavailable_copies = BookCopy.objects.filter(
    book=book
).filter(
    Q(borrowing__return_date__isnull=True, borrowing__status='active') |
    Q(reservation__status='assigned')  # Only 'assigned', not 'picked_up'
).distinct()

print(f"\n  Unavailable copies (per query): {unavailable_copies.count()}")
for copy in unavailable_copies:
    print(f"    - {copy.location}")
    
    # Check why it's unavailable
    active_borr = Borrowing.objects.filter(
        copy=copy,
        return_date__isnull=True,
        status='active'
    ).first()
    
    active_res = Reservation.objects.filter(
        copy=copy,
        status='assigned'  # Only 'assigned', not 'picked_up'
    ).first()
    
    picked_up_res = Reservation.objects.filter(
        copy=copy,
        status='picked_up'
    ).first()
    
    if active_borr:
        print(f"      Reason: Active borrowing by {active_borr.user.username}")
    if active_res:
        print(f"      Reason: Active reservation by {active_res.user.username} ({active_res.status})")
    if picked_up_res:
        print(f"      Note: Has 'picked_up' reservation (IGNORED - already borrowed): {picked_up_res.user.username}")

available_copies = total_copies - unavailable_copies.count()
print(f"\n✅ AVAILABLE COPIES: {available_copies} out of {total_copies}")

# Check if there are any reservations for this book
print(f"\n📋 Reservations for this book:")
reservations = Reservation.objects.filter(book=book)
if reservations.exists():
    for res in reservations:
        print(f"  - User: {res.user.username}")
        print(f"    Status: {res.status}")
        print(f"    Copy: {res.copy.location if res.copy else 'Not assigned'}")
else:
    print("  No reservations")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
if available_copies > 0:
    print(f"✅ The book '{book.title}' IS AVAILABLE ({available_copies} cop{'y' if available_copies == 1 else 'ies'})")
    print("   It should show as available in the catalog!")
else:
    print(f"❌ The book '{book.title}' is NOT AVAILABLE")
    print("   All copies are either borrowed or reserved")
