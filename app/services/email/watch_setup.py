import sys
from config import load_settings
from gmail_client import GmailClient
from state_store import StateStore


def main() -> int:
    settings = load_settings()

    if not settings.gmail_topic_name:
        print("GMAIL_TOPIC_NAME is required to start watch", file=sys.stderr)
        return 2

    client = GmailClient(
        credentials_path=settings.google_credentials_path,
        delegated_subject=settings.gmail_impersonate_email,
    )

    result = client.start_watch(
        topic_name=settings.gmail_topic_name,
        label_ids=settings.gmail_label_ids,
        label_filter_action=settings.gmail_label_filter_action,
    )

    history_id = str(result.get("historyId"))
    print(f"Watch started. Initial historyId: {history_id}")

    # Persist baseline historyId for the impersonated email
    email_address = settings.gmail_impersonate_email or "me"
    StateStore(settings.state_file_path).set_last_history_id(email_address, history_id)
    print("Baseline historyId saved to state store.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



