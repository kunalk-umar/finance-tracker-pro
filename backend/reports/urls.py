from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_list, name='reports'),
    path('export/csv/', views.export_report_csv, name='export_report_csv'),
    path('export/pdf/', views.export_report_pdf, name='export_report_pdf'),
]
