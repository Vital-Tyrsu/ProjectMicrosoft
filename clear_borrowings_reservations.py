"""
Script to delete all borrowings and reservations
Keeps books, book copies, and users intact
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import Borrowing, Reservation

def clear_borrowings_and_reservations():
    """Delete all borrowings and reservations"""
    
    # Count before deletion
    borrowing_count = Borrowing.objects.count()
    reservation_count = Reservation.objects.count()
    
    print("=" * 50)
    print("CLEARING BORROWINGS AND RESERVATIONS")
    print("=" * 50)
    print(f"\nFound:")
    print(f"  - {borrowing_count} borrowing(s)")
    print(f"  - {reservation_count} reservation(s)")
    
    # Confirm deletion
    confirm = input("\n⚠️  Delete all borrowings and reservations? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Delete all borrowings
        Borrowing.objects.all().delete()
        print(f"\n✓ Deleted {borrowing_count} borrowing(s)")
        
        # Delete all reservations
        Reservation.objects.all().delete()
        print(f"✓ Deleted {reservation_count} reservation(s)")
        
        print("\n" + "=" * 50)
        print("CLEANUP COMPLETE!")
        print("=" * 50)
        print("\nBooks, book copies, and users are still intact.")
        print("All copies are now available for new reservations.")
    else:
        print("\n❌ Deletion canceled.")

if __name__ == '__main__':
    clear_borrowings_and_reservations()
