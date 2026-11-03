import json
from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from .services import get_dashboard_data, get_analytics_data
from .models import MLModel, PredictionLog
import requests as req


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@login_required
def dashboard(request):
    data = get_dashboard_data(request.user)
    
    # Serialize chart data to JSON
    monthly_json = json.dumps(data['monthly_data'], cls=DecimalEncoder)
    cat_json = json.dumps([{
        'name': c.get('category__name') or 'Uncategorized',
        'total': float(c['total']),
        'color': c.get('category__color') or '#6c757d',
    } for c in data['category_data']], cls=DecimalEncoder)
    daily_json = json.dumps({'labels': data['daily_labels'], 'values': data['daily_values']})
    
    return render(request, 'analytics/dashboard.html', {
        **data,
        'monthly_json': monthly_json,
        'cat_json': cat_json,
        'daily_json': daily_json,
    })


@login_required
def analytics_page(request):
    data = get_analytics_data(request.user)
    
    monthly_json = json.dumps(data['monthly_trend'], cls=DecimalEncoder)
    cat_expense_json = json.dumps([{
        'name': c.get('category__name') or 'Uncategorized',
        'total': float(c['total']),
        'count': c['count'],
        'color': c.get('category__color') or '#6c757d',
    } for c in data['cat_expense']], cls=DecimalEncoder)
    cat_income_json = json.dumps([{
        'name': c.get('category__name') or 'Uncategorized',
        'total': float(c['total']),
        'count': c['count'],
        'color': c.get('category__color') or '#6c757d',
    } for c in data['cat_income']], cls=DecimalEncoder)
    payment_json = json.dumps([{
        'method': p['payment_method'],
        'total': float(p['total']),
        'count': p['count'],
    } for p in data['payment_data']], cls=DecimalEncoder)
    
    return render(request, 'analytics/analytics.html', {
        **data,
        'monthly_json': monthly_json,
        'cat_expense_json': cat_expense_json,
        'cat_income_json': cat_income_json,
        'payment_json': payment_json,
    })


@login_required
def ml_predictions(request):
    """ML Predictions page — categorization, forecasting, anomaly detection."""
    from transactions.models import Transaction
    
    # Recent predictions
    recent_preds = PredictionLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Anomalies
    anomalies = Transaction.objects.filter(user=request.user, is_anomaly=True).select_related('category').order_by('-date')[:20]
    
    # ML model info
    models_info = MLModel.objects.filter(is_active=True)
    
    # Forecast data
    forecast_data = None
    try:
        resp = req.get(f"{settings.ML_SERVICE_URL}/health", timeout=2)
        ml_service_up = resp.status_code == 200
    except Exception:
        ml_service_up = False
    
    return render(request, 'analytics/ml_predictions.html', {
        'recent_preds': recent_preds,
        'anomalies': anomalies,
        'models_info': models_info,
        'ml_service_up': ml_service_up,
    })


