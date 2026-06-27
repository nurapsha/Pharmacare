from django.contrib import admin
from .models import Medicine, Customer, Supplier, Sale, SaleItem, Category, StockLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email']
    search_fields = ['name', 'contact_person']


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturer', 'price', 'quantity', 'expiry_date', 'is_low_stock']
    list_filter = ['category', 'manufacturer', 'supplier']
    search_fields = ['name', 'generic_name', 'manufacturer']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email']
    search_fields = ['name', 'phone']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'sale_date', 'total_amount']
    inlines = [SaleItemInline]
    readonly_fields = ['invoice_number']


@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ['medicine', 'action', 'quantity_change', 'quantity_after', 'timestamp']
    readonly_fields = ['timestamp']
