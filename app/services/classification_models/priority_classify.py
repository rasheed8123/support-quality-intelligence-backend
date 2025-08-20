import joblib
priority_model = joblib.load("priority_model.pkl")
def classify_priority(email_text: str):
    """
    Classify the priority of an email.
    """
    priority = priority_model.predict([email_text])[0]
    return {"priority": priority}