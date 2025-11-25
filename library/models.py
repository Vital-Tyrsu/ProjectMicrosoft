from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta

class UserManager(BaseUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return super().create_superuser(username, email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=7, choices=ROLE_CHOICES, default='student')
    
    objects = UserManager()

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, null=True, blank=True, unique=True)
    publication_year = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=50, null=True, blank=True)
    isbn = models.CharField(max_length=13, null=True, blank=True, unique=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)

    class Meta:
        db_table = 'books'
        indexes = [
            models.Index(fields=['title'], name='book_title_idx'),  # For search queries
            models.Index(fields=['author'], name='book_author_idx'),  # For search queries
            models.Index(fields=['genre'], name='book_genre_idx'),  # For genre filtering
        ]

    def __str__(self):
        return self.title

    def get_cover_url(self):
        """
        Get book cover URL with fallback priority:
        1. Uploaded image (if exists)
        2. Google Books API (if ISBN exists) - CACHED
        3. Default placeholder gradient
        """
        # Priority 1: Check if we have an uploaded cover
        if self.cover_image:
            return self.cover_image.url
        
        # Priority 2: Try Google Books API if ISBN exists (with caching)
        if self.isbn:
            # Check cache first to avoid repeated API calls
            from django.core.cache import cache
            cache_key = f'book_cover_{self.isbn}'
            cached_url = cache.get(cache_key)
            
            if cached_url:
                return cached_url if cached_url != 'NO_COVER' else None
            
            try:
                import requests
                response = requests.get(
                    f'https://www.googleapis.com/books/v1/volumes?q=isbn:{self.isbn}',
                    timeout=2  # Reduced from 3 to 2 seconds
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('totalItems', 0) > 0:
                        image_links = data['items'][0]['volumeInfo'].get('imageLinks', {})
                        # Try to get the best quality available
                        for quality in ['large', 'medium', 'small', 'thumbnail', 'smallThumbnail']:
                            if quality in image_links:
                                cover_url = image_links[quality]
                                # Cache for 24 hours (86400 seconds)
                                cache.set(cache_key, cover_url, 86400)
                                return cover_url
                
                # No cover found - cache this fact too
                cache.set(cache_key, 'NO_COVER', 86400)
            except:
                # API failed - cache failure for 1 hour to avoid repeated failures
                cache.set(cache_key, 'NO_COVER', 3600)
                pass  # Fail silently and fall back to placeholder
        
        # Priority 3: Return None to use CSS gradient placeholder
        return None

class BookCopy(models.Model):
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('lost', 'Lost'),  # Permanently unavailable
    )
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='good')
    location = models.CharField(
        max_length=50,
        unique=True,  # Each physical location can only hold one book copy
        validators=[RegexValidator(regex=r'^\d+-[A-Z]-\d+$', message='Format must be like "1-A-12"')],
        help_text='Physical shelf location (e.g., 1-A-12). Must be unique across all book copies.'
    )
    lost_date = models.DateTimeField(null=True, blank=True, help_text='Date when book was marked as lost')
    lost_reason = models.TextField(null=True, blank=True, help_text='Reason why book was marked as lost')

    class Meta:
        db_table = 'book_copies'
        indexes = [
            models.Index(fields=['book'], name='bookcopy_book_idx'),  # For finding copies of a book
            models.Index(fields=['condition'], name='bookcopy_condition_idx'),  # For filtering lost books
        ]

    def __str__(self):
        return f"{self.book.title} ({self.location})"
    
    def mark_as_lost(self, reason=None):
        """Mark this copy as permanently lost"""
        self.condition = 'lost'
        self.lost_date = timezone.now()
        self.lost_reason = reason or 'Book not returned after extended overdue period'
        self.save()

class Reservation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    copy = models.ForeignKey(BookCopy, on_delete=models.SET_NULL, null=True, blank=True)
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'reservations'
        indexes = [
            models.Index(fields=['status'], name='reservation_status_idx'),  # For filtering by status
            models.Index(fields=['user', 'status'], name='reservation_user_status_idx'),  # For user's reservations
            models.Index(fields=['expiration_date'], name='reservation_expiry_idx'),  # For expiry checks
            models.Index(fields=['book', 'status'], name='reservation_book_status_idx'),  # For book availability
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"

    def assign_copy(self):
        if self.status == 'pending':
            available_copy = BookCopy.objects.filter(
                book=self.book
            ).exclude(
                condition='lost'  # Never assign lost copies
            ).exclude(
                id__in=Reservation.objects.filter(status='assigned').values('copy_id')  # Only 'assigned', not 'picked_up'
            ).exclude(
                id__in=Borrowing.objects.filter(return_date__isnull=True).values('copy_id')
            ).first()
            if available_copy:
                self.copy = available_copy
                self.status = 'assigned'
                self.expiration_date = timezone.now() + timedelta(days=3)
                self.save()
            else:
                print(f"No available copy for book {self.book.title} for reservation {self.id}")

class Borrowing(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('return_pending', 'Return Pending'),
        ('returned', 'Returned'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    copy = models.ForeignKey(BookCopy, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    return_date = models.DateTimeField(null=True, blank=True)
    renewal_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'borrowings'
        indexes = [
            models.Index(fields=['return_date', 'status'], name='borrowing_return_status_idx'),  # For availability queries
            models.Index(fields=['user', 'return_date'], name='borrowing_user_return_idx'),  # For user's active borrowings
            models.Index(fields=['due_date'], name='borrowing_due_date_idx'),  # For overdue checks
            models.Index(fields=['status'], name='borrowing_status_idx'),  # For filtering by status
        ]

    def __str__(self):
        return f"{self.user.username} - {self.copy.book.title}"
    
    def days_overdue(self):
        """Calculate how many days overdue this borrowing is (returns 0 if not overdue)"""
        if self.return_date is not None:  # Already returned
            return 0
        if self.due_date is None:
            return 0
        
        due = self.due_date.date() if hasattr(self.due_date, 'date') else self.due_date
        today = timezone.now().date()
        
        if today > due:
            return (today - due).days
        return 0
    
    def is_severely_overdue(self, threshold_days=14):
        """Check if book is overdue by more than threshold days (default 14)"""
        return self.days_overdue() >= threshold_days
    
    def can_renew(self):
        """Check if the borrowing can be renewed"""
        if self.renewal_count >= 2:
            return False, "Maximum renewals (2) reached"
        if self.return_date is not None:
            return False, "Book already returned"
        if self.status == 'return_pending':
            return False, "Return is pending"
        # Prevent renewal if overdue by more than 7 days
        if self.days_overdue() > 7:
            return False, f"Book is {self.days_overdue()} days overdue. Cannot renew."
        return True, "Can renew"
    
    def renew(self):
        """Renew the borrowing by 14 days"""
        can_renew, message = self.can_renew()
        if not can_renew:
            return False, message
        
        # Extend due date by 14 days
        if self.due_date:
            self.due_date = self.due_date + timedelta(days=14)
        else:
            self.due_date = timezone.now() + timedelta(days=14)
        
        self.renewal_count += 1
        self.save()
        return True, f"Renewed successfully. New due date: {self.due_date.strftime('%Y-%m-%d')}"

class ReservationLog(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    action_date = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'reservation_logs'

    def __str__(self):
        return f"{self.reservation} - {self.action}"