@login_required
def run_anomaly_detection(request):
    """Trigger anomaly detection on user transactions via ML service."""
    from transactions.models import Transaction
    import json
    
    transactions = Transaction.objects.filter(user=request.user, transaction_type='expense').values(
        'id', 'amount', 'date', 'description', 'merchant'
    )
    txn_list = []
    for t in transactions:
        txn_list.append({
            'id': str(t['id']),
            'amount': float(t['amount']),
            'date': str(t['date']),
            'description': t['description'],
            'merchant': t['merchant'],
        })
    
    try:
        resp = req.post(f"{settings.ML_SERVICE_URL}/detect-anomalies",
                       json={'transactions': txn_list}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            anomaly_ids = data.get('anomaly_ids', [])
            scores = data.get('scores', {})
            
            # Update transactions
            Transaction.objects.filter(user=request.user).update(is_anomaly=False, anomaly_score=None)
            for aid in anomaly_ids:
                Transaction.objects.filter(id=aid, user=request.user).update(
                    is_anomaly=True,
                    anomaly_score=scores.get(str(aid), -1)
                )
            
            from django.contrib import messages
            messages.success(request, f'Anomaly detection complete. Found {len(anomaly_ids)} unusual transactions.')
        else:
            from django.contrib import messages
            messages.error(request, 'ML service returned an error.')
    except Exception as e:
        from django.contrib import messages
        messages.warning(request, f'ML service unavailable. Running local anomaly detection.')
        # Fallback: flag transactions that are more than 2 std devs above mean
        import numpy as np
        amounts = [float(t['amount']) for t in txn_list]
        if len(amounts) >= 10:
            mean = np.mean(amounts)
            std = np.std(amounts)
            threshold = mean + 2 * std
            anomaly_ids = [txn_list[i]['id'] for i, a in enumerate(amounts) if a > threshold]
            Transaction.objects.filter(user=request.user).update(is_anomaly=False)
            for aid in anomaly_ids:
                Transaction.objects.filter(id=aid, user=request.user).update(is_anomaly=True)
            from django.contrib import messages as msg2
            msg2.success(request, f'Local anomaly detection found {len(anomaly_ids)} unusual transactions.')
    
    return redirect('ml_predictions')


@login_required
def predict_category_ajax(request):
    """AJAX endpoint for ML category prediction."""
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        description = data.get('description', '')
        merchant = data.get('merchant', '')
        
        try:
            resp = req.post(f"{settings.ML_SERVICE_URL}/predict-category",
                           json={'description': description, 'merchant': merchant},
                           timeout=3)
            if resp.status_code == 200:
                result = resp.json()
                PredictionLog.objects.create(
                    user=request.user,
                    input_data=json.dumps({'description': description, 'merchant': merchant}),
                    prediction=result.get('category', ''),
                    confidence=result.get('confidence', 0),
                )
                return JsonResponse(result)
        except Exception:
            pass
        
        # Fallback rule-based
        category = rule_based_category(description, merchant)
        return JsonResponse({'category': category, 'confidence': 0.6, 'source': 'rules'})
    return JsonResponse({'error': 'POST required'}, status=400)


def rule_based_category(description, merchant):
    """Simple rule-based fallback categorization."""
    text = f"{description} {merchant}".lower()
    rules = [
        (['swiggy', 'zomato', 'food', 'restaurant', 'cafe', 'pizza', 'burger', 'dhaba', 'hotel', 'dining'], 'Food & Dining'),
        (['uber', 'ola', 'taxi', 'petrol', 'fuel', 'metro', 'bus', 'auto', 'rapido', 'transport'], 'Transportation'),
        (['amazon', 'flipkart', 'myntra', 'shopping', 'mall', 'store', 'market', 'buy', 'purchase'], 'Shopping'),
        (['electricity', 'water', 'gas', 'internet', 'wifi', 'broadband', 'utility', 'bill', 'recharge'], 'Utilities'),
        (['hospital', 'doctor', 'medicine', 'pharmacy', 'health', 'medical', 'clinic', 'apollo', 'max'], 'Healthcare'),
        (['school', 'college', 'course', 'tuition', 'education', 'book', 'udemy', 'coursera'], 'Education'),
        (['netflix', 'spotify', 'prime', 'movie', 'cinema', 'game', 'entertainment', 'hotstar'], 'Entertainment'),
        (['rent', 'maintenance', 'housing', 'flat', 'apartment', 'society'], 'Housing'),
        (['flight', 'hotel', 'travel', 'vacation', 'trip', 'makemytrip', 'booking'], 'Travel'),
        (['gym', 'fitness', 'yoga', 'sports', 'cult.fit'], 'Fitness'),
        (['salary', 'income', 'freelance', 'bonus', 'dividend'], 'Income'),
    ]
    for keywords, category in rules:
        if any(k in text for k in keywords):
            return category
    return 'Other'


@login_required
def get_forecast(request):
    """Get spending forecast from ML service."""
    from transactions.models import Transaction
    from django.db.models import Sum
    
    # Prepare monthly data
    now = date.today()
    monthly_expenses = []
    for i in range(12, -1, -1):
        if now.month - i <= 0:
            m, y = now.month - i + 12, now.year - 1
        else:
            m, y = now.month - i, now.year
        exp = Transaction.objects.filter(
            user=request.user, transaction_type='expense',
            date__month=m, date__year=y
        ).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        monthly_expenses.append({
            'month': f"{y}-{m:02d}",
            'amount': float(exp)
        })
    
    try:
        resp = req.post(f"{settings.ML_SERVICE_URL}/forecast",
                       json={'monthly_expenses': monthly_expenses},
                       timeout=10)
        if resp.status_code == 200:
            return JsonResponse(resp.json())
    except Exception:
        pass
    
    # Fallback simple forecast
    values = [m['amount'] for m in monthly_expenses if m['amount'] > 0]
    if len(values) >= 3:
        avg = sum(values[-3:]) / 3
        forecast = [{'month': f'Month {i+1}', 'amount': avg} for i in range(3)]
    else:
        forecast = [{'month': f'Month {i+1}', 'amount': 0} for i in range(3)]
    
    return JsonResponse({
        'forecast': forecast,
        'historical': monthly_expenses,
        'method': 'moving_average',
        'note': 'ML service unavailable — using moving average fallback.',
    })
