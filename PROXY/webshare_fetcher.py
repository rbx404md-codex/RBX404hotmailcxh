"""
Webshare Rotating Proxy Fetcher
Fetches and validates webshare rotating proxies into FILES/proxy.txt
"""
import os
import time
import requests
from typing import List, Optional, Tuple

from CONFIG.config import (
    WEBSHARE_HOST, WEBSHARE_PORT, WEBSHARE_USER, WEBSHARE_PASS,
    WEBSHARE_COUNTRIES, PROXIES_FILE, FILES_DIR, ADMIN_ID
)

_TEST_URL = "https://httpbin.org/ip"
_TIMEOUT  = 12


def _make_proxy_str(user: str) -> str:
    return f"{WEBSHARE_HOST}:{WEBSHARE_PORT}:{user}:{WEBSHARE_PASS}"


def _proxy_dict(user: str) -> dict:
    url = f"http://{user}:{WEBSHARE_PASS}@{WEBSHARE_HOST}:{WEBSHARE_PORT}"
    return {"http": url, "https": url}


def _test_proxy(user: str) -> Tuple[bool, str]:
    """Test a webshare proxy variant. Returns (ok, ip_or_error)."""
    try:
        r = requests.get(_TEST_URL, proxies=_proxy_dict(user),
                         timeout=_TIMEOUT, verify=False)
        if r.status_code == 200:
            ip = r.json().get("origin", "?")
            return True, ip
        return False, f"HTTP {r.status_code}"
    except requests.exceptions.ProxyError as e:
        return False, f"ProxyError: {str(e)[:60]}"
    except Exception as e:
        return False, str(e)[:60]


def _test_own_ip() -> str:
    """Get own IP (no proxy)."""
    try:
        r = requests.get(_TEST_URL, timeout=10)
        return r.json().get("origin", "unknown")
    except:
        return "unknown"


def fetch_webshare_proxies(notify_admin_fn=None) -> Tuple[List[str], bool]:
    """
    Fetch / validate webshare proxies.

    Returns:
        (proxy_list, used_own_ip)
        proxy_list — list of strings in ip:port:user:pass format
        used_own_ip — True if webshare failed and own IP is being used
    """
    os.makedirs(FILES_DIR, exist_ok=True)
    proxies = []

    # Test main rotating proxy
    ok, info = _test_proxy(WEBSHARE_USER)
    if ok:
        proxies.append(_make_proxy_str(WEBSHARE_USER))
        # Add country-specific variants
        for cc in WEBSHARE_COUNTRIES:
            country_user = f"{WEBSHARE_USER}-country-{cc}"
            c_ok, _ = _test_proxy(country_user)
            if c_ok:
                proxies.append(_make_proxy_str(country_user))
        return proxies, False
    else:
        # Webshare failed — use own IP, notify admin
        own_ip = _test_own_ip()
        if notify_admin_fn:
            try:
                notify_admin_fn(
                    f"⚠️ <b>Webshare Proxy Failed!</b>\n"
                    f"<blockquote>❌ Error: <code>{info}</code>\n"
                    f"🌐 Falling back to own IP: <code>{own_ip}</code>\n"
                    f"🕐 Time: <code>{time.strftime('%H:%M:%S')}</code></blockquote>",
                    parse_mode="HTML"
                )
            except:
                pass
        return [], True  # empty list = use own IP


def clear_proxy_file():
    """Clear the main proxy file (called on startup and every 4 batches)."""
    os.makedirs(FILES_DIR, exist_ok=True)
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        f.write("")


def append_proxies_to_file(proxy_list: List[str]):
    """Append new proxies to proxy.txt (do NOT remove existing lines)."""
    if not proxy_list:
        return
    os.makedirs(FILES_DIR, exist_ok=True)
    # Read existing to avoid exact duplicates
    existing = set()
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing.add(line)
    new_lines = [p for p in proxy_list if p not in existing]
    if new_lines:
        with open(PROXIES_FILE, "a", encoding="utf-8") as f:
            for p in new_lines:
                f.write(p + "\n")
