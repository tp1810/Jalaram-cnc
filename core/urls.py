from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_create, name='customer_create'),
    path('customers/phone-lookup/', views.customer_phone_lookup, name='customer_phone_lookup'),
    path('customers/live-search/', views.live_search_customers, name='live_search_customers'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_update'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customers/<int:pk>/api/', views.customer_api, name='customer_api'),

    # System
    path('system-health/', views.system_health, name='system_health'),
    path('system-health/backup-now/', views.run_backup_now, name='run_backup_now'),

    # Bills
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/create/', views.bill_create, name='bill_create'),
    path('bills/unpaid/', views.unpaid_bills, name='unpaid_bills'),
    path('bills/monthly-revenue/', views.monthly_revenue, name='monthly_revenue'),
    path('bills/live-search/', views.live_search_bills, name='live_search_bills'),
    path('bills/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('bills/<int:pk>/edit/', views.bill_edit, name='bill_edit'),
    path('bills/<int:pk>/delete/', views.bill_delete, name='bill_delete'),
    path('bills/<int:pk>/pdf/', views.bill_pdf, name='bill_pdf'),
]
