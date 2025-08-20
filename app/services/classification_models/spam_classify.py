import joblib
from pathlib import Path

# Get the directory of this file
current_dir = Path(__file__).parent
model_path = current_dir / "spam_model.pkl"

# Load model with error handling
try:
    spam_model = joblib.load(model_path)
except FileNotFoundError:
    print(f"Warning: Spam model not found at {model_path}. Using dummy model.")
    spam_model = None

def classify_category(email_text: str):
    """
    Classify the category of an email.
    """
    if spam_model is None:
        # Return default category when model is not available
        return {"category": "general"}

    try:
        category = spam_model.predict([email_text])[0]
        return {"category": category}
    except Exception as e:
        print(f"Error in category classification: {e}")
        return {"category": "general"}