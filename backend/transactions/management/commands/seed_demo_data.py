"""
Management command: seed_demo_data
Creates a demo user with 6 months of realistic synthetic financial transactions.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --reset  # Clears existing demo data first
"""
import random
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from transactions.models import Transaction, Category
from budgets.models import Budget, FinancialGoal
from accounts.models import UserProfile


DEMO_USERNAME = 'demo_user'
DEMO_PASSWORD = 'Demo@123456'
DEMO_EMAIL = 'demo@financetracker.pro'


EXPENSE_TEMPLATES = [
    # (description, merchant, category_name, amount_range, payment_method, frequency_per_month)
    ('Swiggy food order', 'Swiggy', 'Food & Dining', (200, 600), 'upi', 8),
    ('Zomato delivery', 'Zomato', 'Food & Dining', (150, 500), 'card', 5),
    ('Restaurant dinner', 'Social Kitchen', 'Food & Dining', (800, 2500), 'card', 3),
    ('Cafe Coffee Day', 'CCD', 'Food & Dining', (150, 350), 'upi', 4),
    ('McDonald\'s', 'McDonald\'s', 'Food & Dining', (200, 450), 'card', 2),

    ('Uber ride', 'Uber', 'Transportation', (80, 350), 'upi', 10),
    ('Ola cab', 'Ola', 'Transportation', (70, 280), 'upi', 6),
    ('Metro card recharge', 'DMRC', 'Transportation', (200, 500), 'upi', 2),
    ('Petrol', 'HP Petrol Pump', 'Transportation', (1000, 3000), 'cash', 2),
    ('Rapido bike', 'Rapido', 'Transportation', (30, 100), 'upi', 8),

    ('Amazon shopping', 'Amazon India', 'Shopping', (500, 5000), 'card', 3),
    ('Flipkart order', 'Flipkart', 'Shopping', (300, 4000), 'upi', 2),
    ('Myntra clothes', 'Myntra', 'Shopping', (800, 3000), 'card', 1),
    ('Meesho purchase', 'Meesho', 'Shopping', (200, 1500), 'upi', 2),

    ('Electricity bill', 'BSES Rajdhani', 'Utilities', (800, 2500), 'net_banking', 1),
    ('Airtel broadband', 'Airtel', 'Utilities', (699, 1499), 'net_banking', 1),
    ('Jio mobile recharge', 'Jio', 'Utilities', (299, 599), 'upi', 1),
    ('Water bill', 'DJB', 'Utilities', (200, 500), 'net_banking', 1),

    ('Apollo pharmacy', 'Apollo Pharmacy', 'Healthcare', (200, 1500), 'card', 1),
    ('Doctor visit', 'Max Healthcare', 'Healthcare', (500, 2000), 'card', 1),

    ('Udemy course', 'Udemy', 'Education', (499, 2999), 'card', 1),

    ('Netflix', 'Netflix', 'Entertainment', (499, 649), 'card', 1),
    ('Spotify', 'Spotify', 'Entertainment', (119, 119), 'card', 1),
    ('Movie tickets', 'BookMyShow', 'Entertainment', (400, 1200), 'card', 2),

    ('House rent', 'Landlord', 'Housing', (15000, 25000), 'net_banking', 1),
    ('Society maintenance', 'Society Office', 'Housing', (1500, 3000), 'net_banking', 1),

    ('Gym membership', 'Cult.fit', 'Fitness', (999, 2999), 'card', 1),

    ('Bigbasket grocery', 'Bigbasket', 'Groceries', (800, 3000), 'upi', 4),
    ('Blinkit order', 'Blinkit', 'Groceries', (200, 800), 'upi', 6),
    ('Zepto delivery', 'Zepto', 'Groceries', (150, 600), 'upi', 4),

    ('LIC premium', 'LIC India', 'Insurance', (3000, 8000), 'net_banking', 1),
]

INCOME_TEMPLATES = [
    ('Monthly salary', 'Infosys Limited', 'Income', (75000, 75000), 'net_banking', 1),
    ('Freelance payment', 'Freelance Client', 'Income', (10000, 30000), 'upi', 1),
    ('Investment returns', 'Zerodha', 'Investment', (500, 5000), 'net_banking', 1),
    ('Cashback credit', 'HDFC Bank', 'Income', (200, 2000), 'net_banking', 1),
]

