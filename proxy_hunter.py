"""
PROXY HUNTER + URBAN VPN FETCHER
- Scrapes HTTP proxies from public sources (300 threads)
- Stops the moment 1 live proxy is found
- Uses that live proxy to fetch Urban VPN proxies
- Every new batch: hunts a fresh live proxy first, then fetches Urban VPN
"""

import os
import sys
import time
import random
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import httpx
except ImportError:
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx

# Import file logger
try:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, _script_dir)
    from HOME.logger import log as file_log
except ImportError:
    def file_log(msg, level="INFO"):
        pass  # Fallback if logger not available

# ── Config ────────────────────────────────────────────────────────────────────
CHECK_THREADS   = 300
SCRAPE_THREADS  = 30
CHECK_TIMEOUT   = 5
URBAN_WORKERS   = 50
URBAN_TIMEOUT   = 30
_BASE           = os.path.dirname(os.path.abspath(__file__))

def _httpx_proxy_kwargs(proxy_url: str) -> dict:
    """Return correct httpx proxy kwarg for any httpx version."""
    if not proxy_url:
        return {}
    try:
        ver = tuple(int(x) for x in httpx.__version__.split(".")[:2])
        if ver >= (0, 23):
            return {"proxy": proxy_url}
        else:
            return {"proxies": {"http://": proxy_url, "https://": proxy_url}}
    except Exception:
        return {"proxy": proxy_url}
PROXY_FILE      = os.path.join(_BASE, "FILES", "proxy.txt")
BATCH_INTERVAL  = 300   # 5 min between batches
CLEAR_EVERY     = 4     # full clear every 4 batches

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://raw.githubusercontent.com/almroot/proxylist/master/list.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http",
]

