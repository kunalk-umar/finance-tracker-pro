from django.contrib import admin
from .models import Budget, FinancialGoal

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'category', 'amount', 'spent', 'month', 'year']
    list_filter = ['month', 'year', 'is_overall']

@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'goal_type', 'target_amount', 'current_amount', 'status']
    list_filter = ['goal_type', 'status']
