import csv
import io
from decimal import Decimal
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Transaction, Category
from .forms import TransactionForm, TransactionFilterForm, CSVImportForm


def get_user_categories(user):
    return Category.objects.filter(Q(is_default=True) | Q(user=user))


@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user).select_related('category')
    form = TransactionFilterForm(request.GET)

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            transactions = transactions.filter(date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            transactions = transactions.filter(date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('transaction_type'):
            transactions = transactions.filter(transaction_type=form.cleaned_data['transaction_type'])
        if form.cleaned_data.get('category'):
            transactions = transactions.filter(category=form.cleaned_data['category'])
        if form.cleaned_data.get('min_amount'):
            transactions = transactions.filter(amount__gte=form.cleaned_data['min_amount'])
        if form.cleaned_data.get('max_amount'):
            transactions = transactions.filter(amount__lte=form.cleaned_data['max_amount'])
        if form.cleaned_data.get('search'):
            q = form.cleaned_data['search']
            transactions = transactions.filter(
                Q(description__icontains=q) | Q(merchant__icontains=q) | Q(notes__icontains=q)
            )

    sort = request.GET.get('sort', '-date')
    valid_sorts = ['date', '-date', 'amount', '-amount', 'category__name', '-category__name']
    if sort in valid_sorts:
        transactions = transactions.order_by(sort)

    paginator = Paginator(transactions, 20)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    # Summary stats
    all_txns = Transaction.objects.filter(user=request.user)
    total_income = all_txns.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    total_expense = all_txns.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    return render(request, 'transactions/transaction_list.html', {
        'page_obj': page_obj,
        'filter_form': form,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'sort': sort,
    })


@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(request, f'Transaction of \u20b9{transaction.amount} added successfully!')

            # Try ML categorization if no category selected
            if not transaction.category and transaction.description:
                try:
                    import requests as req
                    from django.conf import settings
                    resp = req.post(f"{settings.ML_SERVICE_URL}/predict-category",
                                   json={'description': transaction.description, 'merchant': transaction.merchant},
                                   timeout=2)
                    if resp.status_code == 200:
                        data = resp.json()
                        transaction.ml_category_suggestion = data.get('category', '')
                        transaction.ml_confidence = data.get('confidence', 0)
                        transaction.save(update_fields=['ml_category_suggestion', 'ml_confidence'])
                except Exception:
                    pass

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'id': str(transaction.id)})
            return redirect('transaction_list')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = TransactionForm(user=request.user)

    categories = get_user_categories(request.user)
    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'categories': categories,
        'title': 'Add Transaction',
        'action': 'Create',
    })


@login_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully!')
            return redirect('transaction_list')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    categories = get_user_categories(request.user)
    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'transaction': transaction,
        'categories': categories,
        'title': 'Edit Transaction',
        'action': 'Update',
    })


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        amount = transaction.amount
        transaction.delete()
        messages.success(request, f'Transaction of \u20b9{amount} deleted.')
        return redirect('transaction_list')
    return render(request, 'transactions/transaction_confirm_delete.html', {'transaction': transaction})


@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    return render(request, 'transactions/transaction_detail.html', {'transaction': transaction})


@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{date.today()}.csv"'

    transactions = Transaction.objects.filter(user=request.user).select_related('category').order_by('-date')

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Description', 'Merchant', 'Amount', 'Payment Method', 'Status', 'Notes'])

    for t in transactions:
        writer.writerow([
            t.date, t.transaction_type, t.category.name if t.category else '',
            t.description, t.merchant, t.amount, t.payment_method, t.status, t.notes
        ])

    return response


@login_required
def import_csv(request):
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a valid CSV file.')
                return redirect('import_csv')

            try:
                decoded = csv_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                imported = 0
                errors = 0

                for row in reader:
                    try:
                        t_type = row.get('type', row.get('transaction_type', 'expense')).lower().strip()
                        if t_type not in ['income', 'expense']:
                            t_type = 'expense'

                        amount_str = str(row.get('amount', '0')).replace(',', '').replace('\u20b9', '').strip()
                        amount = Decimal(amount_str)
                        if amount <= 0:
                            errors += 1
                            continue

                        date_str = row.get('date', str(date.today())).strip()
                        try:
                            txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                txn_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                            except ValueError:
                                txn_date = date.today()

                        cat_name = row.get('category', '').strip()
                        category = None
                        if cat_name:
                            category = Category.objects.filter(
                                Q(name__iexact=cat_name) & (Q(is_default=True) | Q(user=request.user))
                            ).first()

                        Transaction.objects.create(
                            user=request.user,
                            transaction_type=t_type,
                            category=category,
                            amount=amount,
                            date=txn_date,
                            description=row.get('description', 'Imported transaction').strip(),
                            merchant=row.get('merchant', '').strip(),
                            payment_method=row.get('payment_method', 'other').strip() or 'other',
                            notes=row.get('notes', '').strip(),
                        )
                        imported += 1
                    except Exception:
                        errors += 1

                messages.success(request, f'Imported {imported} transactions. {errors} rows skipped.')
                return redirect('transaction_list')

            except Exception as e:
                messages.error(request, f'Error reading file: {str(e)}')
    else:
        form = CSVImportForm()

    return render(request, 'transactions/import_csv.html', {'form': form})
