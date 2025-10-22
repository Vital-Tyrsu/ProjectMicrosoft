"""
Test the availability counting fix
"""

print("=" * 70)
print("AVAILABILITY COUNTING TEST")
print("=" * 70)

print("\n📋 SCENARIO:")
print("   • Book has 2 copies")
print("   • test1 creates reservation → gets assigned copy 1")
print("   • test2 creates reservation → gets assigned copy 2")
print("   • test3 can still create reservation (status: pending)")
print()

print("✅ EXPECTED BEHAVIOR:")
print("   • Book Catalog should show: '0 of 2 copies available'")
print("   • test1 has assigned reservation (copy 1 unavailable)")
print("   • test2 has assigned reservation (copy 2 unavailable)")
print("   • test3 can still reserve (goes to pending queue)")
print()

print("🔧 FIX APPLIED:")
print("   • Changed from complex Exists() queries to simple loop")
print("   • For each copy, check:")
print("     1. Is it borrowed? (Borrowing with return_date=NULL)")
print("     2. Is it reserved? (Reservation with status=assigned/picked_up)")
print("   • If either is true, count as unavailable")
print()

print("📝 HOW TO TEST:")
print("   1. Go to Django Admin → Books")
print("   2. Find a book with 2 copies")
print("   3. Note the book title and ID")
print()
print("   4. Login as test1:")
print("      • Go to Book Catalog")
print("      • Reserve the book")
print("      • Should get 'assigned' status immediately")
print("      • Check catalog: '1 of 2 copies available'")
print()
print("   5. Login as test2:")
print("      • Reserve the same book")
print("      • Should get 'assigned' status immediately")
print("      • Check catalog: '0 of 2 copies available'")
print()
print("   6. Login as test3:")
print("      • Reserve the same book")
print("      • Should get 'pending' status")
print("      • Check catalog: STILL '0 of 2 copies available'")
print()
print("   7. Admin confirms test1's pickup:")
print("      • test1 has active borrowing")
print("      • Check catalog: STILL '0 of 2 copies available'")
print()
print("   8. Admin confirms test1's return:")
print("      • test3's pending reservation → 'assigned'")
print("      • Check catalog: '0 of 2 copies available'")
print()

print("=" * 70)
print("DEBUGGING QUERIES")
print("=" * 70)

print("\nTo debug availability counting, run this in Django shell:")
print()
print("python manage.py shell")
print()
print("Then paste:")
print("""
from library.models import Book, BookCopy, Reservation, Borrowing

# Pick a book
book = Book.objects.first()
print(f"Book: {book.title}")

# Get all copies
copies = BookCopy.objects.filter(book=book)
print(f"Total copies: {copies.count()}")

# Check each copy
for copy in copies:
    print(f"\\nCopy {copy.id} ({copy.location}):")
    
    # Check borrowings
    borrowed = Borrowing.objects.filter(
        copy=copy,
        return_date__isnull=True
    ).exclude(status='returned')
    print(f"  Borrowed: {borrowed.exists()} ({borrowed.count()} records)")
    
    # Check reservations
    reserved = Reservation.objects.filter(
        copy=copy,
        status__in=['assigned', 'picked_up']
    )
    print(f"  Reserved: {reserved.exists()} ({reserved.count()} records)")
    
    # Status
    if borrowed.exists() or reserved.exists():
        print(f"  → UNAVAILABLE")
    else:
        print(f"  → AVAILABLE")

# Calculate total
unavailable = 0
for copy in copies:
    is_borrowed = Borrowing.objects.filter(
        copy=copy,
        return_date__isnull=True
    ).exclude(status='returned').exists()
    
    is_reserved = Reservation.objects.filter(
        copy=copy,
        status__in=['assigned', 'picked_up']
    ).exists()
    
    if is_borrowed or is_reserved:
        unavailable += 1

print(f"\\nSummary: {copies.count() - unavailable} of {copies.count()} available")
""")

print()
print("=" * 70)
print()

print("🎯 KEY INSIGHT:")
print("   • 'assigned' reservations make copies UNAVAILABLE")
print("   • 'pending' reservations do NOT affect availability")
print("   • Users can always create reservations (goes to pending queue)")
print("   • Catalog shows PHYSICAL availability, not queue position")
print()

print("=" * 70)
