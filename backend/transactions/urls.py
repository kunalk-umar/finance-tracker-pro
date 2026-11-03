from django.urls import path
from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('add/', views.transaction_create, name='transaction_create'),
    path('add/', views.transaction_create, name='add_transaction'),
    path('<uuid:pk>/', views.transaction_detail, name='transaction_detail'),
    path('<uuid:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('<uuid:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('export/', views.export_csv, name='export_csv'),
    path('import/', views.import_csv, name='import_csv'),
]
