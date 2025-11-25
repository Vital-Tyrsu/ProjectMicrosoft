from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Case, When, IntegerField, Exists, OuterRef
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from datetime import timedelta
import json
import csv
import io
from .models import Book, BookCopy, Reservation, Borrowing, User
from .email_utils import send_reservation_confirmation, send_reservation_assigned, send_pickup_confirmation, send_return_confirmation

def student_login(request):
    """Login page for students and admins with role detection"""
    if request.user.is_authenticated:
        # Redirect based on role
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('book_catalog')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect based on role
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('book_catalog')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'library/login.html')

def student_logout(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('student_login')

@login_required(login_url='student_login')
def book_catalog(request):
    """Display all books with search and filter functionality + pagination"""
    # Calculate user stats for dashboard
    user = request.user
    active_borrowings = Borrowing.objects.filter(
        user=user,
        return_date__isnull=True  # Any unreturned book
    ).count()
    
    overdue_borrowings = Borrowing.objects.filter(
        user=user,
        return_date__isnull=True,
        due_date__lt=timezone.now()
    ).count()
    
    pending_reservations = Reservation.objects.filter(
        user=user,
        status='pending'
    ).count()
    
    assigned_reservations = Reservation.objects.filter(
        user=user,
        status='assigned'
    ).count()
    
    books = Book.objects.all().order_by('title')  # Add ordering for consistent pagination
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author__icontains=search_query) |
            Q(isbn__icontains=search_query)
        )
    
    # Genre filter
    genre_filter = request.GET.get('genre', '')
    if genre_filter:
        books = books.filter(genre=genre_filter)
    
    # Get all unique genres for filter dropdown (cached for 1 hour)
    from django.core.cache import cache
    genres = cache.get('book_genres_list')
    if not genres:
        genres = list(Book.objects.exclude(genre__isnull=True).exclude(genre='').values_list('genre', flat=True).distinct())
        cache.set('book_genres_list', genres, 3600)  # Cache for 1 hour
    
    # Pagination FIRST - only process 12 books
    page = request.GET.get('page', 1)
    paginator = Paginator(books, 12)
    
    try:
        books_page = paginator.page(page)
    except PageNotAnInteger:
        books_page = paginator.page(1)
    except EmptyPage:
        books_page = paginator.page(paginator.num_pages)
    
    # OPTIMIZED: Calculate availability using annotations (1 query instead of N+1)
    # Get the book IDs for current page
    book_ids = [book.id for book in books_page]
    
    # Annotate books with counts in a single query
    books_with_counts = Book.objects.filter(id__in=book_ids).annotate(
        total_copies=Count('bookcopy', filter=~Q(bookcopy__condition='lost'), distinct=True),  # Exclude lost copies
        unavailable_copies_count=Count(
            'bookcopy',
            filter=Q(
                Q(bookcopy__borrowing__return_date__isnull=True, bookcopy__borrowing__status='active') |
                Q(bookcopy__reservation__status='assigned')
            ) & ~Q(bookcopy__condition='lost'),  # Exclude lost copies
            distinct=True
        )
    )
    
    # Create a lookup dictionary for O(1) access
    availability_lookup = {
        book.id: {
            'total_copies': book.total_copies,
            'unavailable_count': book.unavailable_copies_count,
            'available_copies': book.total_copies - book.unavailable_copies_count
        }
        for book in books_with_counts
    }
    
    # Apply the availability data to the paginated books
    books_with_availability = []
    for book in books_page:
        if book.id in availability_lookup:
            book.total_copies = availability_lookup[book.id]['total_copies']
            book.unavailable_count = availability_lookup[book.id]['unavailable_count']
            book.available_copies = availability_lookup[book.id]['available_copies']
        else:
            # Fallback for edge cases
            book.total_copies = 0
            book.unavailable_count = 0
            book.available_copies = 0
        books_with_availability.append(book)
    
    context = {
        'books': books_page,
        'search_query': search_query,
        'genres': genres,
        'genre_filter': genre_filter,
        'total_books': paginator.count,
        'has_next': books_page.has_next(),
        'has_previous': books_page.has_previous(),
        'current_page': books_page.number,
        'total_pages': paginator.num_pages,
        # User stats for dashboard
        'active_borrowings': active_borrowings,
        'overdue_borrowings': overdue_borrowings,
        'pending_reservations': pending_reservations,
        'assigned_reservations': assigned_reservations,
    }
    return render(request, 'library/book_catalog.html', context)

