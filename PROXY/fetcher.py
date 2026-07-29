"""
RBX404 PROXY FETCHER v1.1 - Advanced Urban VPN Proxy Collector
"""
import sys
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

try:
    import httpx
except ImportError:
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx

MAX_WORKERS = 50
TIMEOUT = 30

def _httpx_proxy_kwargs(proxy_url: str) -> dict:
    """Return correct httpx proxy kwarg for any httpx version."""
    if not proxy_url:
        return {}
    try:
        import httpx as _hx
        ver = tuple(int(x) for x in _hx.__version__.split(".")[:2])
        if ver >= (0, 23):
            return {"proxy": proxy_url}
        else:
            return {"proxies": {"http://": proxy_url, "https://": proxy_url}}
    except Exception:
        return {"proxy": proxy_url}

HEADERS_VPN = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "chrome-extension://eppiocemhmnlbhjplcgkofciegomcon",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}

_CHROME_VERSIONS = [120, 122, 124, 126, 128, 130, 132, 134, 136, 138, 140, 142, 144]
_BROWSERS = ["CHROME", "EDGE", "BRAVE"]
_PLATFORMS = [
    "Windows NT 10.0; Win64; x64",
    "Windows NT 11.0; Win64; x64",
    "Macintosh; Intel Mac OS X 13_6",
    "Macintosh; Intel Mac OS X 14_2",
    "X11; Linux x86_64",
]

def _random_headers() -> dict:
    v = random.choice(_CHROME_VERSIONS)
    plat = random.choice(_PLATFORMS)
    ua = (f"Mozilla/5.0 ({plat}) AppleWebKit/537.36 "
          f"(KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36")
    return {**HEADERS_VPN, "user-agent": ua}

def _random_browser() -> str:
    return random.choice(_BROWSERS)


def _fetch_single_credential(client: httpx.Client, access_token: str, server: Dict, country_code: str) -> Optional[Dict]:
    signature = server.get("signature")
    if not signature:
        return None
    headers_cred = {**HEADERS_VPN, "authorization": f"Bearer {access_token}"}
    try:
        r = client.post(
            "https://api-pro.falais.com/rest/v1/security/tokens/accs-proxy",
            json={"type": "accs-proxy", "clientApp": {"name": "URBAN_VPN_BROWSER_EXTENSION"}, "signature": signature},
            headers=headers_cred, timeout=15)
        r.raise_for_status()
        proxy_data = r.json()
        ip = server.get("address", {}).get("primary", {}).get("ip", "")
        port = server.get("address", {}).get("primary", {}).get("port", "")
        user = proxy_data["value"]
        passwd = proxy_data["value"]
        if ip and port:
            return {
                "url": f"http://{user}:{passwd}@{ip}:{port}",
                "ip": ip,
                "port": str(port),
                "user": user,
                "pass": passwd,
                "country": country_code,
            }
    except:
        pass
    return None


def _proxy_str_to_url(proxy_str: str) -> Optional[str]:
    try:
        parts = proxy_str.strip().split(":")
        if len(parts) == 4:
            h, po, u, pw = parts
            return f"http://{u}:{pw}@{h}:{po}"
        if "@" in proxy_str:
            return f"http://{proxy_str}" if not proxy_str.startswith("http") else proxy_str
        if len(parts) == 2:
            return f"http://{proxy_str}"
    except:
        pass
    return None


