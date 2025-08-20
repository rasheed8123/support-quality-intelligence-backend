import os, uuid, time, logging
from typing import Optional, Dict, Any
from googleapiclient.discovery import Resource
from app.utils.state import load_state, save_state

log = logging.getLogger(__name__)

# In-memory cache to track recently processed files (prevents duplicates)
_processed_files: Dict[str, float] = {}
DEDUP_WINDOW_SECONDS = 30  # Ignore duplicate events within 30 seconds

from app.config import settings

DRIVE_ID = os.getenv("GOOGLE_DRIVE_ID")
SUPPORTS_ALL_DRIVES = os.getenv("SUPPORTS_ALL_DRIVES", "false").lower() == "true"
FOLDER_ID = settings.DRIVE_FOLDER_ID
WEBHOOK_URL = settings.WEBHOOK_PUBLIC_URL

_state = load_state()

def _get_start_page_token(drive: Resource) -> str:
    kwargs = {}
    if DRIVE_ID:
        kwargs = {"driveId": DRIVE_ID, "supportsAllDrives": True}
    resp = drive.changes().getStartPageToken(**kwargs).execute()
    return resp["startPageToken"]

def ensure_start_token(drive: Resource) -> str:
    if not _state.get("start_page_token"):
        _state["start_page_token"] = _get_start_page_token(drive)
        save_state(_state)
    return _state["start_page_token"]

def register_changes_watch(drive: Resource) -> Dict[str, Any]:
    """Create/renew a channel that sends webhooks on any change visible to the SA."""
    token = ensure_start_token(drive)
    body = {
        "id": str(uuid.uuid4()),
        "type": "web_hook",
        "address": WEBHOOK_URL,
        # Optional: set an explicit expiration (ms since epoch). Max ~7 days for changes.watch.
        # "expiration": str(int(time.time()*1000) + 6*60*60*1000)
    }
    kwargs = {"pageToken": token}
    if DRIVE_ID:
        kwargs.update({"driveId": DRIVE_ID, "supportsAllDrives": True})
    resp = drive.changes().watch(body=body, **kwargs).execute()
    log.info("Registered channel: %s", resp)
    _state["channel"] = {
        "id": resp["id"],
        "resourceId": resp["resourceId"],
        "expiration": int(resp.get("expiration", int(time.time()*1000) + 3600*1000))
    }
    save_state(_state)
    return resp

def stop_watch(drive: Resource) -> None:
    ch = _state.get("channel") or {}
    if not ch.get("id") or not ch.get("resourceId"):
        log.warning("No active channel to stop.")
        return
    drive.channels().stop(body={"id": ch["id"], "resourceId": ch["resourceId"]}).execute()
    _state["channel"] = {"id": None, "resourceId": None, "expiration": None}
    save_state(_state)

def _in_target_folder(file_obj: Dict[str, Any]) -> bool:
    if not FOLDER_ID:
        return True  # no filter
    parents = file_obj.get("parents") or []
    return FOLDER_ID in parents

def _is_duplicate_event(file_id: str, file_name: str) -> bool:
    """Check if we've recently processed this file to avoid duplicate processing"""
    current_time = time.time()
    cache_key = f"{file_id}:{file_name}"

    # Clean old entries from cache
    expired_keys = [k for k, timestamp in _processed_files.items()
                   if current_time - timestamp > DEDUP_WINDOW_SECONDS]
    for key in expired_keys:
        del _processed_files[key]

    # Check if this file was recently processed
    if cache_key in _processed_files:
        time_since_last = current_time - _processed_files[cache_key]
        log.info(f"🔄 Duplicate event for {file_name} (last processed {time_since_last:.1f}s ago) - SKIPPING")
        return True

    # Mark this file as processed
    _processed_files[cache_key] = current_time
    return False

def process_file_change(file_obj: Dict[str, Any]) -> None:
    """
    Process a file change event. Replace this with your actual business logic.

    Args:
        file_obj: Google Drive file object with metadata
    """
    file_name = file_obj.get("name")
    file_id = file_obj.get("id")
    mime_type = file_obj.get("mimeType")

    log.info(f"🚀 Processing file: {file_name} (ID: {file_id})")

    # TODO: Replace with your actual processing logic
    # Examples:
    # - Download the file
    # - Analyze content
    # - Send notifications
    # - Update database
    # - Trigger other workflows

    print(f"✅ File processed successfully: {file_name} ({mime_type})")

def fetch_and_process_changes(drive: Resource) -> None:
    """Call after a webhook ping; walks changes since last token and runs your logic."""
    token = ensure_start_token(drive)
    while True:
        params = {
            "pageToken": token,
            "pageSize": 1000,
            "fields": "changes(fileId,removed,file(id,name,mimeType,parents,trashed)),nextPageToken,newStartPageToken"
        }
        if SUPPORTS_ALL_DRIVES:
            params.update({"supportsAllDrives": True, "includeItemsFromAllDrives": True})

        resp = drive.changes().list(**params).execute()

        for ch in resp.get("changes", []):
            if ch.get("removed") or ch.get("file", {}).get("trashed"):
                log.info("🗑️  removed: %s", ch.get("fileId"))
                continue

            f = ch.get("file") or {}
            if not _in_target_folder(f):
                continue

            file_id = f.get("id")
            file_name = f.get("name")

            # Skip duplicate events within the deduplication window
            if _is_duplicate_event(file_id, file_name):
                continue

            # >>> Your workflow here <<<
            log.info("📄 NEW change: %s (%s) mime=%s", file_name, file_id, f.get("mimeType"))
            print(f"🔍 PROCESSING: {file_name} in folder {f.get('parents')}")

            # TODO: Add your actual file processing logic here
            # Example: download/process/analyze/etc.
            process_file_change(f)

        if resp.get("nextPageToken"):
            token = resp["nextPageToken"]
        else:
            # Save the new start token for the next round and exit
            _state["start_page_token"] = resp.get("newStartPageToken", token)
            save_state(_state)
            break


def create_drive_watch(webhook_url: str):
    """Legacy function - use register_changes_watch instead"""
    from app.utils.drive_client import build_drive_client

    service = build_drive_client()

    body = {
        "id": str(uuid.uuid4()),           # must be unique per channel
        "type": "web_hook",
        "address": webhook_url             # e.g. https://<tunnel-url>/webhook/drive
    }

    response = service.changes().watch(body=body).execute()
    print("✅ Drive watch created:", response)
    return response