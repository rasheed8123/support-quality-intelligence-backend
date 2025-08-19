import joblib
# Load the tone classification model
tone_model = joblib.load("spam_model.pkl")
def classify_category(email_text: str):
    """
    Classify the category of an email.
    """
    category = tone_model.predict([email_text])[0]
    return {"category": category}