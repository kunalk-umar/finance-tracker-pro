"""
Finance Tracker Pro — Flask ML Microservice
Provides: expense categorization, spending forecasting, anomaly detection
"""
import os
import logging
import json
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global model store
models = {}
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)


def load_models():
    """Load pre-trained models if they exist."""
    global models
    import joblib
    
    categorizer_path = os.path.join(MODEL_DIR, 'categorizer.joblib')
    if os.path.exists(categorizer_path):
        try:
            models['categorizer'] = joblib.load(categorizer_path)
            logger.info("Loaded categorizer model.")
        except Exception as e:
            logger.error(f"Failed to load categorizer: {e}")
    
    logger.info(f"Models loaded: {list(models.keys())}")


# Rule-based fallback
CATEGORY_RULES = {
    'Food & Dining': ['swiggy', 'zomato', 'food', 'restaurant', 'cafe', 'pizza', 'burger', 'dhaba', 'dining', 'eat', 'lunch', 'dinner', 'breakfast'],
    'Transportation': ['uber', 'ola', 'taxi', 'petrol', 'fuel', 'metro', 'bus', 'auto', 'rapido', 'cab', 'transport', 'commute'],
    'Shopping': ['amazon', 'flipkart', 'myntra', 'shopping', 'mall', 'store', 'market', 'buy', 'purchase', 'meesho', 'ajio'],
    'Utilities': ['electricity', 'water', 'gas', 'internet', 'wifi', 'broadband', 'utility', 'bill', 'recharge', 'mobile', 'dth'],
    'Healthcare': ['hospital', 'doctor', 'medicine', 'pharmacy', 'health', 'medical', 'clinic', 'apollo', 'max', 'diagnostic', 'lab'],
    'Education': ['school', 'college', 'course', 'tuition', 'education', 'book', 'udemy', 'coursera', 'fees', 'library'],
    'Entertainment': ['netflix', 'spotify', 'prime', 'movie', 'cinema', 'game', 'entertainment', 'hotstar', 'zee5', 'theatre'],
    'Housing': ['rent', 'maintenance', 'housing', 'flat', 'apartment', 'society', 'deposit', 'landlord'],
    'Travel': ['flight', 'hotel', 'travel', 'vacation', 'trip', 'makemytrip', 'booking', 'irctc', 'train', 'airbnb'],
    'Fitness': ['gym', 'fitness', 'yoga', 'sports', 'cult.fit', 'swimming', 'crossfit'],
    'Groceries': ['grocery', 'vegetables', 'fruits', 'supermarket', 'dmart', 'reliance fresh', 'bigbasket', 'blinkit', 'zepto', 'instamart'],
    'Insurance': ['insurance', 'lic', 'premium', 'policy', 'cover'],
    'Investment': ['mutual fund', 'sip', 'stocks', 'zerodha', 'groww', 'investment', 'demat', 'nifty', 'sensex'],
    'Personal Care': ['salon', 'haircut', 'beauty', 'spa', 'cosmetics', 'grooming', 'nykaa'],
    'Income': ['salary', 'freelance', 'bonus', 'dividend', 'interest', 'refund', 'cashback'],
}


def rule_based_categorize(text):
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_RULES.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score
    if scores:
        best = max(scores, key=scores.get)
        confidence = min(0.95, 0.5 + scores[best] * 0.15)
        return best, confidence
    return 'Other', 0.3


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Finance Tracker ML Service',
        'models_loaded': list(models.keys()),
        'version': '1.0.0',
    })


@app.route('/predict-category', methods=['POST'])
def predict_category():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    description = data.get('description', '')
    merchant = data.get('merchant', '')
    combined_text = f"{description} {merchant}".strip()
    
    if not combined_text:
        return jsonify({'error': 'description or merchant required'}), 400
    
    # Try ML model first
    if 'categorizer' in models:
        try:
            cat_data = models['categorizer']
            vectorizer = cat_data['vectorizer']
            clf = cat_data['classifier']
            label_encoder = cat_data['label_encoder']
            
            features = vectorizer.transform([combined_text])
            pred_idx = clf.predict(features)[0]
            proba = clf.predict_proba(features)[0]
            confidence = float(np.max(proba))
            category = label_encoder.inverse_transform([pred_idx])[0]
            
            return jsonify({
                'category': category,
                'confidence': round(confidence, 3),
                'source': 'ml_model',
                'text_analyzed': combined_text,
            })
        except Exception as e:
            logger.error(f"ML categorization failed: {e}")
    
    # Fallback to rules
    category, confidence = rule_based_categorize(combined_text)
    return jsonify({
        'category': category,
        'confidence': round(confidence, 3),
        'source': 'rule_based',
        'text_analyzed': combined_text,
    })