CATEGORY_DEFS = [
    # (name, type, color, icon)
    ('Food & Dining', 'expense', '#ef4444', 'fa-utensils'),
    ('Transportation', 'expense', '#f59e0b', 'fa-car'),
    ('Shopping', 'expense', '#8b5cf6', 'fa-shopping-cart'),
    ('Utilities', 'expense', '#3b82f6', 'fa-bolt'),
    ('Healthcare', 'expense', '#10b981', 'fa-heartbeat'),
    ('Education', 'expense', '#06b6d4', 'fa-graduation-cap'),
    ('Entertainment', 'expense', '#ec4899', 'fa-film'),
    ('Housing', 'expense', '#f97316', 'fa-home'),
    ('Travel', 'expense', '#14b8a6', 'fa-plane'),
    ('Fitness', 'expense', '#84cc16', 'fa-dumbbell'),
    ('Groceries', 'expense', '#a855f7', 'fa-shopping-basket'),
    ('Insurance', 'expense', '#64748b', 'fa-shield'),
    ('Personal Care', 'expense', '#f43f5e', 'fa-spa'),
    ('Other Expense', 'expense', '#6c757d', 'fa-ellipsis-h'),
    ('Income', 'income', '#10b981', 'fa-hand-holding-usd'),
    ('Investment', 'income', '#3b82f6', 'fa-chart-line'),
    ('Freelance', 'income', '#f59e0b', 'fa-laptop'),
]