HEADERS_VPN = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "chrome-extension://eppiocemhmnlbhjplcgkofciegomcon",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}
_CHROME_VERSIONS = [120, 122, 124, 126, 128, 130, 132, 134, 136, 138, 140, 142, 144]
_BROWSERS        = ["CHROME", "EDGE", "BRAVE"]
_PLATFORMS       = [
    "Windows NT 10.0; Win64; x64",
    "Windows NT 11.0; Win64; x64",
    "Macintosh; Intel Mac OS X 13_6",
    "X11; Linux x86_64",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _random_headers():
    v    = random.choice(_CHROME_VERSIONS)
    plat = random.choice(_PLATFORMS)
    ua   = (f"Mozilla/5.0 ({plat}) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36")
    return {**HEADERS_VPN, "user-agent": ua}

def _random_browser():
    return random.choice(_BROWSERS)

def _p(line):
    """Parse 'ip:port' or 'ip:port:user:pass' → requests proxy dict."""
    line = line.strip()
    if not line:
        return None
    try:
        parts = line.split(":")
        if len(parts) == 4:
            h, po, u, pw = parts
            url = f"http://{u}:{pw}@{h}:{po}"
            return {"http": url, "https": url, "_raw": line}
        if len(parts) == 2:
            url = f"http://{h}:{po}" if False else f"http://{line}"
            return {"http": url, "https": url, "_raw": line}
    except:
        pass
    return None

def _proxy_str_to_url(s):
    """Convert proxy string to URL for httpx."""
    try:
        parts = s.strip().split(":")
        if len(parts) == 4:
            h, po, u, pw = parts
            return f"http://{u}:{pw}@{h}:{po}"
        if "@" in s:
            return f"http://{s}" if not s.startswith("http") else s
        if len(parts) == 2:
            return f"http://{s}"
    except:
        pass
    return None


# ── Step 1: Scrape ────────────────────────────────────────────────────────────

def _scrape_one(url):
    try:
        r = requests.get(url, timeout=10)
        lines = r.text.strip().splitlines()
        # geonode returns JSON
        if "geonode" in url:
            import json
            data = json.loads(r.text)
            lines = [f"{x['ip']}:{x['port']}" for x in data.get("data", [])]
        proxies = [l.strip() for l in lines if ":" in l.strip()]
        print(f"  ✓ {len(proxies):>5} proxies  ←  {url[:65]}")
        return proxies
    except Exception as e:
        print(f"  ✗ FAIL  ←  {url[:65]}  ({e})")
        return []

def scrape_all():
    print("\n[SCRAPING] Fetching from sources using 30 threads...")
    all_proxies = []
    with ThreadPoolExecutor(max_workers=SCRAPE_THREADS) as ex:
        futures = {ex.submit(_scrape_one, u): u for u in PROXY_SOURCES}
        for f in as_completed(futures):
            all_proxies.extend(f.result())
    unique = list(dict.fromkeys(all_proxies))  # dedup, preserve order
    print(f"\n[SCRAPING] Total unique proxies: {len(unique):,}\n")
    return unique


# ── Step 2: Check — find live proxies (can find multiple) ────────────────────

_live_proxies   = []
_live_lock      = threading.Lock()
_stop_event     = threading.Event()
_checked        = 0
_check_lock     = threading.Lock()

def _check_one(proxy_str):
    global _checked
    if _stop_event.is_set():
        return None

    pd = _p(proxy_str)
    if not pd:
        return None

    try:
        r = requests.get(
            "https://httpbin.org/ip",
            proxies={"http": pd["http"], "https": pd["https"]},
            timeout=(3, CHECK_TIMEOUT),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"},
        )
        if r.status_code == 200:
            with _live_lock:
                if proxy_str not in _live_proxies:
                    _live_proxies.append(proxy_str)
                    count = len(_live_proxies)
                    print(f"\n  [LIVE #{count}] {proxy_str}")
                    if count >= 4:
                        _stop_event.set()
                    with _check_lock:
                        _checked += 1
                    return proxy_str
    except:
        pass

    with _check_lock:
        _checked += 1
        if _checked % 50 == 0 and not _stop_event.is_set():
            print(f"  [CHECK] Checked: {_checked} | Working so far: {len(_live_proxies)}")
    return None

def find_live_proxies(proxy_list, max_live=4):
    """Find up to max_live working proxies, stops immediately when reached."""
    global _live_proxies, _checked
    _live_proxies = []
    _checked      = 0
    _stop_event.clear()

    print(f"[CHECKING] Scanning with {CHECK_THREADS} threads — stops at {max_live} live...\n")
    with ThreadPoolExecutor(max_workers=CHECK_THREADS) as ex:
        futures = [ex.submit(_check_one, p) for p in proxy_list]
        for f in as_completed(futures):
            if len(_live_proxies) >= max_live:
                _stop_event.set()
                for fut in futures:
                    fut.cancel()
                break

    print(f"\n[DONE] Found {len(_live_proxies)} live proxies (checked ~{_checked})")
    return _live_proxies[:]


# ── Step 3: Urban VPN fetch using that proxy ─────────────────────────────────

def _fetch_single_credential(client, access_token, server, country_code):
    signature = server.get("signature")
    if not signature:
        return None
    headers_cred = {**HEADERS_VPN, "authorization": f"Bearer {access_token}"}
    try:
        r = client.post(
            "https://api-pro.falais.com/rest/v1/security/tokens/accs-proxy",
            json={
                "type": "accs-proxy",
                "clientApp": {"name": "URBAN_VPN_BROWSER_EXTENSION"},
                "signature": signature,
            },
            headers=headers_cred, timeout=15,
        )
        r.raise_for_status()
        proxy_data = r.json()
        ip   = server.get("address", {}).get("primary", {}).get("ip", "")
        port = server.get("address", {}).get("primary", {}).get("port", "")
        user = proxy_data["value"]
        pw   = proxy_data["value"]
        if ip and port:
            return f"{ip}:{port}:{user}:{pw}"
    except:
        pass
    return None


def fetch_urban_vpn(auth_proxy_str):
    proxy_url = _proxy_str_to_url(auth_proxy_str) if auth_proxy_str else None
    print(f"\n[URBAN VPN] Using proxy: {auth_proxy_str or 'none (direct)'}")

    try:
        if proxy_url:
            auth_timeout = httpx.Timeout(connect=6, read=10, write=6, pool=5)
        else:
            auth_timeout = httpx.Timeout(URBAN_TIMEOUT)
        auth_kwargs = {"timeout": auth_timeout, "verify": False}
        if proxy_url:
            auth_kwargs.update(_httpx_proxy_kwargs(proxy_url))

        with httpx.Client(**auth_kwargs) as ac:
            hdrs    = _random_headers()
            browser = _random_browser()

            print("[URBAN VPN] Getting anonymous token...")
            r = ac.post(
                "https://api-pro.falais.com/rest/v1/registrations/clientApps"
                "/URBAN_VPN_BROWSER_EXTENSION/users/anonymous",
                json={"clientApp": {"name": "URBAN_VPN_BROWSER_EXTENSION", "browser": browser}},
                headers=hdrs,
            )
            r.raise_for_status()
            anon_token = r.json()["value"]

            print("[URBAN VPN] Getting access token...")
            r = ac.post(
                "https://api-pro.falais.com/rest/v1/security/tokens/accs",
                json={"type": "accs", "clientApp": {"name": "URBAN_VPN_BROWSER_EXTENSION"}},
                headers={**hdrs, "authorization": f"Bearer {anon_token}"},
            )
            r.raise_for_status()
            access_token = r.json()["value"]

            print("[URBAN VPN] Fetching server list...")
            r = ac.get(
                "https://stats.falais.com/api/rest/v2/entrypoints/countries",
                headers={
                    "accept": "application/json",
                    "accept-language": "en-US,en;q=0.9",
                    "authorization": f"Bearer {access_token}",
                    "user-agent": hdrs["user-agent"],
                    "x-client-app": "URBAN_VPN_BROWSER_EXTENSION",
                },
            )
            r.raise_for_status()
            countries = r.json().get("countries", {}).get("elements", [])

        all_servers = []
        for country in countries:
            cc = country.get("code", {}).get("iso2", "??")
            for srv in country.get("servers", {}).get("elements", []):
                all_servers.append((srv, cc))

        total = len(all_servers)
        print(f"[URBAN VPN] Fetching credentials for {total} servers ({URBAN_WORKERS} threads)...")

        results  = []
        done     = 0
        ok       = 0
        lock     = threading.Lock()

        cred_kwargs = {"timeout": httpx.Timeout(connect=6, read=15, write=6, pool=5), "verify": False}
        if proxy_url:
            cred_kwargs.update(_httpx_proxy_kwargs(proxy_url))
        with httpx.Client(**cred_kwargs) as cc:
            def _one(args):
                nonlocal done, ok
                srv, country = args
                res = _fetch_single_credential(cc, access_token, srv, country)
                with lock:
                    done += 1
                    if res:
                        ok += 1
                        results.append(res)
                    if done % 50 == 0 or done == total:
                        print(f"  [URBAN] {done}/{total} done | OK: {ok}")
                return res

            with ThreadPoolExecutor(max_workers=URBAN_WORKERS) as ex:
                futs = [ex.submit(_one, s) for s in all_servers]
                for _ in as_completed(futs):
                    pass

        print(f"\n[URBAN VPN] Done — {ok} proxies fetched out of {total} servers.")
        return results

    except Exception as e:
        import traceback
        print(f"[URBAN VPN] ERROR: {e}")
        print(f"[URBAN VPN] Traceback: {traceback.format_exc()}")
        return []


# ── Save proxies ──────────────────────────────────────────────────────────────

def save_proxies(proxy_list, clear=False):
    os.makedirs("FILES", exist_ok=True)
    mode = "w" if clear else "a"
    existing = set()
    if not clear and os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r") as f:
            existing = set(l.strip() for l in f if l.strip())
    new = [p for p in proxy_list if p not in existing]
    if new:
        with open(PROXY_FILE, mode) as f:
            for p in new:
                f.write(p + "\n")
    print(f"[SAVE] {'Cleared and wrote' if clear else 'Appended'} {len(new)} proxies → {PROXY_FILE}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("   PROXY HUNTER + URBAN VPN FETCHER")
    print("=" * 60)

    batch_num = 0

    while True:
        clear = (batch_num % CLEAR_EVERY == 0)
        print(f"\n{'='*60}")
        print(f"  BATCH #{batch_num + 1}  {'[FULL CLEAR + FRESH FETCH]' if clear else '[APPEND]'}")
        print(f"{'='*60}")

        # 1. Scrape public proxies
        raw_list = scrape_all()

        if not raw_list:
            print("[WARNING] No proxies scraped, retrying in 60s...")
            time.sleep(60)
            continue

        # 2. Find up to 4 live proxies
        live_list = find_live_proxies(raw_list, max_live=4)

        if not live_list:
            print("[WARNING] No live proxy found. Retrying batch in 60s...")
            time.sleep(60)
            continue

        # 3. Try each live proxy until Urban VPN fetch succeeds
        urban_proxies = []
        # Try up to 20 times: 1-14 with live proxy, 15-16 with direct, 17-20 with live if possible
        max_attempts = 20
        print(f"\n[ATTEMPT] Will try up to {max_attempts} times...")

        for attempt in range(1, max_attempts + 1):
            if urban_proxies:
                break

            # Attempt 15 and 16 are direct
            use_proxy = (attempt < 15 or attempt > 16)
            
            # Select a live proxy if we need one
            live_proxy = None
            if use_proxy:
                live_proxy = random.choice(live_list)
                print(f"\n[TRY #{attempt}/{max_attempts}] Using live proxy: {live_proxy}")
            else:
                print(f"\n[TRY #{attempt}/{max_attempts}] Using own IP (Direct)...")
            
            urban_proxies = fetch_urban_vpn(live_proxy if use_proxy else None)

        # 4. Save to file
        if urban_proxies:
            save_proxies(urban_proxies, clear=clear)
            file_log(f"BATCH #{batch_num + 1}: SUCCESS - {len(urban_proxies)} proxies fetched", "INFO")
            batch_num += 1  # Only increment on success
        else:
            print(f"\n[WARNING] ALL {max_attempts} live proxies + direct failed!")
            file_log(f"BATCH #{batch_num + 1}: FAILED - All {max_attempts} proxies failed", "ERROR")
            print("[RETRY] Rescraping and retrying immediately without sleeping...")
            time.sleep(10)  # Short delay before retry
            continue


if __name__ == "__main__":
    run()
