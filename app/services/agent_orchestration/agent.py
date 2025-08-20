from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Dict, Any

# ---- Define state ----
class EmailState(TypedDict):
    email: Dict[str, Any]
    type: Optional[str]
    priority: Optional[str]
    category: Optional[str]
    outbound_scores: Optional[Dict[str, Any]]
    db_record: Optional[Dict[str, Any]]

# ---- Classifier functions (stubs, replace with ML/LLM calls) ----
def spam_classify(state: EmailState):
    email = state["email"]
    # Dummy logic
    label = "spam" if "unsubscribe" in email["body"].lower() else "query"
    state["type"] = label
    print("inside spam_classify")
    return state

def priority_classify(state: EmailState):
    if state["type"] in ["query","information"]:
        state["priority"] = "high" if "urgent" in state["email"]["body"].lower() else "low"
    print("inside priority_classify")
    return state

def category_classification(state: EmailState):
    body = state["email"]["body"].lower()
    if "payment" in body:
        state["category"] = "payment_failure"
    elif "refund" in body:
        state["category"] = "refund_access"
    elif "access" in body:
        state["category"] = "access_issue"
    elif "certificate" in body:
        state["category"] = "certificate_question"
    elif "thank" in body:
        state["category"] = "thank_you_notes"
    else:
        state["category"] = "others"
    print("inside category_classification")
    return state

def outbound_analysis(state: EmailState):
    email = state["email"]
    # Stub for RAG-based QA checks
    state["outbound_scores"] = {
        "factual_accuracy": 0.92,
        "guideline_compliance": 0.88,
        "completeness": 0.9,
        "tone": 0.95,
    }
    print("inside outbound_analysis")
    return state

def write_inbound_to_db(state: EmailState):
    state["db_record"] = {
        "type": state["type"],
        "priority": state["priority"],
        "category": state["category"],
    }
    print("Inbound stored:", state["db_record"])
    print("inside write_inbound_to_db")
    return state

def write_outbound_to_db(state: EmailState):
    state["db_record"] = state["outbound_scores"]
    print("Outbound stored:", state["db_record"])
    print("inside write_outbound_to_db")
    return state

# ---- Build graph ----
workflow = StateGraph(EmailState)

# Entry point
def route_email(state: EmailState):
    if state["email"]["label"] == "inbox":
        return {"next": "spam_classify"}
    else:
        return {"next": "outbound_analysis"}

workflow.add_node("route_email", route_email)
workflow.add_node("spam_classify", spam_classify)
workflow.add_node("priority_classify", priority_classify)
workflow.add_node("category_classification", category_classification)
workflow.add_node("write_inbound", write_inbound_to_db)

workflow.add_node("outbound_analysis", outbound_analysis)
workflow.add_node("write_outbound", write_outbound_to_db)

# Inbound path
workflow.add_edge("spam_classify", "priority_classify")
workflow.add_edge("priority_classify", "category_classification")
workflow.add_edge("category_classification", "write_inbound")
workflow.add_edge("write_inbound", END)

# Outbound path
workflow.add_edge("outbound_analysis", "write_outbound")
workflow.add_edge("write_outbound", END)

workflow.set_entry_point("route_email")

app = workflow.compile()

# ---- Example run ----
sample_inbound = {
    "label": "inbox",
    "body": "Urgent refund request for my course payment",
}
result = app.invoke({"email": sample_inbound})

sample_outbound = {
    "label": "sent",
    "body": "Here is your refund information. Please check.",
}
result = app.invoke({"email": sample_outbound})