@login_required(login_url='student_login')
def create_reservation(request, book_id):
    """Create a reservation for a book"""
    book = get_object_or_404(Book, id=book_id)
    
    # Configuration: Maximum active reservations per user
    MAX_ACTIVE_RESERVATIONS = 3
    
    # Check total active reservations for this user
    active_reservation_count = Reservation.objects.filter(
        user=request.user,
        status__in=['pending', 'assigned']
    ).count()
    
    if active_reservation_count >= MAX_ACTIVE_RESERVATIONS:
        messages.error(
            request,
            f'You already have {active_reservation_count} active reservations. '
            f'Please cancel or complete one before creating a new reservation (limit: {MAX_ACTIVE_RESERVATIONS}).'
        )
        return redirect('book_catalog')
    
    # Check if user already has an active reservation for this book
    existing_reservation = Reservation.objects.filter(
        user=request.user,
        book=book,
        status__in=['pending', 'assigned']
    ).first()
    
    if existing_reservation:
        messages.warning(request, f'You already have an active reservation for "{book.title}".')
        return redirect('book_catalog')
    
    # Check if user currently has this book borrowed
    existing_borrowing = Borrowing.objects.filter(
        user=request.user,
        copy__book=book,
        return_date__isnull=True
    ).first()
    
    if existing_borrowing:
        messages.warning(request, f'You currently have a copy of "{book.title}" borrowed.')
        return redirect('book_catalog')
    
    # Create the reservation
    reservation = Reservation.objects.create(
        user=request.user,
        book=book,
        status='pending'
    )
    
    # Try to assign a copy immediately
    reservation.assign_copy()
    
    if reservation.status == 'assigned':
        # Book was available - send ONLY assignment email (no need for confirmation)
        if reservation.copy:
            send_reservation_assigned(request.user, reservation, reservation.copy)
        messages.success(request, f'Great news! A copy is available and has been assigned to you. Please pick it up by {reservation.expiration_date.strftime("%Y-%m-%d %H:%M")}. Check your email for details.')
    else:
        # No copies available - on waitlist, send confirmation email
        send_reservation_confirmation(request.user, reservation)
        messages.success(request, f'Reservation created for "{book.title}". All copies are currently borrowed. You\'ve been added to the waitlist and will be notified by email when a copy becomes available.')
    
    return redirect('my_reservations')

@login_required(login_url='student_login')
def my_reservations(request):
    """Display user's reservations"""
    reservations = Reservation.objects.filter(user=request.user).order_by('-reservation_date')
    
    context = {
        'reservations': reservations,
    }
    return render(request, 'library/my_reservations.html', context)

@login_required(login_url='student_login')
def confirm_pickup(request, reservation_id):
    """Student confirms they have picked up the book"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    # Only allow confirmation if status is 'assigned'
    if reservation.status != 'assigned':
        messages.error(request, 'This reservation is not ready for pickup confirmation.')
        return redirect('my_reservations')
    
    # Check if a copy is assigned
    if not reservation.copy:
        messages.error(request, 'No copy has been assigned to this reservation yet.')
        return redirect('my_reservations')
    
    # Check if borrowing already exists (prevent duplicate)
    existing_borrowing = Borrowing.objects.filter(
        user=request.user,
        copy=reservation.copy,
        return_date__isnull=True
    ).first()
    
    if existing_borrowing:
        messages.warning(request, 'You already have an active borrowing for this book.')
        reservation.status = 'picked_up'
        reservation.save()
        return redirect('my_borrowings')
    
    # Create the borrowing record
    try:
        borrowing = Borrowing.objects.create(
            user=request.user,
            copy=reservation.copy,
            due_date=timezone.now() + timedelta(days=10)  # Set due date to 10 days from now
        )
        
        # Update reservation status
        reservation.status = 'picked_up'
        reservation.save()
        
        # Send pickup confirmation email
        send_pickup_confirmation(request.user, borrowing)
        
        # Log the action for audit trail
        from .models import ReservationLog
        ReservationLog.objects.create(
            reservation=reservation,
            action='self_pickup_confirmed',
            details=f'Student self-confirmed pickup. Borrowing ID: {borrowing.id}'
        )
        
        messages.success(request, f'Pickup confirmed! You have successfully borrowed "{reservation.book.title}". Due date: {borrowing.due_date.strftime("%Y-%m-%d")}. Check your email for details.')
        return redirect('my_borrowings')
        
    except Exception as e:
        messages.error(request, f'Error creating borrowing record: {str(e)}')
        return redirect('my_reservations')

@login_required(login_url='student_login')
def cancel_reservation(request, reservation_id):
    """Cancel a reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    if reservation.status in ['pending', 'assigned']:
        reservation.status = 'canceled'
        reservation.copy = None
        reservation.save()
        messages.success(request, f'Reservation for "{reservation.book.title}" has been canceled.')
    else:
        messages.error(request, 'This reservation cannot be canceled.')
    
    return redirect('my_reservations')

@login_required(login_url='student_login')
def my_borrowings(request):
    """Display user's current and past borrowings"""
    active_borrowings = Borrowing.objects.filter(
        user=request.user,
        return_date__isnull=True
    ).select_related('copy__book').order_by('-borrow_date')
    
    past_borrowings = Borrowing.objects.filter(
        user=request.user,
        return_date__isnull=False
    ).select_related('copy__book').order_by('-return_date')
    
    context = {
        'active_borrowings': active_borrowings,
        'past_borrowings': past_borrowings,
    }
    return render(request, 'library/my_borrowings.html', context)

@login_required(login_url='student_login')
def renew_borrowing(request, borrowing_id):
    """Student renews their own borrowing"""
    borrowing = get_object_or_404(Borrowing, id=borrowing_id, user=request.user)
    
    # Check if can renew
    can_renew, message = borrowing.can_renew()
    
    if can_renew:
        success, result_message = borrowing.renew()
        if success:
            messages.success(request, f'✓ Book renewed! {result_message}. You now have {borrowing.renewal_count}/2 renewals used.')
        else:
            messages.error(request, result_message)
    else:
        messages.error(request, f'Cannot renew: {message}')
    
    return redirect('my_borrowings')

