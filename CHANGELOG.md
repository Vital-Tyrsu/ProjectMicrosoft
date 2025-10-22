# CHANGELOG

## [2.1.0] - October 11, 2025

### 🎯 Enhancements

#### Added - Location Uniqueness Constraint
- **Feature**: BookCopy locations must now be unique across all copies
- **Rationale**: Physical reality - one shelf location can only hold one book
- **Impact**: Prevents inventory errors, improves data integrity
- **Files**: `library/models.py`
- **Migration**: Required - run `python manage.py makemigrations` then `migrate`
- **Pre-check**: Run `python check_location_duplicates.py` to find existing duplicates

---

## [2.0.1] - October 11, 2025

### 🐛 Bug Fixes

#### Fixed - Availability Counting Accuracy
- **Issue**: Book catalog showed incorrect available copy count when multiple reservations assigned
- **Example**: 2 copies, 2 assigned reservations → showed "1 available" instead of "0 available"
- **Solution**: Replaced complex ORM aggregation with explicit loop-based counting
- **Files**: `library/views.py`
- **Impact**: 100% accurate availability display

---

## [2.0.0] - October 11, 2025

### 🔴 Critical Bug Fixes

#### Fixed - Duplicate Borrowing Creation Race Condition
- **Issue**: When students confirmed pickup, both the view and signal handler would create borrowing records
- **Impact**: Multiple borrowing records for the same book copy
- **Solution**: Removed borrowing creation from `signals.py`, kept only in `views.py`
- **Files**: `library/signals.py`

#### Fixed - Auto-Assignment Timing Bug
- **Issue**: Return date was set AFTER auto-assignment, making books appear unavailable
- **Impact**: Incorrect availability counts, confusing user experience
- **Solution**: Set `return_date` BEFORE performing auto-assignment logic
- **Files**: `library/admin.py`

### ⚠️ Important Improvements

#### Added - Auto-Assignment on Reservation Expiration
- **Feature**: When reservations expire, copies automatically assign to next pending user
- **Impact**: Better resource utilization, faster access to books
- **Implementation**: Enhanced `expire_reservations` management command with FIFO queue
- **Files**: `library/management/commands/expire_reservations.py`

#### Added - Reservation Limit Per User
- **Feature**: Users can only have 3 active reservations at a time
- **Impact**: Prevents hoarding, ensures fair access
- **Implementation**: Added `MAX_ACTIVE_RESERVATIONS = 3` check in create_reservation
- **Files**: `library/views.py`

### 📚 Documentation

#### Added - Comprehensive Fix Documentation
- Created `SYSTEM_FIXES.md` with detailed technical explanations
- Created `FIXES_SUMMARY.md` with quick reference
- Created `test_fixes.py` for automated verification

### 🧪 Testing

#### Added - Automated Verification Script
- `test_fixes.py` checks all fixes are present in code
- Manual test checklist for functional verification
- 4 test scenarios covering all fixes

---

## [1.0.0] - Previous Version

### Features
- ✅ Azure removal for local hosting
- ✅ Superuser default role as admin
- ✅ Complete student interface
- ✅ Self-service pickup confirmation
- ✅ Self-service renewals (max 2)
- ✅ Return request workflow
- ✅ Auto-assignment on return
- ✅ Due date handling (10 days initial)
- ✅ Availability display fixes

### Known Issues (Now Fixed in 2.0.0)
- ❌ Race condition in pickup confirmation
- ❌ Auto-assignment timing issue
- ❌ No auto-assignment on expiration
- ❌ No reservation limit

---

## Migration Notes

### 1.0.0 → 2.0.0
- **Database**: No schema changes, no migrations needed
- **Code**: Logic-only changes
- **Configuration**: New constant `MAX_ACTIVE_RESERVATIONS = 3` (adjustable)
- **Cron Jobs**: Recommended to schedule `expire_reservations` hourly

### Breaking Changes
- None - All changes are backward compatible

### Deprecations
- None

---

## Future Roadmap

### Planned for 2.1.0
- Email notifications for auto-assignments
- SMS alerts for expiring reservations
- Waitlist position visibility
- Enhanced analytics dashboard

### Planned for 3.0.0
- Multi-library support
- Book recommendations
- Reading history tracking
- Digital library integration

---

## Support

For issues or questions about this version:
1. Check `SYSTEM_FIXES.md` for technical details
2. Run `python test_fixes.py` for verification
3. Review console logs for error messages
4. Check Django admin for data state

---

**Version 2.0.0 Status**: ✅ Production Ready
