# 🔄 Renewals & Returns Feature Guide

## ✅ Features Implemented: Self-Service Renewals + Return Requests (Option A)

Students can now:
1. **Renew their own books** (max 2 renewals, +14 days each)
2. **Request returns** (initiate the process, admin verifies)

## 🚀 How It Works

---

### 📚 **RENEWALS** (Self-Service)

#### Student Experience:
1. Go to "My Borrowings"
2. See renewal count: **0/2**, **1/2**, or **2/2**
3. Click **"🔄 Renew"** button
4. Book extended by **14 days** instantly!
5. Renewal count updates: **1/2** → **2/2**

#### Rules:
- ✅ Max **2 renewals** per book
- ✅ Extends **due date by 14 days**
- ✅ Instant confirmation
- ✅ Cannot renew if:
  - Already returned
  - Return is pending
  - Max renewals reached (2/2)

#### Example Flow:
```
Borrow book → Due: Oct 24
         ↓
Renew (1st) → Due: Nov 7 (Renewals: 1/2)
         ↓
Renew (2nd) → Due: Nov 21 (Renewals: 2/2)
         ↓
Cannot renew anymore (max reached)
```

---

### 📤 **RETURNS** (Request + Admin Verification)

#### Student Experience:
1. **Physically return** the book to the library
2. Go to "My Borrowings"
3. Click **"📤 Request Return"** button
4. Status changes to **"Return Pending"**
5. Wait for admin to verify the physical book
6. Admin confirms → Book marked as returned!

#### Admin Experience:
1. Go to **Admin Panel** → **Borrowings**
2. Filter by status: **"Return Pending"**
3. **Physically verify** the book is on the shelf
4. Select the borrowing(s)
5. Choose action: **"✓ Confirm pending returns"**
6. System marks as **returned** with timestamp

#### Why This System?
- 🔒 **Secure**: Admin verifies physical book
- 🚀 **Convenient**: Student initiates process
- 📊 **Trackable**: Clear audit trail
- 🛡️ **Prevents disputes**: Timestamps everything
- ⚖️ **Balanced**: Trust + verification

---

## 📋 Changes Made

### 1. **Updated Borrowing Model** (`models.py`)

**New Fields:**
- `status` - Tracks: 'active', 'return_pending', 'returned'
- `due_date` - When the book is due (set on renewal)

**New Methods:**
- `can_renew()` - Checks if renewal is allowed
- `renew()` - Extends due date by 14 days

### 2. **New Student Views** (`views.py`)

**`renew_borrowing()`**
- Student renews their own book
- Validates renewal count (max 2)
- Updates due date (+14 days)
- Shows success message

**`request_return()`**
- Student requests return
- Changes status to 'return_pending'
- Shows instructions to return physical book

### 3. **Updated Admin Panel** (`admin.py`)

**New Admin Actions:**
- **"Confirm pending returns"** - Verify and process returns
- **"Mark as returned (direct)"** - Direct return (admin-initiated)
- Enhanced renewal action

**List Display Updates:**
- Shows `due_date`
- Shows `status` (Active, Return Pending, Returned)
- Filter by status

### 4. **Updated URLs** (`urls.py`)

**New Routes:**
- `/borrowings/renew/<id>/` - Renew book
- `/borrowings/request-return/<id>/` - Request return

### 5. **Updated Template** (`my_borrowings.html`)

**New Columns:**
- Due Date
- Renewals (0/2, 1/2, 2/2 with color coding)
- Status (Active/Return Pending)
- Actions column

**New Buttons:**
- **🔄 Renew** (disabled if 2/2)
- **📤 Request Return** (changes to waiting message when pending)

**Visual Features:**
- Green renewal count if < 2
- Red renewal count if = 2
- Grayed out renew button when maxed
- Status badges
- Helpful info box

---

## 🎯 Testing Guide

### Test Renewals:

1. **Login as test1**
2. **Borrow a book** (or use existing borrowing)
3. **Go to "My Borrowings"**
4. **See renewal count: 0/2**
5. **Click "Renew"**
   - Confirm dialog appears
   - Due date extends by 14 days
   - Count becomes 1/2
6. **Click "Renew" again**
   - Count becomes 2/2
   - Button grays out
7. **Try to click again**
   - Button disabled (max reached)

### Test Return Requests:

1. **Login as test1**
2. **Have an active borrowing**
3. **Click "📤 Request Return"**
   - Confirm dialog appears
   - Status changes to "Return Pending"
   - Buttons disappear, shows waiting message
4. **Logout and login as admin**
5. **Go to Admin Panel → Borrowings**
6. **Filter by "Return Pending"**
7. **Select the borrowing**
8. **Choose "✓ Confirm pending returns"**
9. **Verify success message**
10. **Login back as test1**
11. **Check "My Borrowings" → Past Borrowings**
12. **Book appears as returned!**

---

## 📊 Database Schema Changes

### Borrowing Model:

