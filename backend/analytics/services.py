"""Analytics service functions — calculate all dashboard data from real DB records."""
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncDay
from transactions.models import Transaction, Category
from budgets.models import Budget
import calendar


def get_dashboard_data(user):
    """Return all data needed for the main dashboard."""
    now = date.today()
    
    # Current month
    curr_start = now.replace(day=1)
    curr_end = now.replace(day=calendar.monthrange(now.year, now.month)[1])
    
    # Previous month
    if now.month == 1:
        prev_month, prev_year = 12, now.year - 1
    else:
        prev_month, prev_year = now.month - 1, now.year
    prev_start = date(prev_year, prev_month, 1)
    prev_end = date(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])
    
    # All user transactions
    all_txns = Transaction.objects.filter(user=user)
    curr_txns = all_txns.filter(date__gte=curr_start, date__lte=curr_end)
    prev_txns = all_txns.filter(date__gte=prev_start, date__lte=prev_end)
    
    # KPI calculations
    total_income = all_txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    total_expense = all_txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    balance = total_income - total_expense
    
    curr_income = curr_txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    curr_expense = curr_txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    curr_savings = curr_income - curr_expense
    savings_rate = round((float(curr_savings) / float(curr_income) * 100), 1) if curr_income > 0 else 0.0
    
    prev_income = prev_txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    prev_expense = prev_txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    
    # Budget utilization
    budgets = Budget.objects.filter(user=user, month=now.month, year=now.year)
    total_budget = budgets.aggregate(s=Sum('amount'))['s'] or Decimal('0')
    budget_utilization = round((float(curr_expense) / float(total_budget) * 100), 1) if total_budget > 0 else 0.0
    
    # Monthly income vs expenses (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        d = date.today()
        if d.month - i <= 0:
            m = d.month - i + 12
            y = d.year - 1
        else:
            m = d.month - i
            y = d.year
        inc = all_txns.filter(transaction_type='income', date__month=m, date__year=y).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        exp = all_txns.filter(transaction_type='expense', date__month=m, date__year=y).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        monthly_data.append({
            'month': datetime(y, m, 1).strftime('%b %Y'),
            'income': float(inc),
            'expense': float(exp),
            'savings': float(inc - exp),
        })
    
    # Category breakdown (current month expenses)
    category_data = curr_txns.filter(transaction_type='expense').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount')).order_by('-total')[:10]
    
    # Daily spending (last 30 days)
    thirty_days_ago = now - timedelta(days=29)
    daily_data = all_txns.filter(
        transaction_type='expense', date__gte=thirty_days_ago
    ).annotate(day=TruncDay('date')).values('day').annotate(total=Sum('amount')).order_by('day')
    
    daily_labels = []
    daily_values = []
    day_map = {d['day'].date() if hasattr(d['day'], 'date') else d['day']: float(d['total']) for d in daily_data}
    for i in range(30):
        d = thirty_days_ago + timedelta(days=i)
        daily_labels.append(d.strftime('%d %b'))
        daily_values.append(day_map.get(d, 0.0))
    
    # Top expense category
    top_category = curr_txns.filter(transaction_type='expense').values(
        'category__name'
    ).annotate(total=Sum('amount')).order_by('-total').first()
    
    # Recent transactions
    recent_txns = all_txns.select_related('category').order_by('-date', '-created_at')[:8]
    
    # Anomalies
    anomalies = all_txns.filter(is_anomaly=True).order_by('-date')[:5]
    
    # Budget alerts
    budget_alerts = []
    for b in budgets:
        if b.utilization_pct >= 80:
            budget_alerts.append(b)
    
    # Income change %
    if prev_income > 0:
        income_change = round((float(curr_income - prev_income) / float(prev_income)) * 100, 1)
    else:
        income_change = 0.0
    if prev_expense > 0:
        expense_change = round((float(curr_expense - prev_expense) / float(prev_expense)) * 100, 1)
    else:
        expense_change = 0.0
    
    # Insights
    insights = generate_insights(user, curr_income, curr_expense, prev_income, prev_expense, savings_rate, top_category, budget_alerts)
    
    return {
        'balance': balance,
        'total_income': total_income,
        'total_expense': total_expense,
        'curr_income': curr_income,
        'curr_expense': curr_expense,
        'curr_savings': curr_savings,
        'savings_rate': savings_rate,
        'prev_income': prev_income,
        'prev_expense': prev_expense,
        'income_change': income_change,
        'expense_change': expense_change,
        'budget_utilization': budget_utilization,
        'total_budget': total_budget,
        'monthly_data': monthly_data,
        'category_data': list(category_data),
        'daily_labels': daily_labels,
        'daily_values': daily_values,
        'top_category': top_category,
        'recent_txns': recent_txns,
        'anomalies': anomalies,
        'budget_alerts': budget_alerts,
        'insights': insights,
        'month_name': now.strftime('%B %Y'),
    }


