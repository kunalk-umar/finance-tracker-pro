from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='api-transactions')
router.register('budgets', views.BudgetViewSet, basename='api-budgets')
router.register('categories', views.CategoryViewSet, basename='api-categories')
router.register('goals', views.FinancialGoalViewSet, basename='api-goals')
router.register('notifications', views.NotificationViewSet, basename='api-notifications')

urlpatterns = [
    # Auth endpoints
    path('auth/register/', views.api_register, name='api-register'),
    path('auth/login/', views.api_login, name='api-login'),
    path('auth/logout/', views.api_logout, name='api-logout'),
    # Analytics endpoints
    path('analytics/dashboard/', views.api_dashboard, name='api-dashboard'),
    path('analytics/monthly/', views.api_monthly, name='api-monthly'),
    path('analytics/categories/', views.api_categories_analytics, name='api-categories'),
    # Router
    path('', include(router.urls)),
]
