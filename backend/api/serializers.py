from rest_framework import serializers
from django.contrib.auth.models import User
from transactions.models import Transaction, Category
from budgets.models import Budget, FinancialGoal
from accounts.models import UserProfile, Notification


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'category_type', 'icon', 'color', 'is_default']


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'category', 'category_name', 'category_color',
            'amount', 'date', 'description', 'merchant', 'payment_method', 'status',
            'ml_category_suggestion', 'ml_confidence', 'is_anomaly', 'anomaly_score',
            'notes', 'tags', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ml_category_suggestion', 'ml_confidence', 'is_anomaly', 'anomaly_score', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BudgetSerializer(serializers.ModelSerializer):
    remaining = serializers.ReadOnlyField()
    utilization_pct = serializers.ReadOnlyField()
    is_exceeded = serializers.ReadOnlyField()
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Budget
        fields = ['id', 'name', 'category', 'category_name', 'amount', 'spent',
                  'month', 'year', 'is_overall', 'remaining', 'utilization_pct', 'is_exceeded']
        read_only_fields = ['id', 'spent']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FinancialGoalSerializer(serializers.ModelSerializer):
    progress_pct = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()

    class Meta:
        model = FinancialGoal
        fields = ['id', 'name', 'goal_type', 'target_amount', 'current_amount',
                  'deadline', 'status', 'description', 'progress_pct', 'remaining']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at']
