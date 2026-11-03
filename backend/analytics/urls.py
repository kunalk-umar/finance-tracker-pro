from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics_page, name='analytics'),
    path('ml/', views.ml_predictions, name='ml_predictions'),
    path('ml/run-anomaly/', views.run_anomaly_detection, name='run_anomaly'),
    path('ml/predict-category/', views.predict_category_ajax, name='predict_category_ajax'),
    path('ml/forecast/', views.get_forecast, name='get_forecast'),
]
