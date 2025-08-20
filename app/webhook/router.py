from fastapi import APIRouter, Request, Header
import logging
from app.utils.drive_client import build_drive_client
from app.services.rag_pipeline.google_drive.drive_watch import register_changes_watch, stop_watch, fetch_and_process_changes
from app.webhook.gmail import router as gmail_router

log = logging.getLogger(__name__)
router = APIRouter()

# Include Gmail routes
router.include_router(gmail_router, tags=["gmail"])

_drive = None
def drive():
    global _drive
    if _drive is None:
        _drive = build_drive_client()
    return _drive

@router.get("/health")
def health():
    return {"ok": True}

@router.post("/admin/register")
def admin_register():
    """Call this after starting cloudflared & the app, to create the watch."""
    return register_changes_watch(drive())

@router.post("/admin/stop")
def admin_stop():
    stop_watch(drive())
    return {"stopped": True}

@router.post("/webhook/drive")
async def webhook_drive(
    request: Request,
    x_goog_channel_id: str | None = Header(default=None),
    x_goog_resource_state: str | None = Header(default=None),
    x_goog_resource_id: str | None = Header(default=None),
    x_goog_message_number: str | None = Header(default=None),
):
    body = await request.body()
    log.info("webhook headers: chan=%s state=%s res=%s msg#=%s",
             x_goog_channel_id, x_goog_resource_state, x_goog_resource_id, x_goog_message_number)
    if body:
        log.info("webhook body: %s", body.decode("utf-8", errors="ignore"))

    # first call after watch() is often "sync" – safe to ignore for processing
    if (x_goog_resource_state or "").lower() != "sync":
        fetch_and_process_changes(drive())

    # Google only needs a quick 2xx
    return {"ok": True}
