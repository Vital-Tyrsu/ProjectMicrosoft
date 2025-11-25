# Location Uniqueness - Quick Implementation Guide

## ✅ What Changed

Added `unique=True` to BookCopy.location field to enforce that each physical shelf location can only hold one book.

---

## 🚀 Implementation Steps

### Step 1: Check for Existing Duplicates
```bash
python check_location_duplicates.py
```

**If you see "✅ No duplicates"**: Skip to Step 3  
**If you see "⚠️ WARNING"**: Continue to Step 2

---

### Step 2: Fix Duplicates (If Found)

#### Option A: Manual Fix (Recommended)
1. Open Django Admin
2. Go to "Book Copies"
3. For each duplicate location, edit and assign a new unique location
4. Example: If two books at "1-A-12", change second one to "1-A-13"

#### Option B: Auto-Fix
```bash
python manage.py shell
```

Then paste:
```python
from library.models import BookCopy
from django.db.models import Count

duplicates = BookCopy.objects.values('location').annotate(
    count=Count('id')
).filter(count__gt=1)

counter = 1
for dup in duplicates:
    copies = list(BookCopy.objects.filter(location=dup['location']))
    for copy in copies[1:]:
        copy.location = f"TEMP-{counter}"
        copy.save()
        print(f"✓ Reassigned copy {copy.id} to {copy.location}")
        counter += 1

print("✅ All duplicates fixed!")
exit()
```

Then manually reassign the TEMP locations to proper ones in admin.

---

### Step 3: Create Migration
```bash
python manage.py makemigrations
```

Expected output:
```
Migrations for 'library':
  library/migrations/0004_alter_bookcopy_location.py
    - Alter field location on bookcopy
```

---

### Step 4: Apply Migration
```bash
python manage.py migrate
```

Expected output:
```
Running migrations:
  Applying library.0004_alter_bookcopy_location... OK
```

---

### Step 5: Test It
Try creating a duplicate in admin:

1. Create a book copy with location "TEST-1"
2. Try to create another copy with location "TEST-1"
3. Should see error: "Book copy with this Location already exists."
4. ✅ Working correctly!

---

## 🎯 Benefits

| Before | After |
|--------|-------|
| ❌ Multiple books at same location | ✅ One book per location |
| ❌ Inventory confusion | ✅ Clear inventory |
| ❌ Users can't find books | ✅ Precise locations |
| ❌ No validation | ✅ Database-enforced |

---

## 📝 Going Forward

### When Adding New Copies:
- Each copy MUST have a unique location
- Use sequential locations: 1-A-12, 1-A-13, 1-A-14...
- Admin will prevent duplicates automatically

### Error Handling:
If you try to save a duplicate location, you'll see:
```
UNIQUE constraint failed: book_copies.location
```

Solution: Choose a different location!

---

## 🆘 Troubleshooting

**Migration fails with "UNIQUE constraint failed":**
- You still have duplicates in database
- Run `python check_location_duplicates.py` again
- Fix all duplicates before migrating

**Can't find available locations:**
- Use format: [Floor]-[Section]-[Shelf]
- Example: 1-A-12, 1-A-13, 2-B-05, etc.
- Locations are freed when copies are deleted

**Need to move a book:**
- Edit the copy in admin
- Change location to new shelf
- Save (will validate uniqueness)

---

## ✨ Summary

**Status**: Code updated, migration ready  
**Risk**: Low (just enforces what should already be true)  
**Benefit**: High (data integrity, better UX)  
**Action**: Run the steps above when ready

**Your library system now enforces physical reality in the database!** 📚
