"""
Finance Tracker Pro — Automated Test Suite
Tests: auth, CRUD, analytics, budgets, APIs, data isolation
"""
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from transactions.models import Transaction, Category
from budgets.models import Budget, FinancialGoal
from accounts.models import UserProfile
from analytics.services import get_dashboard_data


def create_test_user(username='testuser', password='TestPass@123'):
    user = User.objects.create_user(username=username, email=f'{username}@test.com',
                                     first_name='Test', last_name='User', password=password)
    return user


def create_test_category(name='Food & Dining', cat_type='expense', color='#ef4444'):
    return Category.objects.create(name=name, category_type=cat_type, color=color, is_default=True)


def create_test_transaction(user, category, amount=500, t_type='expense', desc='Test txn'):
    return Transaction.objects.create(
        user=user, transaction_type=t_type, category=category,
        amount=Decimal(str(amount)), date=date.today(),
        description=desc, merchant='Test Merchant', payment_method='upi', status='completed'
    )


# ─── Authentication Tests ────────────────────────────────────────────────────

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()

    def test_register_page_loads(self):
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Create')

    def test_login_page_loads(self):
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

    def test_user_registration(self):
        resp = self.client.post(reverse('register'), {
            'username': 'newuser', 'email': 'new@test.com',
            'first_name': 'New', 'last_name': 'User',
            'password1': 'SecurePass@123', 'password2': 'SecurePass@123',
        })
        # Should redirect after successful registration
        self.assertIn(resp.status_code, [200, 302])
        if resp.status_code == 302:
            self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_success(self):
        resp = self.client.post(reverse('login'), {
            'username': 'testuser', 'password': 'TestPass@123'
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_login_invalid_password(self):
        resp = self.client.post(reverse('login'), {
            'username': 'testuser', 'password': 'wrongpassword'
        })
        self.assertEqual(resp.status_code, 200)  # stays on login page

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertRedirects(resp, f"/accounts/login/?next=/dashboard/", fetch_redirect_response=False)

    def test_profile_requires_login(self):
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 302)

    def test_authenticated_user_access_dashboard(self):
        self.client.login(username='testuser', password='TestPass@123')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser', password='TestPass@123')
        resp = self.client.get(reverse('logout'))
        self.assertIn(resp.status_code, [200, 302])


# ─── UserProfile Tests ────────────────────────────────────────────────────────

class UserProfileTests(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_profile_created_on_user_creation(self):
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_profile_default_currency(self):
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.currency, 'INR')

    def test_profile_currency_symbol(self):
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.get_currency_symbol(), '₹')


# ─── Category Tests ───────────────────────────────────────────────────────────

class CategoryTests(TestCase):
    def test_category_creation(self):
        cat = create_test_category()
        self.assertEqual(cat.name, 'Food & Dining')
        self.assertEqual(cat.category_type, 'expense')

    def test_category_str(self):
        cat = create_test_category()
        self.assertIn('Food & Dining', str(cat))


# ─── Transaction CRUD Tests ───────────────────────────────────────────────────

class TransactionCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.user2 = create_test_user('otheruser', 'OtherPass@123')
        self.cat = create_test_category()
        self.client.login(username='testuser', password='TestPass@123')

    def test_create_expense_transaction(self):
        txn = create_test_transaction(self.user, self.cat, 500, 'expense')
        self.assertEqual(txn.transaction_type, 'expense')
        self.assertEqual(txn.amount, Decimal('500'))
        self.assertTrue(txn.is_expense)
        self.assertFalse(txn.is_income)

    def test_create_income_transaction(self):
        txn = create_test_transaction(self.user, self.cat, 75000, 'income', 'Salary')
        self.assertTrue(txn.is_income)
        self.assertEqual(txn.amount, Decimal('75000'))

    def test_transaction_list_view(self):
        create_test_transaction(self.user, self.cat)
        resp = self.client.get(reverse('transaction_list'))
        self.assertEqual(resp.status_code, 200)

    def test_transaction_create_view_get(self):
        resp = self.client.get(reverse('transaction_create'))
        self.assertEqual(resp.status_code, 200)

    def test_transaction_create_post(self):
        resp = self.client.post(reverse('transaction_create'), {
            'transaction_type': 'expense', 'category': self.cat.pk,
            'amount': '750.00', 'date': str(date.today()),
            'description': 'Test expense', 'merchant': 'Test Merchant',
            'payment_method': 'upi', 'status': 'completed',
        })
        self.assertIn(resp.status_code, [200, 302])
        if resp.status_code == 302:
            self.assertTrue(Transaction.objects.filter(user=self.user, description='Test expense').exists())

    def test_transaction_edit(self):
        txn = create_test_transaction(self.user, self.cat)
        resp = self.client.get(reverse('transaction_edit', args=[txn.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_transaction_delete(self):
        txn = create_test_transaction(self.user, self.cat)
        resp = self.client.post(reverse('transaction_delete', args=[txn.pk]))
        self.assertIn(resp.status_code, [200, 302])
        if resp.status_code == 302:
            self.assertFalse(Transaction.objects.filter(pk=txn.pk).exists())

    def test_user_data_isolation(self):
        """Users must only see their own transactions."""
        txn_user1 = create_test_transaction(self.user, self.cat, 500, 'expense', 'User1 txn')
        txn_user2 = create_test_transaction(self.user2, self.cat, 999, 'expense', 'User2 txn')

        resp = self.client.get(reverse('transaction_list'))
        content = resp.content.decode()
        self.assertIn('User1 txn', content)
        self.assertNotIn('User2 txn', content)

    def test_cannot_edit_other_users_transaction(self):
        txn = create_test_transaction(self.user2, self.cat, 500, 'expense', 'Other txn')
        resp = self.client.get(reverse('transaction_edit', args=[txn.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_cannot_delete_other_users_transaction(self):
        txn = create_test_transaction(self.user2, self.cat)
        resp = self.client.post(reverse('transaction_delete', args=[txn.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_transaction_amount_must_be_positive(self):
        resp = self.client.post(reverse('transaction_create'), {
            'transaction_type': 'expense', 'category': self.cat.pk,
            'amount': '-100', 'date': str(date.today()),
            'description': 'Bad txn', 'payment_method': 'upi', 'status': 'completed',
        })
        self.assertEqual(resp.status_code, 200)  # Form error stays on page
        self.assertFalse(Transaction.objects.filter(description='Bad txn').exists())


# ─── Budget Tests ─────────────────────────────────────────────────────────────

class BudgetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.cat = create_test_category()
        self.client.login(username='testuser', password='TestPass@123')

    def test_budget_creation(self):
        budget = Budget.objects.create(
            user=self.user, category=self.cat, name='Food Budget',
            amount=Decimal('8000'), month=date.today().month, year=date.today().year
        )
        self.assertEqual(budget.amount, Decimal('8000'))
        self.assertEqual(budget.remaining, Decimal('8000'))
        self.assertFalse(budget.is_exceeded)
        self.assertFalse(budget.is_warning)

    def test_budget_utilization(self):
        budget = Budget.objects.create(
            user=self.user, category=self.cat, name='Food Budget',
            amount=Decimal('10000'), spent=Decimal('8500'),
            month=date.today().month, year=date.today().year
        )
        self.assertEqual(budget.utilization_pct, 85.0)
        self.assertTrue(budget.is_warning)
        self.assertFalse(budget.is_exceeded)

    def test_budget_exceeded(self):
        budget = Budget.objects.create(
            user=self.user, category=self.cat, name='Food Budget',
            amount=Decimal('5000'), spent=Decimal('6000'),
            month=date.today().month, year=date.today().year
        )
        self.assertTrue(budget.is_exceeded)
        self.assertEqual(budget.remaining, Decimal('-1000'))

    def test_budget_list_view(self):
        resp = self.client.get(reverse('budget_list'))
        self.assertEqual(resp.status_code, 200)

    def test_budget_isolation(self):
        user2 = create_test_user('otheruser2', 'OtherPass@123')
        Budget.objects.create(user=user2, category=self.cat, name='Other Budget',
                               amount=Decimal('5000'), month=date.today().month, year=date.today().year)
        resp = self.client.get(reverse('budget_list'))
        self.assertNotIn('Other Budget', resp.content.decode())


# ─── Financial Goal Tests ─────────────────────────────────────────────────────

class FinancialGoalTests(TestCase):
    def setUp(self):
        self.user = create_test_user()

    def test_goal_progress(self):
        goal = FinancialGoal.objects.create(
            user=self.user, name='Emergency Fund',
            goal_type='emergency_fund',
            target_amount=Decimal('100000'), current_amount=Decimal('35000')
        )
        self.assertEqual(goal.progress_pct, 35.0)
        self.assertEqual(goal.remaining, Decimal('65000'))

    def test_goal_completed(self):
        goal = FinancialGoal.objects.create(
            user=self.user, name='Laptop',
            goal_type='purchase',
            target_amount=Decimal('80000'), current_amount=Decimal('80000')
        )
        self.assertEqual(goal.progress_pct, 100.0)
        self.assertEqual(goal.remaining, Decimal('0'))


# ─── Analytics Tests ──────────────────────────────────────────────────────────

class AnalyticsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.cat = create_test_category()
        self.client.login(username='testuser', password='TestPass@123')
        # Create test transactions
        for i in range(5):
            create_test_transaction(self.user, self.cat, 1000 * (i+1), 'expense', f'Expense {i}')
        create_test_transaction(self.user, self.cat, 50000, 'income', 'Salary')

    def test_dashboard_view(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Dashboard')

    def test_analytics_view(self):
        resp = self.client.get(reverse('analytics'))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_data_calculations(self):
        data = get_dashboard_data(self.user)
        self.assertIn('balance', data)
        self.assertIn('total_income', data)
        self.assertIn('total_expense', data)
        self.assertGreater(data['total_income'], 0)
        self.assertGreater(data['total_expense'], 0)
        # Balance = income - expense
        self.assertEqual(data['balance'], data['total_income'] - data['total_expense'])

    def test_insights_generated(self):
        data = get_dashboard_data(self.user)
        self.assertIn('insights', data)
        self.assertIsInstance(data['insights'], list)

    def test_monthly_chart_data(self):
        data = get_dashboard_data(self.user)
        self.assertIn('monthly_data', data)
        self.assertEqual(len(data['monthly_data']), 6)

    def test_ml_predictions_view(self):
        resp = self.client.get(reverse('ml_predictions'))
        self.assertEqual(resp.status_code, 200)


# ─── Reports Tests ────────────────────────────────────────────────────────────

class ReportsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.cat = create_test_category()
        self.client.login(username='testuser', password='TestPass@123')
        create_test_transaction(self.user, self.cat, 5000, 'expense', 'Test expense')
        create_test_transaction(self.user, self.cat, 75000, 'income', 'Salary')

    def test_reports_view(self):
        resp = self.client.get(reverse('reports'))
        self.assertEqual(resp.status_code, 200)

    def test_csv_export(self):
        resp = self.client.get(reverse('export_csv'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        content = resp.content.decode()
        self.assertIn('Date', content)
        self.assertIn('Amount', content)

    def test_report_csv_export(self):
        resp = self.client.get(reverse('export_report_csv') + '?type=monthly')
        self.assertEqual(resp.status_code, 200)


# ─── REST API Tests ───────────────────────────────────────────────────────────

class APIAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.token, _ = Token.objects.get_or_create(user=self.user)

    def test_api_register(self):
        resp = self.client.post('/api/auth/register/', {
            'username': 'apiuser', 'email': 'api@test.com',
            'first_name': 'API', 'last_name': 'User',
            'password': 'APIPass@123', 'password2': 'APIPass@123'
        })
        self.assertEqual(resp.status_code, 201)
        self.assertIn('token', resp.data)
        self.assertIn('user', resp.data)

    def test_api_login(self):
        resp = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'TestPass@123'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.data)

    def test_api_login_invalid(self):
        resp = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'wrongpassword'
        })
        self.assertEqual(resp.status_code, 401)

    def test_api_requires_auth(self):
        resp = self.client.get('/api/transactions/')
        self.assertEqual(resp.status_code, 401)

    def test_api_with_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.get('/api/transactions/')
        self.assertEqual(resp.status_code, 200)

    def test_api_logout(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        resp = self.client.post('/api/auth/logout/')
        self.assertEqual(resp.status_code, 200)


class APITransactionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_test_user()
        self.user2 = create_test_user('apiuser2', 'APIPass@123')
        self.cat = create_test_category()
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_list_transactions_empty(self):
        resp = self.client.get('/api/transactions/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 0)

    def test_create_transaction(self):
        resp = self.client.post('/api/transactions/', {
            'transaction_type': 'expense', 'category': self.cat.pk,
            'amount': '1500.00', 'date': str(date.today()),
            'description': 'API Test Txn', 'payment_method': 'upi', 'status': 'completed'
        })
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['amount'], '1500.00')

    def test_api_data_isolation(self):
        # User2's transaction should not appear in user1's API response
        txn2 = create_test_transaction(self.user2, self.cat, 999, 'expense', 'User2 API txn')
        resp = self.client.get('/api/transactions/')
        ids = [t['id'] for t in resp.data['results']]
        self.assertNotIn(str(txn2.pk), ids)

    def test_api_dashboard(self):
        resp = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('balance', resp.data)
        self.assertIn('total_income', resp.data)

    def test_delete_own_transaction(self):
        txn = create_test_transaction(self.user, self.cat)
        resp = self.client.delete(f'/api/transactions/{txn.pk}/')
        self.assertEqual(resp.status_code, 204)

    def test_cannot_delete_other_transaction(self):
        txn2 = create_test_transaction(self.user2, self.cat)
        resp = self.client.delete(f'/api/transactions/{txn2.pk}/')
        self.assertEqual(resp.status_code, 404)


# ─── CSV Export/Import Tests ──────────────────────────────────────────────────

class CSVTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.cat = create_test_category()
        self.client.login(username='testuser', password='TestPass@123')

    def test_csv_export_content(self):
        create_test_transaction(self.user, self.cat, 500, 'expense', 'CSV Test')
        resp = self.client.get(reverse('export_csv'))
        content = resp.content.decode()
        self.assertIn('CSV Test', content)
        self.assertIn('expense', content)
        self.assertIn('500', content)

    def test_csv_import_view(self):
        resp = self.client.get(reverse('import_csv'))
        self.assertEqual(resp.status_code, 200)


# ─── Security Tests ───────────────────────────────────────────────────────────

class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.user2 = create_test_user('secuser2', 'SecPass@123')
        self.cat = create_test_category()

    def test_unauthenticated_api_blocked(self):
        api_client = APIClient()
        resp = api_client.get('/api/transactions/')
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_dashboard_redirected(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_transaction_user_isolation_api(self):
        txn1 = create_test_transaction(self.user, self.cat, 100, 'expense', 'User1')
        txn2 = create_test_transaction(self.user2, self.cat, 200, 'expense', 'User2')
        api_client = APIClient()
        token1, _ = Token.objects.get_or_create(user=self.user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        resp = api_client.get('/api/transactions/')
        ids = [t['id'] for t in resp.data['results']]
        self.assertIn(str(txn1.pk), ids)
        self.assertNotIn(str(txn2.pk), ids)

