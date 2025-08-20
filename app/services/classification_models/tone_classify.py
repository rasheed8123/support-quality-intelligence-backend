import requests
import os
from dotenv import load_dotenv
load_dotenv()


API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-mnli"
token = os.getenv("HUGGINGFACE_TOKEN")
headers = {"Authorization": f"Bearer {token}"}  # your token
tone = ["empathetic", "neutral", "dismissive", "frustrated", "urgent", "polite"]
issues = [
    "payment",
    "refund",
    "access issues",
    "course inquiry",
    "certificate",
    "admission",
    "general information",
    "thank you notes",
    "others"
]
def classify_tone(email_text):
    payload = {
        "inputs": email_text,
        "parameters": {
            "candidate_labels": tone
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    return result['labels'][0]


def classify_issue(email_text):
    payload = {
        "inputs": email_text,
        "parameters": {
            "candidate_labels": issues
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    return result['labels'][0]
