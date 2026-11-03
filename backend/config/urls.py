"""
URL configuration for Finance Tracker Pro
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Finance Tracker Pro API",
        default_version='v1',
        description="AI-Powered Personal Finance & Spending Analytics Platform API",
        contact=openapi.Contact(email="support@financetracker.pro"),
        license=openapi.License(name="MIT License"),
    ),
    public=False,
    permission_classes=[permissions.IsAuthenticated],
)

urlpatterns = [
    # Root redirect
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Auth (accounts)
    path('accounts/', include('accounts.urls')),
    
    # App pages
    path('dashboard/', include('analytics.urls')),
    path('transactions/', include('transactions.urls')),
    path('budgets/', include('budgets.urls')),
    path('reports/', include('reports.urls')),
    
    # REST API
    path('api/', include('api.urls')),
    
    # Swagger API docs
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