def fetch_urban_vpn_proxies(progress_callback=None, auth_proxy: str = None) -> List[Dict]:
    new_proxies = []
    proxy_url = _proxy_str_to_url(auth_proxy) if auth_proxy else None

    try:
        if proxy_url:
            auth_timeout = httpx.Timeout(connect=6, read=10, write=6, pool=5)
        else:
            auth_timeout = httpx.Timeout(TIMEOUT)
        auth_client_kwargs = {"timeout": auth_timeout, "verify": False}
        if proxy_url:
            auth_client_kwargs.update(_httpx_proxy_kwargs(proxy_url))

        with httpx.Client(**auth_client_kwargs) as auth_client:
            hdrs = _random_headers()
            browser = _random_browser()

            if progress_callback:
                progress_callback("status", "Getting anonymous token" + (" via proxy..." if proxy_url else "..."))

            r = auth_client.post(
                "https://api-pro.falais.com/rest/v1/registrations/clientApps"
                "/URBAN_VPN_BROWSER_EXTENSION/users/anonymous",
                json={"clientApp": {"name": "URBAN_VPN_BROWSER_EXTENSION", "browser": browser}},
                headers=hdrs)
            r.raise_for_status()
            anon_token = r.json()["value"]

            if progress_callback:
                progress_callback("status", "Getting access token...")

            headers_auth = {**hdrs, "authorization": f"Bearer {anon_token}"}
            r = auth_client.post(
                "https://api-pro.falais.com/rest/v1/security/tokens/accs",
                json={"type": "accs", "clientApp": {"name": "URBAN_VPN_BROWSER_EXTENSION"}},
                headers=headers_auth)
            r.raise_for_status()
            access_token = r.json()["value"]

            if progress_callback:
                progress_callback("status", "Fetching server list...")

            headers_countries = {
                "accept": "application/json",
                "accept-language": "en-US,en;q=0.9",
                "authorization": f"Bearer {access_token}",
                "user-agent": hdrs["user-agent"],
                "x-client-app": "URBAN_VPN_BROWSER_EXTENSION",
            }
            r = auth_client.get("https://stats.falais.com/api/rest/v2/entrypoints/countries",
                                headers=headers_countries)
            r.raise_for_status()
            countries = r.json().get("countries", {}).get("elements", [])

        all_servers = []
        for country in countries:
            cc = country.get("code", {}).get("iso2", "??")
            for server in country.get("servers", {}).get("elements", []):
                all_servers.append((server, cc))

        total_servers = len(all_servers)
        if progress_callback:
            progress_callback("total", total_servers)
            progress_callback("status", f"Fetching {total_servers} servers @ {MAX_WORKERS} threads...")

        fetched_lock = threading.Lock()
        progress_data = {"done": 0, "ok": 0, "fail": 0, "results": []}

        cred_client_kwargs = {"timeout": httpx.Timeout(connect=6, read=15, write=6, pool=5), "verify": False}
        if proxy_url:
            cred_client_kwargs.update(_httpx_proxy_kwargs(proxy_url))
        with httpx.Client(**cred_client_kwargs) as cred_client:
            def fetch_one(args):
                server, cc = args
                result = _fetch_single_credential(cred_client, access_token, server, cc)
                with fetched_lock:
                    progress_data["done"] += 1
                    if result:
                        progress_data["ok"] += 1
                        progress_data["results"].append(result)
                    else:
                        progress_data["fail"] += 1
                    if progress_callback:
                        progress_callback("progress", progress_data["done"], total_servers,
                                         progress_data["ok"], progress_data["fail"])
                return result

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(fetch_one, s) for s in all_servers]
                for future in as_completed(futures):
                    pass

        new_proxies = progress_data["results"]

        if progress_callback:
            progress_callback("complete", len(new_proxies), total_servers,
                              progress_data["ok"], progress_data["fail"])

    except Exception as e:
        if progress_callback:
            progress_callback("error", str(e))
        return []

    return new_proxies


def proxies_to_str_list(proxies: List[Dict]) -> List[str]:
    return [f"{p['ip']}:{p['port']}:{p['user']}:{p['pass']}" for p in proxies]


def save_fetched_proxies(proxies: List[Dict], filepath: str):
    with open(filepath, 'w') as f:
        for p in proxies:
            f.write(f"{p['ip']}:{p['port']}:{p['user']}:{p['pass']}\n")


def get_country_summary(proxies: List[Dict]) -> dict:
    country_count = {}
    for p in proxies:
        cc = p.get("country", "??")
        country_count[cc] = country_count.get(cc, 0) + 1
    return country_count
