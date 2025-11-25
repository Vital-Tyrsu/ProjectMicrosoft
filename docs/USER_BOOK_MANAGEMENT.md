# User & Book Management Guide

## 📖 Handling Lost Books That Are Returned

### Scenario: Student Returns Book After It's Marked Lost

**Three Ways to Handle:**

### 1. **Using Management Command** (Easiest)
```bash
# Restore the book and auto-assign to waiting users
python manage.py restore_lost_book 3-B-4

# Specify condition if book is damaged
python manage.py restore_lost_book 3-B-4 --condition fair
python manage.py restore_lost_book 3-B-4 --condition poor
```

**What it does:**
- ✅ Changes condition from `lost` to `good`/`fair`/`poor`
- ✅ Clears lost_date and lost_reason
- ✅ Shows list of users waiting for the book
- ✅ Automatically assigns to next pending reservation
- ✅ Sends email notification to the user
- ✅ Logs the restoration

**Example Output:**
```
📚 Found lost book: "Harry Potter" at 3-B-4
   Lost Date: 2025-11-10
   Lost Reason: Not returned after 18 days overdue

✅ Book restored!
   Location: 3-B-4
   Condition: lost → fair

🎉 Great news! 2 user(s) waiting for this book:
   1. john_doe (reserved 2025-11-01)
   2. jane_smith (reserved 2025-11-05)

✅ AUTO-ASSIGNED to john_doe! They have been notified by email.
```

---

### 2. **Using Django Admin Panel** (Manual)

1. Go to: **Admin Panel** → **Book Copies**
2. Search for the location (e.g., "3-B-4")
3. Click on the book copy
4. Change fields:
   - **Condition:** `lost` → `good` or `fair`
   - **Lost date:** Clear it (delete the date)
   - **Lost reason:** Clear it
5. Click **Save**

**What happens:**
- Copy becomes available again
- System will auto-assign on next reservation check

---

### 3. **If Book is Too Damaged to Circulate**

Don't restore it - just note it:
- Keep condition as `lost` OR change to `poor`
- Leave it out of circulation
- Order a replacement copy instead

---

## 👤 Deleting Users (With Safeguards)

### **Access:**
Go to: **Django Admin Panel** → **Users**

---

### **Option 1: DEACTIVATE User (Recommended - Safer)**

**Why deactivate instead of delete?**
- ✅ Preserves borrowing history
- ✅ Preserves reservation records
- ✅ Can be reactivated later if needed
- ✅ No data loss

**How to deactivate:**
1. Find the user in the list
2. Check the box next to their name
3. In "Action" dropdown, select: **"Deactivate selected users"**
4. Click **"Go"**

**Result:**
- User cannot log in
- All history preserved
- Can be reactivated later

---

### **Option 2: DELETE User (Permanent - Use with Caution)**

**⚠️ WARNING:**
- Deletes ALL borrowing records for that user
- Deletes ALL reservations for that user
- **Cannot be undone!**

**When you should delete:**
- Test accounts
- Duplicate accounts
- Accounts with no activity

**How to delete:**

#### **Single User:**
1. Go to **Admin Panel** → **Users**
2. Click on the user's name
3. Scroll to bottom
4. Click red **"Delete"** button
5. **Review the warning:**
   ```
   Warning: User john_doe has 5 borrowing(s) and 2 reservation(s).
   These will also be deleted. Consider deactivating the user instead.
   ```
6. If sure, confirm deletion

#### **Multiple Users (Bulk Delete):**
1. Go to **Admin Panel** → **Users**
2. Check boxes next to users you want to delete
3. In "Action" dropdown, select: **"Delete selected users"**
4. Click **"Go"**
5. **Review the warning:**
   ```
   Warning: Deleting 3 users will also delete 12 borrowing(s) and 5 reservation(s).
   Consider deactivating users instead.
   ```
6. If sure, confirm deletion

---

### **Enhanced Features in User Admin:**

**List View Shows:**
- Username
- Email
- Role (student/teacher/admin)
- Active status (✓ or ✗)
- Date joined

**Search Functionality:**
- Search by username, email, first name, last name

**Filter Options:**
- Filter by role
- Filter by active/inactive status

**Bulk Actions:**
- Deactivate selected users ✅ (Recommended)
- Activate selected users
- Delete selected users ⚠️

---

## 🎯 Best Practices

### **For Lost Books:**
1. Always try the `restore_lost_book` command first (easiest)
2. Check who's waiting before restoring
3. Assess book condition honestly
4. If too damaged, order replacement instead

### **For User Management:**
1. **PREFER DEACTIVATE over DELETE**
2. Delete only test accounts or duplicates
3. Always read the warning messages
4. Keep borrowing history for records

### **For Student Accounts:**
- Never delete accounts with active borrowings
- Never delete accounts with unreturned books
- Deactivate instead to preserve records

---

## 📋 Related Commands

```bash
# Restore a lost book
python manage.py restore_lost_book <location>

# Mark books as lost (auto-recovery)
python manage.py mark_lost_books

# Send email reminders
python manage.py send_due_reminders

# Test any command without making changes
python manage.py <command> --dry-run
```

---

## ❓ FAQ

**Q: What if I accidentally deleted a user?**
A: There's no undo. That's why deactivate is recommended. You'll need to manually recreate the account.

**Q: Can I reactivate a deactivated user?**
A: Yes! Select the user → Action → "Activate selected users"

**Q: What happens to a user's borrowed books if I deactivate them?**
A: Nothing changes. Their borrowings stay active. They just can't log in.

**Q: What happens to a user's borrowed books if I DELETE them?**
A: The borrowing records are deleted too, and the books become "orphaned" in the system. **This is bad!**

**Q: Should I delete users who graduated?**
A: No! Deactivate them instead. This preserves the library's borrowing history for future reference.

**Q: A student admitted losing a book. What do I do?**
A: Use `python manage.py mark_lost_books --threshold 0` to immediately mark any overdue book as lost, OR manually change the copy's condition to 'lost' in the admin panel.

**Q: If I restore a lost book, who gets it?**
A: The person who made the OLDEST pending reservation (first-come, first-served).

---

## 🚀 Quick Reference

| Task | Recommended Action | Where |
|------|-------------------|-------|
| Student returns lost book | `restore_lost_book` command | Terminal |
| Student admits losing book | Keep as 'lost', contact student | Admin Panel |
| Remove test account | DELETE | Admin Panel → Users |
| Student graduated | DEACTIVATE | Admin Panel → Users |
| Student misbehaving | DEACTIVATE | Admin Panel → Users |
| Clean up old accounts | DEACTIVATE | Admin Panel → Users |
| Undo a delete | ❌ Not possible | - |
| Undo a deactivate | ✅ Reactivate | Admin Panel → Users |