@login_required(login_url='student_login')
def request_return(request, borrowing_id):
    """Student requests to return a book"""
    borrowing = get_object_or_404(Borrowing, id=borrowing_id, user=request.user)
    
    # Check if already returned or pending
    if borrowing.return_date is not None:
        messages.error(request, 'This book has already been returned.')
        return redirect('my_borrowings')
    
    if borrowing.status == 'return_pending':
        messages.warning(request, 'Return request already submitted. Waiting for admin verification.')
        return redirect('my_borrowings')
    
    # Update status to return_pending
    borrowing.status = 'return_pending'
    borrowing.save()
    
    # Log the action
    from .models import ReservationLog
    # Note: We could create a BorrowingLog model, but for now we'll use success message
    
    messages.success(request, 
        f'✓ Return request submitted for "{borrowing.copy.book.title}"! '
        f'Please return the book to the library. An admin will verify and confirm your return.'
    )
    
    return redirect('my_borrowings')


# ===================================
# ADMIN DASHBOARD VIEWS
# ===================================

@login_required(login_url='student_login')
def admin_dashboard(request):
    """Admin dashboard with comprehensive stats and overview"""
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access the admin dashboard.')
        return redirect('book_catalog')
    
    # Import cache at top of function (it's already used elsewhere in the file)
    from django.core.cache import cache
    
    # Try to get cached statistics (cache for 5 minutes = 300 seconds)
    cache_key = 'admin_dashboard_stats'
    stats = cache.get(cache_key)
    
    if not stats:
        # Calculate statistics (only if not cached)
        stats = {
            'total_books': Book.objects.count(),
            'total_copies': BookCopy.objects.count(),
            'total_users': User.objects.filter(is_staff=False).count(),
            'active_borrowings': Borrowing.objects.filter(
                return_date__isnull=True,
                status='active'
            ).count(),
            'overdue_borrowings': Borrowing.objects.filter(
                return_date__isnull=True,
                status='active',
                due_date__lt=timezone.now()
            ).count(),
            'pending_reservations': Reservation.objects.filter(
                status='pending'
            ).count(),
            'assigned_reservations': Reservation.objects.filter(
                status='assigned'
            ).count(),
            'lost_books': BookCopy.objects.filter(condition='lost').count(),
        }
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)
    
    # Extract stats from cache/calculated
    total_books = stats['total_books']
    total_copies = stats['total_copies']
    total_users = stats['total_users']
    active_borrowings = stats['active_borrowings']
    overdue_borrowings = stats['overdue_borrowings']
    pending_reservations = stats['pending_reservations']
    assigned_reservations = stats['assigned_reservations']
    lost_books = stats['lost_books']
    
    # Recent activity (last 10 actions)
    recent_reservations = Reservation.objects.select_related(
        'user', 'book', 'copy'
    ).order_by('-reservation_date')[:5]
    
    recent_borrowings = Borrowing.objects.select_related(
        'user', 'copy__book'
    ).order_by('-borrow_date')[:5]
    
    # Books running low on copies (less than 2 available)
    low_stock_books = []
    for book in Book.objects.all():
        total_copies_count = BookCopy.objects.filter(book=book).count()
        unavailable_count = BookCopy.objects.filter(book=book).filter(
            Q(borrowing__return_date__isnull=True, borrowing__status='active') |
            Q(reservation__status__in=['assigned', 'picked_up'])
        ).distinct().count()
        available = total_copies_count - unavailable_count
        
        if available < 2 and total_copies_count > 0:
            low_stock_books.append({
                'book': book,
                'available': available,
                'total': total_copies_count
            })
    
    context = {
        'total_books': total_books,
        'total_copies': total_copies,
        'total_users': total_users,
        'active_borrowings': active_borrowings,
        'overdue_borrowings': overdue_borrowings,
        'pending_reservations': pending_reservations,
        'assigned_reservations': assigned_reservations,
        'lost_books': lost_books,
        'recent_reservations': recent_reservations,
        'recent_borrowings': recent_borrowings,
        'low_stock_books': low_stock_books[:5],  # Top 5 low stock
    }
    
    return render(request, 'library/admin_dashboard.html', context)


