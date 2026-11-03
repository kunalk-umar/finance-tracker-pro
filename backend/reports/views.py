import csv
import io
from datetime import date, datetime
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from transactions.models import Transaction, Category
from budgets.models import Budget
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@login_required
def report_list(request):
    now = date.today()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    report_type = request.GET.get('type', 'monthly')

    all_txns = Transaction.objects.filter(user=request.user)

    if report_type == 'monthly':
        txns = all_txns.filter(date__month=month, date__year=year)
        period_label = datetime(year, month, 1).strftime('%B %Y')
    elif report_type == 'annual':
        txns = all_txns.filter(date__year=year)
        period_label = str(year)
    else:
        txns = all_txns
        period_label = 'All Time'

    total_income = txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    total_expense = txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    net_savings = total_income - total_expense
    savings_rate = round((float(net_savings) / float(total_income) * 100), 1) if total_income > 0 else 0.0

    category_breakdown = txns.filter(transaction_type='expense').values(
        'category__name'
    ).annotate(total=Sum('amount'), count=Count('id')).order_by('-total')

    income_sources = txns.filter(transaction_type='income').values(
        'category__name', 'merchant'
    ).annotate(total=Sum('amount'), count=Count('id')).order_by('-total')

    monthly_summary = []
    if report_type == 'annual':
        for m in range(1, 13):
            m_txns = all_txns.filter(date__month=m, date__year=year)
            m_inc = m_txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
            m_exp = m_txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
            monthly_summary.append({
                'month': datetime(year, m, 1).strftime('%b'),
                'income': m_inc,
                'expense': m_exp,
                'savings': m_inc - m_exp,
            })

    years = list(range(2020, now.year + 2))
    months = [(i, datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]

    return render(request, 'reports/report_list.html', {
        'txns': txns.select_related('category').order_by('-date')[:100],
        'total_income': total_income,
        'total_expense': total_expense,
        'net_savings': net_savings,
        'savings_rate': savings_rate,
        'category_breakdown': category_breakdown,
        'income_sources': income_sources,
        'monthly_summary': monthly_summary,
        'period_label': period_label,
        'report_type': report_type,
        'year': year,
        'month': month,
        'years': years,
        'months': months,
    })


@login_required
def export_report_csv(request):
    now = date.today()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    report_type = request.GET.get('type', 'monthly')

    all_txns = Transaction.objects.filter(user=request.user)
    if report_type == 'monthly':
        txns = all_txns.filter(date__month=month, date__year=year)
        filename = f"report_{year}_{month:02d}.csv"
    elif report_type == 'annual':
        txns = all_txns.filter(date__year=year)
        filename = f"report_{year}.csv"
    else:
        txns = all_txns
        filename = f"report_all.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Description', 'Merchant', 'Amount (INR)', 'Payment Method', 'Status'])
    for t in txns.select_related('category').order_by('-date'):
        writer.writerow([
            t.date, t.transaction_type, t.category.name if t.category else 'Uncategorized',
            t.description, t.merchant, t.amount, t.payment_method, t.status
        ])
    return response


@login_required
def export_report_pdf(request):
    if not REPORTLAB_AVAILABLE:
        from django.http import HttpResponse
        return HttpResponse("PDF export requires reportlab. Please install it.", content_type='text/plain')

    now = date.today()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    report_type = request.GET.get('type', 'monthly')

    all_txns = Transaction.objects.filter(user=request.user)
    if report_type == 'monthly':
        txns = all_txns.filter(date__month=month, date__year=year)
        period_label = datetime(year, month, 1).strftime('%B %Y')
        filename = f"report_{year}_{month:02d}.pdf"
    elif report_type == 'annual':
        txns = all_txns.filter(date__year=year)
        period_label = str(year)
        filename = f"report_{year}.pdf"
    else:
        txns = all_txns
        period_label = 'All Time'
        filename = f"report_all.pdf"

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch*0.5, leftMargin=inch*0.5,
                            topMargin=inch*0.75, bottomMargin=inch*0.75)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER,
                                  textColor=colors.HexColor('#1a1a2e'), fontSize=20)
    story.append(Paragraph('Finance Tracker Pro', title_style))
    story.append(Paragraph(f'Financial Report — {period_label}', styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))

    # Summary
    total_income = txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    total_expense = txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    net = total_income - total_expense

    summary_data = [
        ['Metric', 'Amount (INR)'],
        ['Total Income', f'₹{total_income:,.2f}'],
        ['Total Expenses', f'₹{total_expense:,.2f}'],
        ['Net Savings', f'₹{net:,.2f}'],
    ]
    t = Table(summary_data, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))

    # Transactions table
    story.append(Paragraph('Transaction Details', styles['Heading3']))
    txn_data = [['Date', 'Type', 'Category', 'Description', 'Amount']]
    for trx in txns.select_related('category').order_by('-date')[:50]:
        txn_data.append([
            str(trx.date),
            trx.transaction_type.title(),
            trx.category.name if trx.category else 'Other',
            trx.description[:30],
            f'₹{trx.amount:,.2f}',
        ])
    txn_table = Table(txn_data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 2.5*inch, 1.2*inch])
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4f8')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    story.append(txn_table)

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
