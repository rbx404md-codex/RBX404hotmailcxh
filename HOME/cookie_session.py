import threading
import time
from PROXY.proxy import init_proxies


class CookieStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0
        self.checked = 0
        self.hits = 0        # valid (tiktok) / premium (netflix, chatgpt)
        self.free = 0        # chatgpt free accounts
        self.bad = 0
        self.errors = 0
        self.proxy_err = 0
        self.retries = 0
        self.hits_list: list = []   # (source, result, cookies_dict, content, filename)
        self.free_list: list = []   # chatgpt free: same tuple
        self.bad_list: list = []    # source names
        self.error_list: list = []  # source names


class CookieCheckerSession:
    def __init__(self, user_id: int, service: str, cookie_files: list):
        """
        service: 'netflix' | 'chatgpt' | 'tiktok'
        cookie_files: list of (source_name, cookies_dict)
        """
        self.user_id = user_id
        self.service = service
        self.cookie_files = cookie_files
        self.stats = CookieStats()
        self.stats.total = len(cookie_files)
        self.proxies = init_proxies()
        self.stop_event = threading.Event()
        self.finished = False
        self.started = time.time()
        self.msg_id = None
        self.chat_id = None
        self.executor = None
        self.futures = []
        self.seen: set = set()
        self.seen_lock = threading.Lock()
