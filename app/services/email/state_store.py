import json
import os
import threading
from typing import Any, Dict, Optional


class StateStore:
    """Simple, threadsafe JSON file store for Gmail history IDs per email address."""

    def __init__(self, file_path: str = "state.json") -> None:
        self.file_path = file_path
        self._lock = threading.Lock()
        if not os.path.exists(self.file_path):
            self._write({})

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        tmp_path = f"{self.file_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, self.file_path)

    def get_last_history_id(self, email_address: str) -> Optional[str]:
        with self._lock:
            data = self._read()
            value = data.get("history", {}).get(email_address)
            return str(value) if value is not None else None

    def set_last_history_id(self, email_address: str, history_id: str) -> None:
        with self._lock:
            data = self._read()
            history_map = data.get("history", {})
            history_map[email_address] = str(history_id)
            data["history"] = history_map
            self._write(data)



