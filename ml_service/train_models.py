"""
Direct model training script.
Trains TF-IDF + Random Forest Classifier for transaction categorization
and tests Isolation Forest & Forecasting algorithms.
Saves model directly to ml_service/models/categorizer.joblib.
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

DATASET = [
    # Food & Dining
    ("Swiggy food order", "Food & Dining"),
    ("Zomato pizza delivery", "Food & Dining"),
    ("Restaurant dinner with friends", "Food & Dining"),
    ("McDonald's burger meal", "Food & Dining"),
    ("Cafe Coffee Day cappuccino", "Food & Dining"),
    ("Dominos pizza cheese burst", "Food & Dining"),
    ("KFC fried chicken bucket", "Food & Dining"),
    ("Starbucks coffee latte", "Food & Dining"),
    ("Subway sandwich combo", "Food & Dining"),
    ("Burger King whopper", "Food & Dining"),
    ("Haldiram snacks sweets", "Food & Dining"),
    ("Bikanervala thali lunch", "Food & Dining"),
    ("Chai Point tea and samosa", "Food & Dining"),
    ("Barbeque Nation buffet", "Food & Dining"),
    ("Pizza Hut garlic bread", "Food & Dining"),
    ("Breakfast at local dhaba", "Food & Dining"),
    ("Office cafeteria lunch", "Food & Dining"),
    ("Biryani Blues hyderabadi biryani", "Food & Dining"),

    # Transportation
    ("Uber ride to office", "Transportation"),
    ("Ola cab airport drop", "Transportation"),
    ("Metro card smart recharge", "Transportation"),
    ("Petrol pump fuel refill", "Transportation"),
    ("HP Petrol diesel fill", "Transportation"),
    ("Indian Oil petrol", "Transportation"),
    ("Rapido bike taxi ride", "Transportation"),
    ("Bus ticket reservation", "Transportation"),
    ("Auto rickshaw fare cash", "Transportation"),
    ("Toll plaza Fastag recharge", "Transportation"),
    ("Parking fee mall", "Transportation"),
    ("BluSmart EV cab ride", "Transportation"),
    ("Train local pass renewal", "Transportation"),

    # Shopping
    ("Amazon India electronics order", "Shopping"),
    ("Flipkart mobile smartphone purchase", "Shopping"),
    ("Myntra casual shirt jeans", "Shopping"),
    ("Meesho online clothing order", "Shopping"),
    ("Ajio shoes sneakers", "Shopping"),
    ("Zara jacket purchase", "Shopping"),
    ("H&M cotton t-shirt", "Shopping"),
    ("Nike sports running shoes", "Shopping"),
    ("Croma laptop accessories", "Shopping"),
    ("Reliance Digital headphones", "Shopping"),
    ("Decathlon sports gym gear", "Shopping"),
    ("Shoppers Stop perfume", "Shopping"),
    ("Ikea study desk furniture", "Shopping"),
    ("Nykaa fashion cosmetics", "Shopping"),

    # Utilities
    ("Electricity bill payment BSES", "Utilities"),
    ("Tata Power electricity bill", "Utilities"),
    ("Airtel broadband fiber wifi bill", "Utilities"),
    ("Jio prepaid mobile recharge 5G", "Utilities"),
    ("Vodafone Idea postpaid bill", "Utilities"),
    ("Indane LPG gas cylinder refill", "Utilities"),
    ("Bharat Gas booking online", "Utilities"),
    ("Delhi Jal Board water bill", "Utilities"),
    ("Tata Play DTH tv recharge", "Utilities"),
    ("Piped natural gas bill IGL", "Utilities"),
    ("Municipal corporation house tax", "Utilities"),

    # Healthcare
    ("Apollo pharmacy medicine purchase", "Healthcare"),
    ("Doctor consultation fee clinic", "Healthcare"),
    ("Max healthcare OPD consultation", "Healthcare"),
    ("Fortis hospital diagnostic test", "Healthcare"),
    ("Dr Lal PathLabs blood test", "Healthcare"),
    ("PharmEasy medicine online order", "Healthcare"),
    ("1mg prescription drugs", "Healthcare"),
    ("Dental clinic root canal cleaning", "Healthcare"),
    ("Eye specialist glasses lens", "Healthcare"),
    ("Health checkup full body package", "Healthcare"),

    # Education
    ("Udemy python data science course", "Education"),
    ("Coursera machine learning certification", "Education"),
    ("School annual term fees", "Education"),
    ("College tuition semester fee", "Education"),
    ("Book purchase Oxford bookstore", "Education"),
    ("Kindle ebook technical reading", "Education"),
    ("Coaching institute test series fee", "Education"),
    ("EdX computer science course", "Education"),

    # Entertainment
    ("Netflix 4K UHD monthly subscription", "Entertainment"),
    ("Spotify Premium family plan music", "Entertainment"),
    ("Amazon Prime video membership", "Entertainment"),
    ("Disney Hotstar cricket stream", "Entertainment"),
    ("BookMyShow IMAX movie tickets", "Entertainment"),
    ("PVR Cinemas popcorn coke tickets", "Entertainment"),
    ("PlayStation Network game purchase", "Entertainment"),
    ("Steam games weekend sale", "Entertainment"),
    ("YouTube Premium music streaming", "Entertainment"),

    # Housing
    ("Monthly apartment house rent", "Housing"),
    ("Society maintenance monthly charges", "Housing"),
    ("Apartment security deposit landlord", "Housing"),
    ("Plumber repair bathroom leakage", "Housing"),
    ("Electrician home wiring repair", "Housing"),
    ("Urban Company home deep cleaning", "Housing"),

    # Groceries
    ("Bigbasket monthly grocery staples", "Groceries"),
    ("Blinkit 10-min instant grocery delivery", "Groceries"),
    ("Zepto fresh milk bread eggs", "Groceries"),
    ("Dmart supermarket monthly shopping", "Groceries"),
    ("Instamart snacks biscuits soda", "Groceries"),
    ("Nature's Basket imported cheese fruits", "Groceries"),
    ("Local vegetable fruit market mandi", "Groceries"),
    ("Reliance Fresh vegetable flour oil", "Groceries"),

    # Fitness
    ("Cult.fit gym workout membership", "Fitness"),
    ("Anytime Fitness annual gym pass", "Fitness"),
    ("Yoga class monthly fee studio", "Fitness"),
    ("Swimming pool access membership", "Fitness"),
    ("Whey protein powder supplement", "Fitness"),

    # Travel
    ("MakeMyTrip round trip flight ticket", "Travel"),
    ("IRCTC train ticket booking AC chair", "Travel"),
    ("Goibibo hotel room booking resort", "Travel"),
    ("Airbnb holiday villa stay", "Travel"),
    ("IndiGo flight Delhi to Mumbai", "Travel"),
    ("Uber outstation cab weekend trip", "Travel"),

    # Income
    ("Monthly company salary direct credit", "Income"),
    ("Client freelance payment invoice", "Income"),
    ("Quarterly annual bonus credited", "Income"),
    ("Stock dividend payout credited", "Income"),
    ("Bank savings account interest", "Income"),
    ("Refund credited back to card", "Income"),
]

def train_and_save():
    print("🚀 Training Expense Categorizer (Random Forest Classifier)...")
    texts = [item[0] for item in DATASET]
    labels = [item[1] for item in DATASET]

    le = LabelEncoder()
    y = le.fit_transform(labels)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)
    X = vectorizer.fit_transform(texts)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    print(f"✅ Model Performance:")
    print(f"   Accuracy:  {acc:.4f} ({acc*100:.1f}%)")
    print(f"   Precision: {prec:.4f}")
    print(f"   Recall:    {rec:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   Classes ({len(le.classes_)}): {', '.join(le.classes_)}")

    model_data = {
        'vectorizer': vectorizer,
        'classifier': clf,
        'label_encoder': le,
        'metrics': {
            'accuracy': float(acc),
            'precision': float(prec),
            'recall': float(rec),
            'f1_score': float(f1),
            'training_samples': len(texts)
        }
    }

    model_path = os.path.join(MODEL_DIR, 'categorizer.joblib')
    joblib.dump(model_data, model_path)
    print(f"💾 Saved model to: {model_path}")

    # Register in Django DB if available
    try:
        import sys
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
        sys.path.insert(0, backend_path)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()
        from analytics.models import MLModel
        
        MLModel.objects.update_or_create(
            name='Expense Categorizer (Random Forest)',
            model_type='categorizer',
            defaults={
                'version': '1.0',
                'file_path': model_path,
                'accuracy': round(acc * 100, 2),
                'precision': round(prec * 100, 2),
                'recall': round(rec * 100, 2),
                'f1_score': round(f1, 4),
                'training_samples': len(texts),
                'is_active': True,
            }
        )
        print("✅ Registered MLModel record in database.")
    except Exception as e:
        print(f"ℹ Note: Django model registration deferred: {e}")

if __name__ == '__main__':
    train_and_save()

