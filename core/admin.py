from django.contrib import admin
from .models import Customer, Bill, BillItem


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1
    fields = ['description', 'size', 'amount']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'city', 'created_at']
    search_fields = ['name', 'phone_number', 'city']
    list_filter = ['city', 'created_at']
    ordering = ['-created_at']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'customer_name', 'customer_phone', 'customer_city', 'created_at']
    search_fields = ['bill_number', 'customer_name', 'customer_phone']
    list_filter = ['created_at']
    readonly_fields = ['bill_number']
    inlines = [BillItemInline]
    ordering = ['-created_at']