@login_required(login_url='student_login')
def admin_reservations(request):
    """Admin view to manage all reservations with filtering and bulk actions"""
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('book_catalog')
    
    # Handle bulk actions
    if request.method == 'POST':
        action = request.POST.get('action')
        reservation_ids = request.POST.getlist('reservation_ids')
        
        if action and reservation_ids:
            reservations = Reservation.objects.filter(id__in=reservation_ids)
            
            if action == 'mark_picked_up':
                # Mark as picked up and create borrowing records
                count = 0
                for reservation in reservations:
                    if reservation.status == 'assigned' and reservation.copy:
                        # Create borrowing record
                        Borrowing.objects.create(
                            user=reservation.user,
                            copy=reservation.copy,
                            borrow_date=timezone.now(),
                            due_date=timezone.now() + timedelta(days=14)
                        )
                        reservation.status = 'picked_up'
                        reservation.save()
                        count += 1
                
                messages.success(request, f'✓ Successfully processed {count} pickup(s)')
            
            elif action == 'assign_copy':
                # Manually assign copies to pending reservations
                count = 0
                for reservation in reservations:
                    if reservation.status == 'pending':
                        # Find an available copy
                        available_copy = BookCopy.objects.filter(
                            book=reservation.book
                        ).exclude(
                            id__in=Reservation.objects.filter(status='assigned').values('copy_id')  # Only 'assigned', not 'picked_up'
                        ).exclude(
                            id__in=Borrowing.objects.filter(return_date__isnull=True).values('copy_id')
                        ).first()
                        
                        if available_copy:
                            reservation.copy = available_copy
                            reservation.status = 'assigned'
                            reservation.expiration_date = timezone.now() + timedelta(days=3)
                            reservation.save()
                            count += 1
                            
                            # Send assignment email to user
                            send_reservation_assigned(reservation.user, reservation, available_copy)
                
                if count > 0:
                    messages.success(request, f'✓ Successfully assigned {count} reservation(s) and sent notification emails')
                else:
                    messages.warning(request, 'No available copies found for selected reservations')
            
            elif action == 'cancel':
                # Cancel selected reservations
                count = reservations.filter(status__in=['pending', 'assigned']).count()
                reservations.filter(status__in=['pending', 'assigned']).update(status='canceled')
                messages.success(request, f'✓ Canceled {count} reservation(s)')
            
            return redirect('admin_reservations')
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    user_filter = request.GET.get('user', '')  # Filter by specific user
    
    # Base queryset
    reservations = Reservation.objects.select_related(
        'user', 'book', 'copy'
    ).order_by('-reservation_date')
    
    # Apply user filter (from clicked stat card)
    if user_filter:
        reservations = reservations.filter(user_id=user_filter)
    
    # Apply status filter
    if status_filter != 'all':
        reservations = reservations.filter(status=status_filter)
    
    # Apply search filter
    if search_query:
        reservations = reservations.filter(
            Q(book__title__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(reservations, 20)
    page = request.GET.get('page', 1)
    
    try:
        reservations_page = paginator.page(page)
    except PageNotAnInteger:
        reservations_page = paginator.page(1)
    except EmptyPage:
        reservations_page = paginator.page(paginator.num_pages)
    
    context = {
        'reservations': reservations_page,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': reservations.count(),
    }
    
    return render(request, 'library/admin_reservations.html', context)


@login_required(login_url='student_login')
def admin_borrowings(request):
    """Admin view to manage all borrowings with filtering and actions"""
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('book_catalog')
    
    # Handle actions
    if request.method == 'POST':
        action = request.POST.get('action')
        borrowing_id = request.POST.get('borrowing_id')
        
        if action and borrowing_id:
            borrowing = get_object_or_404(Borrowing, id=borrowing_id)
            
            if action == 'process_return':
                # Single-step: Mark as returned AND shelve (auto-assign to waitlist)
                borrowing.return_date = timezone.now()
                borrowing.status = 'returned'
                borrowing.save()
                
                # Send return confirmation email to the user who returned the book
                send_return_confirmation(borrowing.user, borrowing)
                
                # Immediately check if there are pending reservations for this book
                next_reservation = Reservation.objects.filter(
                    book=borrowing.copy.book,
                    status='pending'
                ).order_by('reservation_date').first()
                
                if next_reservation:
                    # Auto-assign to next person in waitlist
                    next_reservation.copy = borrowing.copy
                    next_reservation.status = 'assigned'
                    next_reservation.expiration_date = timezone.now() + timedelta(days=3)
                    next_reservation.save()
                    
                    # Send assignment email to next person
                    send_reservation_assigned(next_reservation.user, next_reservation, borrowing.copy)
                    
                    messages.success(request, f'✓ Book returned and assigned to {next_reservation.user.username} at {borrowing.copy.location}. Pickup expires in 3 days. Notification emails sent.')
                else:
                    messages.success(request, f'✓ Book returned and shelved at {borrowing.copy.location}. Available for new reservations. Confirmation email sent to {borrowing.user.email}.')
            
            elif action == 'extend_due_date':
                borrowing.due_date = borrowing.due_date + timedelta(days=7)
                borrowing.save()
                messages.success(request, f'✓ Due date extended to {borrowing.due_date.strftime("%B %d, %Y")}')
            
            return redirect('admin_borrowings')
    
    # Get filter parameters
    filter_type = request.GET.get('filter', 'active_all')
    search_query = request.GET.get('search', '')
    user_filter = request.GET.get('user', '')  # Filter by specific user
    status_filter = request.GET.get('status', '')  # Direct status filter
    overdue_filter = request.GET.get('overdue', '')  # Overdue filter
    
    # Base queryset
    borrowings = Borrowing.objects.select_related(
        'user', 'copy__book'
    ).order_by('-borrow_date')
    
    # Apply user filter (from clicked stat card)
    if user_filter:
        borrowings = borrowings.filter(user_id=user_filter)
    
    # Apply status filter (from clicked stat card)
    if status_filter == 'active':
        borrowings = borrowings.filter(return_date__isnull=True, status='active')
    
    # Apply overdue filter (from clicked stat card)
    if overdue_filter == 'true':
        borrowings = borrowings.filter(
            return_date__isnull=True,
            status='active',
            due_date__lt=timezone.now()
        )
    
    # Apply filter type (from dropdown)
    if filter_type == 'active_all':
        # Show all unreturned books (both active and return_pending)
        if not status_filter and not overdue_filter:  # Don't override stat card filters
            borrowings = borrowings.filter(return_date__isnull=True)
    elif filter_type == 'active':
        borrowings = borrowings.filter(return_date__isnull=True, status='active')
    elif filter_type == 'return_pending':
        borrowings = borrowings.filter(return_date__isnull=True, status='return_pending')
    elif filter_type == 'overdue':
        borrowings = borrowings.filter(
            return_date__isnull=True,
            status='active',
            due_date__lt=timezone.now()
        )
    elif filter_type == 'returned':
        borrowings = borrowings.filter(status='returned')
    
    # Apply search filter
    if search_query:
        borrowings = borrowings.filter(
            Q(copy__book__title__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(borrowings, 20)
    page = request.GET.get('page', 1)
    
    try:
        borrowings_page = paginator.page(page)
    except PageNotAnInteger:
        borrowings_page = paginator.page(1)
    except EmptyPage:
        borrowings_page = paginator.page(paginator.num_pages)
    
    context = {
        'borrowings': borrowings_page,
        'filter_type': filter_type,
        'search_query': search_query,
        'total_count': borrowings.count(),
        'now': timezone.now(),
    }
    
    return render(request, 'library/admin_borrowings.html', context)


@login_required(login_url='student_login')
def admin_users(request):
    """Admin view: Display all users with search and filter"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('book_catalog')
    
    # Get all users
    users_list = User.objects.all().order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Filter by role
    role_filter = request.GET.get('role', '')
    if role_filter == 'admin':
        users_list = users_list.filter(is_staff=True)
    elif role_filter == 'student':
        users_list = users_list.filter(is_staff=False)
    
    # Annotate with stats (use distinct=True to avoid duplicate counts)
    users_list = users_list.annotate(
        active_borrowings_count=Count('borrowing', filter=Q(borrowing__status='active'), distinct=True),
        pending_reservations_count=Count('reservation', filter=Q(reservation__status__in=['pending', 'assigned']), distinct=True)
    )
    
    # Pagination
    paginator = Paginator(users_list, 20)  # 20 users per page
    page = request.GET.get('page', 1)
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
        'total_users': User.objects.count(),
        'total_students': User.objects.filter(is_staff=False).count(),
        'total_admins': User.objects.filter(is_staff=True).count(),
    }
    
    return render(request, 'library/admin_users.html', context)


@login_required(login_url='student_login')
def admin_user_detail(request, user_id):
    """Admin view: Display detailed information about a specific user"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('book_catalog')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get user's borrowings
    borrowings = Borrowing.objects.filter(user=user).select_related(
        'copy__book'
    ).order_by('-borrow_date')
    
    # Get user's reservations
    reservations = Reservation.objects.filter(user=user).select_related(
        'book', 'copy'
    ).order_by('-reservation_date')
    
    # Calculate stats
    total_borrowings = borrowings.count()
    active_borrowings = borrowings.filter(status='active').count()
    overdue_borrowings = borrowings.filter(
        status='active',
        due_date__lt=timezone.now()
    ).count()
    
    total_reservations = reservations.count()
    pending_reservations = reservations.filter(status='pending').count()
    assigned_reservations = reservations.filter(status='assigned').count()
    
    context = {
        'viewed_user': user,
        'borrowings': borrowings[:10],  # Show last 10
        'reservations': reservations[:10],  # Show last 10
        'total_borrowings': total_borrowings,
        'active_borrowings': active_borrowings,
        'overdue_borrowings': overdue_borrowings,
        'total_reservations': total_reservations,
        'pending_reservations': pending_reservations,
        'assigned_reservations': assigned_reservations,
    }
    
    return render(request, 'library/admin_user_detail.html', context)


@require_http_methods(["POST"])
def admin_change_user_role(request, user_id):
    """Admin action: Change a user's role"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('book_catalog')
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent changing your own role
    if user.id == request.user.id:
        messages.error(request, 'You cannot change your own role.')
        return redirect('admin_user_detail', user_id=user_id)
    
    new_role = request.POST.get('role')
    
    # Validate role
    valid_roles = ['student', 'teacher', 'admin']
    if new_role not in valid_roles:
        messages.error(request, 'Invalid role selected.')
        return redirect('admin_user_detail', user_id=user_id)
    
    # Update role
    old_role = user.role
    user.role = new_role
    
    # Update staff status based on role
    if new_role == 'admin':
        user.is_staff = True
    elif new_role == 'teacher':
        user.is_staff = True  # Teachers have staff access
    else:  # student
        user.is_staff = False
        user.is_superuser = False
    
    user.save()
    
    # Role display names
    role_names = {'student': 'Student', 'teacher': 'Teacher', 'admin': 'Admin'}
    messages.success(
        request, 
        f'✅ {user.username}\'s role changed from {role_names[old_role]} to {role_names[new_role]}.'
    )
    
    return redirect('admin_user_detail', user_id=user_id)


@require_http_methods(["POST"])
def admin_delete_user(request, user_id):
    """Admin action: Delete or deactivate a user with safety checks"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('book_catalog')
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent self-deletion
    if user.id == request.user.id:
        messages.error(request, '❌ You cannot delete your own account.')
        return redirect('admin_user_detail', user_id=user_id)
    
    # Check for active borrowings
    active_borrowings = Borrowing.objects.filter(
        user=user,
        return_date__isnull=True
    ).count()
    
    # Check for pending/assigned reservations
    active_reservations = Reservation.objects.filter(
        user=user,
        status__in=['pending', 'assigned']
    ).count()
    
    action = request.POST.get('action', 'deactivate')
    
    if action == 'delete' and (active_borrowings > 0 or active_reservations > 0):
        messages.error(
            request,
            f'❌ Cannot delete {user.username}: User has {active_borrowings} active borrowing(s) '
            f'and {active_reservations} active reservation(s). Please resolve these first or deactivate the account instead.'
        )
        return redirect('admin_user_detail', user_id=user_id)
    
    if action == 'delete':
        # Permanent deletion (only if no active items)
        username = user.username
        user.delete()
        messages.success(
            request,
            f'✅ User "{username}" has been permanently deleted from the system.'
        )
        return redirect('admin_users')
    else:
        # Deactivate (safe, preserves history)
        user.is_active = False
        user.save()
        messages.success(
            request,
            f'✅ User "{user.username}" has been deactivated. They can no longer log in, '
            f'but their borrowing/reservation history is preserved.'
        )
        return redirect('admin_user_detail', user_id=user_id)


# ===================================
# DATA MANAGEMENT VIEWS
# ===================================

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_data_management(request):
    """Data Management Center - Landing page"""
    # Calculate statistics
    total_books = Book.objects.count()
    total_copies = BookCopy.objects.count()
    books_with_copies = Book.objects.annotate(
        copy_count=Count('bookcopy')
    ).filter(copy_count__gt=0).count()
    books_without_copies = total_books - books_with_copies
    
    context = {
        'total_books': total_books,
        'total_copies': total_copies,
        'books_with_copies': books_with_copies,
        'books_without_copies': books_without_copies,
    }
    
    return render(request, 'library/admin_data_management.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_import_csv(request):
    """CSV Import - Upload and process CSV file"""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return render(request, 'library/admin_import_csv.html')
        
        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File must be a CSV file.')
            return render(request, 'library/admin_import_csv.html')
        
        # Validate file size (5MB max)
        if csv_file.size > 5 * 1024 * 1024:
            messages.error(request, 'File size must be under 5MB.')
            return render(request, 'library/admin_import_csv.html')
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            books_created = 0
            books_updated = 0
            errors = []
            
            for row_num, row in enumerate(csv_data, start=2):  # Start at 2 (header is row 1)
                try:
                    title = row.get('title', '').strip()
                    author = row.get('author', '').strip()
                    isbn = row.get('isbn', '').strip()
                    genre = row.get('genre', '').strip()
                    publication_year = row.get('publication_year', '').strip()
                    publisher = row.get('publisher', '').strip()
                    description = row.get('description', '').strip()
                    
                    # Validate required fields
                    if not title or not author:
                        errors.append(f'Row {row_num}: Title and author are required')
                        continue
                    
                    # Convert year to integer if provided
                    year = None
                    if publication_year:
                        try:
                            year = int(publication_year)
                        except ValueError:
                            errors.append(f'Row {row_num}: Invalid year "{publication_year}"')
                    
                    # Check if book exists (by ISBN or title+author)
                    book = None
                    if isbn:
                        book = Book.objects.filter(isbn=isbn).first()
                    
                    if not book:
                        book = Book.objects.filter(title=title, author=author).first()
                    
                    if book:
                        # Update existing book
                        if isbn and not book.isbn:
                            book.isbn = isbn
                        if genre:
                            book.genre = genre
                        if year:
                            book.publication_year = year
                        if publisher:
                            book.publisher = publisher
                        if description:
                            book.description = description
                        book.save()
                        books_updated += 1
                    else:
                        # Create new book
                        Book.objects.create(
                            title=title,
                            author=author,
                            isbn=isbn or '',
                            genre=genre or '',
                            publication_year=year
                        )
                        books_created += 1
                
                except Exception as e:
                    errors.append(f'Row {row_num}: {str(e)}')
            
            # Show results
            if books_created > 0:
                messages.success(request, f'✅ Successfully imported {books_created} new books.')
            if books_updated > 0:
                messages.info(request, f'ℹ️ Updated {books_updated} existing books.')
            if errors:
                error_msg = f'⚠️ {len(errors)} errors occurred:\n' + '\n'.join(errors[:5])
                if len(errors) > 5:
                    error_msg += f'\n... and {len(errors) - 5} more'
                messages.warning(request, error_msg)
            
            return redirect('admin_data_management')
        
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return render(request, 'library/admin_import_csv.html')
    
    return render(request, 'library/admin_import_csv.html')


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_download_sample_csv(request):
    """Generate and download sample CSV file"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="library_books_sample.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['title', 'author', 'isbn', 'genre', 'publication_year', 'publisher', 'description'])
    writer.writerow([
        'Harry Potter and the Philosopher\'s Stone',
        'J.K. Rowling',
        '9780590353427',
        'Fantasy',
        '1997',
        'Scholastic',
        'A young wizard discovers his magical heritage on his eleventh birthday.'
    ])
    writer.writerow([
        'The Hobbit',
        'J.R.R. Tolkien',
        '9780547928227',
        'Fantasy',
        '1937',
        'Houghton Mifflin',
        'A hobbit reluctantly joins a quest to reclaim a dwarven treasure.'
    ])
    writer.writerow([
        '1984',
        'George Orwell',
        '9780451524935',
        'Science Fiction',
        '1949',
        'Signet Classic',
        'A dystopian social science fiction novel and cautionary tale.'
    ])
    
    return response


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_add_book_manual(request):
    """Manual Book Add - Form submission"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip()
        isbn = request.POST.get('isbn', '').strip()
        genre = request.POST.get('genre', '').strip()
        publication_year = request.POST.get('publication_year', '').strip()
        publisher = request.POST.get('publisher', '').strip()
        description = request.POST.get('description', '').strip()
        cover_image = request.FILES.get('cover_image')
        
        # Validate required fields
        if not title or not author:
            messages.error(request, 'Title and author are required.')
            return render(request, 'library/admin_add_book_manual.html')
        
        # Convert year to integer if provided
        year = None
        if publication_year:
            try:
                year = int(publication_year)
                if year < 1000 or year > 2100:
                    messages.error(request, 'Publication year must be between 1000 and 2100.')
                    return render(request, 'library/admin_add_book_manual.html')
            except ValueError:
                messages.error(request, 'Invalid publication year.')
                return render(request, 'library/admin_add_book_manual.html')
        
        # Validate ISBN if provided
        if isbn and not isbn.isdigit():
            messages.error(request, 'ISBN must contain only digits.')
            return render(request, 'library/admin_add_book_manual.html')
        
        if isbn and len(isbn) not in [10, 13]:
            messages.error(request, 'ISBN must be 10 or 13 digits.')
            return render(request, 'library/admin_add_book_manual.html')
        
        # Validate image if provided
        if cover_image:
            if cover_image.size > 2 * 1024 * 1024:  # 2MB
                messages.error(request, 'Image size must be under 2MB.')
                return render(request, 'library/admin_add_book_manual.html')
        
        try:
            # Check for duplicates
            if isbn and Book.objects.filter(isbn=isbn).exists():
                messages.warning(request, f'A book with ISBN {isbn} already exists.')
                return render(request, 'library/admin_add_book_manual.html')
            
            # Create book
            book = Book.objects.create(
                title=title,
                author=author,
                isbn=isbn or '',
                genre=genre or '',
                publication_year=year,
                cover_image=cover_image
            )
            
            messages.success(request, f'✅ Successfully added "{book.title}" by {book.author}.')
            return redirect('admin_data_management')
        
        except Exception as e:
            messages.error(request, f'Error adding book: {str(e)}')
            return render(request, 'library/admin_add_book_manual.html')
    
    return render(request, 'library/admin_add_book_manual.html')


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_add_book_isbn(request):
    """ISBN Lookup - Fetch book data and create"""
    if request.method == 'POST':
        book_data_json = request.POST.get('book_data')
        
        if not book_data_json:
            messages.error(request, 'No book data provided.')
            return redirect('admin_add_book_isbn')
        
        try:
            book_data = json.loads(book_data_json)
            
            title = book_data.get('title', '').strip()
            author = book_data.get('author', '').strip()
            isbn = book_data.get('isbn', '').strip()
            genre = book_data.get('genre', '').strip()
            publication_year = book_data.get('publication_year')
            publisher = book_data.get('publisher', '').strip()
            description = book_data.get('description', '').strip()
            cover_url = book_data.get('cover_url', '').strip()
            
            # Validate required fields
            if not title or not author:
                messages.error(request, 'Title and author are required.')
                return redirect('admin_add_book_isbn')
            
            # Check for duplicates
            if isbn and Book.objects.filter(isbn=isbn).exists():
                messages.warning(request, f'A book with ISBN {isbn} already exists.')
                return redirect('admin_add_book_isbn')
            
            # Download cover image if URL provided
            cover_image = None
            if cover_url:
                try:
                    import requests
                    from django.core.files.base import ContentFile
                    
                    response = requests.get(cover_url, timeout=10)
                    if response.status_code == 200:
                        # Generate filename from ISBN or title
                        filename = f"{isbn or title[:30].replace(' ', '_')}.jpg"
                        cover_image = ContentFile(response.content, name=filename)
                except Exception as e:
                    print(f"Error downloading cover: {e}")
            
            # Create book
            book = Book.objects.create(
                title=title,
                author=author,
                isbn=isbn or '',
                genre=genre or '',
                publication_year=publication_year if publication_year else None,
                cover_image=cover_image
            )
            
            messages.success(request, f'✅ Successfully added "{book.title}" by {book.author} from ISBN lookup.')
            return redirect('admin_data_management')
        
        except json.JSONDecodeError:
            messages.error(request, 'Invalid book data format.')
            return redirect('admin_add_book_isbn')
        except Exception as e:
            messages.error(request, f'Error adding book: {str(e)}')
            return redirect('admin_add_book_isbn')
    
    return render(request, 'library/admin_add_book_isbn.html')


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_scan_book(request):
    """Barcode Scanner - Interface for scanning"""
    return render(request, 'library/admin_scan_book.html')


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def admin_manage_copies(request):
    """Manage Copies - Add, edit, delete copies"""
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        copy_count = request.POST.get('copy_count')
        location_prefix = request.POST.get('location_prefix', '').strip()
        
        if not book_id or not copy_count:
            messages.error(request, 'Invalid request.')
            return redirect('admin_manage_copies')
        
        try:
            book = Book.objects.get(id=book_id)
            count = int(copy_count)
            
            if count < 1 or count > 50:
                messages.error(request, 'Please enter a valid number of copies (1-50).')
                return redirect('admin_manage_copies')
            
            # Generate location prefix if not provided
            # Format: SHELF-SECTION-NUMBER (e.g., 1-A-12)
            if not location_prefix:
                # Default to "1-A" (Shelf 1, Section A)
                location_prefix = "1-A"
            
            # Validate location prefix format (should be DIGIT-LETTER like "1-A")
            import re
            if not re.match(r'^\d+-[A-Z]$', location_prefix):
                # Try to fix common formats or use default
                location_prefix = "1-A"
            
            # Find the highest existing number for this location prefix (across ALL books)
            # since location must be unique globally
            existing_locations = BookCopy.objects.filter(
                location__startswith=f"{location_prefix}-"
            ).values_list('location', flat=True)
            
            # Extract numbers from existing locations
            existing_numbers = []
            for loc in existing_locations:
                try:
                    # Extract the number after the last dash
                    num = int(loc.split('-')[-1])
                    existing_numbers.append(num)
                except (ValueError, IndexError):
                    continue
            
            # Start from the highest number + 1, or 1 if no existing locations
            start_num = max(existing_numbers) + 1 if existing_numbers else 1
            
            # Create copies
            copies_created = []
            for i in range(count):
                copy_num = start_num + i
                location = f"{location_prefix}-{copy_num}"
                
                # Double-check location doesn't exist (safety check)
                if BookCopy.objects.filter(location=location).exists():
                    # Skip to next number if somehow it exists
                    continue
                
                # Create the copy without 'status' field
                copy = BookCopy.objects.create(
                    book=book,
                    location=location,
                    condition='Good'  # Default condition
                )
                copies_created.append(location)
            
            copy_word = "copy" if count == 1 else "copies"
            ellipsis = "..." if len(copies_created) > 5 else ""
            messages.success(
                request,
                f'✅ Successfully added {count} {copy_word} '
                f'of "{book.title}". Locations: {", ".join(copies_created[:5])}{ellipsis}'
            )
            
            return redirect('admin_manage_copies')
        
        except Book.DoesNotExist:
            messages.error(request, 'Book not found.')
            return redirect('admin_manage_copies')
        except ValueError:
            messages.error(request, 'Invalid number of copies.')
            return redirect('admin_manage_copies')
        except Exception as e:
            messages.error(request, f'Error adding copies: {str(e)}')
            return redirect('admin_manage_copies')
    
    # GET request - show all books
    books = Book.objects.all().prefetch_related('bookcopy_set').order_by('title')
    
    context = {
        'books': books
    }
    
    return render(request, 'library/admin_manage_copies.html', context)


@user_passes_test(lambda u: u.role == 'admin')
def admin_edit_book(request):
    """Edit book details (title, author, genre, year)"""
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        title = request.POST.get('title', '').strip()
        author = request.POST.get('author', '').strip()
        genre = request.POST.get('genre', '').strip()
        publication_year = request.POST.get('publication_year', '').strip()
        
        if not book_id or not title or not author:
            messages.error(request, 'Title and author are required.')
            return redirect('admin_manage_copies')
        
        try:
            book = Book.objects.get(id=book_id)
            
            # Update book fields
            book.title = title
            book.author = author
            book.genre = genre if genre else None
            
            # Handle publication year
            if publication_year:
                try:
                    year = int(publication_year)
                    if 1000 <= year <= 2100:
                        book.publication_year = year
                    else:
                        messages.warning(request, 'Invalid publication year. Book updated without year change.')
                except ValueError:
                    messages.warning(request, 'Invalid publication year format. Book updated without year change.')
            else:
                book.publication_year = None
            
            book.save()
            
            messages.success(
                request,
                f'✅ Successfully updated "{book.title}"'
            )
            
            return redirect('admin_manage_copies')
        
        except Book.DoesNotExist:
            messages.error(request, 'Book not found.')
            return redirect('admin_manage_copies')
        except Exception as e:
            messages.error(request, f'Error updating book: {str(e)}')
            return redirect('admin_manage_copies')
    
    return redirect('admin_manage_copies')


# ===================================
# CUSTOM ERROR HANDLERS
# ===================================

def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, '404.html', status=404)


def custom_500(request):
    """Custom 500 error page"""
    return render(request, '500.html', status=500)
