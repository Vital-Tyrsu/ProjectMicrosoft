"""
Check for duplicate locations before migration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
django.setup()

from library.models import BookCopy
from django.db.models import Count

print("=" * 70)
print("BOOK COPY LOCATION DUPLICATE CHECK")
print("=" * 70)

# Find duplicate locations
duplicates = BookCopy.objects.values('location').annotate(
    count=Count('id')
).filter(count__gt=1)

if duplicates.count() > 0:
    print(f"\n⚠️  WARNING: Found {duplicates.count()} duplicate location(s)!\n")
    
    for dup in duplicates:
        print(f"📍 Location '{dup['location']}' has {dup['count']} copies:")
        copies = BookCopy.objects.filter(location=dup['location'])
        for copy in copies:
            print(f"   - {copy.book.title} (Copy ID: {copy.id}, Condition: {copy.condition})")
        print()
    
    print("=" * 70)
    print("🔧 ACTION REQUIRED: Fix duplicates before running migration")
    print("=" * 70)
    print("\nOption 1: Manually fix in Django Admin")
    print("   1. Go to Admin → Book Copies")
    print("   2. Edit each duplicate copy")
    print("   3. Assign unique locations (e.g., 1-A-13, 1-A-14, etc.)")
    print()
    print("Option 2: Auto-fix with sequential locations")
    print("   Run: python manage.py shell")
    print("   Then paste:")
    print("""
from library.models import BookCopy
from django.db.models import Count

duplicates = BookCopy.objects.values('location').annotate(
    count=Count('id')
).filter(count__gt=1)

counter = 1
for dup in duplicates:
    copies = list(BookCopy.objects.filter(location=dup['location']))
    # Keep first one, reassign others
    for copy in copies[1:]:
        copy.location = f"TEMP-{counter}"
        copy.save()
        print(f"Reassigned copy {copy.id} to {copy.location}")
        counter += 1

print("✅ Duplicates fixed!")
    """)
    print()
    print("After fixing, run:")
    print("   python manage.py makemigrations")
    print("   python manage.py migrate")
    print()
    
else:
    print("\n✅ No duplicate locations found!")
    print("\nYou can safely proceed with migration:")
    print("   python manage.py makemigrations")
    print("   python manage.py migrate")
    print()

print("=" * 70)
print("CURRENT BOOK COPY SUMMARY")
print("=" * 70)

total_copies = BookCopy.objects.count()
unique_locations = BookCopy.objects.values('location').distinct().count()

print(f"\nTotal book copies: {total_copies}")
print(f"Unique locations: {unique_locations}")

if total_copies == unique_locations:
    print("\n✅ All locations are unique - ready for migration!")
else:
    print(f"\n⚠️  {total_copies - unique_locations} duplicate(s) need to be resolved")

print("\n" + "=" * 70)
