"""
Simple file logger - logs all messages to a rotating log file.
"""
import os
import time
import threading
from datetime import datetime

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_BASE, "LOGS")
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB max per log file
_lock = threading.Lock()


def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _rotate_if_needed():
    """If log file is too big, archive it."""
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = os.path.join(LOG_DIR, f"bot_{ts}.log")
        try:
            os.rename(LOG_FILE, archive)
        except Exception:
            pass


def log(message: str, level: str = "INFO"):
    """Append a timestamped log line to the log file."""
    _ensure_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}\n"
    with _lock:
        _rotate_if_needed()
        try:
            with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
                f.write(line)
        except Exception:
            pass


def get_last_minutes(minutes: int = 5) -> str:
    """Return log lines from the last N minutes."""
    _ensure_dir()
    if not os.path.exists(LOG_FILE):
        return "No logs found."
    cutoff = time.time() - (minutes * 60)
    lines = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                # Parse timestamp from [YYYY-MM-DD HH:MM:SS]
                if raw_line.startswith("[") and len(raw_line) > 20:
                    try:
                        ts_str = raw_line[1:20]
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp()
                        if ts >= cutoff:
                            lines.append(raw_line)
                    except ValueError:
                        lines.append(raw_line)  # include unparsed lines
                else:
                    lines.append(raw_line)
    except Exception as e:
        return f"Error reading logs: {e}"
    return "\n".join(lines) if lines else f"No logs in the last {minutes} minutes."


def get_log_file_path() -> str:
    return LOG_FILE
