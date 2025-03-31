from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils import timezone
from datetime import timedelta
import requests
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import User, Book, BookCopy, Reservation, Borrowing, ReservationLog

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'role')
    list_filter = ('role',)
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Role', {'fields': ('role',)}),
    )

    def has_view_permission(self, request, obj=None):
        return request.user.role == 'admin'

    def has_change_permission(self, request, obj=None):
        return request.user.role == 'admin'

    def has_add_permission(self, request):
        return request.user.role == 'admin'

    def has_delete_permission(self, request, obj=None):
        return request.user.role == 'admin'

class BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'publication_year', 'genre', 'isbn')
        export_order = ('id', 'title', 'author', 'publication_year', 'genre', 'isbn')

class BookAdmin(ImportExportModelAdmin):
    resource_class = BookResource
    list_display = ('title', 'author', 'publication_year', 'genre', 'isbn')
    change_list_template = 'admin/library/book/change_list.html'  # Explicitly set the template

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-isbn/', self.admin_site.admin_view(self.import_by_isbn), name='book_import_isbn'),
            path('scan-barcode/', self.admin_site.admin_view(self.scan_barcode), name='book_scan_barcode'),
        ]
        return custom_urls + urls

    def import_by_isbn(self, request):
        if request.method == 'POST':
            isbn = request.POST.get('isbn', '')
            if isbn:
                try:
                    response = requests.get(f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}')
                    response.raise_for_status()
                    data = response.json()
                    if data['totalItems'] > 0:
                        book_data = data['items'][0]['volumeInfo']
                        book = Book.objects.create(
                            title=book_data.get('title', 'Unknown'),
                            author=', '.join(book_data.get('authors', ['Unknown'])),
                            publication_year=book_data.get('publishedDate', '')[:4] if 'publishedDate' in book_data else None,
                            genre=book_data.get('categories', ['Unknown'])[0] if 'categories' in book_data else None,
                            isbn=isbn
                        )
                        self.message_user(request, f"Imported {book.title}")
                    else:
                        self.message_user(request, "No book found for this ISBN", level=messages.ERROR)
                except requests.RequestException as e:
                    self.message_user(request, f"Error fetching ISBN: {e}", level=messages.ERROR)
            else:
                self.message_user(request, "Please provide an ISBN", level=messages.ERROR)
            return redirect('admin:library_book_changelist')

        return render(request, 'admin/library/book/import_isbn.html', {
            'title': 'Import Book by ISBN',
        })

    def scan_barcode(self, request):
        if request.method == 'POST':
            barcode = request.POST.get('barcode', '')
            if barcode:
                try:
                    response = requests.get(f'https://www.googleapis.com/books/v1/volumes?q=isbn:{barcode}')
                    response.raise_for_status()
                    data = response.json()
                    if data['totalItems'] > 0:
                        book_data = data['items'][0]['volumeInfo']
                        book = Book.objects.create(
                            title=book_data.get('title', 'Unknown'),
                            author=', '.join(book_data.get('authors', ['Unknown'])),
                            publication_year=book_data.get('publishedDate', '')[:4] if 'publishedDate' in book_data else None,
                            genre=book_data.get('categories', ['Unknown'])[0] if 'categories' in book_data else None,
                            isbn=barcode
                        )
                        self.message_user(request, f"Imported {book.title} via barcode")
                    else:
                        self.message_user(request, "No book found for this barcode", level=messages.ERROR)
                except requests.RequestException as e:
                    self.message_user(request, f"Error fetching barcode: {e}", level=messages.ERROR)
            else:
                self.message_user(request, "Please provide a barcode", level=messages.ERROR)
            return redirect('admin:library_book_changelist')

        return render(request, 'admin/library/book/scan_barcode.html', {
            'title': 'Scan Book Barcode',
        })

