from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class Category(models.Model):
    CATEGORY_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    ICON_CHOICES = [
        ('fa-utensils', 'Food & Dining'),
        ('fa-car', 'Transportation'),
        ('fa-shopping-cart', 'Shopping'),
        ('fa-bolt', 'Utilities'),
        ('fa-heartbeat', 'Healthcare'),
        ('fa-graduation-cap', 'Education'),
        ('fa-film', 'Entertainment'),
        ('fa-home', 'Housing'),
        ('fa-plane', 'Travel'),
        ('fa-dumbbell', 'Fitness'),
        ('fa-briefcase', 'Work'),
        ('fa-hand-holding-usd', 'Income'),
        ('fa-chart-line', 'Investment'),
        ('fa-piggy-bank', 'Savings'),
        ('fa-ellipsis-h', 'Other'),
    ]

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES)
    icon = models.CharField(max_length=50, default='fa-ellipsis-h')
    color = models.CharField(max_length=7, default='#6c757d')
    is_default = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='custom_categories')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        indexes = [
            models.Index(fields=['category_type']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category_type})"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('wallet', 'Wallet'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    date = models.DateField()
    description = models.CharField(max_length=500)
    merchant = models.CharField(max_length=200, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='other')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='completed')
    # ML-related fields
    ml_category_suggestion = models.CharField(max_length=100, blank=True)
    ml_confidence = models.FloatField(null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)
    anomaly_score = models.FloatField(null=True, blank=True)
    # Metadata
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.transaction_type} {self.amount} on {self.date}"

    @property
    def is_income(self):
        return self.transaction_type == 'income'

    @property
    def is_expense(self):
        return self.transaction_type == 'expense'

