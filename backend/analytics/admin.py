from django.contrib import admin
from .models import MLModel, PredictionLog

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'version', 'accuracy', 'trained_at', 'is_active']

@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'prediction', 'confidence', 'was_correct', 'created_at']
    list_filter = ['was_correct']