```python
class Borrowing(models.Model):
    user = ForeignKey(User)
    copy = ForeignKey(BookCopy)
    borrow_date = DateTimeField()
    due_date = DateTimeField()         # NEW
    return_date = DateTimeField()
    renewal_count = IntegerField()
    status = CharField()                # NEW
    # Choices: 'active', 'return_pending', 'returned'
```

### Migration Required:

You need to run migrations to add the new fields:

```powershell
python manage.py makemigrations
python manage.py migrate
```

**Note:** The migration will add:
- `status` field (default: 'active')
- `due_date` field (nullable)

---

## 🔒 Security Features

### Renewals:
✅ Students can only renew their own books
✅ Max 2 renewals enforced
✅ Cannot renew returned books
✅ Cannot renew pending returns
✅ Login required

### Returns:
✅ Students can only request their own returns
✅ Admin must physically verify book
✅ Two-step process prevents fraud
✅ Status tracking prevents duplicates
✅ Audit trail in database
✅ Login required for both student and admin

---

## 🎨 User Interface

### My Borrowings Page:

```
┌─────────────────────────────────────────────────────────────┐
│ 📚 My Borrowings                                            │
├─────────────────────────────────────────────────────────────┤
│ 🔵 Currently Borrowed                                       │
├──────────┬────────┬────────┬──────────┬──────────┬─────────┤
│ Book     │ Due    │ Renew  │ Status   │ Actions             │
├──────────┼────────┼────────┼──────────┼─────────────────────┤
│ Title 1  │ Oct 24 │ 0/2 🟢 │ Active   │ [🔄 Renew] [📤 Req] │
│ Title 2  │ Nov 7  │ 1/2 🟢 │ Active   │ [🔄 Renew] [📤 Req] │
│ Title 3  │ Nov 21 │ 2/2 🔴 │ Active   │ [Renew] [📤 Req]    │
│ Title 4  │ Oct 20 │ 0/2    │ Pending  │ ⏳ Waiting for admin │
└──────────┴────────┴────────┴──────────┴─────────────────────┘

ℹ️ How it works:
• Renew: Extend your borrowing by 14 days (max 2 renewals per book)
• Request Return: Click this AFTER you return the book to the library.
  An admin will verify and confirm.
```

---

## 🔄 Admin Panel Views

### Borrowing List:

**Filters:**
- Status (Active / Return Pending / Returned)
- Return Date

**Actions:**
1. **✓ Confirm pending returns** - Process student return requests
2. **Mark as returned (direct)** - Admin-initiated returns
3. **Renew borrowing** - Admin can renew for students

**Workflow:**
```
Student Request → Status: Return Pending → Admin Verifies → Status: Returned
```

---

## 🚀 Benefits

### For Students:
✅ **Instant renewals** - No waiting for admin
✅ **Clear visibility** - See renewal count
✅ **Convenient returns** - Initiate anytime
✅ **No disputes** - Timestamp tracked
✅ **Better UX** - Self-service autonomy

### For Admins:
✅ **Less workload** - Auto-renewals
✅ **Better tracking** - Status system
✅ **Physical verification** - Still secure
✅ **Audit trail** - All actions logged
✅ **Flexible** - Can still do direct returns

### For Library:
✅ **Reduced admin time** - Automation
✅ **Better records** - Status tracking
✅ **Fraud prevention** - Two-step returns
✅ **Happy students** - Convenience
✅ **Scalable** - Handles 700 students easily

---

## 🔮 Future Enhancements (If Needed)

### If You See Fraud/Abuse:

#### Option: Add QR Code Returns
```
Student returns book →
Scans QR code →
System verifies book ID →
Auto-confirms return
```

**Benefits:**
- 100% automated
- Physical verification via QR
- No admin needed
- Instant processing

**Implementation Time:** ~30 minutes
**When to use:** If you see students requesting returns without actually returning books

---

## ⚙️ Configuration Options

### Customizable Values in Code:

**Renewal Extension:**
- Current: 14 days
- Location: `models.py` → `Borrowing.renew()` → `timedelta(days=14)`

**Max Renewals:**
- Current: 2
- Location: `models.py` → `Borrowing.can_renew()` → `if self.renewal_count >= 2`

**Default Status:**
- Current: 'active'
- Location: `models.py` → `status = models.CharField(default='active')`

---

## 📝 Summary

| Feature | Type | Security | Convenience |
|---------|------|----------|-------------|
| **Renewals** | Self-service | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Returns** | Request + Verify | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Overall:** ⭐⭐⭐⭐⭐ Perfect balance of security and convenience!

---

## ✅ Ready to Use!

### Next Steps:

1. **Run migrations:**
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Start server:**
   ```powershell
   python manage.py runserver
   ```

3. **Test as student:**
   - Login as test1
   - Go to "My Borrowings"
   - Try renewing and requesting returns!

4. **Test as admin:**
   - Go to admin panel
   - Check "Borrowings" with status filter
   - Process pending returns!

---

**🎉 Features complete and ready to rock!**

Trust your students with renewals, verify their returns, and upgrade to QR later if needed. Smart, practical, and scalable! 💪📚
