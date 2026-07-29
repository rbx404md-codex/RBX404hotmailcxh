import os
import random
import threading
import requests
from CONFIG.config import PROXIES_FILE, ADMIN_PROXIES_FILE, BUILTIN_PROXIES, FILES_DIR


def load_proxies_from_file():
    """Load auto-fetched proxies from proxies.txt only."""
    proxies = []
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    proxies.append(line)
    return proxies


def load_admin_proxies():
    """Load admin-added proxies from admin_proxies.txt only."""
    proxies = []
    if os.path.exists(ADMIN_PROXIES_FILE):
        with open(ADMIN_PROXIES_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    proxies.append(line)
    return proxies


def save_proxies_to_file(proxy_list):
    """Save auto-fetched proxies to FILES/proxy.txt."""
    os.makedirs(FILES_DIR, exist_ok=True)
    with open(PROXIES_FILE, "w", encoding="utf-8") as f:
        for p in proxy_list:
            f.write(p + "\n")


def save_admin_proxies_to_file(proxy_list):
    """Save admin-added proxies to FILES/admin_proxies.txt."""
    os.makedirs(FILES_DIR, exist_ok=True)
    with open(ADMIN_PROXIES_FILE, "w", encoding="utf-8") as f:
        for p in proxy_list:
            f.write(p + "\n")


def init_proxies():
    """Return combined list: auto-fetched + admin-added (deduplicated)."""
    os.makedirs(FILES_DIR, exist_ok=True)
    if not os.path.exists(PROXIES_FILE):
        save_proxies_to_file(BUILTIN_PROXIES)
    fetched = load_proxies_from_file()
    admin = load_admin_proxies()
    # Merge deduplicating (admin proxies first so they're always kept)
    seen = set()
    combined = []
    for p in admin + fetched:
        if p not in seen:
            seen.add(p)
            combined.append(p)
    return combined


def update_global_proxy_pool():
    """Update the global proxy pool in state - called after proxy refresh."""
    try:
        from HOME import state
        new_proxies = init_proxies()
        with state.global_proxy_pool_lock:
            state.global_proxy_pool = new_proxies
        return len(new_proxies)
    except Exception:
        return 0


class ProxyRotator:
    def __init__(self, plist=None, use=True):
        self.lock = threading.Lock()
        self.use = use
        self.proxies = []
        self.idx = 0
        self.fails = {}
        self.mf = 6
        self.use_global_pool = False  # Flag to use dynamic global pool

        raw = plist or []
        if use and not raw:
            # Try to use global pool first
            try:
                from HOME import state
                with state.global_proxy_pool_lock:
                    if state.global_proxy_pool:
                        raw = state.global_proxy_pool[:]
                        self.use_global_pool = True
                    else:
                        raw = BUILTIN_PROXIES[:]
            except Exception:
                raw = BUILTIN_PROXIES[:]

        for r in raw:
            p = self._p(r.strip())
            if p:
                self.proxies.append(p)
        if self.proxies:
            random.shuffle(self.proxies)

    def _p(self, r):
        if not r:
            return None
        try:
            if r.count(":") == 3 and "@" not in r:
                parts = r.split(":")
                h, po, u, pw = parts[0], parts[1], parts[2], parts[3]
                url = f"http://{u}:{pw}@{h}:{po}"
                return {"http": url, "https": url, "_r": r}
            if "@" in r:
                return {"http": f"http://{r}", "https": f"http://{r}", "_r": r}
            if r.count(":") == 1:
                return {"http": f"http://{r}", "https": f"http://{r}", "_r": r}
        except:
            pass
        return None

    def refresh_from_global_pool(self):
        """Refresh proxy list from global pool - called when proxies are updated."""
        if not self.use_global_pool:
            return False

        try:
            from HOME import state
            with state.global_proxy_pool_lock:
                if not state.global_proxy_pool:
                    return False
                raw = state.global_proxy_pool[:]

            new_proxies = []
            for r in raw:
                p = self._p(r.strip())
                if p:
                    new_proxies.append(p)

            if new_proxies:
                with self.lock:
                    # Keep current index position relative to pool size
                    old_size = len(self.proxies)
                    if old_size > 0:
                        relative_pos = self.idx % old_size
                        new_idx = int((relative_pos / old_size) * len(new_proxies))
                    else:
                        new_idx = 0

                    self.proxies = new_proxies
                    random.shuffle(self.proxies)
                    self.idx = new_idx
                    # Clear fail counts for fresh start
                    self.fails.clear()
                return True
        except Exception:
            pass
        return False

    def get(self):
        if not self.use or not self.proxies:
            return None
        with self.lock:
            for _ in range(len(self.proxies)):
                p = self.proxies[self.idx % len(self.proxies)]
                self.idx += 1
                if self.fails.get(p["_r"], 0) < self.mf:
                    return {"http": p["http"], "https": p["https"]}
            self.fails.clear()
            p = self.proxies[self.idx % len(self.proxies)]
            self.idx += 1
            return {"http": p["http"], "https": p["https"]}

    def ok(self, px):
        if not px:
            return
        with self.lock:
            for p in self.proxies:
                if p["http"] == px.get("http"):
                    self.fails[p["_r"]] = 0
                    break

    def fail(self, px):
        if not px:
            return
        with self.lock:
            for p in self.proxies:
                if p["http"] == px.get("http"):
                    self.fails[p["_r"]] = self.fails.get(p["_r"], 0) + 1
                    break

    def total(self):
        return len(self.proxies)


def test_single_proxy(proxy_str):
    pr = ProxyRotator([proxy_str], True)
    px = pr.get()
    if not px:
        return False
    try:
        r = requests.get("https://httpbin.org/ip", proxies=px, timeout=10)
        return r.status_code == 200
    except:
        return False
