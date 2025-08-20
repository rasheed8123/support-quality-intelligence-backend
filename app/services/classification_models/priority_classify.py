import joblib
import os

# Get the directory where this module is located
module_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(module_dir, "priority_model.pkl")

priority_model = joblib.load(model_path)

def classify_priority(email_text: str):
    """
    Classify the priority of an email.
    """
    priority = priority_model.predict([email_text])[0]
    return {"priority": priority}