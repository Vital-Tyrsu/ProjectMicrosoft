from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_login, name='student_login'),
    path('login/', views.student_login, name='student_login'),
    path('logout/', views.student_logout, name='student_logout'),
    path('catalog/', views.book_catalog, name='book_catalog'),
    path('reserve/<int:book_id>/', views.create_reservation, name='create_reservation'),
    path('reservations/', views.my_reservations, name='my_reservations'),
    path('reservations/cancel/<int:reservation_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('reservations/confirm-pickup/<int:reservation_id>/', views.confirm_pickup, name='confirm_pickup'),
    path('borrowings/', views.my_borrowings, name='my_borrowings'),
    path('borrowings/renew/<int:borrowing_id>/', views.renew_borrowing, name='renew_borrowing'),
    path('borrowings/request-return/<int:borrowing_id>/', views.request_return, name='request_return'),
    
    # Admin routes
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/reservations/', views.admin_reservations, name='admin_reservations'),
    path('admin-dashboard/borrowings/', views.admin_borrowings, name='admin_borrowings'),
    path('admin-dashboard/users/', views.admin_users, name='admin_users'),
    path('admin-dashboard/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin-dashboard/users/<int:user_id>/change-role/', views.admin_change_user_role, name='admin_change_user_role'),
    path('admin-dashboard/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    
    # Data Management routes
    path('admin-dashboard/data-management/', views.admin_data_management, name='admin_data_management'),
    path('admin-dashboard/import-csv/', views.admin_import_csv, name='admin_import_csv'),
    path('admin-dashboard/download-sample-csv/', views.admin_download_sample_csv, name='admin_download_sample_csv'),
    path('admin-dashboard/add-book/', views.admin_add_book_manual, name='admin_add_book_manual'),
    path('admin-dashboard/add-book-isbn/', views.admin_add_book_isbn, name='admin_add_book_isbn'),
    path('admin-dashboard/scan-book/', views.admin_scan_book, name='admin_scan_book'),
    path('admin-dashboard/manage-copies/', views.admin_manage_copies, name='admin_manage_copies'),
    path('admin-dashboard/edit-book/', views.admin_edit_book, name='admin_edit_book'),
]