@app.route('/detect-anomalies', methods=['POST'])
def detect_anomalies():
    """Isolation Forest anomaly detection on transactions."""
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    
    data = request.get_json()
    if not data or 'transactions' not in data:
        return jsonify({'error': 'transactions array required'}), 400
    
    transactions = data['transactions']
    if len(transactions) < 5:
        return jsonify({
            'anomaly_ids': [],
            'scores': {},
            'message': 'Need at least 5 transactions for anomaly detection.',
            'count': 0,
        })
    
    try:
        df = pd.DataFrame(transactions)
        
        # Feature engineering
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        
        # Amount-based features
        features = df[['amount']].copy()
        features['amount_log'] = np.log1p(features['amount'])
        features['amount_zscore'] = (features['amount'] - features['amount'].mean()) / (features['amount'].std() + 1e-8)
        
        # Add day of week if date available
        if 'date' in df.columns:
            try:
                df['date_parsed'] = pd.to_datetime(df['date'])
                features['day_of_week'] = df['date_parsed'].dt.dayofweek
                features['day_of_month'] = df['date_parsed'].dt.day
            except Exception:
                features['day_of_week'] = 0
                features['day_of_month'] = 15
        
        scaler = StandardScaler()
        X = scaler.fit_transform(features)
        
        # Isolation Forest
        contamination = min(0.1, max(0.02, 3 / len(X)))
        clf = IsolationForest(n_estimators=100, contamination=contamination, random_state=42)
        clf.fit(X)
        
        predictions = clf.predict(X)
        scores = clf.score_samples(X)
        
        anomaly_ids = []
        score_map = {}
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:
                txn_id = str(df.iloc[i]['id'])
                anomaly_ids.append(txn_id)
                score_map[txn_id] = round(float(score), 4)
        
        return jsonify({
            'anomaly_ids': anomaly_ids,
            'scores': score_map,
            'count': len(anomaly_ids),
            'total_analyzed': len(transactions),
            'method': 'IsolationForest',
        })
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/forecast', methods=['POST'])
def forecast():
    """Time-series forecasting of monthly expenses."""
    data = request.get_json()
    if not data or 'monthly_expenses' not in data:
        return jsonify({'error': 'monthly_expenses required'}), 400
    
    monthly_expenses = data['monthly_expenses']
    amounts = [m['amount'] for m in monthly_expenses if m['amount'] > 0]
    
    if len(amounts) < 3:
        return jsonify({
            'forecast': [],
            'historical': monthly_expenses,
            'method': 'insufficient_data',
            'message': 'Need at least 3 months of data for forecasting.',
        })
    
    try:
        # Try Linear Regression with trend
        from sklearn.linear_model import LinearRegression
        import numpy as np
        
        # Prepare data
        X = np.arange(len(amounts)).reshape(-1, 1)
        y = np.array(amounts)
        
        # Fit model
        model = LinearRegression()
        model.fit(X, y)
        
        # Forecast next 3 months
        future_X = np.arange(len(amounts), len(amounts) + 3).reshape(-1, 1)
        predictions = model.predict(future_X)
        predictions = np.maximum(predictions, 0)  # No negative spending
        
        # Also compute moving average
        window = min(3, len(amounts))
        ma_pred = np.mean(amounts[-window:])
        
        # Blend: 60% linear regression + 40% moving average
        blended = [0.6 * p + 0.4 * ma_pred for p in predictions]
        
        from datetime import datetime, date
        now = date.today()
        forecast_months = []
        for i in range(3):
            m = (now.month + i) % 12 + 1
            y_off = now.year + ((now.month + i) // 12)
            forecast_months.append(datetime(y_off, m, 1).strftime('%b %Y'))
        
        forecast_data = [
            {'month': forecast_months[i], 'amount': round(blended[i], 2)}
            for i in range(3)
        ]
        
        # R² score
        y_pred_train = model.predict(X)
        ss_res = np.sum((y - y_pred_train) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return jsonify({
            'forecast': forecast_data,
            'historical': monthly_expenses,
            'method': 'LinearRegression+MovingAverage',
            'r2_score': round(float(r2), 3),
            'trend': 'increasing' if model.coef_[0] > 0 else 'decreasing',
            'monthly_avg': round(float(np.mean(amounts)), 2),
        })
    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        # Ultra simple fallback
        avg = sum(amounts[-3:]) / min(3, len(amounts))
        return jsonify({
            'forecast': [{'month': f'Month {i+1}', 'amount': round(avg, 2)} for i in range(3)],
            'historical': monthly_expenses,
            'method': 'moving_average_fallback',
            'error': str(e),
        })


@app.route('/train-categorizer', methods=['POST'])
def train_categorizer():
    """Train or retrain the expense categorizer."""
    import joblib
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    import json
    
    data = request.get_json()
    training_data = data.get('training_data', [])
    
    # Use provided data + built-in dataset
    built_in = [
        ("Swiggy food order", "Food & Dining"),
        ("Zomato pizza delivery", "Food & Dining"),
        ("Restaurant dinner", "Food & Dining"),
        ("McDonald's burger", "Food & Dining"),
        ("Cafe Coffee Day", "Food & Dining"),
        ("Dominos pizza", "Food & Dining"),
        ("KFC chicken", "Food & Dining"),
        ("Uber ride to office", "Transportation"),
        ("Ola cab airport", "Transportation"),
        ("Metro card recharge", "Transportation"),
        ("Petrol pump fuel", "Transportation"),
        ("Rapido bike ride", "Transportation"),
        ("Bus ticket booking", "Transportation"),
        ("Amazon shopping", "Shopping"),
        ("Flipkart mobile purchase", "Shopping"),
        ("Myntra clothes", "Shopping"),
        ("Meesho order", "Shopping"),
        ("Big Bazaar groceries", "Shopping"),
        ("Ajio fashion", "Shopping"),
        ("Electricity bill payment", "Utilities"),
        ("Airtel internet recharge", "Utilities"),
        ("Jio mobile bill", "Utilities"),
        ("Water bill", "Utilities"),
        ("Gas cylinder", "Utilities"),
        ("DTH recharge", "Utilities"),
        ("Apollo pharmacy medicine", "Healthcare"),
        ("Doctor consultation fee", "Healthcare"),
        ("Max hospital OPD", "Healthcare"),
        ("Diagnostic lab test", "Healthcare"),
        ("Medicine purchase", "Healthcare"),
        ("School fees payment", "Education"),
        ("Udemy course purchase", "Education"),
        ("College tuition fees", "Education"),
        ("Book purchase", "Education"),
        ("Coursera subscription", "Education"),
        ("Netflix subscription", "Entertainment"),
        ("Spotify premium", "Entertainment"),
        ("Amazon Prime", "Entertainment"),
        ("Movie ticket booking", "Entertainment"),
        ("Game purchase", "Entertainment"),
        ("Rent payment", "Housing"),
        ("Society maintenance", "Housing"),
        ("House repair", "Housing"),
        ("Flat deposit", "Housing"),
        ("MakeMyTrip flight", "Travel"),
        ("IRCTC train booking", "Travel"),
        ("Hotel booking", "Travel"),
        ("Airbnb stay", "Travel"),
        ("Cult.fit gym", "Fitness"),
        ("Gym membership", "Fitness"),
        ("Yoga class", "Fitness"),
        ("Swimming fees", "Fitness"),
        ("Bigbasket grocery", "Groceries"),
        ("Blinkit instant delivery", "Groceries"),
        ("Zepto vegetables", "Groceries"),
        ("Dmart shopping", "Groceries"),
        ("Instamart grocery", "Groceries"),
        ("Salary credit", "Income"),
        ("Freelance payment received", "Income"),
        ("Bonus credited", "Income"),
        ("Dividend income", "Income"),
        ("LIC premium", "Insurance"),
        ("Health insurance", "Insurance"),
        ("Groww mutual fund SIP", "Investment"),
        ("Zerodha stocks purchase", "Investment"),
        ("Nykaa cosmetics", "Personal Care"),
        ("Salon haircut", "Personal Care"),
        ("Spa treatment", "Personal Care"),
    ]
    
    all_data = built_in + [(d['text'], d['category']) for d in training_data if 'text' in d and 'category' in d]
    
    texts = [item[0] for item in all_data]
    labels = [item[1] for item in all_data]
    
    le = LabelEncoder()
    y = le.fit_transform(labels)
    
    # TF-IDF + Random Forest
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)
    X = vectorizer.fit_transform(texts)
    
    if len(set(labels)) > 1 and len(texts) > 10:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y if len(set(y)) > 1 else None)
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    report = classification_report(y_test, y_pred, target_names=le.classes_, output_dict=True, zero_division=0)
    
    # Save model
    model_data = {
        'vectorizer': vectorizer,
        'classifier': clf,
        'label_encoder': le,
    }
    model_path = os.path.join(MODEL_DIR, 'categorizer.joblib')
    joblib.dump(model_data, model_path)
    models['categorizer'] = model_data
    
    logger.info(f"Categorizer trained. Accuracy: {accuracy:.3f}")
    
    return jsonify({
        'status': 'success',
        'accuracy': round(accuracy, 3),
        'classes': list(le.classes_),
        'training_samples': len(texts),
        'report': report,
        'model_path': model_path,
    })


if __name__ == '__main__':
    load_models()
    port = int(os.environ.get('ML_SERVICE_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
