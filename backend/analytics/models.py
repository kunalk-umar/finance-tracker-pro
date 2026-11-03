from django.db import models
from django.contrib.auth.models import User


class MLModel(models.Model):
    MODEL_TYPES = [
        ('categorizer', 'Expense Categorizer'),
        ('forecaster', 'Spending Forecaster'),
        ('anomaly_detector', 'Anomaly Detector'),
    ]

    name = models.CharField(max_length=100)
    model_type = models.CharField(max_length=30, choices=MODEL_TYPES)
    version = models.CharField(max_length=20, default='1.0')
    file_path = models.CharField(max_length=500)
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    training_samples = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ml_models'
        ordering = ['-trained_at']

    def __str__(self):
        return f"{self.name} v{self.version}"


class PredictionLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions', null=True, blank=True)
    model = models.ForeignKey(MLModel, on_delete=models.SET_NULL, null=True, related_name='predictions')
    input_data = models.TextField()
    prediction = models.CharField(max_length=200)
    confidence = models.FloatField(null=True, blank=True)
    was_correct = models.BooleanField(null=True, blank=True)
    corrected_label = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prediction_logs'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'created_at'])]

    def __str__(self):
        return f"Prediction: {self.prediction} ({self.created_at.date()})"

