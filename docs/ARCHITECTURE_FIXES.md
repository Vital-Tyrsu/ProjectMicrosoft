# System Architecture - Before & After Fixes

## 🔴 Issue #1: Duplicate Borrowing Creation

### BEFORE (Broken)
```
Student clicks "Confirm Pickup"
    ↓
views.py: confirm_pickup()
    ↓
Creates Borrowing #1 ← First creation
    ↓
Updates reservation.status = 'picked_up'
    ↓
Saves reservation
    ↓
🔥 TRIGGERS SIGNAL 🔥
    ↓
signals.py: handle_reservation_save()
    ↓
Detects status = 'picked_up'
    ↓
Creates Borrowing #2 ← Second creation (DUPLICATE!)
    ↓
❌ RESULT: Two borrowing records for same copy
```

### AFTER (Fixed)
```
Student clicks "Confirm Pickup"
    ↓
views.py: confirm_pickup()
    ↓
Creates Borrowing ← ONLY creation point
    ↓
Updates reservation.status = 'picked_up'
    ↓
Saves reservation
    ↓
Triggers signal
    ↓
signals.py: handle_reservation_save()
    ↓
Logs status change only
    ↓
✅ RESULT: Single borrowing record
```

---

## 🔴 Issue #2: Auto-Assignment Timing

### BEFORE (Broken)
```
Admin clicks "Confirm Return"
    ↓
borrowing.status = 'returned'
    ↓
Auto-assign to pending reservation
    ↓
    [At this point: return_date = NULL]
    ↓
Availability query checks:
    - return_date__isnull=True? YES!
    ↓
❌ Book still shows as "BORROWED"
    ↓
THEN set borrowing.return_date = now()
    ↓
❌ Too late - query already ran
```

### AFTER (Fixed)
```
Admin clicks "Confirm Return"
    ↓
borrowing.return_date = now() ← SET FIRST
borrowing.status = 'returned'
borrowing.save()
    ↓
    [Now: return_date = 2025-10-11]
    ↓
Auto-assign to pending reservation
    ↓
Availability query checks:
    - return_date__isnull=True? NO!
    ↓
✅ Book shows as "AVAILABLE"
    ↓
✅ Correct from the start
```

---

## ⚠️ Issue #3: Expired Reservations

### BEFORE (Inefficient)
```
Cron runs: expire_reservations
    ↓
Find expired reservations
    ↓
FOR EACH expired:
    - status = 'expired'
    - copy = None
    - save()
    ↓
Copy is now FREE
    ↓
❌ But no one gets notified
❌ Book sits idle
❌ User B with pending reservation still waiting
```

### AFTER (Optimized)
```
Cron runs: expire_reservations
    ↓
Find expired reservations
    ↓
FOR EACH expired:
    - Save copy reference
    - status = 'expired'
    - copy = None
    - save()
    ↓
    Find next pending reservation (FIFO)
    ↓
    IF pending exists:
        - Assign copy to them
        - status = 'assigned'
        - expiration_date = now() + 3 days
        - save()
        ↓
        ✅ User B gets the book immediately
        ✅ No idle time
        ✅ Fair queue system
```

---

## ⚠️ Issue #4: Unlimited Reservations

### BEFORE (Exploitable)
```
Student creates reservation
    ↓
Check: Same book already reserved?
    ↓
    NO → Allow
    YES → Block
    ↓
Student can create:
    - Book A (pending)
    - Book B (pending)
    - Book C (pending)
    - Book D (pending)
    - Book E (pending)
    ... unlimited ...
    ↓
❌ Resource hoarding
❌ Unfair to other users
```

### AFTER (Controlled)
```
Student creates reservation
    ↓
Count active reservations
    ↓
    IF count >= 3:
        ❌ Show error message
        ❌ Block creation
    ELSE:
        Check: Same book already reserved?
        ↓
        NO → Allow
        YES → Block
    ↓
Student can have max 3:
    - Book A (pending)
    - Book B (assigned)
    - Book C (pending)
    [LIMIT REACHED]
    ↓
Must cancel one before creating more
    ↓
✅ Fair distribution
✅ No hoarding
```

---

## Flow Diagram: Complete Reservation Lifecycle

```
NEW RESERVATION
    ↓
Check: < 3 active? ─NO→ ❌ Error: Limit reached
    ↓ YES
    ↓
Create (status: pending)
    ↓
Auto-assign if copy available ─YES→ status: assigned
    ↓ NO                              ↓
    ↓                                 expiration: +3 days
Wait in queue                         ↓
    ↓                                 ↓
    ↓                        Student confirms pickup
    ↓                                 ↓
    ↓                        status: picked_up
    ↓                                 ↓
    ↓                        CREATE BORROWING (views.py only)
    ↓                                 ↓
    ↓                        due_date: +10 days
    ↓                                 ↓
    ├─────────────────────────────────┤
    │     BORROWED (Active)           │
    │  - Can renew (max 2x)           │
    │  - Can request return           │
    └─────────────────────────────────┘
                    ↓
            Student requests return
                    ↓
            status: return_pending
                    ↓
            Admin verifies & confirms
                    ↓
            return_date = now() ← SET FIRST
            status = returned
                    ↓
            Find pending reservations
                    ↓
            Auto-assign to next in queue
                    ↓
            ✅ CYCLE COMPLETE

PARALLEL: Expiration Check (Hourly Cron)
    ↓
Find assigned with expiration_date < now
    ↓
FOR EACH:
    - Expire the reservation
    - Auto-assign to next pending
    ↓
✅ No books sit idle
```

---

## Key Improvements Summary

| Issue | Before | After | Impact |
|-------|--------|-------|--------|
| **Duplicate Borrowing** | 2 records created | 1 record created | 50% reduction, no conflicts |
| **Availability** | Delayed update | Immediate update | Real-time accuracy |
| **Expiration** | Manual reassignment | Auto-reassignment | Zero idle time |
| **Hoarding** | Unlimited | 3 max limit | Fair access |

---

## Code Ownership Clarity

| Responsibility | Owner | File |
|---------------|-------|------|
| Borrowing Creation | `confirm_pickup()` | `views.py` |
| Status Logging | `handle_reservation_save()` | `signals.py` |
| Return Processing | `confirm_return()` | `admin.py` |
| Expiration + Reassign | `expire_reservations` | `management/commands/` |
| Limit Enforcement | `create_reservation()` | `views.py` |

---

**Result**: Clean, efficient, race-condition-free system! 🎉
