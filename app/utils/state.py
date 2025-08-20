import json
from pathlib import Path
from typing import Any, Dict

def get_state_file() -> Path:
    """Get state file path with fallback locations"""
    # Priority order for state file
    locations = [
        "config/state.json",  # Recommended location
        "state.json"          # Legacy root location
    ]

    for location in locations:
        path = Path(location)
        if path.exists():
            return path

    # Default to config directory (will be created if needed)
    return Path("config/state.json")

def load_state() -> Dict[str, Any]:
    state_file = get_state_file()
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {
        "start_page_token": None,
        "channel": {"id": None, "resourceId": None, "expiration": None}
    }

def save_state(state: Dict[str, Any]) -> None:
    state_file = get_state_file()
    # Ensure parent directory exists
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