def generate_insights(user, curr_income, curr_expense, prev_income, prev_expense, savings_rate, top_category, budget_alerts):
    insights = []
    
    if curr_income > 0 and savings_rate >= 20:
        insights.append({'type': 'success', 'icon': 'fa-star', 'text': f'Great job! Your savings rate is {savings_rate:.1f}% this month.'})
    elif curr_income > 0 and savings_rate < 10:
        insights.append({'type': 'warning', 'icon': 'fa-exclamation-triangle', 'text': f'Your savings rate is only {savings_rate:.1f}%. Consider reducing expenses.'})
    
    if prev_expense > 0 and curr_expense > 0:
        exp_change = ((float(curr_expense) - float(prev_expense)) / float(prev_expense)) * 100
        if exp_change > 20:
            insights.append({'type': 'danger', 'icon': 'fa-arrow-up', 'text': f'Expenses increased by {exp_change:.1f}% compared to last month.'})
        elif exp_change < -10:
            insights.append({'type': 'success', 'icon': 'fa-arrow-down', 'text': f'Expenses decreased by {abs(exp_change):.1f}% compared to last month. Great control!'})
    
    if top_category:
        insights.append({'type': 'info', 'icon': 'fa-chart-pie', 'text': f'Your highest spending category this month is {top_category["category__name"]}.'})
    
    if budget_alerts:
        for b in budget_alerts[:2]:
            insights.append({'type': 'warning', 'icon': 'fa-bell', 'text': f'Budget alert: {b.name} is at {b.utilization_pct}% utilization.'})
    
    if curr_income > curr_expense:
        insights.append({'type': 'success', 'icon': 'fa-piggy-bank', 'text': f'You saved ₹{curr_income - curr_expense:,.2f} this month.'})
    elif curr_expense > curr_income and curr_income > 0:
        insights.append({'type': 'danger', 'icon': 'fa-exclamation-circle', 'text': 'Warning: Your expenses exceed income this month!'})
    
    return insights


def get_analytics_data(user):
    """Full analytics page data."""
    all_txns = Transaction.objects.filter(user=user)
    
    # 12-month trend
    monthly_trend = []
    now = date.today()
    for i in range(11, -1, -1):
        if now.month - i <= 0:
            m, y = now.month - i + 12, now.year - 1
        else:
            m, y = now.month - i, now.year
        inc = all_txns.filter(transaction_type='income', date__month=m, date__year=y).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        exp = all_txns.filter(transaction_type='expense', date__month=m, date__year=y).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        monthly_trend.append({
            'month': datetime(y, m, 1).strftime('%b %Y'),
            'income': float(inc),
            'expense': float(exp),
            'savings': float(inc - exp),
        })
    
    # Category analysis (all time)
    cat_expense = all_txns.filter(transaction_type='expense').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    
    cat_income = all_txns.filter(transaction_type='income').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    
    # Payment method breakdown
    payment_data = all_txns.filter(transaction_type='expense').values('payment_method').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total')
    
    # Anomalies
    anomalies = all_txns.filter(is_anomaly=True).select_related('category').order_by('-date')
    
    return {
        'monthly_trend': monthly_trend,
        'cat_expense': list(cat_expense),
        'cat_income': list(cat_income),
        'payment_data': list(payment_data),
        'anomalies': anomalies,
    }
