from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, datetime
from decimal import Decimal

from transactions.models import Transaction, Category
from budgets.models import Budget, FinancialGoal
from accounts.models import UserProfile, Notification
from analytics.services import get_dashboard_data, get_analytics_data
from .serializers import (
    UserSerializer, UserRegistrationSerializer, CategorySerializer,
    TransactionSerializer, BudgetSerializer, FinancialGoalSerializer,
    NotificationSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Registration successful.',
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'message': 'Login successful.',
        })
    return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard(request):
    data = get_dashboard_data(request.user)
    # Serialize
    return Response({
        'balance': float(data['balance']),
        'total_income': float(data['total_income']),
        'total_expense': float(data['total_expense']),
        'curr_income': float(data['curr_income']),
        'curr_expense': float(data['curr_expense']),
        'curr_savings': float(data['curr_savings']),
        'savings_rate': data['savings_rate'],
        'budget_utilization': data['budget_utilization'],
        'income_change': data['income_change'],
        'expense_change': data['expense_change'],
        'monthly_data': data['monthly_data'],
        'insights': data['insights'],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_monthly(request):
    year = int(request.query_params.get('year', date.today().year))
    month = int(request.query_params.get('month', date.today().month))
    txns = Transaction.objects.filter(user=request.user, date__month=month, date__year=year)
    income = txns.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    expense = txns.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or Decimal('0')
    return Response({
        'year': year,
        'month': month,
        'income': float(income),
        'expense': float(expense),
        'savings': float(income - expense),
        'transaction_count': txns.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_categories_analytics(request):
    data = Transaction.objects.filter(user=request.user, transaction_type='expense').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    return Response(list(data))


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).select_related('category')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            Q(is_default=True) | Q(user=self.request.user)
        )


class FinancialGoalViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialGoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})
