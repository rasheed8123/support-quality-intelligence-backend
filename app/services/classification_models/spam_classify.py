import joblib
import os

# Get the directory where this module is located
module_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(module_dir, "spam_model.pkl")

# Load the spam classification model
spam_model = joblib.load(model_path)

def classify_category(email_text: str):
    """
    Classify the category of an email.
    """
    category = spam_model.predict([email_text])[0]
    return {"category": category}