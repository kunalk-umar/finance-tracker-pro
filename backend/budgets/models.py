from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from transactions.models import Category


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets', null=True, blank=True)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    month = models.IntegerField()  # 1-12
    year = models.IntegerField()
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_overall = models.BooleanField(default=False)  # True = overall monthly budget
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budgets'
        indexes = [
            models.Index(fields=['user', 'month', 'year']),
            models.Index(fields=['user', 'category']),
        ]
        unique_together = [['user', 'category', 'month', 'year']]

    def __str__(self):
        cat = self.category.name if self.category else "Overall"
        return f"{self.user.username}: {cat} budget {self.month}/{self.year}"

    @property
    def remaining(self):
        return self.amount - self.spent

    @property
    def utilization_pct(self):
        if self.amount == 0:
            return 0
        return round((float(self.spent) / float(self.amount)) * 100, 1)

    @property
    def is_exceeded(self):
        return self.spent > self.amount

    @property
    def is_warning(self):
        return self.utilization_pct >= 80


class FinancialGoal(models.Model):
    GOAL_TYPES = [
        ('savings', 'Savings Target'),
        ('debt_payoff', 'Debt Payoff'),
        ('purchase', 'Major Purchase'),
        ('emergency_fund', 'Emergency Fund'),
        ('retirement', 'Retirement'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('achieved', 'Achieved'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES, default='savings')
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'financial_goals'
        indexes = [models.Index(fields=['user', 'status'])]

    def __str__(self):
        return f"{self.user.username}: {self.name}"

    @property
    def progress_pct(self):
        if self.target_amount == 0:
            return 0
        return round((float(self.current_amount) / float(self.target_amount)) * 100, 1)

    @property
    def remaining(self):
        return self.target_amount - self.current_amount

