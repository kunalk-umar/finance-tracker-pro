from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from .models import Budget, FinancialGoal
from .forms import BudgetForm, FinancialGoalForm
from transactions.models import Transaction, Category


def get_budget_spent(budget):
    """Calculate actual spending for a budget period."""
    qs = Transaction.objects.filter(
        user=budget.user,
        transaction_type='expense',
        date__month=budget.month,
        date__year=budget.year,
    )
    if budget.category and not budget.is_overall:
        qs = qs.filter(category=budget.category)
    result = qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    return result


@login_required
def budget_list(request):
    now = datetime.now()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))
    
    budgets = Budget.objects.filter(user=request.user, month=month, year=year)
    
    # Update spent amounts
    for budget in budgets:
        budget.spent = get_budget_spent(budget)
        budget.save(update_fields=['spent'])
    
    # Calculate totals
    total_budget = budgets.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    total_spent_sum = sum(b.spent for b in budgets)
    
    # Get expenses by category for this month
    category_spending = Transaction.objects.filter(
        user=request.user, transaction_type='expense',
        date__month=month, date__year=year
    ).values('category__name', 'category__color').annotate(total=Sum('amount')).order_by('-total')
    
    goals = FinancialGoal.objects.filter(user=request.user, status='active')
    
    months = [(i, datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    years = list(range(2020, now.year + 2))
    
    return render(request, 'budgets/budget_list.html', {
        'budgets': budgets,
        'goals': goals,
        'total_budget': total_budget,
        'total_spent': total_spent_sum,
        'category_spending': category_spending,
        'month': month,
        'year': year,
        'months': months,
        'years': years,
        'month_name': datetime(year, month, 1).strftime('%B'),
    })


@login_required
def budget_create(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.spent = get_budget_spent(budget)
            budget.save()
            messages.success(request, f'Budget "{budget.name}" created successfully!')
            return redirect('budget_list')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = BudgetForm(user=request.user)
    return render(request, 'budgets/budget_form.html', {'form': form, 'title': 'Add Budget', 'action': 'Create'})


@login_required
def budget_edit(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.spent = get_budget_spent(budget)
            budget.save()
            messages.success(request, 'Budget updated successfully!')
            return redirect('budget_list')
    else:
        form = BudgetForm(instance=budget, user=request.user)
    return render(request, 'budgets/budget_form.html', {'form': form, 'budget': budget, 'title': 'Edit Budget', 'action': 'Update'})


@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted.')
        return redirect('budget_list')
    return render(request, 'budgets/budget_confirm_delete.html', {'budget': budget})


@login_required
def goal_create(request):
    if request.method == 'POST':
        form = FinancialGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Goal "{goal.name}" created!')
            return redirect('budget_list')
    else:
        form = FinancialGoalForm()
    return render(request, 'budgets/goal_form.html', {'form': form, 'title': 'Add Goal', 'action': 'Create'})


@login_required
def goal_edit(request, pk):
    goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = FinancialGoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goal updated!')
            return redirect('budget_list')
    else:
        form = FinancialGoalForm(instance=goal)
    return render(request, 'budgets/goal_form.html', {'form': form, 'goal': goal, 'title': 'Edit Goal', 'action': 'Update'})


@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(FinancialGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Goal deleted.')
        return redirect('budget_list')
    return render(request, 'budgets/budget_confirm_delete.html', {'object': goal, 'type': 'goal'})