class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'status', 'expiration_date', 'available_copies')
    list_filter = ('status',)
    actions = ['mark_expired', 'mark_picked_up', 'mark_canceled']

    def available_copies(self, obj):
        available = BookCopy.objects.filter(
            book=obj.book
        ).exclude(
            id__in=Reservation.objects.filter(status__in=['assigned', 'picked_up']).values('copy_id')
        ).exclude(
            id__in=Borrowing.objects.filter(return_date__isnull=True).values('copy_id')
        ).count()
        return available

    available_copies.short_description = "Available Copies"

    def mark_expired(self, request, queryset):
        queryset.update(status='expired', copy=None)
        self.message_user(request, "Selected reservations marked as expired")

    def mark_picked_up(self, request, queryset):
        updated_count = 0
        for reservation in queryset:
            if reservation.status == 'assigned':
                reservation.status = 'picked_up'
                reservation.save()
                updated_count += 1
                # Check the latest ReservationLog for this reservation
                latest_log = ReservationLog.objects.filter(reservation=reservation).order_by('-action_date').first()
                if latest_log and latest_log.action == 'borrowing_failed':
                    self.message_user(
                        request,
                        f"Failed to create Borrowing for reservation {reservation.id}: {latest_log.details}",
                        level=messages.WARNING
                    )
                elif latest_log and latest_log.action == 'borrowing_skipped':
                    self.message_user(
                        request,
                        f"Borrowing already exists for reservation {reservation.id}: {latest_log.details}",
                        level=messages.WARNING
                    )
        if updated_count > 0:
            self.message_user(request, f"{updated_count} reservations marked as picked up")
        else:
            self.message_user(request, "No reservations were updated (must be in 'assigned' status)", level=messages.WARNING)

    def mark_canceled(self, request, queryset):
        queryset.update(status='canceled', copy=None)
        self.message_user(request, "Selected reservations marked as canceled")

    mark_expired.short_description = "Mark as expired"
    mark_picked_up.short_description = "Mark as picked up"
    mark_canceled.short_description = "Mark as canceled"

class BorrowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'copy', 'borrow_date', 'return_date', 'renewal_count')
    list_filter = ('return_date',)
    actions = ['mark_returned', 'renew_borrowing']

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user', 'copy')
        print(f"BorrowingAdmin queryset: {qs}")
        return qs

    def mark_returned(self, request, queryset):
        updated_count = queryset.filter(return_date__isnull=True).update(return_date=timezone.now())
        if updated_count > 0:
            self.message_user(request, f"Marked {updated_count} borrowings as returned")
        else:
            self.message_user(request, "No active borrowings were updated", level=messages.WARNING)

    def renew_borrowing(self, request, queryset):
        renewed_count = 0
        for borrowing in queryset:
            # Check if the borrowing is still active (not returned)
            if borrowing.return_date and borrowing.return_date < timezone.now():
                self.message_user(
                    request,
                    f"Cannot renew borrowing for {borrowing.user.username}: Book was due on {borrowing.return_date}",
                    level=messages.WARNING
                )
                continue
            if borrowing.return_date is None:
                self.message_user(
                    request,
                    f"Cannot renew borrowing for {borrowing.user.username}: Return date not set",
                    level=messages.WARNING
                )
                continue
            # Check renewal limit
            if borrowing.renewal_count < 2:
                borrowing.renewal_count += 1
                # Extend the return_date by 14 days from the current return_date
                borrowing.return_date = borrowing.return_date + timedelta(days=14)
                borrowing.save()
                self.message_user(
                    request,
                    f"Renewed borrowing for {borrowing.user.username}. New return date: {borrowing.return_date}",
                    level=messages.SUCCESS
                )
                renewed_count += 1
            else:
                self.message_user(
                    request,
                    f"Cannot renew borrowing for {borrowing.user.username}: Max renewals (2) reached",
                    level=messages.WARNING
                )
        if renewed_count == 0 and not queryset.exists():
            self.message_user(request, "No borrowings were renewed", level=messages.WARNING)

    mark_returned.short_description = "Mark as returned"
    renew_borrowing.short_description = "Renew borrowing"

admin.site.register(User, CustomUserAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(BookCopy)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Borrowing, BorrowingAdmin)
admin.site.register(ReservationLog)