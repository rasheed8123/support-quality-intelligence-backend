import joblib
import os
from pathlib import Path

# Get the directory of this file
current_dir = Path(__file__).parent
model_path = current_dir / "priority_model.pkl"

# Load model with error handling
try:
    priority_model = joblib.load(model_path)
except FileNotFoundError:
    print(f"Warning: Priority model not found at {model_path}. Using dummy model.")
    priority_model = None
def classify_priority(email_text: str):
    """
    Classify the priority of an email.
    """
    if priority_model is None:
        # Return default priority when model is not available
        return {"priority": "medium"}

    try:
        priority = priority_model.predict([email_text])[0]
        return {"priority": priority}
    except Exception as e:
        print(f"Error in priority classification: {e}")
        return {"priority": "medium"}