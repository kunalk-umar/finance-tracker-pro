from django.contrib import admin
from .models import Transaction, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'is_default', 'user']
    list_filter = ['category_type', 'is_default']
    search_fields = ['name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'date', 'category', 'description', 'is_anomaly']
    list_filter = ['transaction_type', 'category', 'payment_method', 'is_anomaly']
    search_fields = ['description', 'merchant', 'user__username']
    date_hierarchy = 'date'
    ordering = ['-date']
