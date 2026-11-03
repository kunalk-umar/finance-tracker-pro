"""
Initial model training script.
Run this once to pre-train models before starting the service.
Usage: python train_initial.py
"""
import requests
import json

def train_categorizer():
    print("Training expense categorizer...")
    try:
        resp = requests.post(
            'http://localhost:5001/train-categorizer',
            json={'training_data': []},
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Categorizer trained!")
            print(f"   Accuracy: {data['accuracy']:.1%}")
            print(f"   Classes: {', '.join(data['classes'])}")
            print(f"   Samples: {data['training_samples']}")
        else:
            print(f"❌ Training failed: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the ML service is running: python app.py")

if __name__ == '__main__':
    train_categorizer()