class Command(BaseCommand):
    help = 'Seed demo user and realistic synthetic financial data (clearly labeled as synthetic)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo data before seeding')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n[DEMO DATA] This is SYNTHETIC data for demonstration only.\n'))

        # 1. Categories
        self.stdout.write('Creating categories...')
        cat_map = {}
        for name, ctype, color, icon in CATEGORY_DEFS:
            cat, _ = Category.objects.get_or_create(
                name=name, category_type=ctype,
                defaults={'color': color, 'icon': icon, 'is_default': True}
            )
            cat_map[name] = cat
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(cat_map)} categories ready'))

        # 2. Demo user
        self.stdout.write('Creating demo user...')
        if options['reset'] and User.objects.filter(username=DEMO_USERNAME).exists():
            user = User.objects.get(username=DEMO_USERNAME)
            user.transactions.all().delete()
            user.budgets.all().delete()
            user.goals.all().delete()
            self.stdout.write('  ✓ Cleared existing demo data')

        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={
                'email': DEMO_EMAIL,
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )
        if created or options['reset']:
            user.set_password(DEMO_PASSWORD)
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.currency = 'INR'
        profile.monthly_income_goal = Decimal('75000')
        profile.monthly_savings_goal = Decimal('15000')
        profile.phone = '+91 9876543210'
        profile.bio = 'Demo account for Finance Tracker Pro. All transactions are synthetic.'
        profile.save()

        self.stdout.write(self.style.SUCCESS(f'  ✓ Demo user: {DEMO_USERNAME} / {DEMO_PASSWORD}'))

        # 3. Generate 6 months of transactions
        self.stdout.write('Generating 6 months of transactions...')
        today = date.today()
        total_created = 0

        for months_back in range(5, -1, -1):
            if today.month - months_back <= 0:
                m = today.month - months_back + 12
                y = today.year - 1
            else:
                m = today.month - months_back
                y = today.year

            month_start = date(y, m, 1)
            import calendar
            month_end = date(y, m, calendar.monthrange(y, m)[1])

            # Income first
            for desc, merchant, cat_name, amount_range, payment, freq in INCOME_TEMPLATES:
                for _ in range(freq):
                    if random.random() < 0.85:  # 85% chance each month
                        amt_min, amt_max = amount_range
                        amount = Decimal(str(random.randint(amt_min, amt_max)))
                        txn_date = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))
                        category = cat_map.get(cat_name)
                        Transaction.objects.create(
                            user=user,
                            transaction_type='income',
                            category=category,
                            amount=amount,
                            date=txn_date,
                            description=f'[DEMO] {desc}',
                            merchant=merchant,
                            payment_method=payment,
                            status='completed',
                            notes='Synthetic demo transaction',
                        )
                        total_created += 1

            # Expenses
            for desc, merchant, cat_name, amount_range, payment, freq in EXPENSE_TEMPLATES:
                for _ in range(freq):
                    if random.random() < 0.75:
                        amt_min, amt_max = amount_range
                        # Add some variance (±20%)
                        base = random.randint(amt_min, amt_max)
                        variance = random.uniform(0.8, 1.2)
                        amount = Decimal(str(round(base * variance, 2)))
                        if amount <= 0:
                            amount = Decimal(str(amt_min))
                        txn_date = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))
                        category = cat_map.get(cat_name)
                        Transaction.objects.create(
                            user=user,
                            transaction_type='expense',
                            category=category,
                            amount=amount,
                            date=txn_date,
                            description=f'[DEMO] {desc}',
                            merchant=merchant,
                            payment_method=payment,
                            status='completed',
                            notes='Synthetic demo transaction',
                        )
                        total_created += 1

            # Add 1-2 "anomalous" large transactions per month
            if random.random() < 0.3:
                large_amt = Decimal(str(random.randint(15000, 50000)))
                txn_date = month_start + timedelta(days=random.randint(0, 25))
                Transaction.objects.create(
                    user=user,
                    transaction_type='expense',
                    category=cat_map.get('Shopping'),
                    amount=large_amt,
                    date=txn_date,
                    description=f'[DEMO] Large purchase — laptop/phone',
                    merchant='Apple Store',
                    payment_method='card',
                    status='completed',
                    notes='Synthetic anomalous demo transaction',
                )
                total_created += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {total_created} transactions created'))

        # 4. Budgets for current month
        self.stdout.write('Creating monthly budgets...')
        now = date.today()
        budget_defs = [
            ('Food & Dining Budget', 'Food & Dining', 8000),
            ('Transportation Budget', 'Transportation', 5000),
            ('Shopping Budget', 'Shopping', 10000),
            ('Utilities Budget', 'Utilities', 4000),
            ('Entertainment Budget', 'Entertainment', 2000),
            ('Groceries Budget', 'Groceries', 6000),
            ('Overall Monthly Budget', None, 70000),
        ]
        for bname, cat_name, amount in budget_defs:
            cat = cat_map.get(cat_name) if cat_name else None
            Budget.objects.update_or_create(
                user=user, category=cat, month=now.month, year=now.year,
                defaults={'name': bname, 'amount': Decimal(str(amount)), 'is_overall': cat is None}
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(budget_defs)} budgets created'))

        # 5. Financial Goals
        self.stdout.write('Creating financial goals...')
        goals = [
            ('Emergency Fund', 'emergency_fund', 100000, 35000, date(now.year + 1, 6, 30)),
            ('Laptop Purchase', 'purchase', 80000, 45000, date(now.year, now.month + 3 if now.month <= 9 else 12, 30)),
            ('Annual Vacation', 'savings', 50000, 12000, date(now.year, 12, 31)),
        ]
        for gname, gtype, target, current, deadline in goals:
            FinancialGoal.objects.update_or_create(
                user=user, name=gname,
                defaults={
                    'goal_type': gtype,
                    'target_amount': Decimal(str(target)),
                    'current_amount': Decimal(str(current)),
                    'deadline': deadline,
                    'status': 'active',
                    'description': f'[DEMO] Synthetic goal for demonstration.',
                }
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(goals)} goals created'))

        self.stdout.write(self.style.SUCCESS(f'''
╔══════════════════════════════════════════════════════╗
║           Finance Tracker Pro — Demo Data Ready      ║
╠══════════════════════════════════════════════════════╣
║  URL:       http://localhost:8000/                   ║
║  Username:  demo_user                                ║
║  Password:  Demo@123456                              ║
║                                                      ║
║  ⚠ All data is SYNTHETIC for demonstration only     ║
╚══════════════════════════════════════════════════════╝
        '''))

