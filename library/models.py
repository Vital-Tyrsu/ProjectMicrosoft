from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=7, choices=ROLE_CHOICES, default='student')
    azure_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

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

    class Meta:
        db_table = 'books'

    def __str__(self):
        return self.title

class BookCopy(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    condition = models.CharField(max_length=50)
    location = models.CharField(
        max_length=50,
        validators=[RegexValidator(regex=r'^\d+-[A-Z]-\d+$', message='Format must be like "1-A-12"')]
    )

    class Meta:
        db_table = 'book_copies'

    def __str__(self):
        return f"{self.book.title} ({self.location})"

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

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"

    def assign_copy(self):
        if self.status == 'pending':
            available_copy = BookCopy.objects.filter(
                book=self.book
            ).exclude(
                id__in=Reservation.objects.filter(status__in=['assigned', 'picked_up']).values('copy_id')
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    copy = models.ForeignKey(BookCopy, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(auto_now_add=True)
    return_date = models.DateTimeField(null=True, blank=True)
    renewal_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'borrowings'

    def __str__(self):
        return f"{self.user.username} - {self.copy.book.title}"

class ReservationLog(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    action_date = models.DateTimeField(auto_now_add=True)
    details = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'reservation_logs'

    def __str__(self):
        return f"{self.reservation} - {self.action}"